"""Build the Deluge plugin egg by repacking the wheel built with `uv build`.

The egg contains all wheel members unchanged,
plus an `EGG-INFO` directory with the metadata Deluge reads.
"""

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from email.parser import HeaderParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EGG_INFO_FILES = {
    "METADATA": "EGG-INFO/PKG-INFO",
    "entry_points.txt": "EGG-INFO/entry_points.txt",
    "top_level.txt": "EGG-INFO/top_level.txt",
}


def build_wheel(out_dir: Path) -> Path:
    uv = os.environ.get("UV", "uv")
    # setuptools builds in-tree and reuses `build/lib`,
    # so files from a previous package layout would leak into the wheel.
    shutil.rmtree(REPO_ROOT / "build", ignore_errors=True)
    # Build into an empty directory, so the produced wheel is unambiguous.
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([uv, "build", "--wheel", "--out-dir", tmp, str(REPO_ROOT)], check=True)
        (wheel,) = Path(tmp).glob("*.whl")
        out_dir.mkdir(parents=True, exist_ok=True)
        return Path(shutil.move(wheel, out_dir / wheel.name))


def egg_name_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "_", value)


# Deluge only loads plugins from eggs, never from wheels,
# and setuptools' `bdist_egg` is deprecated, so the wheel is repacked instead.
def wheel_to_egg(wheel: Path, out_dir: Path) -> Path:
    with zipfile.ZipFile(wheel) as whl:
        dist_info = next(name.split("/")[0] for name in whl.namelist() if name.split("/")[0].endswith(".dist-info"))
        metadata = HeaderParser().parsestr(whl.read(f"{dist_info}/METADATA").decode())
        egg_path = out_dir / f"{egg_name_part(metadata['Name'])}-{egg_name_part(metadata['Version'])}-py3.egg"
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(egg_path, "w", zipfile.ZIP_DEFLATED) as egg:
            for info in whl.infolist():
                if info.filename.startswith(f"{dist_info}/"):
                    continue
                egg.writestr(info, whl.read(info))
            for source, target in EGG_INFO_FILES.items():
                egg.writestr(target, whl.read(f"{dist_info}/{source}"))
    return egg_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--wheel", type=Path, help="repack this wheel instead of building one")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "dist", help="output directory (default: dist)")
    args = parser.parse_args()

    wheel = args.wheel or build_wheel(args.out_dir)
    print(wheel_to_egg(wheel, args.out_dir))


if __name__ == "__main__":
    main()
