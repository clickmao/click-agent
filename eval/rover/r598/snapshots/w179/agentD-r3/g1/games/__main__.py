import sys

from games import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    game_id = sys.argv[1] if len(sys.argv) > 1 else ""
    text = sys.stdin.read()
    game = MODULES.get(game_id)
    if game is None:
        sys.exit(1)
    sys.stdout.write(game.solve(text))


if __name__ == "__main__":
    main()
