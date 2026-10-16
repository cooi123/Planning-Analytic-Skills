import json
import unittest

from ibm_watsonx_orchestrate.agent_builder.tools.types import (
    AgentPreInvokePayload,
    GlobalContext,
    Message,
    PluginContext,
    Role,
    TextContent,
)

from paw_data_context_guard import _guard_data_context


def make_context(value=None, location="state_context"):
    state = {}
    global_state = {}
    parameters = {}
    if location == "state_context":
        state = {"context": {"data_context": value}}
    elif location == "global_direct":
        global_state = {"data_context": value}
    elif location == "parameters_context":
        parameters = {"context": {"data_context": value}}
    plugin_context = PluginContext(
        state=state,
        global_context=GlobalContext(request_id="test", state=global_state),
    )
    payload = AgentPreInvokePayload(
        agent_id="pa-analyst",
        messages=[Message(role=Role.USER, content=TextContent(type="text", text="What am I viewing?"))],
        parameters=parameters,
    )
    return plugin_context, payload


def sample_payload(server="__TM1_SERVER_NAME__", selected_cells=None):
    return {
        "timestamp": "2026-08-24T01:02:03Z",
        "openWidgets": [
            {
                "selectedCubeName": "DRP Route P&L",
                "cubes": [
                    {
                        "cubeName": "DRP Route P&L",
                        "serverName": server,
                        "mdxQuery": {"Mdx": "SELECT ...", "isMdxTruncated": True},
                        "selectedCells": selected_cells or [],
                        "futureField": "tolerated",
                    }
                ],
                "futureWidgetField": 1,
            }
        ],
        "futureTopField": {"also": "tolerated"},
    }


