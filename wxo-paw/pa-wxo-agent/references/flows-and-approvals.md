# Writes through Flows: structural approval

Use this for a scenario-write tool or another production write needing approval.
For the wider build, see [agent best practices](agent-best-practices.md).
Evidence comes from `run-scenario-structural-approval-fix.md` and the supplied Flow
files; the later fix supersedes Architecture §6.3's approval-only design.

## Why guidelines are not a safety gate

A hypothetical question triggered a production write without human confirmation.
The model supplied its own “approved” prompt. Stronger guidelines fixed happy
paths but introduced an unsolicited proposal after decline. A changed-value
follow-up then bypassed the Flow again through plain-chat confirmation; only an
incidental Unicode mismatch blocked that write. *(failed live 3 times with guideline-only gating)*

A confirmation-text check proves the values match the supplied text. It cannot
prove a human approved text the model composed for itself. Keep that check as
an independent layer, and remove direct access to the write tool.
*(Approval fix §1–§4, confirmed live)*

## The pattern

Put the registered write tool in a Tool Node inside the approval Flow. Only Yes
has an edge to it. The default/No branch returns a decline without execution.
Exclude the raw write tool from the agent's `tools:`; include the Flow and
`i__get_flow_status_intrinsic_tool__`. *(Approval fix §4, confirmed live)*

Pass the full typed write contract into the Flow. Display the exact proposal and
map that same text to `approved_confirmation_prompt`. In the write tool, check
values and scope against it before writing; read back the result afterward.
Account explicitly for TM1's sparse zero storage. *(Approval fix §4; Architecture §11)*

The skeleton below shortens the source contract to generic fields and renames
nodes. SDK calls follow the supplied structural Flow; this adaptation is
**untested**. Register the matching `apply_scenario_drivers` tool separately with
its own requirements and connections. Its implementation owns the confirmation
check and read-back; they are not implemented by this graph alone.

```python
from pydantic import BaseModel
from ibm_watsonx_orchestrate.flow_builder.flows import END, START, Flow, flow
from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind

class ApprovalInput(BaseModel):
    confirmation_prompt: str
    scenario_version: str
    assumptions: dict[str, float]
    assumption_target: str

class WriteInput(BaseModel):
    scenario_version: str
    assumptions: dict[str, float]
    assumption_target: str
    approved_confirmation_prompt: str

class ApprovalOutput(BaseModel):
    approved: bool
    result: str

@flow(name="scenario_approval", display_name="Scenario Approval",
      description="Approve the exact proposal before execution.",
      input_schema=ApprovalInput, output_schema=ApprovalOutput,
      suppress_agent_summarization=False)
def build_approval(aflow: Flow = None) -> Flow:
    activity = aflow.userflow(name="approval_activity",
                              display_name="Scenario approval required")
    choice = activity.field(
        name="approved", display_name="Approve exact scenario proposal",
        text="{flow.input.confirmation_prompt}",
        direction="input", kind=UserFieldKind.Boolean)
    activity.edge(START, choice)
    activity.edge(choice, END)
    run_node = aflow.tool("apply_scenario_drivers", name="write_execution",
                          display_name="Execute approved scenario",
                          input_schema=WriteInput)
    run_node.map_node_input_with_variable("scenario_version", "input.scenario_version")
    run_node.map_node_input_with_variable("assumptions", "input.assumptions")
    run_node.map_node_input_with_variable("assumption_target", "input.assumption_target")
    run_node.map_node_input_with_variable(
        "approved_confirmation_prompt", "input.confirmation_prompt")
    decline_node = aflow.script(
        script="self.output.result = 'DECLINED: no TM1 write occurred.'",
        name="scenario_declined")
    branch = aflow.conditions(name="approval_branch")
    branch.condition(to_node=run_node,
        expression="flow.approval_activity.approved.output.value == True")
    branch.condition(to_node=decline_node, default=True)
    aflow.edge(START, activity)
    aflow.edge(activity, branch)
    aflow.edge(run_node, END)
    aflow.edge(decline_node, END)
    aflow.map_output("approved", "flow.approval_activity.approved.output.value")
    aflow.map_output("result", "flow.write_execution.output "
        "if flow.approval_activity.approved.output.value == True "
        "else flow.scenario_declined.output.result")
    return aflow
```

After No, stop and ask what the user wants next; do not autonomously fetch data
or propose again. A changed value needs a fresh native approval, never a plain
“Yes/No” sentence. *(Approval fix §2–§4, confirmed live)*

## Flow gotchas

All rows below were found by live execution after compile and import succeeded.
*(Approval fix §4.1 and §5)*

| Gotcha | Use instead |
|---|---|
| A conditions default branch targets END directly | Route through a `script()` node with a normal edge to END |
| `flow.<activity>.<field>.value` silently reads blank and always declines | `flow.<activity>.<field>.output.value`; explicitly test Yes |
| A bare field reference yields a wrapper object | Read its `.output.value`, not the wrapper |
| `map_output` treats `default_value` as Python source | Use one explicit Python ternary; an unquoted sentence is invalid code |
| Short node references fail in live expressions | Tool string: `flow.<node>.output`; script field: `flow.<node>.output.result` |
| Structured output shows a raw preview card | Set `suppress_agent_summarization=False`; independently recheck narrated figures |

The flag removed the card with no observed numeric fidelity loss. Its broader
platform semantics were not documented by the source; do not infer more from the
flag's name. *(Approval fix §5, confirmed live check)*

## Validating a Flow

1. Compile locally and inspect `to_json()` edges, conditions and mappings before
   connecting a write-capable path. *(Approval fix §4.2)*
2. Import a disposable Flow name onto the test analyst. Its agent list must still
   exclude the raw write tool; a successful controlled write then proves the graph
   can invoke it independently. This test adds a write path to that test agent.
   *(Approval fix §4.2, confirmed live)*
3. Reset a test value, independently read it, run No and Yes separately, then query
   TM1 directly after each. Do not trust the agent's success statement.
   *(Approval fix §4.2, confirmed live)*
4. Test “yes, but change the value” while approval is pending, a plain decline,
   and a fresh proposal. Verify exact value, target and narration. Repeat on the
   real agent and in real PAW chat. *(Approval fix §4.2; Context §7)*
5. Only promote after both branches pass. Compile, JSON inspection and tool import
   cannot prove runtime behaviour or the native controls. *(Approval fix §4.1–§4.2)*

## Known open issue

A second approval Flow invocation in the same conversation returned 401 surfaced
as 424, reproduced twice. Both failed safe without a write or fabricated success.
Use a fresh chat per scenario until investigated. A platform token/auth-refresh
cause is **[inferred]**, not verified; the Flow has no local token-refresh logic
to repair. *(Approval fix §7, open)*
