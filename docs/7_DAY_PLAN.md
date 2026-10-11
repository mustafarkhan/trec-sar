# Your 7 days

The code and results already exist. The week is about **running it yourself, understanding it well enough to defend
it, and making it visible.**

| Day | Do | Output |
|---|---|---|
| 1 | Create the GitHub repo `trecsar`, push everything. Run `pytest` and `run_experiments.py` on your laptop; confirm your numbers match `results/summary.md`. | Repo public; LinkedIn post 1 |
| 2 | Read `core/trecsar_core/planner.py` and `sim.py` end to end. Change one parameter (e.g. relays, radio power) and re-run. Write down what changed and why. | Post 2 with the forest map |
| 3 | Install Ubuntu 24.04 (dual boot or WSL2) and ROS 2 Jazzy, or build the Docker image. `colcon build`. | Post 3 (method) |
| 4 | Run `bringup.launch.py scenario:=hazmat_industrial`. Fix whatever breaks first (Nav2 params, bridge topics) — that debugging is real experience. Record the screen. | Post 4 (results) |
| 5 | Run the forest and tunnel scenarios. Compare `planner:=trecsar` and `planner:=greedy_bayes`. Record a 2-minute demo video. | Post 5 with video |
| 6 | Open `perception/train_sar_yolo.ipynb` in Colab and train the thermal detector. Put the test metrics in `results/perception_metrics.json` and the README. | Post 6 (failure modes) |
| 7 | Update CV (see `docs/CV_LINKEDIN.md`) and LinkedIn Projects/Featured. Apply to 5 roles. | Post 7; applications sent |

If day 3–5 go badly (they sometimes do with ROS installs), the 2D benchmark, results and docs are already a
complete, honest portfolio piece. Say "3D stack in progress" rather than skipping the post.
