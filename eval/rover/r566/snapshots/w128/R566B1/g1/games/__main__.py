"""CLI 入口: python3 -m games <game_id>, 从 stdin 读全文, 输出 solve 结果。"""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    if len(sys.argv) < 2:
        return
    gid = sys.argv[1]
    mod = _MODULES.get(gid)
    if mod is None:
        return
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
