import sys
from . import life, sub, nim, wythoff

GAME = {"life": life, "sub": sub, "nim": nim, "wythoff": wythoff}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = GAME[game_id].solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
