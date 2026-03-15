# Quick Start — Running Everything

## 1. Install dependencies
```bash
pip install uv
uv pip install -e .
# Or manually:
pip install httpx pyyaml python-dotenv fastapi "uvicorn[standard]"
```

## 2. Set API keys
```bash
cp .env.example .env
# Edit .env:
# OPENROUTER_API_KEY=sk-or-v1-...
# TAVILY_API_KEY=tvly-...
# NEBIUS_API_KEY=...   (get from https://tokenfactory.nebius.com/)
```

## 3. Run the multi-agent orchestrator (mock sim)
```bash
# This runs SCOUT → PLANNER → SAFETY in parallel with mock sim data
# No MuJoCo needed — uses fake state + Nebius Token Factory for LLM calls
python -m agents.orchestrator
```

## 4. Run the marketplace storefront
```bash
uvicorn store.app:app --reload --port 8000
# Open http://localhost:8000
```

## 5. Run the robot control panel
```bash
uvicorn robot.app:app --reload --port 8001
# Open http://localhost:8001
```

## 6. Run the self-expanding agent demo
```bash
python orchestrator.py
# Detects capability gaps, searches catalogs, generates skills
```

---

## For Stephen: Connecting Real MuJoCo

### Setup MuJoCo + G1 model
```bash
pip install mujoco
git clone https://github.com/google-deepmind/mujoco_menagerie.git
# Test it works:
python -c "import mujoco; m = mujoco.MjModel.from_xml_path('mujoco_menagerie/unitree_g1/scene.xml'); print(f'G1 loaded: {m.nq} qpos, {m.nv} qvel')"
```

### Launch the viewer (local machine with display only)
```bash
# Standalone viewer:
python -m mujoco.viewer --mjcf mujoco_menagerie/unitree_g1/scene.xml

# Or with passive viewer (macOS needs mjpython):
mjpython -c "
import mujoco, mujoco.viewer, time
model = mujoco.MjModel.from_xml_path('mujoco_menagerie/unitree_g1/scene.xml')
data = mujoco.MjData(model)
with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
"
```

### Wire into the orchestrator
**Edit only `agents/sim_interface.py`.** Replace mock methods with real MuJoCo calls:

```python
import mujoco
import numpy as np

class SimInterface:
    def __init__(self, model_path="mujoco_menagerie/unitree_g1/scene.xml"):
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)

    async def get_state(self):
        return {
            "time": self.data.time,
            "qpos": self.data.qpos.tolist(),
            "qvel": self.data.qvel.tolist(),
            "position": self.data.qpos[:3].tolist(),
            "orientation": self.data.qpos[3:7].tolist(),
            "velocity": self.data.qvel[:3].tolist(),
            "angular_vel": self.data.qvel[3:6].tolist(),
            "stability": float(np.clip(1.0 - abs(self.data.qvel[3:6]).mean(), 0, 1)),
            "battery": 85.0,
            "joint_positions": self.data.qpos[7:].tolist(),
        }

    async def get_camera_frame(self):
        self.renderer.update_scene(self.data)
        frame = self.renderer.render()
        import io, base64
        from PIL import Image
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode()

    async def send_command(self, action, params):
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
```

That's it. The orchestrator picks up the real sim automatically.
