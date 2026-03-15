import asyncio
import json
from pathlib import Path

import httpx
import yaml

from agent.planner import detect_gaps, generate_skill_file, ingest_skill
from agent.catalog import search_and_select_module
from schemas import CapabilityGap, RobotProfile

SKILLS_DIR = Path("skills")
DEMO_OUTPUT_DIR = Path("demo_output")

# Errors we expect from API calls and parsing
_API_ERRORS = (RuntimeError, httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
_PARSE_ERRORS = (json.JSONDecodeError, yaml.YAMLError, KeyError, TypeError)


def print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def print_capabilities(profile: RobotProfile) -> None:
    caps = [c["id"] for c in profile.capabilities]
    print(f"🤖  Capabilities: {caps}")


async def fill_gap(
    idx: int, total: int, gap: CapabilityGap, profile: RobotProfile,
) -> bool:
    """Search for hardware, generate a skill file, and ingest it for one gap.

    Returns:
        True if the gap was successfully filled, False otherwise.
    """
    print_separator()
    print(f"⚠️  Gap {idx}/{total}: {gap.need} ({gap.priority})")
    print(f"    Reason: {gap.reason}")
    print(f"    Category: {gap.hardware_category}")
    print()

    print("🔍  Searching catalogs...")
    try:
        module = await search_and_select_module(gap, profile)
    except (*_API_ERRORS, *_PARSE_ERRORS) as e:
        print(f"❌  Catalog search failed for {gap.need}: {e}")
        return False
    print(f"🛒  Selected: {module.name} (${module.price:.2f})")
    print(f"    URL: {module.url}")
    print(f"    Rationale: {module.rationale}")
    print()

    print("📝  Generating skill file...")
    try:
        skill_yaml = await generate_skill_file(module, profile, gap)
    except (*_API_ERRORS, *_PARSE_ERRORS) as e:
        print(f"❌  Skill generation failed for {gap.need}: {e}")
        return False

    skill_path = SKILLS_DIR / f"{gap.need}.yaml"
    skill_path.write_text(skill_yaml)
    print(f"    Saved → {skill_path}")
    print()

    try:
        skill = ingest_skill(skill_yaml, profile)
    except (*_PARSE_ERRORS,) as e:
        print(f"❌  Skill ingestion failed for {gap.need}: {e}")
        return False

    tool_names = [t["name"] for t in skill.get("agent_tools", [])]
    print(f"📦  Installed: {skill['skill_id']} → tools: {tool_names}")
    print_capabilities(profile)
    print()
    return True


def print_plan(result: dict) -> None:
    """Print an executable plan from a gap detection result."""
    print("📝  Execution plan:")
    for i, step in enumerate(result.get("plan", []), 1):
        print(f"    {i}. {step}")


async def run_demo(task: str) -> None:
    """Run the full self-expanding robot agent demo loop.

    Args:
        task: Natural language task for the robot to attempt.
    """
    SKILLS_DIR.mkdir(exist_ok=True)
    DEMO_OUTPUT_DIR.mkdir(exist_ok=True)

    profile = RobotProfile()

    print_separator("═")
    print(f"📋  TASK ASSIGNED: {task}")
    print_separator("═")
    print_capabilities(profile)
    print()

    # --- First gap detection ---
    print("🧠  Planning...")
    try:
        result = await detect_gaps(task, profile)
    except (*_API_ERRORS, *_PARSE_ERRORS) as e:
        print(f"❌  Gap detection failed: {e}")
        return

    if result["status"] == "executable":
        print("✅  TASK IS ALREADY EXECUTABLE")
        print_plan(result)
        return

    gaps = result["gaps"]
    print(f"⚠️  Found {len(gaps)} capability gap(s)\n")

    # --- Fill each gap ---
    for idx, gap in enumerate(gaps, 1):
        await fill_gap(idx, len(gaps), gap, profile)

    # --- Retry gap detection ---
    print_separator("═")
    print("🔄  Retrying with updated capabilities...")
    print_capabilities(profile)
    print()

    try:
        result2 = await detect_gaps(task, profile)
    except (*_API_ERRORS, *_PARSE_ERRORS) as e:
        print(f"❌  Retry gap detection failed: {e}")
        print_separator("═")
        return

    if result2["status"] == "executable":
        print("✅  TASK NOW EXECUTABLE")
        print()
        print_plan(result2)
    else:
        remaining = [g.need for g in result2["gaps"]]
        print(f"⚠️  Still missing capabilities: {remaining}")
        print("    (Manual hardware installation required)")

    print_separator("═")


TASKS = [
    "Navigate to the red box on the table, pick it up, and bring it back to the charging station",
    "Patrol the perimeter of the warehouse and report any obstacles",
]

def main() -> None:
    import sys

    task_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if task_index >= len(TASKS):
        print(f"Unknown task index {task_index}. Available: 0, 1")
        sys.exit(1)

    asyncio.run(run_demo(TASKS[task_index]))


if __name__ == "__main__":
    main()
