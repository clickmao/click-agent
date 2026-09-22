"""CLI entry: python3 -m games <game_id> reads all stdin and writes solve() output."""
import sys

from games import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    game = sys.argv[1]
    text = sys.stdin.read()
    out = _MODULES[game].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
