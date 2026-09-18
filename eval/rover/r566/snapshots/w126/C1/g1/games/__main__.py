import sys

from . import life, sub, nim, wythoff

GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    module = GAMES[sys.argv[1]]
    text = sys.stdin.read()
    sys.stdout.write(module.solve(text))


if __name__ == "__main__":
    main()
