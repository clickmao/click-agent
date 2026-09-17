import sys

from games import life, sub, nim, wythoff

MODS = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    gid = sys.argv[1]
    text = sys.stdin.read()
    out = MODS[gid].solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
