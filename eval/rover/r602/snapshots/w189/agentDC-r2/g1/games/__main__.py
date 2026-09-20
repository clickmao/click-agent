"""CLI 入口：python3 -m games <game_id>，game_id 取 life/sub/nim/wythoff。

从标准输入读取全部文本，调用对应模块的 solve，将其返回值写到标准输出。
不打印任何额外文字，任何异常都在 stderr 之外被吞掉以保持静默。
"""
import sys


def main() -> int:
    argv = sys.argv[1:]
    game_id = argv[0] if argv else ""
    text = sys.stdin.read()
    if game_id == "life":
        import games.life as mod
    elif game_id == "sub":
        import games.sub as mod
    elif game_id == "nim":
        import games.nim as mod
    elif game_id == "wythoff":
        import games.wythoff as mod
    else:
        return 1
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
