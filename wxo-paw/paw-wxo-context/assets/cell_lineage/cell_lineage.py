"""Turn a PAW selected cell into a full TM1 coordinate, and build the MDX that
walks its hierarchy (parents, ancestors, children, siblings, leaves, attributes).

PAW's data_context gives a selected cell only as rowIndex/colIndex plus a value.
The dimensions and fixed members live in the widget's MDX:

    WITH ...                      calculated members (no hierarchy behind them)
    SELECT <set> ON 0,            column dimension(s)
           <set> ON 1             row dimension(s)
    FROM [cube]
    WHERE ( ... )                 slicer: one fixed member per dimension

This module parses that MDX deterministically. Row and column *labels* still come
from executing the MDX (execute_mdx_and_get_view) and resolving the indexes with
resolve_selected_cells, because row sets are usually dynamic (DESCENDANTS, EXCEPT,
ORDER) and cannot be read from the text.

Pure functions first, @tool wrappers at the bottom.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# [Dim].[Hier].[Member] -- brackets inside names are escaped as ]]
_NAME = r"\[((?:[^\]]|\]\])+)\]"
_MEMBER3_RE = re.compile(_NAME + r"\." + _NAME + r"\." + _NAME)
_AXIS_RE = re.compile(r"\bON\s+(\d+|COLUMNS|ROWS)\b", re.IGNORECASE)
_WITH_MEMBER_RE = re.compile(r"\bMEMBER\s+" + _NAME + r"\." + _NAME + r"\." + _NAME + r"\s+AS\b", re.IGNORECASE)


def _unescape(name: str) -> str:
    return name.replace("]]", "]")


def _q(name: str) -> str:
    """Quote a TM1 object name for MDX."""
    return "[" + name.replace("]", "]]") + "]"


def _member_ref(dim: str, hier: str, member: str) -> str:
    return f"{_q(dim)}.{_q(hier)}.{_q(member)}"


def _depth_map(text: str) -> List[int]:
    """Bracket/brace/paren nesting depth at each character, ignoring [...] names."""
    depths, depth, in_name = [], 0, False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_name:
            if ch == "]" and i + 1 < len(text) and text[i + 1] == "]":
                depths += [depth, depth]
                i += 2
                continue
            if ch == "]":
                in_name = False
        elif ch == "[":
            in_name = True
        elif ch in "({":
            depth += 1
        elif ch in ")}":
            depth -= 1
        depths.append(depth)
        i += 1
    return depths


def _find_top_level(text: str, pattern: "re.Pattern[str]") -> List[re.Match]:
    depths = _depth_map(text)
    return [m for m in pattern.finditer(text) if depths[m.start()] == 0]


def split_mdx(mdx: str) -> Dict[str, Any]:
    """Split a SELECT statement into WITH, axes, cube and WHERE parts."""
    text = mdx.strip()

    select_hits = _find_top_level(text, re.compile(r"\bSELECT\b", re.IGNORECASE))
    if not select_hits:
        raise ValueError("No top-level SELECT found")
    select_at = select_hits[0]
    with_text = text[: select_at.start()].strip()

    from_hits = [m for m in _find_top_level(text, re.compile(r"\bFROM\b", re.IGNORECASE)) if m.start() > select_at.end()]
    if not from_hits:
        raise ValueError("No top-level FROM found")
    from_at = from_hits[0]
    select_body = text[select_at.end(): from_at.start()]

    where_hits = [m for m in _find_top_level(text, re.compile(r"\bWHERE\b", re.IGNORECASE)) if m.start() > from_at.end()]
    if where_hits:
        cube_text = text[from_at.end(): where_hits[0].start()]
        where_text = text[where_hits[0].end():].strip()
    else:
        cube_text = text[from_at.end():]
        where_text = ""
    cube_match = re.search(_NAME, cube_text)
    cube = _unescape(cube_match.group(1)) if cube_match else cube_text.strip()

    axes: Dict[int, str] = {}
    start = 0
    for m in _find_top_level(select_body, _AXIS_RE):
        label = m.group(1).upper()
        index = {"COLUMNS": 0, "ROWS": 1}.get(label, None)
        index = int(label) if index is None else index
        axes[index] = select_body[start: m.start()].strip().lstrip(",").strip()
        start = m.end()

    return {"with": with_text, "axes": axes, "cube": cube, "where": where_text}


def member_refs(text: str) -> List[Tuple[str, str, str]]:
    return [tuple(_unescape(g) for g in m.groups()) for m in _MEMBER3_RE.finditer(text)]


def calculated_members(with_text: str) -> List[Tuple[str, str, str]]:
    return [tuple(_unescape(g) for g in m.groups()) for m in _WITH_MEMBER_RE.finditer(with_text)]


def axis_dimensions(axis_text: str) -> List[Tuple[str, str]]:
    """Ordered, unique (dimension, hierarchy) pairs referenced on an axis.

    Members referenced only inside a value expression (e.g. the measure in
    ORDER(..., [cube].([Version].[Var %]), BASC)) are excluded when they belong
    to a different dimension than the set being ordered -- best effort: a
    dimension counts for the axis when it appears inside DESCENDANTS/EXCEPT/
    member lists, which in practice means 'all dims referenced, minus dims that
    only appear after a [cube]. prefix'.
    """
    cleaned = re.sub(_NAME + r"\.\(", "(", axis_text)  # drop "[cube].(" prefixes
    value_exprs = [m.group(m.lastindex) for m in re.finditer(_NAME + r"\.\(([^)]*)\)", axis_text)]
    value_only = {(d, h) for expr in value_exprs for d, h, _ in member_refs(expr)}
    seen: List[Tuple[str, str]] = []
    for d, h, _ in member_refs(cleaned):
        if (d, h) not in seen:
            seen.append((d, h))
    in_set = [(d, h) for d, h in seen if (d, h) not in value_only]
    return in_set or seen


def slicer(where_text: str) -> Dict[str, Tuple[str, str]]:
    """WHERE clause -> {dimension: (hierarchy, member)}."""
    return {d: (h, m) for d, h, m in member_refs(where_text)}


def describe_view(mdx: str) -> Dict[str, Any]:
    """Structure of a widget's MDX: cube, axis dimensions, slicer, calc members."""
    parts = split_mdx(mdx)
    calcs = calculated_members(parts["with"])
    axes = {}
    for idx, text in sorted(parts["axes"].items()):
        dims = axis_dimensions(text)
        literal = [m for d, h, m in member_refs(text)]
        dynamic = bool(re.search(r"\b(DESCENDANTS|EXCEPT|ORDER|FILTER|TM1SUBSETALL|TM1FILTERBYLEVEL|DRILLDOWNMEMBER|CHILDREN|TOPCOUNT|BOTTOMCOUNT|HEAD|TAIL|DISTINCT|GENERATE)\b", text, re.IGNORECASE))
        axes[idx] = {
            "dimensions": [{"dimension": d, "hierarchy": h} for d, h in dims],
            "nested": len(dims) > 1,
            "members_readable_from_text": not dynamic,
            "literal_members": literal if not dynamic else None,
            "sorted_by_value": bool(re.search(r"\bORDER\s*\(", text, re.IGNORECASE)),
        }
    return {
        "cube": parts["cube"],
        "axes": axes,
        "slicer": [{"dimension": d, "hierarchy": h, "member": m} for d, (h, m) in slicer(parts["where"]).items()],
        "calculated_members": [{"dimension": d, "hierarchy": h, "member": m} for d, h, m in calcs],
    }


