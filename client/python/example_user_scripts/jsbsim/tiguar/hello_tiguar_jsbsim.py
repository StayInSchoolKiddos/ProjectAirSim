"""Tiguar visuals driven by UNMODIFIED Skywalker X8 placeholder dynamics.

This demo does not model Tiguar aerodynamics, mass, propulsion or performance.
Start Blocks in Play mode before running this script from any directory.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

from projectairsim import Drone, ProjectAirSimClient, World
from projectairsim.utils import projectairsim_log

# Reuse the existing X8 initialization, finite-state guards and controller.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "x8_skywalker"))
from hello_x8_jsbsim import (  # noqa: E402
    CONTROL_PERIOD_NS, CONTROL_PERIOD_SEC, CRUISE_AIRSPEED_KTS, WAYPOINTS,
    ensure_finite_state, seed_air_launch,
)
from x8_autopilot import WaypointFollower, X8Autopilot  # noqa: E402


def main(max_sim_time: float, telemetry: Path | None = None) -> None:
    if not math.isfinite(max_sim_time) or max_sim_time < CONTROL_PERIOD_SEC:
        raise ValueError("--max-sim-time must be finite and at least 0.02 seconds")
    client = ProjectAirSimClient()
    connected = False
    rows = []
    try:
        projectairsim_log().warning(
            "TIGUAR VISUAL DEMO: using Skywalker X8 placeholder physics and controls"
        )
        client.connect()
        connected = True
        world = World(
            client, "scene_tiguar_jsbsim.jsonc", delay_after_load_sec=0,
            sim_config_path=str(SCRIPT_DIR / "sim_config"),
        )
        drone = Drone(client, world, "Tiguar")
        seed_air_launch(drone)
        autopilot = X8Autopilot(drone, CONTROL_PERIOD_SEC)
        autopilot.set_controls(elevator=0.0, aileron=0.0, throttle=1.0)
        follower = WaypointFollower(autopilot, WAYPOINTS)
        for iteration in range(int(max_sim_time / CONTROL_PERIOD_SEC)):
            ensure_finite_state(autopilot)
            complete = follower.update(CRUISE_AIRSPEED_KTS)
            world.continue_for_sim_time(CONTROL_PERIOD_NS)
            ensure_finite_state(autopilot)
            if iteration % 50 == 0:
                row = {
                    "time_s": (iteration + 1) * CONTROL_PERIOD_SEC,
                    "waypoint": follower.index + 1,
                    "altitude_ft": autopilot.get("position/h-sl-ft"),
                    "airspeed_kt": autopilot.get("velocities/vtrue-kts"),
                    "roll_rad": autopilot.get("attitude/phi-rad"),
                    "pitch_rad": autopilot.get("attitude/theta-rad"),
                }
                rows.append(row)
                projectairsim_log().info(f"Tiguar (X8 placeholder): {row}")
            if complete:
                projectairsim_log().info("Tiguar/X8 placeholder waypoint circuit completed")
                break
        else:
            projectairsim_log().info(f"Tiguar/X8 placeholder run completed: {max_sim_time}s")
        # The scene uses a paused steppable clock and remains paused after the run.
    finally:
        if connected:
            client.disconnect()
        if telemetry and rows:
            telemetry.parent.mkdir(parents=True, exist_ok=True)
            with telemetry.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-sim-time", type=float, default=20.0)
    parser.add_argument("--telemetry", type=Path)
    args = parser.parse_args()
    main(args.max_sim_time, args.telemetry)
