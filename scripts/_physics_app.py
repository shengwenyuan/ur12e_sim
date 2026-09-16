"""Shared startup for independent Isaac physics tools."""

import argparse
import json
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "runtime"), str(ROOT / ".deps/inference")]


def run(args, task):
    """Start Kit before importing physics modules and persist all outcomes."""
    # Isaac extensions become importable only after SimulationApp starts.
    # pylint: disable=import-outside-toplevel,import-error
    from isaacsim import SimulationApp

    # pylint: enable=import-outside-toplevel,import-error

    args.output.mkdir(parents=True, exist_ok=True)
    app = SimulationApp(
        {
            "headless": not getattr(args, "gui", False),
            "multi_gpu": False,
            "width": 640,
            "height": 480,
            "fast_shutdown": True,
        }
    )
    report = {"passed": False}
    try:
        report = task(app, ROOT, args)
    # CLI boundary records failures before closing Kit; no retry or motion.
    # pylint: disable=broad-exception-caught
    except (Exception, KeyboardInterrupt) as error:
        report["error"] = str(error) or type(error).__name__
        traceback.print_exc()
    finally:
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        print("RESULT", report, flush=True)
        app.close(exit_code=0 if report["passed"] else 1)
    return 0 if report["passed"] else 1


def diagnostic(task):
    """Common CLI for bounded, headless physics diagnostics."""
    parser = argparse.ArgumentParser(description=task.__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return run(parser.parse_args(), task)
