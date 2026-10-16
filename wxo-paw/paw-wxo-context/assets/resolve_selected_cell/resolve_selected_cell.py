import json
import re
from typing import Any, Dict, List, Optional

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


# Matches a top-level "data": "<escaped JSON string content>" field without
# requiring the REST of the envelope to be valid JSON -- see
# _normalize_source_text's docstring for why this matters.
_DATA_FIELD_RE = re.compile(r'"data"\s*:\s*"((?:\\.|[^"\\])*)"')
_EXPECTED_VALUE_FIELD_RE = re.compile(r'"expected_value"\s*:\s*"((?:\\.|[^"\\])*)"')


def _json_unescape(raw: str) -> Optional[str]:
    """Decode a JSON string's escape sequences (\\n, \\", etc.) in isolation,
    by wrapping it back into a minimal valid JSON string and parsing just
    that -- works even when the surrounding envelope is otherwise broken."""
    try:
        return json.loads('"' + raw + '"')
    except (ValueError, TypeError):
        return None


def _normalize_source_text(text: str) -> "tuple[str, Optional[str]]":
    """Unwrap a raw MCP-tool JSON envelope if present (the same shape
    execute_mdx_and_get_view returns: '{"data": "|  | ... |\\n| ... |", "state":
    "<blob>"}'), so the real markdown table with real newlines is what gets
    parsed -- confirmed live 2026-10-04 that generate_finance_chart needed the
    identical fix for the identical reason. If table_text isn't JSON, or has no
    string "data" field, it is returned completely unchanged.

    Tries strict json.loads first, but falls back to a regex-based extraction
    of just the "data" field (and, if present, "expected_value") when that
    fails -- confirmed live 2026-10-04 that the calling agent reproducing this
    tool's own ~2KB+ envelope (including a large, totally irrelevant base64
    "state" blob) as a string argument is itself failure-prone: a single
    subtle corruption anywhere in that huge blob breaks strict JSON parsing
    of the WHOLE envelope, even though the actual table content ("data") was
    reproduced correctly. The regex fallback only needs the "data" field's
    own escaping to be intact, independent of everything else in the
    envelope -- do not require the full envelope to be strictly valid JSON
    just to reach the one field that is actually needed.

    Also defensively recovers a misplaced expected_value -- confirmed live
    2026-10-04 that the calling agent nested "expected_value" as an extra key
    inside the table_text JSON blob instead of passing it as its own argument,
    which silently skipped the value cross-check entirely (no error, just a
    verification that quietly never ran). Returns (normalized_text,
    recovered_expected_value_or_None) so the caller can fall back to this if
    its own expected_value argument was left empty."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return text, None

    try:
        parsed = json.loads(stripped)
    except (ValueError, TypeError):
        parsed = None

    if isinstance(parsed, dict):
        recovered = parsed.get("expected_value")
        recovered = recovered if isinstance(recovered, str) and recovered.strip() else None
        if isinstance(parsed.get("data"), str) and parsed["data"].strip():
            return parsed["data"], recovered
        return text, recovered

    # Strict parse failed (likely corruption elsewhere in the envelope) --
    # fall back to pulling just the "data" (and "expected_value") fields out
    # with a regex, each independently JSON-unescaped.
    data_match = _DATA_FIELD_RE.search(stripped)
    recovered = None
    expected_match = _EXPECTED_VALUE_FIELD_RE.search(stripped)
    if expected_match:
        recovered = _json_unescape(expected_match.group(1))
        recovered = recovered if recovered and recovered.strip() else None
    if data_match:
        data_text = _json_unescape(data_match.group(1))
        if data_text and data_text.strip():
            return data_text, recovered

    return text, recovered


def _split_row(line: str) -> List[str]:
    """Split one pipe-delimited line into cells, tolerating an optional
    leading/trailing pipe (the GFM-style format execute_mdx_and_get_view
    produces: '|  | Total Revenue | ... |')."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [f.strip() for f in stripped.split("|")]


def _is_separator_row(cells: List[str]) -> bool:
    """A markdown header-separator row ('| - | - | - |') - every cell is empty
    or made up only of '-' characters. Must be excluded before indexing by
    row_index, or every real data row's position would be off by one."""
    return all(not c or set(c) == {"-"} for c in cells)


_MAGNITUDE_SUFFIXES = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
_CURRENCY_SYMBOLS = "$€£¥₹"


