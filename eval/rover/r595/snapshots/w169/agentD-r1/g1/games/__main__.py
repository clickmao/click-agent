import sys
from games import life, sub, nim, wythoff

MODULES = {"life": life, "sub": sub, "nim": nim, "wythoff": wythoff}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(MODULES[game_id].solve(text))


if __name__ == "__main__":
    main()
