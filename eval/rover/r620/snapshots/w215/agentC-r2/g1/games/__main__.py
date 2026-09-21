"""CLI 入口: python3 -m games <game_id>

game_id 取 life / sub / nim / wythoff; 从 stdin 读全部文本,
调用对应模块的 solve, 把返回值写到 stdout (不加额外换行, stderr 静默)。
"""

import sys

from games import life, nim, sub, wythoff

_GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in _GAMES:
        return 1
    text = sys.stdin.read()
    out = _GAMES[argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