def cell_coordinates(mdx: str, row_labels: List[str], col_labels: List[str]) -> Dict[str, Any]:
    """Full coordinate of a resolved cell.

    row_labels / col_labels: the member name(s) on each axis for this cell, in
    nesting order, as returned by resolve_selected_cells (one per dimension
    when axes are nested).
    """
    view = describe_view(mdx)
    calc_names = {(c["dimension"], c["member"]) for c in view["calculated_members"]}
    coords: List[Dict[str, Any]] = []

    def add_axis(idx: int, labels: List[str]) -> None:
        dims = view["axes"].get(idx, {}).get("dimensions", [])
        if len(labels) != len(dims):
            raise ValueError(
                f"Axis {idx} has {len(dims)} dimension(s) {[d['dimension'] for d in dims]} "
                f"but {len(labels)} label(s) were given"
            )
        for d, label in zip(dims, labels):
            coords.append({
                "dimension": d["dimension"], "hierarchy": d["hierarchy"], "member": label,
                "source": f"axis {idx}",
                "calculated": (d["dimension"], label) in calc_names,
            })

    add_axis(0, col_labels)
    add_axis(1, row_labels)
    for s in view["slicer"]:
        coords.append({**s, "source": "slicer", "calculated": False})
    return {
        "cube": view["cube"],
        "coordinates": coords,
        "note": "Dimensions of the cube not listed here are at their default member. "
                "Compare against get_cube_dimensions to find them.",
    }


