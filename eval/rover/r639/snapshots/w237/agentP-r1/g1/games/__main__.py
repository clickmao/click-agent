"""CLI: python3 -m games <life|sub|nim|wythoff>"""
import sys

from games import life, nim, sub, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in _MODULES:
        return
    text = sys.stdin.read()
    out = _MODULES[sys.argv[1]].solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
