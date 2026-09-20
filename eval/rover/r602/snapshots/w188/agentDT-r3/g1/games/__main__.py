"""CLI entry point: python3 -m games <game_id>."""

import sys


def main() -> None:
    game_id = sys.argv[1].strip()
    if game_id not in ('life', 'sub', 'nim', 'wythoff'):
        return
    if game_id == 'life':
        from games import life as module
    elif game_id == 'sub':
        from games import sub as module
    elif game_id == 'nim':
        from games import nim as module
    else:
        from games import wythoff as module

    text = sys.stdin.read()
    out = module.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
