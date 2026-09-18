import sys

def main():
    if len(sys.argv) < 2:
        return
    game = sys.argv[1]
    if game == 'life':
        from games import life as mod
    elif game == 'sub':
        from games import sub as mod
    elif game == 'nim':
        from games import nim as mod
    elif game == 'wythoff':
        from games import wythoff as mod
    else:
        return
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
