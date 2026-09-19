import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    if len(sys.argv) < 2:
        return
    mod = _MODULES.get(sys.argv[1])
    if mod is None:
        return
    out = mod.solve(sys.stdin.read())
    if out:
        sys.stdout.write(out)


if __name__ == '__main__':
    main()
