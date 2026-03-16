#!/usr/bin/env python3
"""RoboStore Demo — G1 simulation controlled by natural language.

Run with:  mjpython demo.py

Waits for legs to be purchased, then launches MuJoCo viewer.
Accepts commands from CLI and web app (port 8765).
"""

import json
import re
import threading
import time
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler

import mujoco
import mujoco.viewer
import numpy as np
import torch
from dotenv import load_dotenv

load_dotenv()

WALKING_PATH = "mujoco_sims/unitree_ros/robots/g1_description/scene_rl.xml"
POLICY_PATH = "deploy/g1_policy.pt"

KPS = np.array([100,100,100,150,40,40, 100,100,100,150,40,40], dtype=np.float32)
KDS = np.array([2,2,2,4,2,2, 2,2,2,4,2,2], dtype=np.float32)
DEFAULT_ANGLES = np.array([-0.1,0,0,0.3,-0.2,0, -0.1,0,0,0.3,-0.2,0], dtype=np.float32)
CMD_SCALE = np.array([2.0, 2.0, 0.25], dtype=np.float32)
DT = 0.002
DECIMATION = 10
ACTION_SCALE = 0.25

C = "\033[96m"; G = "\033[92m"; Y = "\033[93m"; M = "\033[95m"
R = "\033[91m"; B = "\033[1m"; D = "\033[2m"; X = "\033[0m"

PLANNER_PROMPT = """\
You are a motion planner for a Unitree G1 humanoid robot in a MuJoCo simulation.
Convert natural language commands into a sequence of velocity steps.

The robot walks using an RL policy that takes velocity commands:
  vx: forward/back speed (-0.5 to 1.0 m/s)
  vy: lateral speed (-0.3 to 0.3 m/s)
  yr: yaw turn rate (-0.8 to 0.8 rad/s, positive = turn left)

Output JSON: {"steps": [{"cmd": [vx, vy, yr], "duration_s": float, "label": "string"}, ...]}
  - duration_s: 0.5 to 15.0 per step
  - label: short description of what this step does

Physics notes:
  - Robot walks about 0.5m/s forward at vx=0.5
  - A 90-degree turn takes about yr=0.5 for 3 seconds
  - A 180-degree turn takes about yr=0.5 for 6 seconds
  - A full 360-degree circle while walking: vx=0.4, yr=0.35, duration=12s

Examples:
"walk forward" -> {"steps": [{"cmd": [0.5,0,0], "duration_s": 4, "label": "walk forward"}]}
"walk forward 5 meters" -> {"steps": [{"cmd": [0.5,0,0], "duration_s": 10, "label": "walk 5m forward"}]}
"turn around" -> {"steps": [{"cmd": [0,0,0.5], "duration_s": 6, "label": "turn 180 degrees"}]}
"walk forward and come back" -> {"steps": [
  {"cmd": [0.5,0,0], "duration_s": 5, "label": "walk forward"},
  {"cmd": [0,0,0.5], "duration_s": 6, "label": "turn around"},
  {"cmd": [0.5,0,0], "duration_s": 5, "label": "walk back"}]}
"walk in a triangle" -> {"steps": [
  {"cmd": [0.5,0,0], "duration_s": 4, "label": "side 1"},
  {"cmd": [0,0,0.5], "duration_s": 4, "label": "turn 120 degrees"},
  {"cmd": [0.5,0,0], "duration_s": 4, "label": "side 2"},
  {"cmd": [0,0,0.5], "duration_s": 4, "label": "turn 120 degrees"},
  {"cmd": [0.5,0,0], "duration_s": 4, "label": "side 3"},
  {"cmd": [0,0,0.5], "duration_s": 4, "label": "turn 120 degrees"}]}
"walk in a circle" -> {"steps": [{"cmd": [0.4,0,0.35], "duration_s": 12, "label": "walk in circle"}]}
"figure 8" -> {"steps": [
  {"cmd": [0.4,0,0.35], "duration_s": 12, "label": "left circle"},
  {"cmd": [0.4,0,-0.35], "duration_s": 12, "label": "right circle"}]}
"strafe left" -> {"steps": [{"cmd": [0,0.3,0], "duration_s": 3, "label": "strafe left"}]}
"moonwalk" -> {"steps": [{"cmd": [-0.3,0,0], "duration_s": 5, "label": "moonwalk backward"}]}
"dance" -> {"steps": [
  {"cmd": [0,0,0.6], "duration_s": 2, "label": "spin left"},
  {"cmd": [0,0,-0.6], "duration_s": 2, "label": "spin right"},
  {"cmd": [0.3,0.2,0], "duration_s": 2, "label": "diagonal step"},
  {"cmd": [0.3,-0.2,0], "duration_s": 2, "label": "diagonal other way"},
  {"cmd": [0,0,0.8], "duration_s": 4, "label": "full spin"}]}
"patrol" -> {"steps": [
  {"cmd": [0.5,0,0], "duration_s": 6, "label": "patrol out"},
  {"cmd": [0,0,0.5], "duration_s": 6, "label": "turn around"},
  {"cmd": [0.5,0,0], "duration_s": 6, "label": "patrol back"},
  {"cmd": [0,0,0.5], "duration_s": 6, "label": "turn around"}]}

Be creative with complex commands. Break them into logical steps.
Output ONLY the JSON. No explanation."""


