import sys


def main():
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
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
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