def _clean_number(raw: str) -> Optional[float]:
    """Parses either a raw TM1-style number ('79,382,396.00') or a PAW-style
    display value ('79.4M', '17.8%', '$31,709,088', '(19,910,700)') into a
    comparable float. Accounting parentheses and a unicode minus are negative."""
    raw = str(raw).strip()
    if not raw or raw.upper() in {"N/A", "NA"}:
        return None
    cleaned = raw.replace(",", "").replace("%", "").replace("pp", "").replace("−", "-")
    cleaned = "".join(ch for ch in cleaned if ch not in _CURRENCY_SYMBOLS and not ch.isspace())
    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative, cleaned = True, cleaned[1:-1]
    if cleaned.startswith("-") and not cleaned.startswith("--"):
        negative, cleaned = not negative, cleaned[1:]
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    multiplier = 1.0
    if cleaned and cleaned[-1].upper() in _MAGNITUDE_SUFFIXES:
        multiplier = _MAGNITUDE_SUFFIXES[cleaned[-1].upper()]
        cleaned = cleaned[:-1].strip()
    try:
        value = float(cleaned) * multiplier
    except ValueError:
        return None
    return -value if negative else value


def _values_match(expected_raw: str, expected: float, found_raw: str, found: float) -> bool:
    """Equal within display rounding (2%, at least 0.05). When exactly one side
    is a percentage, PAW's '17.8%' and TM1's raw 0.178 are the same value."""
    def close(a: float, b: float) -> bool:
        return abs(a - b) <= max(0.05, abs(a) * 0.02)

    if close(expected, found):
        return True
    expected_pct, found_pct = "%" in expected_raw, "%" in found_raw
    if expected_pct and not found_pct:
        return close(expected, found * 100)
    if found_pct and not expected_pct:
        return close(expected * 100, found)
    return False


def _parse_table(text: str) -> "tuple[Optional[List[str]], Optional[List[List[str]]], Optional[str]]":
    """Shared table parser used by both the single-cell and multi-cell tools.
    Returns (header, data_rows, error_message) -- error_message is None on
    success, in which case header/data_rows are populated."""
    lines = [ln for ln in text.splitlines() if "|" in ln and ln.strip()]
    if len(lines) < 2:
        return None, None, (
            "ERROR: could not find a parseable pipe-delimited table in table_text. "
            "Pass execute_mdx_and_get_view's unmodified output for the selected "
            "cell's own cube entry — do not retype or reconstruct the table."
        )

    header = _split_row(lines[0])
    ncols = len(header)

    data_rows: List[List[str]] = []
    for line in lines[1:]:
        row = _split_row(line)
        if len(row) != ncols:
            continue
        if _is_separator_row(row):
            continue
        data_rows.append(row)

    if not data_rows:
        return None, None, "ERROR: table_text had a header but no usable data rows. Cannot resolve the selected cell."

    return header, data_rows, None


def _resolve_one(
    header: List[str], data_rows: List[List[str]], row_index: int, col_index: int, expected_value: str
) -> Dict[str, Any]:
    """Resolve a single (row_index, col_index) pair against an already-parsed
    table. Returns a dict with status ("resolved", "mismatch", or "error"),
    a human-readable "report" string, and (on success) "row_label"/
    "col_label"/"value" fields."""
    ncols = len(header)

    if row_index < 0 or row_index >= len(data_rows):
        return {
            "status": "error",
            "report": (
                f"ERROR: row_index {row_index} is out of range — this table has "
                f"{len(data_rows)} data row(s) (0 to {len(data_rows) - 1}). The "
                "contextual MDX/table passed does not match the selected cell's "
                "own cube entry — do not guess a row anyway."
            ),
        }

    col_lookup = col_index + 1  # column 0 of header/each row is the row-label cell
    if col_lookup < 1 or col_lookup >= ncols:
        return {
            "status": "error",
            "report": (
                f"ERROR: col_index {col_index} is out of range — this table has "
                f"{ncols - 1} data column(s) (0 to {ncols - 2}). The contextual "
                "MDX/table passed does not match the selected cell's own cube "
                "entry — do not guess a column anyway."
            ),
        }

    row = data_rows[row_index]
    row_label = row[0]
    col_label = header[col_lookup]
    found_value_raw = row[col_lookup]
    found_value_num = _clean_number(found_value_raw)

    base = {
        "row_label": row_label,
        "col_label": col_label,
        "value": found_value_raw,
    }

    lines_out = [
        "RESOLVED — deterministic index lookup (do not re-derive or second-guess this)",
        f"Row label: {row_label}",
        f"Column label: {col_label}",
        f"Value at this position: {found_value_raw}",
    ]

    if expected_value and expected_value.strip():
        expected_num = _clean_number(expected_value)
        if expected_num is None or found_value_num is None:
            lines_out.append(
                f"MATCH CHECK: could not numerically compare expected_value "
                f"'{expected_value}' against found value '{found_value_raw}' — "
                "treat as UNVERIFIED, do not name a route/measure from this cell."
            )
            return {"status": "unverified", "report": "\n".join(lines_out), **base}
        if _values_match(expected_value, expected_num, found_value_raw, found_value_num):
            lines_out.append(f"MATCH CHECK: MATCH — expected '{expected_value}' matches the value found here.")
            return {"status": "resolved", "report": "\n".join(lines_out), **base}
        lines_out.insert(0, "MISMATCH — DO NOT TRUST THIS RESOLUTION")
        lines_out.append(
            f"MATCH CHECK: MISMATCH — expected_value '{expected_value}' does not match "
            f"the value found at row_index={row_index}, col_index={col_index} "
            f"({found_value_raw}). This row/column pair is almost certainly NOT the "
            "cell the user actually selected (stale, truncated, or mismatched MDX). "
            "Do not name a route or measure from this result — tell the user the "
            "selected cell could not be verified instead."
        )
        return {"status": "mismatch", "report": "\n".join(lines_out), **base}

    return {"status": "resolved_unverified", "report": "\n".join(lines_out), **base}


