from glob import glob

from setuptools import setup

package_name = "luotsi_mission"

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
    description="LUOTSI link-aware search mission stack",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mission_manager = luotsi_mission.mission_manager:main",
            "link_sim = luotsi_mission.link_sim:main",
            "aerial_spotter = luotsi_mission.aerial_spotter:main",
            "sim_detector = luotsi_mission.sim_detector:main",
            "yolo_detector = luotsi_mission.yolo_detector:main",
        ],
    },
)
