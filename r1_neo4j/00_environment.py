"""Record the R1 environment (Neo4j/APOC versions as reported by the server, Python,
package versions, OS) in results/r1/environment.json."""

import json
import platform
import subprocess
from importlib.metadata import version

from common import RESULTS_DIR, Runner, get_driver

PACKAGES = ["neo4j", "pandas", "numpy", "networkx", "matplotlib", "pm4py"]


def macos_version():
    try:
        return subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


def main():
    driver = get_driver()
    try:
        runner = Runner(driver, verbose=False)
        [dbms] = runner.run("CALL dbms.components() YIELD name, versions, edition "
                            "RETURN name, versions[0] AS version, edition")
        [apoc] = runner.run("RETURN apoc.version() AS version")
    finally:
        driver.close()

    env = {
        "neo4j": {"name": dbms["name"], "version": dbms["version"], "edition": dbms["edition"]},
        "apoc": apoc["version"],
        "python": platform.python_version(),
        "packages": {p: version(p) for p in PACKAGES},
        "os": {"system": platform.system(), "macos": macos_version(),
               "kernel": platform.release(), "machine": platform.machine()},
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "environment.json", "w") as f:
        json.dump(env, f, indent=2)
    print(json.dumps(env, indent=2))


if __name__ == "__main__":
    main()
