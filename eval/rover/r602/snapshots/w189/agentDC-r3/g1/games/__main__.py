import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    text = sys.stdin.read()
    sys.stdout.write(MODULES[sys.argv[1]].solve(text))


if __name__ == "__main__":
    main()
