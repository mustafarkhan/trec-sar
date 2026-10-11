# Running TREC-SAR

## A. 2D simulator (Windows, macOS or Linux)

```bash
git clone https://github.com/mustafarkhan/trec-sar.git && cd trec-sar
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e "core[viz,test]"
pytest -q core/tests
python3 scripts/run_experiments.py --runs 200            # ~3 min on 2 cores
python3 scripts/make_figures.py
```

Change a scenario parameter (e.g. radio power in `core/trecsar_core/link.py`, relays or time limits in
`core/trecsar_core/scenarios.py`) and re-run to see how the conclusions move. That is the point of the benchmark.

## B. 3D demo — ROS 2 Jazzy + Gazebo Harmonic

### Option 1: Ubuntu 24.04 (native or dual boot) — recommended

```bash
# ROS 2 Jazzy: follow https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html, then:
sudo apt install ros-jazzy-ros-gz ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
                 ros-jazzy-slam-toolbox ros-jazzy-xacro ros-jazzy-joint-state-publisher python3-scipy
pip install -e core --break-system-packages
cd ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch trecsar_bringup bringup.launch.py scenario:=forest_winter planner:=trecsar
```

### Option 2: Windows 11 with WSL2

Install Ubuntu 24.04 from the Microsoft Store, then follow Option 1 inside it. WSLg shows the Gazebo and RViz
windows. Expect lower frame rates; start with `scenario:=hazmat_industrial` (smallest world).

### Option 3: Docker

```bash
docker build -t trecsar -f docker/Dockerfile .
xhost +local:docker            # Linux, to show GUIs
docker run --rm -it --net=host -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix trecsar \
  ros2 launch trecsar_bringup bringup.launch.py scenario:=tunnel
```

### What you should see

- Gazebo: the scenario world (snow and spruce, tunnels, or tank farm) and the tracked UGV at the command post.
- RViz: SLAM map, the probability map shrinking where the robot has looked, relay markers, Nav2 plan, and an
  **operator video panel that goes black when the link drops**.
- Terminal: state changes (`SEARCH`, `LINK_RECOVERY`, `REPORT`, `DONE`) and the final `CASUALTY REPORTED` JSON.

### Useful commands

```bash
ros2 topic echo /trecsar/state
ros2 topic echo /link/margin_db
ros2 topic echo /trecsar/report
ros2 launch trecsar_bringup bringup.launch.py scenario:=forest_winter planner:=greedy_bayes   # compare
ros2 run trecsar_mission yolo_detector --ros-args -p image_topic:=/camera/image              # image detector
```

### Regenerating worlds (after changing a scenario)

```bash
python3 ros2_ws/src/trecsar_gazebo/scripts/terrain_to_sdf.py forest_winter --seed 1002
```

Keep the seed equal to `casualty_seed` in `trecsar_bringup/launch/bringup.launch.py`.

### First-run troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Robot does not move | Nav2 lifecycle not active yet | Wait ~20 s; check `ros2 lifecycle get /controller_server` |
| `Nav2 not ready yet` repeats | navigation_launch failed on a parameter | Read the first error in the terminal; adjust `nav2_params.yaml` |
| No `/trecsar/ground_truth_pose` | Pose bridge topic name differs in your Gazebo version | `gz topic -l` and edit `trecsar_gazebo/config/bridge.yaml` |
| Robot spins in place | Skid-steer friction too high | Lower `mu2` in the xacro or `rotate_to_heading_angular_vel` |
| Very slow simulation | Forest world has ~1,500 collision shapes | Use hazmat/tunnel first; lower lidar samples |
