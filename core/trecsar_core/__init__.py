"""TREC-SAR core — link-aware Bayesian search for search-and-rescue ground robots.

Pure Python (numpy/scipy). No ROS dependency, so it runs on any laptop and is
wrapped by the ROS 2 nodes in ros2_ws/src/trecsar_mission.
"""
from .belief import Belief, prior_map
from .detector import Detector
from .link import LinkModel
from .planner import PLANNERS, PathOracle
from .scenarios import SCENARIOS, Scenario, build
from .sim import RunResult, World, run

__all__ = ["Belief", "prior_map", "Detector", "LinkModel", "PLANNERS", "PathOracle",
           "SCENARIOS", "Scenario", "build", "RunResult", "World", "run"]
__version__ = "0.1.0"
