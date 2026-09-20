import io
import sys

from . import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}

def main():
    game_id = sys.argv[1] if len(sys.argv) > 1 else ''
    text = sys.stdin.read()
    mod = _MODULES.get(game_id)
    if mod is None:
        return
    sys.stdout.write(mod.solve(text))

if __name__ == '__main__':
    main()
