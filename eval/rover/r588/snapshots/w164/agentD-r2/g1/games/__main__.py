"""CLI entry point: python3 -m games <game_id>."""

import sys

if __name__ == "__main__":
    import games.life as life
    import games.sub as sub
    import games.nim as nim
    import games.wythoff as wythoff

    table = {
        "life": life.solve,
        "sub": sub.solve,
        "nim": nim.solve,
        "wythoff": wythoff.solve,
    }
    data = sys.stdin.read()
    sys.stdout.write(table[sys.argv[1]](data))
