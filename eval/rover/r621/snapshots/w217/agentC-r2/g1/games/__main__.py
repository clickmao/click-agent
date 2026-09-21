import sys

from games import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    game_id = argv[1] if len(argv) > 1 else ""
    mod = MODULES.get(game_id)
    if mod is None:
        return
    text = sys.stdin.read()
    out = mod.solve(text)
    if out:
        sys.stdout.write(out)


if __name__ == "__main__":
    main(sys.argv)