class GuardTests(unittest.TestCase):
    def run_guard(self, value=None, location="state_context"):
        context, payload = make_context(value, location)
        result = _guard_data_context(context, payload)
        return result, context

    def test_absent_context_fails_closed(self):
        result, context = self.run_guard(None)
        self.assertIn('"status":"ABSENT"', result.modified_payload.messages[-1].content.text)
        self.assertEqual(context.state["paw_data_context_status"], "ABSENT")

    def test_valid_object_is_fingerprinted_and_injected(self):
        result, context = self.run_guard(sample_payload(selected_cells=[{"rowIndex": 1, "colIndex": 2, "formattedValue": "17.2%"}]))
        text = result.modified_payload.messages[-1].content.text
        self.assertIn('"status":"VALID"', text)
        self.assertIn('"cube_name":"DRP Route P&L"', text)
        self.assertIn('"formattedValue":"17.2%"', text)
        self.assertNotIn("futureTopField", text)
        self.assertNotIn("futureWidgetField", text)
        self.assertNotIn("futureField", text)
        self.assertIn('"sha256":', text)
        self.assertEqual(context.state["paw_data_context_status"], "VALID")

    def test_valid_json_string_and_alternative_location(self):
        result, _ = self.run_guard(json.dumps(sample_payload()), "parameters_context")
        self.assertIn('"status":"VALID"', result.modified_payload.messages[-1].content.text)
        self.assertIn('"source":"payload.parameters.context.data_context"', result.modified_payload.messages[-1].content.text)

    def test_flattened_or_malformed_shape_is_rejected(self):
        result, _ = self.run_guard({"selectedCubeName": "invented", "selectedCells": []})
        text = result.modified_payload.messages[-1].content.text
        self.assertIn('"status":"INVALID"', text)
        self.assertIn('"observed_shape":', text)
        self.assertIn('"selectedCubeName":{"type":"string"', text)
        self.assertNotIn("invented", text)

    def test_server_mismatch_is_explicit(self):
        result, _ = self.run_guard(sample_payload(server="Another server"), "global_direct")
        text = result.modified_payload.messages[-1].content.text
        self.assertIn('"status":"SERVER_MISMATCH"', text)
        self.assertIn('"Another server"', text)

    def test_asset_metadata_without_widgets_is_not_treated_as_cell_context(self):
        metadata_only = {
            "browserLanguage": "en",
            "timestamp": "2026-08-24T07:29:00.000Z",
            "userInformation": {
                "email": "hidden@example.com",
                "lastLogin": "2026-08-24T00:00Z",
                "openAssetName": "Route Profitability Control Tower",
                "perspective": "pa-plan-contribute",
                "role": "Analyst",
                "username": "hidden-user",
            },
        }
        result, _ = self.run_guard(metadata_only)
        text = result.modified_payload.messages[-1].content.text
        self.assertIn('"status":"METADATA_ONLY"', text)
        self.assertIn('"open_asset_name":"Route Profitability Control Tower"', text)
        self.assertIn('"perspective":"pa-plan-contribute"', text)
        self.assertNotIn("hidden@example.com", text)
        self.assertNotIn("hidden-user", text)

    def test_live_dashboard_object_mapping_is_normalized(self):
        mapped = {
            "browserLanguage": "en",
            "timestamp": "2026-08-24T07:36:00.000Z",
            "selectedCubeName": "DRP Route P&L",
            "selectedWidgetID": "widget-123",
            "openWidgets": {
                "widget-123": {
                    "cubes": {
                        "DRP Route P&L": {
                            "cubeName": "DRP Route P&L",
                            "serverName": "__TM1_SERVER_NAME__",
                            "mdxQuery": {"Mdx": "SELECT ...", "isMdxTruncated": False},
                            "selectedCells": [
                                {"rowIndex": 0, "colIndex": 1, "formattedValue": "126.5M"}
                            ],
                        }
                    }
                }
            },
            "userInformation": {"perspective": "dashboard"},
        }
        result, _ = self.run_guard(mapped)
        text = result.modified_payload.messages[-1].content.text
        self.assertIn('"status":"VALID"', text)
        self.assertIn('"perspective":"dashboard"', text)
        self.assertIn('"selected_widget_id":"widget-123"', text)
        self.assertIn('"selected_cube_name":"DRP Route P&L"', text)
        self.assertIn('"formattedValue":"126.5M"', text)

    def test_live_open_cubes_alias_and_widget_level_selection(self):
        mapped = {
            "timestamp": "2026-08-24T07:40:00.000Z",
            "selectedCubeName": "DRP Route P&L",
            "selectedWidgetID": "widget-456",
            "openWidgets": {
                "widget-456": {
                    "openCubes": [
                        {"cubeName": "DRP Route P&L", "serverName": "__TM1_SERVER_NAME__"},
                        {"cubeName": "DRP Route Operations", "serverName": "__TM1_SERVER_NAME__"},
                    ],
                    "mdxQuery": {"Mdx": "SELECT ...", "isMdxTruncated": True},
                    "selectedCells": [
                        {"rowIndex": 2, "colIndex": 0, "formattedValue": "MEL-SYD"}
                    ],
                }
            },
        }
        result, _ = self.run_guard(mapped)
        text = result.modified_payload.messages[-1].content.text
        self.assertIn('"status":"VALID"', text)
        self.assertIn('"cube_name":"DRP Route P&L"', text)
        self.assertIn('"cube_name":"DRP Route Operations"', text)
        self.assertIn('"is_selected_cube":true', text)
        self.assertIn('"formattedValue":"MEL-SYD"', text)

    def test_live_single_widget_object_with_open_cubes(self):
        direct_widget = {
            "timestamp": "2026-08-24T07:45:00.000Z",
            "openWidgets": {
                "openCubes": [
                    {"cubeName": "DRP Route P&L", "serverName": "__TM1_SERVER_NAME__"},
                    {"cubeName": "DRP Route Operations", "serverName": "__TM1_SERVER_NAME__"},
                ]
            },
        }
        result, _ = self.run_guard(direct_widget)
        text = result.modified_payload.messages[-1].content.text
        self.assertIn('"status":"VALID"', text)
        self.assertIn('"widget_count":1', text)
        self.assertIn('"cube_count":2', text)
        self.assertIn('"is_selected_widget":false', text)
        self.assertIn('"cube_name":"DRP Route P&L"', text)
        self.assertIn('"cube_name":"DRP Route Operations"', text)
        self.assertIn('"is_selected_cube":false', text)

    def test_valid_context_exposes_safe_metadata_but_not_identity(self):
        payload = sample_payload()
        payload["browserLanguage"] = "en"
        payload["userInformation"] = {
            "email": "hidden@example.com",
            "username": "hidden-user",
            "openAssetName": "Route Profitability Control Tower",
            "perspective": "pa-plan-contribute",
            "role": "Analyst",
        }
        result, _ = self.run_guard(payload)
        text = result.modified_payload.messages[-1].content.text
        self.assertIn('"perspective":"pa-plan-contribute"', text)
        self.assertIn('"open_asset_name":"Route Profitability Control Tower"', text)
        self.assertIn('"role":"Analyst"', text)
        self.assertNotIn("hidden@example.com", text)
        self.assertNotIn("hidden-user", text)


if __name__ == "__main__":
    unittest.main()
