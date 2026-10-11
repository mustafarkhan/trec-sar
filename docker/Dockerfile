# ROS 2 Jazzy + Gazebo Harmonic + Nav2 + slam_toolbox + TREC-SAR
FROM osrf/ros:jazzy-desktop
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-ros-gz ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
      ros-jazzy-xacro ros-jazzy-joint-state-publisher python3-pip python3-scipy python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /trecsar
COPY . /trecsar
RUN pip install --break-system-packages -e core
RUN . /opt/ros/jazzy/setup.sh && cd ros2_ws && colcon build --symlink-install
RUN echo "source /opt/ros/jazzy/setup.bash && source /trecsar/ros2_ws/install/setup.bash" >> /root/.bashrc
SHELL ["/bin/bash", "-c"]
ENTRYPOINT ["/bin/bash", "-c", "source /opt/ros/jazzy/setup.bash && source /trecsar/ros2_ws/install/setup.bash && exec \"$@\"", "--"]
CMD ["bash"]
