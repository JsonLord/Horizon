"""Smoke the real stdio transport without credentials or external news requests."""

import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    async with stdio_client(
        StdioServerParameters(command=sys.executable, args=["-m", "src.mcp.server"])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            required = {
                "hz_run_pipeline",
                "hz_get_run_stage",
                "hz_get_run_summary",
                "hz_submit_research",
                "hz_get_job",
                "hz_list_profiles",
                "hz_get_profile",
                "hz_list_reports",
                "hz_get_report",
                "hz_search_archive",
                "hz_get_changes",
                "hz_register_institution",
                "hz_dispatch_research",
                "hz_get_workflow_run",
                "hz_get_workflow_report",
                "hz_list_workflow_runs",
                "hz_list_github_profiles",
                "hz_list_schedules",
                "hz_get_schedule",
                "hz_create_schedule",
                "hz_update_schedule",
                "hz_pause_schedule",
                "hz_resume_schedule",
                "hz_delete_schedule",
                "hz_get_schedule_runs",
                "hz_propose_research_profile",
                "hz_propose_source",
            }
            assert required <= names, required - names
            result = await session.call_tool("hz_list_profiles", {})
            assert not result.isError
            profiles = json.loads(result.content[0].text)["profiles"]
            assert len(profiles) == 9
            profile = await session.call_tool(
                "hz_get_profile", {"profile_id": "world/global"}
            )
            assert not profile.isError
            blocked = await session.call_tool(
                "hz_dispatch_research",
                {"profile_id": "world/global", "ref": "unapproved-ref"},
            )
            payload = json.loads(blocked.content[0].text)
            assert (
                payload["ok"] is False
                and payload["error"]["code"] == "REF_NOT_AUTHORIZED"
            )
            dispatch_schema = next(
                t.inputSchema for t in tools.tools if t.name == "hz_dispatch_research"
            )
            assert dispatch_schema["properties"]["lookback_hours"]["minimum"] == 1
            assert dispatch_schema["properties"]["lookback_hours"]["maximum"] == 168
            resources = await session.list_resources()
            assert {"horizon://profiles", "horizon://reports"} <= {
                str(r.uri) for r in resources.resources
            }
            print(
                json.dumps(
                    {
                        "ok": True,
                        "tools": len(names),
                        "profiles": len(profiles),
                        "transport": "stdio",
                    }
                )
            )


if __name__ == "__main__":
    asyncio.run(main())
