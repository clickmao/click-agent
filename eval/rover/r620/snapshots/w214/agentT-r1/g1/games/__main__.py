import sys

from . import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    game_id = sys.argv[1] if len(sys.argv) > 1 else ""
    mod = _MODULES.get(game_id)
    if mod is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == "__main__":
    main()