def lineage_mdx(cube: str, coordinates: List[Dict[str, Any]], dimension: str) -> Dict[str, str]:
    """MDX queries that walk one coordinate's hierarchy, holding every other
    coordinate fixed so each returned row carries the matching cube value."""
    target = next((c for c in coordinates if c["dimension"] == dimension), None)
    if target is None:
        raise ValueError(f"{dimension} is not one of this cell's coordinates")
    if target.get("calculated"):
        raise ValueError(f"{target['member']} is a calculated member (WITH MEMBER); it has no hierarchy")

    others = [c for c in coordinates if c["dimension"] != dimension]
    if not others:
        raise ValueError("Need at least one other coordinate to put on axis 0")
    col = others[0]
    where = others[1:]
    col_set = "{" + _member_ref(col["dimension"], col["hierarchy"], col["member"]) + "}"
    where_clause = (" WHERE (" + ", ".join(_member_ref(c["dimension"], c["hierarchy"], c["member"]) for c in where) + ")") if where else ""
    m = _member_ref(target["dimension"], target["hierarchy"], target["member"])
    hier = f"{_q(target['dimension'])}.{_q(target['hierarchy'])}"
    frm = f" FROM {_q(cube)}"

    def q(row_set: str) -> str:
        return f"SELECT {col_set} ON 0, {row_set} ON 1{frm}{where_clause}"

    attr_cube = "}ElementAttributes_" + target["dimension"]
    return {
        "rollup_path": q("{ASCENDANTS(" + m + ")}"),
        "all_direct_parents": q(
            "{FILTER(TM1SUBSETALL(" + hier + "), COUNT(INTERSECT(" + hier
            + ".CURRENTMEMBER.CHILDREN, {" + m + "})) > 0)}"
        ),
        "children": q("{" + m + ".CHILDREN}"),
        "siblings": q("{" + m + ".SIBLINGS}"),
        "leaf_descendants": q("{TM1FILTERBYLEVEL(DESCENDANTS(" + m + "), 0)}"),
        "share_of_parent": q(
            "{" + m + ", " + m + ".PARENT}"
        ),
        "attributes": f"SELECT {{TM1SUBSETALL({_q(attr_cube)}.{_q(attr_cube)})}} ON 0, "
                      f"{{{_q(target['dimension'])}.{_q(target['dimension'])}.{_q(target['member'])}}} ON 1 "
                      f"FROM {_q(attr_cube)}",
    }


# --------------------------------------------------------------------------
# watsonx Orchestrate tool wrappers
# --------------------------------------------------------------------------
try:
    from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
except ImportError:  # allows local testing without the ADK
    def tool(*_a, **_k):
        def wrap(f):
            return f
        return wrap if not (_a and callable(_a[0])) else _a[0]

    class ToolPermission:  # type: ignore
        READ_ONLY = None


@tool(permission=ToolPermission.READ_ONLY)
def describe_selected_view(mdx: str) -> str:
    """Describe the structure of a PAW widget's MDX: which dimensions sit on
    columns (axis 0) and rows (axis 1), whether each axis is nested, whether its
    members can be read from the text or need the query executed, whether rows
    are sorted by value, the fixed slicer members (WHERE), and any calculated
    members (WITH MEMBER).

    Args:
        mdx: The mdx string of the cube entry that has the selected cells,
            exactly as it appears in the verified PAW context.

    Returns:
        JSON describing the view.
    """
    try:
        return json.dumps(describe_view(mdx), indent=2)
    except ValueError as exc:
        return f"ERROR: {exc}"


@tool(permission=ToolPermission.READ_ONLY)
def get_selected_cell_coordinates(mdx: str, row_labels: List[str], col_labels: List[str]) -> str:
    """Build the full TM1 coordinate of a selected cell: one member per
    dimension, labelled by where it came from (axis 0, axis 1 or slicer).

    Call only after resolve_selected_cells returned RESOLVED + MATCH for this
    cell, and pass its row and column labels unchanged.

    Args:
        mdx: The same contextual MDX that was executed for resolution.
        row_labels: Row member name(s) for the cell, outermost first.
        col_labels: Column member name(s) for the cell, outermost first.

    Returns:
        JSON with the cube and coordinate list, or an ERROR line.
    """
    try:
        return json.dumps(cell_coordinates(mdx, row_labels, col_labels), indent=2)
    except ValueError as exc:
        return f"ERROR: {exc}"


@tool(permission=ToolPermission.READ_ONLY)
def build_lineage_queries(cube: str, coordinates_json: str, dimension: str) -> str:
    """Build MDX that explores one dimension of a selected cell: its roll-up path
    (ASCENDANTS), every direct parent (handles multiple parents), children,
    siblings, leaf descendants, share of parent, and element attributes. All
    other coordinates are held fixed so each row returns the matching value.

    Run each query with execute_mdx_and_get_view. Do not edit them.

    Args:
        cube: Cube name from get_selected_cell_coordinates.
        coordinates_json: The "coordinates" list from
            get_selected_cell_coordinates, as JSON.
        dimension: The dimension to explore, e.g. "DRP Route".

    Returns:
        JSON map of query name to MDX, or an ERROR line.
    """
    try:
        coords = json.loads(coordinates_json)
        if isinstance(coords, dict):
            coords = coords.get("coordinates", [])
        return json.dumps(lineage_mdx(cube, coords, dimension), indent=2)
    except (ValueError, TypeError) as exc:
        return f"ERROR: {exc}"
