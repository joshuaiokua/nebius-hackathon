from dataclasses import dataclass, field


@dataclass
class RobotProfile:
    robot_id: str = "unitree-a1-sim"
    platform: str = "Unitree A1"
    os: str = "Ubuntu 22.04 / ROS2 Humble"
    power_budget_w: int = 15
    usb_ports_available: int = 2
    mount_points: list[str] = field(default_factory=lambda: [
        "front_chin", "back_plate", "left_rail", "right_rail"
    ])
    capabilities: list[dict] = field(default_factory=lambda: [
        {"id": "locomotion", "description": "4-legged walk/trot gaits"},
        {"id": "imu", "description": "6-axis orientation + acceleration"},
    ])

    def has_capability(self, cap_id: str) -> bool:
        return any(c["id"] == cap_id for c in self.capabilities)

    def add_capability(self, cap: dict) -> None:
        if not self.has_capability(cap["id"]):
            self.capabilities.append(cap)


@dataclass
class CapabilityGap:
    need: str                  # "depth_perception", "vision", "gripper"
    reason: str                # human-readable explanation
    hardware_category: str     # "stereo camera", "lidar", "gripper"
    priority: str = "critical" # "critical" | "nice_to_have"


@dataclass
class SelectedModule:
    name: str           # "OAK-D Lite Stereo Camera"
    price: float        # 149.00
    url: str            # product URL
    pid: str            # product ID
    specs: dict = field(default_factory=dict)  # interface, power_watts, etc.
    rationale: str = ""


if __name__ == "__main__":
    profile = RobotProfile()
    print("Default RobotProfile:")
    print(f"  robot_id: {profile.robot_id}")
    print(f"  platform: {profile.platform}")
    print(f"  capabilities: {[c['id'] for c in profile.capabilities]}")
    print(f"  has locomotion: {profile.has_capability('locomotion')}")
    print(f"  has vision: {profile.has_capability('vision')}")
    profile.add_capability({"id": "vision", "description": "RGB camera"})
    print(f"  after add_capability('vision'): {[c['id'] for c in profile.capabilities]}")
