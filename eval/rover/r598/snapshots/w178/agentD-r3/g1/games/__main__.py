import sys


def main():
    game_id = sys.argv[1]
    mod = __import__("games." + game_id, fromlist=["solve"])
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == "__main__":
    main()
