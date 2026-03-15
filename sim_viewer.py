#!/usr/bin/env python3
"""Live G1 viewer — native MuJoCo window + CLI commands.

Run with: mjpython sim_viewer.py

Type velocity commands in the terminal while watching the robot in the 3D viewer.
Commands:
  w / walk       - walk forward (0.5 m/s, 4s)
  b / back       - walk backward
  l / left       - turn left
  r / right      - turn right
  s / stop       - stop moving
  run            - run forward (1.0 m/s)
  q / quit       - exit

Or type custom: <vx> <vy> <yaw_rate> <duration>
  Example: 0.3 0.0 0.2 3.0  (walk forward + turn left for 3s)
"""

import sys
import threading
import time

import mujoco
import mujoco.viewer
import numpy as np
import torch

MODEL_PATH = "mujoco_sims/unitree_ros/robots/g1_description/scene_rl.xml"
POLICY_PATH = "deploy/g1_policy.pt"

KPS = np.array([100,100,100,150,40,40, 100,100,100,150,40,40], dtype=np.float32)
KDS = np.array([2,2,2,4,2,2, 2,2,2,4,2,2], dtype=np.float32)
DEFAULT_ANGLES = np.array([-0.1,0,0,0.3,-0.2,0, -0.1,0,0,0.3,-0.2,0], dtype=np.float32)
CMD_SCALE = np.array([2.0, 2.0, 0.25], dtype=np.float32)
DT = 0.002
DECIMATION = 10
ACTION_SCALE = 0.25
NUM_ACTIONS = 12
NUM_OBS = 47

PRESETS = {
    "w": ([0.5, 0, 0], 4.0, "walk forward"),
    "walk": ([0.5, 0, 0], 4.0, "walk forward"),
    "b": ([-0.3, 0, 0], 3.0, "walk backward"),
    "back": ([-0.3, 0, 0], 3.0, "walk backward"),
    "l": ([0.0, 0, 0.5], 3.0, "turn left"),
    "left": ([0.0, 0, 0.5], 3.0, "turn left"),
    "r": ([0.0, 0, -0.5], 3.0, "turn right"),
    "right": ([0.0, 0, -0.5], 3.0, "turn right"),
    "s": ([0, 0, 0], 1.0, "stop"),
    "stop": ([0, 0, 0], 1.0, "stop"),
    "run": ([1.0, 0, 0], 4.0, "run forward"),
}


def gravity_orientation(q):
    qw, qx, qy, qz = q
    return np.array([2*(-qz*qx+qw*qy), -2*(qz*qy+qw*qx), 1-2*(qw*qw+qz*qz)])


def main():
    model = mujoco.MjModel.from_xml_path(MODEL_PATH)
    data = mujoco.MjData(model)
    model.opt.timestep = DT

    policy = torch.jit.load(POLICY_PATH, map_location="cpu")
    policy.eval()

    action = np.zeros(NUM_ACTIONS, dtype=np.float32)
    target_dof_pos = DEFAULT_ANGLES.copy()
    obs = np.zeros(NUM_OBS, dtype=np.float32)
    step_count = 0
    cmd = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    cmd_steps_left = 0

    def input_loop():
        nonlocal cmd, cmd_steps_left
        print("\n\033[1;36m=== G1 Sim Viewer ===\033[0m")
        print("Commands: w(alk) b(ack) l(eft) r(ight) s(top) run q(uit)")
        print("Custom:   <vx> <vy> <yaw_rate> <seconds>")
        print()

        while True:
            try:
                text = input("\033[1;32mg1>\033[0m ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if text in ("q", "quit", "exit"):
                print("Bye!")
                import os; os._exit(0)

            if text in PRESETS:
                vel, dur, label = PRESETS[text]
                cmd[:] = vel
                cmd_steps_left = int(dur / DT)
                print(f"  \033[96m{label}\033[0m  cmd={vel} for {dur}s")
                continue

            parts = text.split()
            if len(parts) >= 3:
                try:
                    vx, vy, yr = float(parts[0]), float(parts[1]), float(parts[2])
                    dur = float(parts[3]) if len(parts) > 3 else 3.0
                    cmd[:] = [vx, vy, yr]
                    cmd_steps_left = int(dur / DT)
                    print(f"  \033[96mcustom\033[0m  cmd=[{vx},{vy},{yr}] for {dur}s")
                    continue
                except ValueError:
                    pass

            print("  Unknown command. Try: w, b, l, r, s, run, or <vx> <vy> <yr> <dur>")

    threading.Thread(target=input_loop, daemon=True).start()

    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            step_start = time.time()

            # PD control + policy
            tau = (target_dof_pos - data.qpos[7:]) * KPS + (0 - data.qvel[6:]) * KDS
            data.ctrl[:] = tau
            mujoco.mj_step(model, data)
            step_count += 1

            if step_count % DECIMATION == 0:
                qj = (data.qpos[7:] - DEFAULT_ANGLES) * 1.0
                dqj = data.qvel[6:] * 0.05
                grav = gravity_orientation(data.qpos[3:7])
                omega = data.qvel[3:6] * 0.25
                phase = (step_count * DT) % 0.8 / 0.8
                obs[:3] = omega
                obs[3:6] = grav
                obs[6:9] = cmd * CMD_SCALE
                obs[9:21] = qj
                obs[21:33] = dqj
                obs[33:45] = action
                obs[45:47] = [np.sin(2*np.pi*phase), np.cos(2*np.pi*phase)]
                with torch.no_grad():
                    action = policy(torch.from_numpy(obs).unsqueeze(0)).numpy().squeeze()
                target_dof_pos = action * ACTION_SCALE + DEFAULT_ANGLES

            # Command countdown
            if cmd_steps_left > 0:
                cmd_steps_left -= 1
                if cmd_steps_left <= 0:
                    cmd[:] = 0.0

            viewer.sync()

            # Real-time pacing
            elapsed = time.time() - step_start
            sleep_time = DT - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    main()
