import sys

import games.life as life
import games.nim as nim
import games.sub as sub
import games.wythoff as wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game_id = sys.argv[1] if len(sys.argv) > 1 else ''
    mod = MODULES.get(game_id)
    if mod is None:
        return
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
