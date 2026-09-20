"""CLI 入口: python3 -m games <game_id>, game_id ∈ {life,sub,nim,wythoff}。"""

import sys


def main() -> None:
    game_id = sys.argv[1]
    data = sys.stdin.read()
    if game_id == 'life':
        from . import life as mod
    elif game_id == 'sub':
        from . import sub as mod
    elif game_id == 'nim':
        from . import nim as mod
    elif game_id == 'wythoff':
        from . import wythoff as mod
    else:
        return
    sys.stdout.write(mod.solve(data))


if __name__ == '__main__':
    main()
