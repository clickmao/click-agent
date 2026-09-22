import sys

import games.life
import games.sub
import games.nim
import games.wythoff

_MODULES = {
    "life": games.life,
    "sub": games.sub,
    "nim": games.nim,
    "wythoff": games.wythoff,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(_MODULES[game_id].solve(text))


if __name__ == "__main__":
    main()
