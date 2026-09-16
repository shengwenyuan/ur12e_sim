"""Expand pinned Xacros into geometry-only URDFs using Ubuntu ROS Jazzy."""

import argparse
import os
import pathlib
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def prepare(root: pathlib.Path, sources: pathlib.Path) -> None:
    """Resolve external pinned packages and remove all hardware plugins."""
    models = {
        "ur12e": (
            "ur_description",
            "ur.urdf.xacro",
            ["ur_type:=ur12e", "name:=ur12e"],
        ),
        "hande": (
            "robotiq_hande_description",
            "robotiq_hande_gripper.urdf.xacro",
            [],
        ),
    }
    with tempfile.TemporaryDirectory() as temporary:
        prefix = pathlib.Path(temporary)
        index = prefix / "share/ament_index/resource_index/packages"
        index.mkdir(parents=True)
        for package in sources.iterdir():
            if package.is_dir():
                (index / package.name).touch()
                (prefix / "share" / package.name).symlink_to(package.resolve())
        for name, (package, filename, args) in models.items():
            source = sources / package / "urdf" / filename
            result = subprocess.run(
                ["xacro", str(source), *args],
                env=dict(os.environ, AMENT_PREFIX_PATH=str(prefix)),
                check=True,
                capture_output=True,
                text=True,
            )
            robot = ET.fromstring(result.stdout)
            for plugin in robot.findall("ros2_control"):
                robot.remove(plugin)
            output = (
                root
                / "assets"
                / ("robots/ur12e" if name == "ur12e" else "grippers/hande")
            )
            output.mkdir(parents=True, exist_ok=True)
            ET.indent(robot)
            ET.ElementTree(robot).write(
                output / f"{name}.urdf", encoding="utf-8", xml_declaration=True
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    arguments = parser.parse_args()
    prepare(pathlib.Path(__file__).resolve().parents[1], arguments.source_root)
