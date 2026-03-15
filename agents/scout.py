from agent.planner import nebius_vision_call


class ScoutAgent:
    """SCOUT agent — analyzes camera frames to understand the environment."""

    async def analyze_frame(self, image_b64: str) -> str:
        """Analyze a camera frame and return a scene description.

        Args:
            image_b64: Base64-encoded image from the robot's camera.

        Returns:
            Natural language description of the scene.
        """
        prompt = (
            "You are a robot scout agent. Describe the scene in detail: "
            "objects, their positions, distances, surfaces, obstacles, "
            "and anything relevant for robot navigation and manipulation."
        )
        return await nebius_vision_call(image_b64, prompt)
