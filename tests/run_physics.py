"""Bounded Ubuntu-only contact/client checks against a localhost fake server."""

import argparse
import json
import pathlib
import subprocess
import sys
import time

# Finally blocks explicitly terminate bounded children before waiting.
# pylint: disable=consider-using-with

ROOT = pathlib.Path(__file__).resolve().parents[1]


def command(script, *args):
    """Run each Kit case in a fresh process using the existing interpreter."""
    return [sys.executable, str(ROOT / script), *map(str, args)]


def run(output):
    """Persist actual process statuses, reports and isolated GPU memory use."""
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in ("contact", "physics", "camera"):
        with (output / f"{name}.log").open("w") as log:
            result = subprocess.run(
                command(f"scripts/{name}_probe.py", "--output", output / name),
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=90,
            )
        report = json.loads((output / name / "report.json").read_text())
        results[name] = {
            "exit_code": result.returncode,
            "report": report,
            "passed": result.returncode == 0 and report["passed"],
        }
    for name, fault in (("client", None), ("nan", "nan"), ("stale", "stale")):
        results[name] = client_case(output, name, fault)
    summary = {
        "passed": all(r["passed"] for r in results.values()),
        "cases": results,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary["passed"]


def client_case(output, name, fault):
    """Check healthy or invalid chunks using actual rendering and physics."""
    server_args = ["--port", "18081", "--delay", "0.3"]
    if fault:
        server_args += ["--fault", fault]
    with (output / f"{name}-server.log").open("w") as server_log:
        server = subprocess.Popen(
            command("tests/fake_server.py", *server_args),
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(50):
                if (
                    "FAKE_SERVER_READY"
                    in (output / f"{name}-server.log").read_text()
                ):
                    break
                if server.poll() is not None:
                    raise RuntimeError("Fixture server failed to start")
                time.sleep(0.1)
            else:
                raise TimeoutError("Fixture server did not become ready")
            return execute_client(output, name, fault)
        finally:
            server.terminate()
            server.wait(timeout=5)


def execute_client(output, name, fault):
    """Sample total device VRAM during one isolated bounded client process."""
    args = command(
        "scripts/inference_client.py",
        "--server",
        "ws://127.0.0.1:18081",
        "--scene",
        ROOT / "scenes/tabletop_home/scene.usda",
        "--cameras",
        ROOT / "tests/fixtures/cameras.json",
        "--action-hz",
        "30",
        "--prompt",
        "fixture only",
        "--allow-fixture-cameras",
        "--chunks",
        "4",
        "--output",
        output / name,
    )
    with (output / f"{name}.log").open("w") as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        samples = []
        deadline = time.monotonic() + 90
        try:
            while process.poll() is None:
                if time.monotonic() > deadline:
                    raise TimeoutError("Client exceeded bounded test duration")
                memory = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                ).strip()
                samples.append(int(memory))
                time.sleep(0.5)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
    report = json.loads((output / name / "report.json").read_text())
    trace = json.loads((output / name / "trace.json").read_text())
    passed = (
        process.returncode == 0 and report["passed"] and len(trace) == 32
        if fault is None
        else process.returncode == 1 and not report["passed"] and not trace
    )
    return {
        "passed": passed,
        "exit_code": process.returncode,
        "report": report,
        "actions_executed": len(trace),
        "peak_device_memory_mib": max(samples),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    raise SystemExit(0 if run(parser.parse_args().output) else 1)
