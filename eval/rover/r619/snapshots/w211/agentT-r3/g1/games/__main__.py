"""CLI entry point: python3 -m games <game_id>."""
import sys


def main() -> None:
    game = sys.argv[1]
    if game == 'life':
        from games import life as mod
    elif game == 'sub':
        from games import sub as mod
    elif game == 'nim':
        from games import nim as mod
    elif game == 'wythoff':
        from games import wythoff as mod
    else:
        return
    sys.stdout.write(mod.solve(sys.stdin.read()))


if __name__ == '__main__':
    main()
