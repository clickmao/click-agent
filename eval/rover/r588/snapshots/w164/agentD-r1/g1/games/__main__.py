import sys

from games import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) < 2:
        return
    game_id = argv[1]
    mod = MODULES.get(game_id)
    if mod is None:
        return
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    sys.stdout.flush()


if __name__ == "__main__":
    main(sys.argv)
