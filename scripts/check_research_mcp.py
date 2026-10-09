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
