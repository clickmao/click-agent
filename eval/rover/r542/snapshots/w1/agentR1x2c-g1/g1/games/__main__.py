import sys


def main():
    game_id = sys.argv[1] if len(sys.argv) > 1 else ''
    text = sys.stdin.read()
    if game_id == 'life':
        from games import life as mod
    elif game_id == 'sub':
        from games import sub as mod
    elif game_id == 'nim':
        from games import nim as mod
    elif game_id == 'wythoff':
        from games import wythoff as mod
    else:
        return
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
