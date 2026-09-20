import sys

from . import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    if len(sys.argv) < 2:
        return
    game = sys.argv[1]
    mod = _MODULES.get(game)
    if mod is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == "__main__":
    main()
