"""CLI entry: python3 -m games <game_id> reads stdin, writes solve() result."""
import sys


def main():
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
    mods = {
        'life': 'games.life',
        'sub': 'games.sub',
        'nim': 'games.nim',
        'wythoff': 'games.wythoff',
    }
    name = mods.get(game_id)
    if name is None:
        return
    mod = __import__(name, fromlist=['solve'])
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