class Demo:
    def __init__(self):
        self.has_legs = False
        self.legs_ready = threading.Event()
        self.model = None
        self.data = None
        self.policy = None
        self.action = np.zeros(12, dtype=np.float32)
        self.target_dof = DEFAULT_ANGLES.copy()
        self.obs = np.zeros(47, dtype=np.float32)
        self.step_count = 0
        self.cmd = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.cmd_steps = 0

    def request_legs(self):
        self.legs_ready.set()

    def install_legs(self):
        if self.has_legs:
            return
        print(f"\n  {G}{'='*40}{X}")
        print(f"  {G}  LEGS INSTALLED — Loading RL policy...{X}")
        print(f"  {G}{'='*40}{X}")
        self.model = mujoco.MjModel.from_xml_path(WALKING_PATH)
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = DT
        self.policy = torch.jit.load(POLICY_PATH, map_location="cpu")
        self.policy.eval()
        self.has_legs = True
        print(f"  {G}  Ready.{X}\n")

    def physics_step(self):
        if not self.has_legs:
            return
        tau = (self.target_dof - self.data.qpos[7:]) * KPS + (0 - self.data.qvel[6:]) * KDS
        self.data.ctrl[:] = tau
        mujoco.mj_step(self.model, self.data)
        self.step_count += 1

        if self.step_count % DECIMATION == 0:
            qj = (self.data.qpos[7:] - DEFAULT_ANGLES) * 1.0
            dqj = self.data.qvel[6:] * 0.05
            qw, qx, qy, qz = self.data.qpos[3:7]
            grav = np.array([2*(-qz*qx+qw*qy), -2*(qz*qy+qw*qx), 1-2*(qw*qw+qz*qz)])
            omega = self.data.qvel[3:6] * 0.25
            phase = (self.step_count * DT) % 0.8 / 0.8
            o = self.obs
            o[:3] = omega; o[3:6] = grav; o[6:9] = self.cmd * CMD_SCALE
            o[9:21] = qj; o[21:33] = dqj; o[33:45] = self.action
            o[45:47] = [np.sin(2*np.pi*phase), np.cos(2*np.pi*phase)]
            with torch.no_grad():
                self.action = self.policy(torch.from_numpy(o).unsqueeze(0)).numpy().squeeze()
            self.target_dof = self.action * ACTION_SCALE + DEFAULT_ANGLES

        if self.cmd_steps > 0:
            self.cmd_steps -= 1
            if self.cmd_steps <= 0:
                self.cmd[:] = 0.0

    def set_velocity(self, vx, vy, yr, duration_s):
        if not self.has_legs:
            print(f"  {R}No legs installed{X}")
            return
        self.cmd[:] = [vx, vy, yr]
        self.cmd_steps = int(duration_s / DT)

    def get_position(self):
        if self.data is None:
            return 0, 0
        return float(self.data.qpos[0]), float(self.data.qpos[1])

    def is_busy(self):
        return self.cmd_steps > 0


demo = Demo()


def parse_llm_json(raw):
    """Extract JSON from LLM response, handling markdown fences and extra text."""
    cleaned = raw.strip()
    for fence in ("```json", "```"):
        cleaned = cleaned.removeprefix(fence).removesuffix(fence).strip()
    brace_start = cleaned.find("{")
    if brace_start < 0:
        raise ValueError("No JSON found")
    depth = 0
    for i, ch in enumerate(cleaned[brace_start:], brace_start):
        if ch == "{": depth += 1
        elif ch == "}": depth -= 1
        if depth == 0:
            return json.loads(cleaned[brace_start:i+1])
    raise ValueError("Incomplete JSON")


def execute_plan(steps):
    """Execute a list of velocity steps sequentially."""
    total = len(steps)
    for i, step in enumerate(steps):
        cmd = step["cmd"]
        dur = max(0.5, min(15.0, float(step.get("duration_s", 3.0))))
        label = step.get("label", f"step {i+1}")
        vx = max(-0.5, min(1.0, float(cmd[0])))
        vy = max(-0.3, min(0.3, float(cmd[1])))
        yr = max(-0.8, min(0.8, float(cmd[2])))
        print(f"  {C}[{i+1}/{total}]{X} {label}  [{vx:.1f}, {vy:.1f}, {yr:.1f}] {dur:.0f}s")
        demo.set_velocity(vx, vy, yr, dur)
        while demo.is_busy():
            time.sleep(0.02)
    x, y = demo.get_position()
    print(f"  {G}Done.{X} Position: ({x:.1f}, {y:.1f})")


class CmdHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        if self.path == "/cmd":
            cmd = body.get("cmd", [0,0,0])
            dur = body.get("duration_s", 2.0)
            demo.set_velocity(float(cmd[0]), float(cmd[1]), float(cmd[2]), float(dur))
            self._ok({"status": "ok"})
        elif self.path == "/legs":
            demo.request_legs()
            self._ok({"status": "ok"})
        else:
            self.send_response(404); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in [("Access-Control-Allow-Origin","*"),("Access-Control-Allow-Methods","POST, OPTIONS"),("Access-Control-Allow-Headers","Content-Type")]:
            self.send_header(k, v)
        self.end_headers()

    def _ok(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def input_thread():
    SHORTCUTS = {
        "w": ([0.5,0,0], 4.0, "walk forward"),
        "b": ([-0.3,0,0], 3.0, "walk backward"),
        "l": ([0,0,0.5], 3.0, "turn left"),
        "r": ([0,0,-0.5], 3.0, "turn right"),
        "s": ([0,0,0], 0.5, "stop"),
        "run": ([1.0,0,0], 4.0, "run forward"),
        "stop": ([0,0,0], 0.5, "stop"),
    }

    while True:
        try:
            text = input(f"{B}{C}demo>{X} ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("q", "quit", "exit"):
            import os; os._exit(0)
        if text.lower() == "legs":
            demo.request_legs()
            continue
        if not demo.has_legs:
            print(f"  {Y}No legs yet. Use web app or type 'legs'{X}")
            continue
        if demo.is_busy():
            print(f"  {Y}Still executing...{X}")
            continue

        key = text.lower()
        if key in SHORTCUTS:
            vel, dur, label = SHORTCUTS[key]
            print(f"  {C}[1/1]{X} {label}  [{vel[0]:.1f}, {vel[1]:.1f}, {vel[2]:.1f}] {dur:.0f}s")
            demo.set_velocity(*vel, dur)
            # Wait in background so prompt returns fast
            threading.Thread(target=lambda: (
                _wait_and_report()
            ), daemon=True).start()
            continue

        # Natural language → LLM planner
        try:
            from agent.planner import llm_call
            print(f"  {Y}[PLAN]{X} Thinking...")
            loop = asyncio.new_event_loop()
            raw = loop.run_until_complete(llm_call(PLANNER_PROMPT, f"Command: {text}", max_tokens=700))
            result = parse_llm_json(raw)

            steps = result.get("steps", None)
            if steps is None:
                steps = [{"cmd": result["cmd"], "duration_s": result.get("duration_s", 3.0), "label": "move"}]

            # Execute in background so prompt returns immediately
            threading.Thread(target=execute_plan, args=(steps,), daemon=True).start()
        except Exception as e:
            print(f"  {R}Error: {e}{X}")


def _wait_and_report():
    while demo.is_busy():
        time.sleep(0.02)
    x, y = demo.get_position()
    print(f"  {G}Done.{X} Position: ({x:.1f}, {y:.1f})")


def main():
    threading.Thread(target=lambda: HTTPServer(("127.0.0.1", 8765), CmdHandler).serve_forever(), daemon=True).start()
    threading.Thread(target=input_thread, daemon=True).start()

    print(f"\n{B}{C}{'='*50}{X}")
    print(f"{B}{C}  RoboStore Demo{X}")
    print(f"{B}{C}{'='*50}{X}")
    print(f"  {D}Listening on http://127.0.0.1:8765{X}")
    print(f"\n  {Y}G1 has no legs. Waiting for purchase...{X}")
    print(f"  {D}Use the web app (localhost:8001) or type 'legs'{X}\n")

    demo.legs_ready.wait()
    demo.install_legs()

    print(f"  {D}Stabilizing...{X}")
    for _ in range(1000):
        demo.cmd_steps = 1
        demo.physics_step()
    demo.cmd_steps = 0
    demo.cmd[:] = 0
    print(f"  {G}Standing. Type a command.{X}\n")

    with mujoco.viewer.launch_passive(demo.model, demo.data) as viewer:
        while viewer.is_running():
            t0 = time.time()
            if demo.cmd_steps > 0:
                demo.physics_step()
            viewer.sync()
            sleep = DT - (time.time() - t0)
            if sleep > 0:
                time.sleep(sleep)


if __name__ == "__main__":
    main()
