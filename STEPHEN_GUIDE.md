# Stephen's Guide — Wiring MuJoCo to the Orchestrator

## How It All Fits Together

```
User types: "build a wall and walk around it"
                    │
                    ▼
            ┌──────────────┐
            │  main.py CLI  │  ← interactive prompt
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │ Orchestrator  │  ← detects "build" = scene command
            │  .command()   │     detects "walk" = movement command
            └──────┬───────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
   ┌─────────────┐   ┌───────────────┐
   │SceneBuilder │   │SCOUT→PLANNER  │
   │ generates   │   │→SAFETY→EXEC   │
   │ MJCF XML    │   │               │
   └──────┬──────┘   └───────┬───────┘
          │                   │
          ▼                   ▼
   ┌─────────────────────────────────┐
   │     SimInterface (YOUR FILE)     │
   │                                  │
   │  get_state() → data.qpos/qvel   │
   │  get_camera_frame() → render     │
   │  send_command() → data.ctrl      │
   │  inject_scene_xml() → YOU ADD    │
   └─────────────────────────────────┘
          │
          ▼
      MuJoCo G1 Sim
```

## Step 1: Install MuJoCo (if not done)

```bash
pip install mujoco Pillow
```

## Step 2: Verify your G1 loads

```bash
cd ~/nebius-hackathon
python mujoco_sims/view_g1.py
# Should open the G1 viewer
```

## Step 3: Set API keys

```bash
cp .env.example .env
# Add at minimum:
# OPENROUTER_API_KEY=sk-or-v1-...
# Or NEBIUS_API_KEY=... (preferred, from tokenfactory.nebius.com)
```

## Step 4: Run the CLI with mock sim (test everything works)

```bash
pip install httpx pyyaml python-dotenv
python main.py
```

Type commands like:
- `walk forward` — tests the full SCOUT → PLANNER → SAFETY → EXECUTOR pipeline
- `build a red cube ahead` — tests SceneBuilder (generates XML, but mock sim ignores it)
- `wave` — tests preset executor

If this works, the LLM pipeline is good. Now you just need to connect real MuJoCo.

## Step 5: Replace sim_interface.py with real MuJoCo

Edit `agents/sim_interface.py`. Replace the entire class:

```python
import asyncio
import base64
import io
import mujoco
import numpy as np
from PIL import Image


class SimInterface:
    def __init__(self, model_path="mujoco_sims/unitree_ros/robots/g1_description/g1_23dof.xml"):
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        # Step to initial state
        mujoco.mj_step(self.model, self.data)

    async def get_state(self) -> dict:
        return {
            "time": float(self.data.time),
            "qpos": self.data.qpos.tolist(),
            "qvel": self.data.qvel.tolist(),
            "position": self.data.qpos[:3].tolist(),
            "orientation": self.data.qpos[3:7].tolist(),
            "velocity": self.data.qvel[:3].tolist(),
            "angular_vel": self.data.qvel[3:6].tolist(),
            "stability": float(np.clip(1.0 - np.abs(self.data.qvel[3:6]).mean(), 0, 1)),
            "battery": 85.0,
            "joint_positions": self.data.qpos[7:].tolist(),
        }

    async def get_camera_frame(self) -> str:
        self.renderer.update_scene(self.data)
        frame = self.renderer.render()
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode()

    async def send_command(self, action: str, params: dict) -> dict:
        targets = params.get("targets", [0.0] * self.model.nu)
        steps = params.get("duration_steps", 100)
        for _ in range(steps):
            self.data.ctrl[:len(targets)] = targets
            mujoco.mj_step(self.model, self.data)
        return {
            "status": "ok",
            "action": action,
            "steps_executed": steps,
            "new_state": await self.get_state(),
        }

    async def inject_scene_xml(self, mjcf_xml: str) -> dict:
        """Inject new bodies/geoms into the running scene from MJCF XML string.
        
        This is how SceneBuilder output gets into the sim.
        
        Option A (simple): Rebuild the entire model with new XML appended
        Option B (advanced): Use mujoco.MjSpec for runtime modification
        
        For the hackathon, Option A is fine:
        """
        # Read the original XML
        import xml.etree.ElementTree as ET
        
        # Load original scene XML
        tree = ET.parse(self.model_path if hasattr(self, 'model_path') 
                       else "mujoco_sims/unitree_ros/robots/g1_description/g1_23dof.xml")
        root = tree.getroot()
        worldbody = root.find('worldbody')
        
        # Parse the new elements and append them
        # Wrap in a root tag so ET can parse multiple top-level elements
        new_elements = ET.fromstring(f"<wrapper>{mjcf_xml}</wrapper>")
        for elem in new_elements:
            worldbody.append(elem)
        
        # Write to temp file and reload
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xml', mode='w', delete=False) as f:
            tree.write(f)
            temp_path = f.name
        
        # Reload model with new scene
        self.model = mujoco.MjModel.from_xml_path(temp_path)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        mujoco.mj_step(self.model, self.data)
        
        return {"status": "ok", "message": f"Scene updated with new elements"}
```

## Step 6: Wire the viewer (so we can SEE it)

For the demo, you want both:
- The MuJoCo viewer window (live 3D view)
- Camera frames sent to the dashboard

Run with the passive viewer:

```python
# In a separate script or modify main.py:
import mujoco
import mujoco.viewer

# Get the SimInterface's model and data
sim = orchestrator.sim  # or however you access it

with mujoco.viewer.launch_passive(sim.model, sim.data) as viewer:
    while viewer.is_running():
        # The orchestrator's send_command() calls mj_step internally
        # Just sync the viewer
        viewer.sync()
```

On macOS: use `mjpython` instead of `python` for the viewer.

## Step 7: Test the full loop

```bash
# macOS:
mjpython main.py

# Linux:
python main.py
```

Type:
1. `build a red cube 1 meter ahead` → should see cube appear in viewer
2. `walk forward` → G1 should attempt to walk
3. `build a staircase of 3 steps and walk up it` → staircase appears, then G1 plans to climb

## What Goes Wrong (and fixes)

| Problem | Fix |
|---|---|
| Robot collapses immediately | Need a standing controller/keyframe. Load the `stand` keyframe: `mujoco.mj_resetDataKeyframe(model, data, 0)` |
| Scene XML injection breaks model | The generated XML has invalid geom types or positions. Check SceneBuilder output manually first |
| Camera frame is black | Renderer needs a light source. Make sure the scene XML has `<light>` elements |
| Joint targets don't match actuators | Check `model.nu` (number of actuators) matches the 23 targets we send. Print it. |
| Robot moves but falls over | The placeholder joint targets are approximate. Tune them or use a pre-trained walking policy |

## Files You Touch

| File | What You Do |
|---|---|
| `agents/sim_interface.py` | Replace mock → real MuJoCo (code above) |
| `agents/executor.py` | Tune ACTION_TARGETS joint values if G1 falls over |
| `mujoco_sims/view_g1.py` | Your existing viewer script, keep for reference |
