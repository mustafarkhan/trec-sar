from glob import glob

from setuptools import setup

package_name = "trecsar_mission"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Mustafa R. Khan",
    maintainer_email="mustafarkhan@users.noreply.github.com",
    description="TREC-SAR link-aware search mission stack",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mission_manager = trecsar_mission.mission_manager:main",
            "link_sim = trecsar_mission.link_sim:main",
            "aerial_spotter = trecsar_mission.aerial_spotter:main",
            "sim_detector = trecsar_mission.sim_detector:main",
            "yolo_detector = trecsar_mission.yolo_detector:main",
        ],
    },
)
