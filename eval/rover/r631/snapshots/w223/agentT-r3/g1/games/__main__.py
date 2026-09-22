import sys

from . import life, nim, sub, wythoff

_SOLVERS = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main() -> None:
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = _SOLVERS[game_id](text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
