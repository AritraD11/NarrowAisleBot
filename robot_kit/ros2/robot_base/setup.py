import os
from glob import glob
from setuptools import setup

package_name = "robot_base"

setup(
    name=package_name,
    version="1.0.0",
    packages=[package_name, package_name + ".dashboard"],
    package_data={package_name + ".dashboard": ["static/*"]},
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "urdf"), glob("urdf/*.urdf")),
    ],
    install_requires=["setuptools"],
    zip_safe=False,
    maintainer="robot kit",
    maintainer_email="robot@example.com",
    description="Robot kit base stack",
    license="MIT",
    entry_points={
        "console_scripts": [
            "mcu_bridge = robot_base.mcu_bridge:main",
            "base_controller = robot_base.base_controller:main",
            "wheel_odometry = robot_base.wheel_odometry:main",
            "scan_filter = robot_base.scan_filter:main",
            "telemetry_logger = robot_base.telemetry_logger:main",
            "dashboard = robot_base.dashboard.server:main",
        ],
    },
)
