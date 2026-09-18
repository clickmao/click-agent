import sys


GAMES = ('life', 'sub', 'nim', 'wythoff')


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in GAMES:
        return
    sys.stdout.write(''.join(sys.stdin.read()))


if __name__ == '__main__':
    main()
