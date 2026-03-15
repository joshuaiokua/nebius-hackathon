#!/usr/bin/env python3
"""RoboStore CLI — natural language to robot simulation.

Interactive loop: type a command, watch the multi-agent pipeline execute it.
This is the demo entry point.

Usage:
    python main.py
"""

import asyncio
import sys

from agents.orchestrator import AsyncOrchestrator
from agents.sim_interface import SimInterface

# ANSI
C_PROMPT = "\033[1;36m"  # bold cyan
C_DIM = "\033[2m"        # dim
C_BOLD = "\033[1m"       # bold
C_GREEN = "\033[92m"     # green
C_RED = "\033[91m"       # red
C_RST = "\033[0m"        # reset

BANNER = f"""{C_BOLD}
 ____       _         ____  _
|  _ \\ ___ | |__  ___/ ___|| |_ ___  _ __ ___
| |_) / _ \\| '_ \\/ _ \\___ \\| __/ _ \\| '__/ _ \\
|  _ < (_) | |_) (_) |__) | || (_) | | |  __/
|_| \\_\\___/|_.__/\\___/____/ \\__\\___/|_|  \\___|
{C_RST}{C_DIM}
  Natural Language → Multi-Agent → MuJoCo Simulation
  Type any command. 'quit' to exit. 'help' for examples.
{C_RST}"""

HELP_TEXT = f"""{C_BOLD}Examples:{C_RST}
  {C_GREEN}walk forward{C_RST}              — preset movement
  {C_GREEN}wave at me{C_RST}               — preset gesture
  {C_GREEN}do a little dance{C_RST}        — LLM figures out joint targets
  {C_GREEN}raise both arms up{C_RST}       — LLM-generated movement
  {C_GREEN}build a wall ahead{C_RST}       — scene modification
  {C_GREEN}build stairs then walk up{C_RST} — scene + movement combo
  {C_GREEN}turn left and walk forward{C_RST} — compound movement
"""


async def main() -> None:
    print(BANNER)

    sim = SimInterface()
    orch = AsyncOrchestrator(sim=sim)

    while True:
        try:
            user_input = input(f"\n{C_PROMPT}robostore> {C_RST}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_DIM}Goodbye!{C_RST}")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print(f"{C_DIM}Goodbye!{C_RST}")
            break
        if user_input.lower() in ("help", "?"):
            print(HELP_TEXT)
            continue

        try:
            result = await orch.command(user_input)
            status = result.get("status", "done")
            if status == "vetoed":
                print(f"\n{C_RED}VETOED by SAFETY agent.{C_RST}")
                concerns = result.get("safety", {}).get("concerns", [])
                if concerns:
                    for c in concerns:
                        print(f"  {C_RED}- {c}{C_RST}")
            else:
                print(f"\n{C_GREEN}Done.{C_RST}")
        except Exception as e:
            print(f"\n{C_RED}Error: {e}{C_RST}")


if __name__ == "__main__":
    asyncio.run(main())
