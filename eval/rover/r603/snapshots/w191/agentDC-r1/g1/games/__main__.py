import sys

from . import life, nim, sub, wythoff

MODULES = {"life": life, "sub": sub, "nim": nim, "wythoff": wythoff}


def main():
    gid = sys.argv[1]
    text = sys.stdin.read()
    out = MODULES[gid].solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
