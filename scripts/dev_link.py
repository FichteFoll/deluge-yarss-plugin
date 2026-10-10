"""Link the source tree into a Deluge config directory for development.

Generates the `*.egg-info` metadata in the repository root
and writes an `.egg-link` file pointing to it into `<config>/plugins`,
so Deluge loads the plugin directly from the working tree.
"""

import argparse
import subprocess
import sys
from email.parser import HeaderParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def generate_egg_info() -> Path:
    subprocess.run(
        [sys.executable, "-c", "from setuptools import setup; setup()", "egg_info"],
        cwd=REPO_ROOT,
        check=True,
    )
    (egg_info,) = REPO_ROOT.glob("*.egg-info")
    return egg_info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("~/.config/deluge"),
        help="Deluge config directory (default: ~/.config/deluge)",
    )
    args = parser.parse_args()

    egg_info = generate_egg_info()
    name = HeaderParser().parsestr((egg_info / "PKG-INFO").read_text())["Name"]

    plugins_dir = args.config.expanduser() / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    egg_link = plugins_dir / f"{name}.egg-link"
    egg_link.write_text(f"{REPO_ROOT}\n")

    print(f"Generated {egg_info}")
    print(f"Wrote {egg_link} -> {REPO_ROOT}")
    print("Re-run this script after changing the project metadata or entry points.")


if __name__ == "__main__":
    main()
