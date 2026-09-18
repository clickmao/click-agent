import sys


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    mod = __import__('games.' + game_id, fromlist=['solve'])
    sys.stdout.write(mod.solve(text))


main()
