import sys

from . import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    if len(sys.argv) >= 2 and sys.argv[1] in _MODULES:
        data = sys.stdin.read()
        out = _MODULES[sys.argv[1]].solve(data)
        if out:
            sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
