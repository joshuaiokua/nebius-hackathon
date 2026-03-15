"""SceneBuilder — LLM-powered MuJoCo MJCF scene generation from natural language.

Takes natural language prompts and generates valid MuJoCo XML body elements
that can be injected into a running simulation scene.

Examples:
    >>> builder = SceneBuilder()
    >>> xml = await builder.build_from_prompt("build a staircase of 5 steps")
    # Returns MJCF XML like:
    # <body name="staircase" pos="1 0 0">
    #   <body name="step_1" pos="0 0 0.05">
    #     <geom type="box" size="0.3 0.5 0.05" rgba="0.6 0.6 0.6 1"/>
    #   </body>
    #   <body name="step_2" pos="0.3 0 0.15">
    #     <geom type="box" size="0.3 0.5 0.05" rgba="0.6 0.6 0.6 1"/>
    #   </body>
    #   ...
    # </body>

    >>> xml = await builder.build_from_prompt("add a wall 2 meters ahead")
    # <body name="wall" pos="2 0 0.5">
    #   <geom type="box" size="0.05 2 1" rgba="0.8 0.8 0.8 1"/>
    # </body>

    >>> xml = await builder.build_from_prompt("scatter 5 random boxes")
    # <body name="box_1" pos="1.2 0.5 0.15">
    #   <geom type="box" size="0.15 0.15 0.15" rgba="0.9 0.2 0.2 1"/>
    # </body>
    # <body name="box_2" pos="-0.8 1.3 0.15">
    #   <geom type="box" size="0.15 0.15 0.15" rgba="0.2 0.9 0.2 1"/>
    # </body>
    # ...

Stephen handles the actual XML injection into the running sim.
"""

from __future__ import annotations

from agent.planner import nebius_llm_call

_SYSTEM_PROMPT = """\
You are a MuJoCo scene generator. Given a natural language description, output ONLY valid MuJoCo MJCF XML body elements.

Rules:
- Output raw XML only. No markdown, no explanation, no code fences.
- Use <body> elements with name and pos attributes.
- Use <geom> elements with type, size, pos (optional), and rgba attributes.
- Valid geom types: box, sphere, cylinder, capsule, plane, mesh.
- Positions are in meters. The robot stands at the origin (0, 0, 0) facing +X.
- Ground plane is at Z=0. Place objects so they rest on the ground (Z = half-height for boxes).
- Give each body a unique descriptive name attribute.
- Use realistic sizes (a step ~0.3m deep, 0.15m tall; a wall ~0.05m thick, 2m wide, 1m tall).
- For multiple objects, output multiple <body> elements (no wrapper needed).
- Use rgba for color (values 0-1, fourth component is alpha, always 1).

Example input: "place a red cube 1 meter ahead"
Example output:
<body name="red_cube" pos="1 0 0.15">
  <geom type="box" size="0.15 0.15 0.15" rgba="0.9 0.1 0.1 1"/>
</body>
"""


class SceneBuilder:
    """Generates MuJoCo MJCF XML from natural language prompts via LLM."""

    async def build_from_prompt(self, prompt: str) -> str:
        """Generate MJCF XML body elements from a natural language scene description.

        Args:
            prompt: Natural language like 'build a staircase of 10 steps in front
                    of the robot' or 'scatter 5 random boxes'.

        Returns:
            String of valid MJCF XML body/geom elements ready for injection.
        """
        raw = await nebius_llm_call(_SYSTEM_PROMPT, prompt)
        # Strip any accidental markdown fences the LLM might add
        xml = raw.strip()
        for fence in ("```xml", "```mjcf", "```"):
            xml = xml.removeprefix(fence).removesuffix(fence).strip()
        return xml
