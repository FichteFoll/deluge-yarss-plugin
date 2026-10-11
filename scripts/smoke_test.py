"""Check that a plugin egg loads and enables in a throwaway Deluge daemon.

Starts `deluged` with a temporary config directory containing the egg,
enables the plugin through `deluge-console`
and waits for the plugin's `Enabled <Name>` and Deluge's `Plugin <Name> enabled` log lines.
Exits non-zero if they do not appear or the log contains a traceback.
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from email.parser import HeaderParser
from pathlib import Path

NAMESPACE_WARNING = 'is not using the "deluge_" namespace'
TAIL_LINES = 60


class SmokeTestError(Exception):
    pass


def find_executable(name: str) -> str:
    sibling = Path(sys.executable).parent / name
    if sibling.is_file():
        return str(sibling)
    return shutil.which(name) or name


def plugin_name(egg: Path) -> str:
    with zipfile.ZipFile(egg) as zf:
        return HeaderParser().parsestr(zf.read("EGG-INFO/PKG-INFO").decode())["Name"]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def read_text(path: Path) -> str:
    return path.read_text(errors="replace") if path.is_file() else ""


def wait_for_port(port: int, daemon: subprocess.Popen, deadline: float) -> None:
    while time.monotonic() < deadline:
        if daemon.poll() is not None:
            raise SmokeTestError(f"deluged exited with code {daemon.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise SmokeTestError(f"deluged did not listen on port {port}")


def localclient_password(config_dir: Path) -> str:
    for line in (config_dir / "auth").read_text().splitlines():
        username, password, *_ = line.split(":")
        if username == "localclient":
            return password
    raise SmokeTestError("no localclient entry in auth file")


def wait_for_log_lines(log_file: Path, lines: list[str], daemon: subprocess.Popen, deadline: float) -> None:
    while time.monotonic() < deadline:
        log = read_text(log_file)
        if "Traceback" in log:
            raise SmokeTestError("log contains a traceback")
        if all(line in log for line in lines):
            return
        if daemon.poll() is not None:
            raise SmokeTestError(f"deluged exited with code {daemon.returncode}")
        time.sleep(0.5)
    missing = [line for line in lines if line not in read_text(log_file)]
    raise SmokeTestError(f"not logged: {', '.join(repr(line) for line in missing)}")


def stop(daemon: subprocess.Popen) -> None:
    daemon.terminate()
    try:
        daemon.wait(timeout=30)
    except subprocess.TimeoutExpired:
        daemon.kill()
        daemon.wait()


def print_tail(label: str, path: Path) -> None:
    if not path.is_file():
        return
    print(f"--- {label} ({path.name}) ---", file=sys.stderr)
    print("\n".join(read_text(path).splitlines()[-TAIL_LINES:]), file=sys.stderr)


def run(args: argparse.Namespace, config_dir: Path) -> bool:
    name = plugin_name(args.egg)
    plugins_dir = config_dir / "plugins"
    plugins_dir.mkdir()
    shutil.copy(args.egg, plugins_dir)
    log_file = config_dir / "deluged.log"
    stderr_file = config_dir / "deluged.stderr"
    port = free_port()
    deadline = time.monotonic() + args.timeout
    # The importlib plugin loader reports plugins outside the `deluge_` namespace
    # as a DeprecationWarning, which is hidden by default.
    warnings_filter = ",".join(filter(None, [os.environ.get("PYTHONWARNINGS"), "default::DeprecationWarning"]))
    env = {**os.environ, "PYTHONWARNINGS": warnings_filter}

    try:
        with stderr_file.open("wb") as stderr:
            daemon = subprocess.Popen(
                [args.deluged, "-c", config_dir, "-d", "-L", "info", "-l", log_file]
                + ["-p", str(port), "-i", "127.0.0.1", "-u", "127.0.0.1"],
                stderr=stderr,
                env=env,
            )
        try:
            wait_for_port(port, daemon, deadline)
            subprocess.run(
                [args.console, "-c", config_dir, "-d", "127.0.0.1", "-p", str(port)]
                + ["-U", "localclient", "-P", localclient_password(config_dir), f"plugin --enable {name}"],
                check=True,
                timeout=max(deadline - time.monotonic(), 1),
            )
            wait_for_log_lines(log_file, [f"Enabled {name}", f"Plugin {name} enabled"], daemon, deadline)
        finally:
            stop(daemon)
        if "Traceback" in read_text(log_file):
            raise SmokeTestError("log contains a traceback")
    except (SmokeTestError, OSError, subprocess.SubprocessError) as ex:
        print(f"Smoke test failed: {ex}", file=sys.stderr)
        print_tail("deluged log", log_file)
        print_tail("deluged stderr", stderr_file)
        return False

    for line in read_text(stderr_file).splitlines():
        if NAMESPACE_WARNING in line:
            print(f"Notice: the plugin loader warned: {line.strip()}")
    print(f"Smoke test passed: {name} enabled in {args.deluged}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("egg", type=Path, help="plugin egg to test")
    parser.add_argument("--deluged", default=find_executable("deluged"), help="deluged executable")
    parser.add_argument("--console", default=find_executable("deluge-console"), help="deluge-console executable")
    parser.add_argument("--timeout", type=float, default=60, help="seconds to wait in total (default: 60)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="deluge-smoke-") as tmp:
        sys.exit(0 if run(args, Path(tmp)) else 1)


if __name__ == "__main__":
    main()
