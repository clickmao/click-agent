import sys

from . import life, sub, nim, wythoff

GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    game_id = sys.argv[1]
    data = sys.stdin.read()
    out = GAMES[game_id].solve(data)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
