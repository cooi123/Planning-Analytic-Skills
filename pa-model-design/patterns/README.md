# Pattern registry

Each file is one modelling pattern. `pa-model-design` **lists this directory** and
reads what matches. It does not carry a hard-coded list. Adding a pattern means
adding a file here and nothing else.

## Contract

Every pattern file starts with this frontmatter:

```yaml
---
id: <kebab-case-id>
applies_when: <one sentence stating the condition that selects this pattern>
conflicts_with: [<id>, ...]   # optional
---
```

and contains these sections, in order:

| Section | Contains |
|---|---|
| `## Structure` | Cubes, dimensions, and how data flows between them |
| `## Rules` | Rule statements with scope, version-neutral |
| `## Feeders` | The feeder for every leaf rule, and why that source |
| `## Failure modes` | What goes wrong in practice, and the symptom it presents |

## Rules for pattern authors

- Use `{Placeholder}` for every name. A pattern containing a literal cube or element
  name from some past project is a bug, because it will be copied verbatim into a design.
- Reference config as `{{config.x.y}}` rather than restating a project's choice.
- Do not pin a PA version.
- `## Failure modes` is not optional. A pattern that only shows the happy path teaches
  the reader nothing they could not guess.

## Selection

When two patterns both match, the more specific `applies_when` wins, and the design
spec records why. When none match, design from
`../references/dimensional-modelling.md` and add the new pattern here.
