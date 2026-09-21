import sys

from . import life, nim, sub, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    gid = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(_MODULES[gid].solve(text))


main()
