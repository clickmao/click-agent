import sys

def main():
    args = sys.argv[1:]
    if not args:
        return
    gid = args[0]
    text = sys.stdin.read()
    mod = __import__('games.' + gid, fromlist=['solve'])
    out = mod.solve(text)
    sys.stdout.write(out)

if __name__ == '__main__':
    main()
