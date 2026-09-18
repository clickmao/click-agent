import sys

from . import life, nim, sub, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    game = sys.argv[1]
    data = sys.stdin.read()
    sys.stdout.write(MODULES[game].solve(data))


if __name__ == "__main__":
    main()