@tool(permission=ToolPermission.READ_ONLY)
def resolve_selected_cell(
    table_text: str,
    row_index: int,
    col_index: int,
    expected_value: str = "",
) -> str:
    """Deterministically resolve a PAW-selected cell's zero-based row/column index against an already-retrieved table, without an LLM counting rows and columns in pasted text itself.

    This exists because that counting step has been confirmed unreliable live,
    multiple times, even with explicit step-by-step instructions to do it
    carefully: it has produced a wrong route name while still sounding
    completely confident, including one case that reached an approved,
    executed production TM1 write against the wrong route. This tool replaces
    that LLM reasoning step with plain Python indexing into the exact same
    table — deterministic, not a guess, every time.

    Always pair this with execute_mdx_and_get_view: first execute the selected
    cell's own non-truncated contextual MDX completely unmodified (never a
    reconstructed or simplified query — a different query's rows may not be
    in the same order), then pass that tool's raw output straight into this
    one along with the selected_cell rowIndex/colIndex exactly as PAW's
    verified context reported them. Do not pre-parse, retype, or summarize
    the table yourself first.

    Args:
        table_text: The raw, unmodified text/output returned by
            execute_mdx_and_get_view for the SAME cube entry the selected
            cell belongs to. This tool also accepts that tool's raw JSON
            envelope directly (it unwraps the "data" field itself), so there
            is no need to extract the table text by hand first — pass
            whatever execute_mdx_and_get_view returned, unmodified.
        row_index: The zero-based selected_cell rowIndex exactly as PAW's
            verified context reported it for this cell. Do not adjust,
            re-derive, or guess this value.
        col_index: The zero-based selected_cell colIndex exactly as PAW's
            verified context reported it for this cell. This refers to the
            first DATA column (e.g. column 0 is the first measure, such as
            "Total Revenue") — this tool accounts for the table's leading
            row-label column internally, do not add an offset yourself.
        expected_value: REQUIRED — not actually optional despite the type
            signature allowing a blank default; this tool returns an ERROR
            if it is left empty, confirmed live 2026-10-04/05 that it was
            repeatedly omitted and the cell got named anyway with no
            cross-check at all. Pass the formattedValue or raw value PAW
            reported for this exact selected cell. This tool independently
            compares it (tolerant of ordinary display rounding) against the
            value actually found at row_index/col_index and reports an
            explicit MATCH or MISMATCH. A MISMATCH means the indexes do not
            actually correspond to this cell (wrong or stale MDX, a
            truncated table, or a reused table from an earlier turn) — the
            resolved row/column name must NOT be trusted or narrated to the
            user in that case; say the cell could not be verified instead of
            naming a route or measure anyway.

    Returns:
        On success: RESOLVED, the row label (e.g. the route), the column
        header (e.g. the P&L line), the raw value found at that position, and
        — when expected_value was supplied — an explicit MATCH or MISMATCH
        verdict comparing them. On failure (table not parseable, index out of
        range, or a MISMATCH), a plain-text ERROR explaining why — do not
        proceed to name a route or measure from this cell in that case.
    """
    if not table_text or not table_text.strip():
        return "ERROR: table_text was empty. Cannot resolve the selected cell."

    text, recovered_expected_value = _normalize_source_text(table_text)
    if (not expected_value or not expected_value.strip()) and recovered_expected_value:
        expected_value = recovered_expected_value

    if not expected_value or not expected_value.strip():
        return (
            "ERROR: expected_value is required and was not supplied (directly or recoverable "
            "from table_text). Confirmed live 2026-10-04/05, repeatedly, that calls without it "
            "went on to name a route with no cross-check at all -- this tool will not resolve a "
            "cell without the one value that can verify the row/column is actually correct. "
            "Call again with expected_value set to the formattedValue/raw value PAW reported "
            "for this exact selected cell."
        )

    header, data_rows, error = _parse_table(text)
    if error:
        return error

    result = _resolve_one(header, data_rows, row_index, col_index, expected_value)
    return result["report"]


