"""CLI: python3 -m games <life|sub|nim|wythoff>."""
import sys


def main(argv):
    if len(argv) != 2:
        return
    game_id = argv[1]
    mods = {
        'life': 'games.life',
        'sub': 'games.sub',
        'nim': 'games.nim',
        'wythoff': 'games.wythoff',
    }
    if game_id not in mods:
        return
    mod = __import__(mods[game_id], fromlist=['solve'])
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main(sys.argv)
