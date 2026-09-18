"""CLI entry point: python3 -m games <game_id>

<game_id> is one of life/sub/nim/wythoff. The whole standard input is read,
the module's solve() is called, and its return value is written to standard
output verbatim (no trailing newline added). Nothing is written to stderr.
"""

import sys


def main(argv):
    if len(argv) != 2:
        return 0
    game_id = argv[1]
    modules = {
        'life': 'games.life',
        'sub': 'games.sub',
        'nim': 'games.nim',
        'wythoff': 'games.wythoff',
    }
    if game_id not in modules:
        return 0
    __import__(modules[game_id])
    mod = sys.modules[modules[game_id]]
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
