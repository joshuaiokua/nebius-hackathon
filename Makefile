.PHONY: store robot dev demo

# Run the RoboStore on port 8000
store:
	uv run uvicorn store.app:app --host 0.0.0.0 --port 8000 --reload

# Run the Robot Control Panel on port 8001
robot:
	uv run uvicorn robot.app:app --host 0.0.0.0 --port 8001 --reload

# Run both in parallel (like `yarn dev`)
dev:
	uv run uvicorn store.app:app --host 0.0.0.0 --port 8000 --reload & \
	uv run uvicorn robot.app:app --host 0.0.0.0 --port 8001 --reload & \
	wait

# Run the CLI demo
demo:
	uv run python -m orchestrator
