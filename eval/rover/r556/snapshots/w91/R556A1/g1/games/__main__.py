import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    if len(sys.argv) < 2:
        return
    game = sys.argv[1]
    if game not in MODULES:
        return
    text = sys.stdin.read()
    sys.stdout.write(MODULES[game].solve(text))


if __name__ == "__main__":
    main()
