"""CLI 入口: python3 -m games <game_id>  (life|sub|nim|wythoff).

从 stdin 读全部文本, 调对应模块的 solve, 结果写 stdout(不多写一个换行;
用 sys.stdout.write 保持字节级可控). stderr 静默.
"""
import sys


def _load(gid):
    if gid == "life":
        from games import life as mod
    elif gid == "sub":
        from games import sub as mod
    elif gid == "nim":
        from games import nim as mod
    elif gid == "wythoff":
        from games import wythoff as mod
    else:
        return None
    return mod


def main(argv):
    if len(argv) < 2:
        return 2
    mod = _load(argv[1])
    if mod is None:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
