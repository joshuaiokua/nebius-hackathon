#!/usr/bin/env python3
"""RoboStore Demo — starts waiting for legs, then launches walking G1 viewer.

Run with:  mjpython demo.py

Phase 1: Waits for legs to be purchased (via web app or 'legs' command)
Phase 2: Launches MuJoCo viewer with full RL walking G1
Phase 3: Accepts walk/turn commands from web app (port 8765) and CLI

Web app communicates via HTTP:
  POST /legs  {} — triggers the viewer launch with walking G1
  POST /cmd   {"cmd": [vx,vy,yr], "duration_s": N} — velocity command
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

VELOCITY_PROMPT = """\
You are a G1 humanoid robot motion planner. Convert the movement command into \
a sequence of velocity steps. Each step has a velocity and duration.

Output a JSON object: {"steps": [{"cmd": [vx, vy, yr], "duration_s": float}, ...]}
- vx: forward/back speed, -0.5 to 1.0 m/s
- vy: lateral speed, -0.3 to 0.3 m/s
- yr: yaw turn rate, -0.8 to 0.8 rad/s (positive = left)
- duration_s: 0.5 to 6.0 seconds per step

Examples:
- "walk forward" → {"steps": [{"cmd": [0.5, 0, 0], "duration_s": 3.0}]}
- "walk in a circle" → {"steps": [{"cmd": [0.4, 0, 0.4], "duration_s": 10.0}]}
- "walk in a triangle" → {"steps": [
    {"cmd": [0.5, 0, 0], "duration_s": 3.0},
    {"cmd": [0, 0, 0.7], "duration_s": 3.0},
    {"cmd": [0.5, 0, 0], "duration_s": 3.0},
    {"cmd": [0, 0, 0.7], "duration_s": 3.0},
    {"cmd": [0.5, 0, 0], "duration_s": 3.0},
    {"cmd": [0, 0, 0.7], "duration_s": 3.0}
  ]}
- "walk forward then turn around and come back" → {"steps": [
    {"cmd": [0.5, 0, 0], "duration_s": 4.0},
    {"cmd": [0, 0, 0.8], "duration_s": 4.0},
    {"cmd": [0.5, 0, 0], "duration_s": 4.0}
  ]}
- "do a figure 8" → {"steps": [
    {"cmd": [0.4, 0, 0.4], "duration_s": 5.0},
    {"cmd": [0.4, 0, -0.4], "duration_s": 5.0}
  ]}
- "spin in place" → {"steps": [{"cmd": [0, 0, 0.8], "duration_s": 8.0}]}

