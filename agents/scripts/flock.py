#!/usr/bin/env python3
"""
Portable flock wrapper using Python fcntl — works on macOS (no system flock) and Linux.

Modes:
  flock.py <lockfile> <timeout_sec> <shell_cmd>   Block acquiring lock, then run shell cmd
  flock.py --nb <lockfile> <shell_cmd>            Non-blocking: exit 1 if locked, else run

Lock files are created with 0o600 permissions.
Exit 0 = lock acquired + command succeeded
Exit 1 = lock held (non-blocking mode only)
Exit 2 = command exited non-zero
Exit 3 = error
"""
import fcntl, os, subprocess, sys

mode = sys.argv[1] if len(sys.argv) >= 2 else ""
if mode == "--nb":
    lockfile, cmd = sys.argv[2], sys.argv[3:]
else:
    lockfile, timeout, cmd = sys.argv[1], int(sys.argv[2]), sys.argv[3:]

os.makedirs(os.path.dirname(lockfile) or ".", exist_ok=True)
fd = os.open(lockfile, os.O_CREAT | os.O_RDWR, 0o600)

try:
    if mode == "--nb":
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: sys.exit(1)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX)
except OSError as e:
    sys.stderr.write(f"flock error: {e}\n")
    sys.exit(3)

try:
    r = subprocess.run(" ".join(cmd) if isinstance(cmd, list) else cmd,
                       shell=True, executable="/bin/bash")
    sys.exit(r.returncode)
finally:
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
