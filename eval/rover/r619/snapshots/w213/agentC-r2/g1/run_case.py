"""Run a public case through the package and print stdout for byte comparison."""

import subprocess
import sys

CASE = sys.argv[1]
GAME = sys.argv[2]
data = sys.stdin.buffer.read()
res = subprocess.run(
    [sys.executable, "-m", "games", GAME], input=data, stdout=subprocess.PIPE
)
sys.stdout.buffer.write(res.stdout)