Output ONLY the JSON. No explanation."""


class Demo:
    def __init__(self):
        self.has_legs = False
        self.legs_ready = threading.Event()

        # These get initialized when legs arrive
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
        """Signal that legs should be installed (called from any thread)."""
        self.legs_ready.set()

    def install_legs(self):
        """Actually load the model (must be called from main thread)."""
        if self.has_legs:
            return
        print(f"\n  {G}{'='*40}{X}")
        print(f"  {G}  LEGS INSTALLED — Loading walking model...{X}")
        print(f"  {G}{'='*40}{X}")
        self.model = mujoco.MjModel.from_xml_path(WALKING_PATH)
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = DT
        self.policy = torch.jit.load(POLICY_PATH, map_location="cpu")
        self.policy.eval()
        self.has_legs = True
        print(f"  {G}  Launching MuJoCo viewer...{X}\n")

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
            print(f"  {R}No legs installed yet{X}")
            return
        self.cmd[:] = [vx, vy, yr]
        self.cmd_steps = int(duration_s / DT)
        print(f"  {G}[EXEC]{X} cmd=[{vx:.1f}, {vy:.1f}, {yr:.1f}] for {duration_s:.1f}s")


demo = Demo()


class CmdHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/cmd":
            cmd = body.get("cmd", [0, 0, 0])
            dur = body.get("duration_s", 2.0)
            demo.set_velocity(float(cmd[0]), float(cmd[1]), float(cmd[2]), float(dur))
            self._respond({"status": "ok"})
        elif self.path == "/legs":
            demo.request_legs()
            self._respond({"status": "ok"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _respond(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def run_cmd_server():
    server = HTTPServer(("127.0.0.1", 8765), CmdHandler)
    server.serve_forever()


def input_thread():
    PRESETS = {
        "w": ([0.5,0,0], 4.0), "walk": ([0.5,0,0], 4.0),
        "b": ([-0.3,0,0], 3.0), "back": ([-0.3,0,0], 3.0),
        "l": ([0,0,0.5], 3.0), "left": ([0,0,0.5], 3.0),
        "r": ([0,0,-0.5], 3.0), "right": ([0,0,-0.5], 3.0),
        "s": ([0,0,0], 0.5), "stop": ([0,0,0], 0.5),
        "run": ([1.0,0,0], 4.0),
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
            print(f"  {Y}No legs yet. Purchase from web app or type 'legs'{X}")
            continue

        key = text.lower()
        if key in PRESETS:
            vel, dur = PRESETS[key]
            demo.set_velocity(*vel, dur)
            continue

        try:
            from agent.planner import llm_call
            print(f"  {Y}[PLAN]{X} Planning motion...")
            loop = asyncio.new_event_loop()
            raw = loop.run_until_complete(llm_call(VELOCITY_PROMPT, f"Command: {text}", max_tokens=512))
            cleaned = raw.strip()
            for fence in ("```json", "```"):
                cleaned = cleaned.removeprefix(fence).removesuffix(fence).strip()

            # Find the JSON object (may be nested)
            brace_start = cleaned.find("{")
            if brace_start >= 0:
                depth = 0
                for i, ch in enumerate(cleaned[brace_start:], brace_start):
                    if ch == "{": depth += 1
                    elif ch == "}": depth -= 1
                    if depth == 0:
                        cleaned = cleaned[brace_start:i+1]
                        break

            result = json.loads(cleaned)

            # Handle both single command and multi-step plans
            steps = result.get("steps", None)
            if steps is None:
                # Old single-command format
                steps = [{"cmd": result["cmd"], "duration_s": result.get("duration_s", 3.0)}]

            print(f"  {G}[PLAN]{X} {len(steps)} step(s):")
            for i, step in enumerate(steps):
                cmd = step["cmd"]
                dur = max(0.5, min(10.0, float(step.get("duration_s", 3.0))))
                vx = max(-0.5, min(1.0, float(cmd[0])))
                vy = max(-0.3, min(0.3, float(cmd[1])))
                yr = max(-0.8, min(0.8, float(cmd[2])))
                print(f"    {i+1}. [{vx:.1f}, {vy:.1f}, {yr:.1f}] for {dur:.1f}s")
                demo.set_velocity(vx, vy, yr, dur)
                # Wait for this step to finish before starting the next
                while demo.cmd_steps > 0:
                    time.sleep(0.05)
                time.sleep(0.2)  # brief pause between steps

            print(f"  {G}[DONE]{X} Motion complete")
        except Exception as e:
            print(f"  {R}Error: {e}{X}")


def main():
    threading.Thread(target=run_cmd_server, daemon=True).start()
    threading.Thread(target=input_thread, daemon=True).start()

    print(f"\n{B}{C}{'='*50}{X}")
    print(f"{B}{C}  RoboStore Demo{X}")
    print(f"{B}{C}{'='*50}{X}")
    print(f"  {D}Command server on http://127.0.0.1:8765{X}")
    print(f"\n  {Y}G1 has no legs. Waiting for purchase...{X}")
    print(f"  {D}Use the web app (localhost:8001) or type 'legs'{X}\n")

    # Wait for legs signal (from web app or CLI)
    demo.legs_ready.wait()

    # Load model on main thread (required for macOS OpenGL)
    demo.install_legs()

    # Run policy for 2s to reach stable standing pose
    print(f"  {D}Stabilizing...{X}")
    for _ in range(1000):
        demo.cmd_steps = 1  # keep policy active during init
        demo.physics_step()
    demo.cmd_steps = 0
    demo.cmd[:] = 0
    print(f"  {G}Ready. Robot is standing.{X}\n")

    # Launch viewer
    with mujoco.viewer.launch_passive(demo.model, demo.data) as viewer:
        while viewer.is_running():
            t0 = time.time()

            if demo.cmd_steps > 0:
                # Active command — run physics with RL policy
                demo.physics_step()
            else:
                # Idle — don't step physics, robot stays frozen in place
                pass

            viewer.sync()
            sleep = DT - (time.time() - t0)
            if sleep > 0:
                time.sleep(sleep)


if __name__ == "__main__":
    main()
