import sys

from games import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MODULES:
        return
    text = sys.stdin.read()
    sys.stdout.write(MODULES[sys.argv[1]].solve(text))


if __name__ == "__main__":
    main()
