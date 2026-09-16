"""Import geometry-only URDF assets with the existing Isaac 6.0.1 runtime."""

import argparse
import json
import pathlib


def main() -> None:
    """Convert arm and tool without playing physics or connecting to robots."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    sources = parser.parse_args().source_root.resolve()
    for name in ("ur_description", "robotiq_hande_description"):
        if not (sources / name / "meshes").is_dir():
            parser.error(f"Missing upstream mesh package: {sources / name}")
    # pylint: disable=import-outside-toplevel,import-error
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "multi_gpu": False})
    from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig

    root = pathlib.Path(__file__).resolve().parents[1]
    packages = [
        {"name": path.name, "path": str(path)}
        for path in sources.iterdir()
        if path.is_dir()
    ]
    results = {}
    try:
        for relative, name in (
            ("robots/ur12e", "ur12e"),
            ("grippers/hande", "hande"),
        ):
            directory = root / "assets" / relative
            config = URDFImporterConfig(
                urdf_path=str(directory / f"{name}.urdf"),
                usd_path=str(directory / "usd"),
                ros_package_paths=packages,
                merge_fixed_joints=False,
                merge_mesh=False,
                collision_from_visuals=False,
                collision_type="Convex Decomposition",
                allow_self_collision=True,
                fix_base=True,
                joint_target_type="none",
            )
            results[name] = URDFImporter(config).import_urdf()
        print(json.dumps(results), flush=True)
    finally:
        app.close()


if __name__ == "__main__":
    main()
