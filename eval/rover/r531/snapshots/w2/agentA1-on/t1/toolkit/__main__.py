"""CLI 入口: python3 -m toolkit <vm|jsonmini> (也可用别名 vm_run / json_mini)."""
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    data = sys.stdin.read()
    if not argv:
        return 2
    cmd = argv[0]
    if cmd in ("vm", "vm_run"):
        from . import vm as mod
    elif cmd in ("jsonmini", "json_mini"):
        from . import jsonmini as mod
    else:
        return 2
    sys.stdout.write(mod.solve(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
