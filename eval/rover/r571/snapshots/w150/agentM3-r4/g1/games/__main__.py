import sys

from games import life, nim, sub, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MODULES:
        return
    sys.stdout.write(MODULES[sys.argv[1]].solve(sys.stdin.read()))


if __name__ == "__main__":
    main()
