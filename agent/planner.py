import json
import os

import httpx
import yaml
from dotenv import load_dotenv

from schemas import CapabilityGap, RobotProfile, SelectedModule

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_API_URL = "https://api.studio.nebius.com/v1/chat/completions"


async def nebius_llm_call(
    system: str,
    user: str,
    max_tokens: int = 2048,
    model: str = "Qwen/Qwen3-235B-A22B",
) -> str:
    """Make a single LLM call via Nebius Token Factory.

    Args:
        system: System prompt.
        user: User message.
        max_tokens: Maximum tokens in the response.
        model: Model identifier on Nebius.

    Returns:
        The model's response text.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            NEBIUS_API_URL,
            headers={"Authorization": f"Bearer {NEBIUS_API_KEY}"},
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Nebius API error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def nebius_vision_call(image_b64: str, prompt: str) -> str:
    """Call vision model — Nebius Qwen2-VL primary, OpenRouter fallback."""
    if NEBIUS_API_KEY:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                NEBIUS_API_URL,
                headers={"Authorization": f"Bearer {NEBIUS_API_KEY}"},
                json={
                    "model": "Qwen/Qwen2-VL-72B-Instruct",
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        {"type": "text", "text": prompt},
                    ]}],
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
    # Fallback to OpenRouter with vision model
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "anthropic/claude-sonnet-4",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": prompt},
                ]}],
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Vision API error {resp.status_code}: {resp.text}")
        return resp.json()["choices"][0]["message"]["content"]


async def _openrouter_llm_call(system: str, user: str, max_tokens: int = 2048) -> str:
    """Make a single LLM call via OpenRouter (fallback provider)."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "anthropic/claude-sonnet-4",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter API error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def llm_call(system: str, user: str, max_tokens: int = 2048) -> str:
    """Make an LLM call — tries Nebius first, falls back to OpenRouter.

    Args:
        system: System prompt.
        user: User message.
        max_tokens: Maximum tokens in the response.

    Returns:
        The model's response text.
    """
    if NEBIUS_API_KEY:
        try:
            return await nebius_llm_call(system, user, max_tokens)
        except Exception:
            pass
    return await _openrouter_llm_call(system, user, max_tokens)


def _strip_fences(raw: str) -> str:
    return (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```yaml")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )


async def detect_gaps(task: str, profile: RobotProfile) -> dict:
    """Detect capability gaps for a given task.

    Args:
        task: Natural language task description.
        profile: Current robot capability profile.

    Returns:
        Either {"status": "executable", "plan": [...]} or
        {"status": "capability_gap", "gaps": [CapabilityGap, ...]}.
    """
    caps_summary = json.dumps(profile.capabilities, indent=2)

    system = (
        "You are a robot task planner. Given a task and a robot's current capabilities, "
        "determine if the robot can execute the task or if it has capability gaps.\n\n"
        "Output ONLY valid JSON — no markdown, no explanation, no code fences.\n\n"
        "If the robot CAN execute the task with its current capabilities, output:\n"
        '{"status": "executable", "plan": ["step1", "step2", ...]}\n\n'
        "If the robot is MISSING capabilities, output:\n"
        '{"status": "capability_gap", "gaps": [\n'
        '  {"need": "depth_perception", "reason": "...", "hardware_category": "stereo camera", "priority": "critical"},\n'
        "  ...\n"
        "]}\n\n"
        "Priority must be 'critical' or 'nice_to_have'.\n"
        "hardware_category should be a specific, searchable hardware type (e.g. 'stereo camera', 'lidar', 'robotic gripper')."
    )

    user = (
        f"Task: {task}\n\n"
        f"Current robot capabilities:\n{caps_summary}"
    )

    raw = await llm_call(system, user)
    data = json.loads(_strip_fences(raw))

    if data.get("status") == "capability_gap":
        gaps = [
            CapabilityGap(
                need=g["need"],
                reason=g["reason"],
                hardware_category=g["hardware_category"],
                priority=g.get("priority", "critical"),
            )
            for g in data["gaps"]
        ]
        return {"status": "capability_gap", "gaps": gaps}

    return data


async def generate_skill_file(
    module: SelectedModule, profile: RobotProfile, gap: CapabilityGap
) -> str:
    """Generate a YAML skill file for a hardware module.

    Args:
        module: The selected hardware module.
        profile: Current robot profile (for compatibility context).
        gap: The capability gap this module addresses.

    Returns:
        YAML string for the skill file.
    """
    system = (
        "You are a robotics integration engineer. Generate a YAML skill file for a hardware module.\n\n"
        "Output ONLY valid YAML — no markdown, no explanation, no code fences.\n\n"
        "Use this exact schema:\n"
        "skill_id: <kebab-case-id>\n"
        "hardware: <module name>\n"
        "compatibility: [<platform>, <os>, <python version>]\n"
        "installation:\n"
        "  physical: <mount instructions using real mount points>\n"
        "  software:\n"
        "    - <pip install real-package>\n"
        "    - <ros2 launch command>\n"
        "agent_tools:\n"
        "  - name: <tool_name>\n"
        "    description: <what it returns>\n"
        "    entrypoint: skills/<capability>/<tool_name>.py\n"
        "agent_context_update: >\n"
        "  <1-2 sentences the agent should know now that this capability is active>\n\n"
        "Use REAL package names (e.g. depthai, rplidar-sdk, open3d). "
        "Include 2-3 agent_tools. Make mount instructions specific to the robot's mount points."
    )

    user = (
        f"Module: {module.name} (${module.price})\n"
        f"Capability gap: {gap.need} — {gap.reason}\n"
        f"Hardware category: {gap.hardware_category}\n"
        f"Robot platform: {profile.platform}, OS: {profile.os}\n"
        f"Available mount points: {', '.join(profile.mount_points)}\n"
        f"Specs: {json.dumps(module.specs)}"
    )

    raw = await llm_call(system, user)
    return _strip_fences(raw)


def ingest_skill(skill_yaml: str, profile: RobotProfile) -> dict:
    """Parse a skill YAML and update the robot profile with the new capability.

    Args:
        skill_yaml: Raw YAML string of the skill file.
        profile: Robot profile to mutate in place.

    Returns:
        Parsed skill dict.
    """
    skill = yaml.safe_load(skill_yaml)

    tool_names = [t["name"] for t in skill.get("agent_tools", [])]
    cap = {
        "id": skill["skill_id"],
        "description": f"{skill['hardware']} — tools: {tool_names}",
    }
    profile.add_capability(cap)

    return skill


if __name__ == "__main__":
    import asyncio

    async def main():
        profile = RobotProfile()
        task = "Navigate to the red box on the table, pick it up, and bring it back to the charging station"
        print(f"Task: {task}")
        print(f"Capabilities: {[c['id'] for c in profile.capabilities]}")
        print("Detecting gaps...")
        result = await detect_gaps(task, profile)
        print(f"Result: {result['status']}")
        if result["status"] == "capability_gap":
            for g in result["gaps"]:
                print(f"  Gap: {g.need} ({g.priority}) — {g.reason}")

    asyncio.run(main())
