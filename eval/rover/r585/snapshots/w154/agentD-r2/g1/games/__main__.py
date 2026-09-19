import sys


def main():
    args = sys.argv[1:]
    if not args:
        return
    game_id = args[0]
    if game_id == 'life':
        from . import life as mod
    elif game_id == 'sub':
        from . import sub as mod
    elif game_id == 'nim':
        from . import nim as mod
    elif game_id == 'wythoff':
        from . import wythoff as mod
    else:
        return
    text = sys.stdin.read()
    result = mod.solve(text)
    sys.stdout.write(result)


if __name__ == '__main__':
    main()
