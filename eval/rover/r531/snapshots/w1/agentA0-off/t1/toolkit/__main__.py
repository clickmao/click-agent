"""CLI 入口: python3 -m toolkit <vm|jsonmini>。stdin 读全部文本, 调 solve, 写 stdout。"""

import sys

from . import vm, jsonmini

_COMMANDS = {
    "vm": vm.solve,
    "jsonmini": jsonmini.solve,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _COMMANDS:
        return 2
    text = sys.stdin.read()
    try:
        result = _COMMANDS[argv[0]](text)
    except Exception:
        result = "ERR"
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