@tool(permission=ToolPermission.READ_ONLY)
def resolve_selected_cells(
    table_text: str,
    cells: List[Dict[str, Any]],
) -> str:
    """Deterministically resolve MULTIPLE PAW-selected cells against the same already-retrieved table in a single call, instead of one resolve_selected_cell call per cell.

    Use this whenever more than one cell is selected and belongs to the SAME
    cube entry/MDX (for example: two cells in the same route-comparison
    table, or an Actual cell and a Budget cell in the same Actual-vs-Budget
    row). This exists because having the calling agent orchestrate a
    separate resolve_selected_cell call per cell — a loop — was confirmed
    live 2026-10-04/05, repeatedly, to be unreliable: with 2 or 3 cells
    actually selected, only 1 call was made, or the loop stopped partway
    through, even with explicit step-by-step instructions to continue for
    every cell. The underlying row/column-to-name mapping has never been the
    unreliable part (it has been correct every single time it was actually
    invoked) — getting the agent to reliably make N separate tool calls was.
    This tool removes that risk by doing the whole list in one deterministic
    pass: call execute_mdx_and_get_view ONCE for the shared contextual MDX,
    then call this tool ONCE with every selected cell's rowIndex/colIndex/
    expected_value as one list, instead of calling resolve_selected_cell
    once per cell.

    Args:
        table_text: The raw, unmodified text/output returned by
            execute_mdx_and_get_view for the cube entry all of these cells
            belong to. Same acceptance rules as resolve_selected_cell — pass
            it unmodified, this tool unwraps the JSON envelope itself.
        cells: A list with one entry per selected cell, in the same order
            PAW's context listed them, each a JSON object with exactly these
            keys: "row_index" (int, the cell's zero-based rowIndex exactly as
            context reported it), "col_index" (int, likewise colIndex), and
            "expected_value" (string — the formattedValue/raw value PAW
            reported for THAT specific cell; REQUIRED per entry, same as for
            resolve_selected_cell — an entry missing it returns an ERROR for
            that cell alone rather than resolving it unverified, since it is
            the only thing that can catch a wrong row/column for that
            cell). Example: [{"row_index": 1, "col_index": 0,
            "expected_value": "8,916.0K"}, {"row_index": 1, "col_index": 1,
            "expected_value": "15.4M"}].

    Returns:
        One block per cell, in the same order given, each independently
        showing RESOLVED (row label, column label, value) plus an explicit
        MATCH/MISMATCH verdict, or an ERROR for that specific cell alone — a
        failure resolving one cell never prevents the others from being
        reported. Only narrate a route/measure for a cell whose own block
        shows RESOLVED with MATCH; for any other cell, report its value (and,
        if safely known, its measure) without naming a route.
    """
    if not table_text or not table_text.strip():
        return "ERROR: table_text was empty. Cannot resolve any selected cell."
    if not cells:
        return "ERROR: cells was empty — pass at least one {row_index, col_index, expected_value} entry."

    text, recovered_expected_value = _normalize_source_text(table_text)
    header, data_rows, error = _parse_table(text)
    if error:
        return error

    blocks = []
    for i, cell in enumerate(cells, start=1):
        try:
            row_index = int(cell.get("row_index"))
            col_index = int(cell.get("col_index"))
        except (TypeError, ValueError):
            blocks.append(
                f"Cell {i}: ERROR — row_index/col_index missing or not valid integers in "
                f"this entry ({cell!r}). Do not guess a route/measure for this cell."
            )
            continue
        expected_value = cell.get("expected_value") or ""
        if (not expected_value or not str(expected_value).strip()) and recovered_expected_value:
            expected_value = recovered_expected_value
        if not expected_value or not str(expected_value).strip():
            blocks.append(
                f"Cell {i}: ERROR — expected_value is required and was not supplied for this "
                "entry. This tool will not resolve a cell without the one value that can verify "
                "the row/column is actually correct. Do not guess a route/measure for this cell."
            )
            continue
        result = _resolve_one(header, data_rows, row_index, col_index, str(expected_value))
        blocks.append(f"Cell {i}:\n{result['report']}")

    return "\n\n".join(blocks)
