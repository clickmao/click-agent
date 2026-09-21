"""python3 -m games <game_id>：从 stdin 读全文，调用对应 solve，写 stdout。"""

import importlib
import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    game_id = sys.argv[1]
    if game_id not in ("life", "sub", "nim", "wythoff"):
        return 1
    mod = importlib.import_module("games." + game_id)
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
