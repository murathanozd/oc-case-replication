"""Step 7:  python -m r2_python.environment  ->  results/r2/environment.json (Python, packages, OS)."""

from __future__ import annotations

import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .run_all import ROOT, write_json


def packages() -> dict[str, str]:
    out = {}
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        name = line.split("==")[0].strip()
        if name:
            try:
                out[name] = version(name)
            except PackageNotFoundError:
                out[name] = "not installed"
    return dict(sorted(out.items()))


def main() -> None:
    write_json("environment", {
        "python": platform.python_version(),
        "packages": packages(),
        "used_by_r2": {"implementation": "standard library only", "tests": ["pytest", "networkx"]},
        "os": {"system": platform.system(), "macos": platform.mac_ver()[0] or None,
               "kernel": platform.release(), "machine": platform.machine()},
    })
    print(f"wrote {Path('results/r2/environment.json')}")


if __name__ == "__main__":
    main()
