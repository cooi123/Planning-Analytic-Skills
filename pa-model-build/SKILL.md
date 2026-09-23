---
name: pa-model-build
description: >-
  Implement an approved IBM Planning Analytics (TM1) design spec on a server,
  creating dimensions, cubes, rules, feeders, and TurboIntegrator processes in
  dependency order, with a review checkpoint at each phase. Invoke explicitly. Use
  for "build the model", "create these cubes", "implement the design spec", "deploy
  the model to dev", or "apply this design". Requires an approved spec from
  pa-model-design and a live connection; it will not infer a design from a
  conversation.
user-invocable: true
disable-model-invocation: true
---

# PA model build

Implement a design spec against a live Planning Analytics server.

> **This skill writes to a server.** It runs only when a person invokes it by name.
> Never start building because a conversation drifted toward implementation. If the
> request was not an explicit instruction to build, stop and ask.

## Step 0. Preconditions

All four must hold. If any fails, stop and report which:

1. **An approved spec exists** at `design/<module>.spec.yaml`. No spec, no build.
   Run `pa-model-design` first. Do not reconstruct a spec from chat history.
2. **Conventions load** from `./pa-conventions.yaml`, `./config/pa-conventions.yaml`,
   or `../config/pa-conventions.yaml`.
3. **A live connection exists** via the MCP server or configured tooling. Never ask
   for credentials. If there is no connection, that is a setup problem for the user
   to resolve.
4. **The target environment is writable.** Resolve it from
   `{{config.environments}}` and refuse any environment with `writable: false`.

## Step 1. Confirm before writing

State, and get explicit agreement on:

- Target environment and database, by name.
- Object counts: how many dimensions, cubes, rules, processes.
- Anything that will be **modified or replaced** rather than created.

That third item is the one that matters. Creating is recoverable. Overwriting a
populated cube or an existing rules file is not. Enumerate every existing object the
build would touch and get a decision on each before the first write.

If the spec carries unresolved `assumptions`, surface them now. Building on an
unconfirmed assumption is how a model gets rebuilt twice.

## Step 2. Build in dependency order

Follow the spec's `build_sequence`. Where it is absent, use:

```
dimensions -> attributes -> cubes -> rules and feeders -> TI processes -> chores -> views -> security
```

Per phase:

1. Create the objects, resolving every name through `{{config.naming}}`.
2. Verify creation before continuing by reading the object back.
3. At a phase with `review_checkpoint: true`, run `pa-model-review` in conformance
   mode and stop on any finding at or above `{{config.review.fail_on}}`.

Never proceed past a failed checkpoint. Each phase depends on the one before, so a
defect carried forward costs more to unwind than to fix in place.

### Rules and feeders

Write the complete rules file in one operation, in required order: `FEEDSTRINGS`
(only if string rules exist), `SKIPCHECK`, rules ordered by the spec's `precedence`,
`FEEDERS`, feeders.

Never write rules without their feeders in the same operation. A cube left with
SKIPCHECK and no feeders reads zeros in every consolidation, and anyone who looks at
it in that window will reasonably conclude the model is broken.

After writing, spot-check a fed consolidation against the sum of its leaves.

### TI processes

Generate from the spec's tab-by-tab logic. Every parameter declared in the spec
becomes a real parameter. Resolving names from literals is a blocking defect
(TI-002), not a shortcut.

Execute each new process once against a scoped test case before wiring it into a
chore.

## Step 3. Verify

Run a full `pa-model-review` in conformance mode against the spec.

Report: objects created, objects modified, checkpoint results, findings, and anything
in the spec **not** built and why.

## Step 4. Record

Update the spec's `deviations` with anything built differently from the design, and
why. A spec that no longer describes the server is worse than no spec, because the
next review will trust it.

## Hard constraints

- **Confirm before every destructive action.** Deleting or overwriting any object with
  data requires its own explicit approval, not blanket approval for the build.
- **Never write to an environment marked `writable: false`.**
- **Never ask for or store credentials**, and never echo a token, key, or connection
  string into output or a file.
- **Never hard-code** a server, database, cube, or file path into generated process
  code. Resolve from parameters or a control cube.
- **Stop on the first blocking checkpoint failure.** Report; do not work around.
- If the spec and the server disagree mid-build, stop and report. Do not reconcile
  silently in either direction.

## Files

| Path | Contains |
|---|---|
| `../pa-model-design/references/design-spec-template.md` | The spec contract this skill consumes |
| `../pa-model-design/references/ti-processes.md` | Tab semantics, parameters, idempotency |
| `../pa-model-review/checks/checks.yaml` | Checkpoint standard |
