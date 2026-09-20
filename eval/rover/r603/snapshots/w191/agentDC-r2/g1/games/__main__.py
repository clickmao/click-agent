import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        return 2
    game_id = argv[0]
    mod = MODULES.get(game_id)
    if mod is None:
        return 2
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
