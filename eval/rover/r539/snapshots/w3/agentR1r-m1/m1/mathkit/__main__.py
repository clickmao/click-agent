import json
import sys


OP_MODULES = {
    "qr_count": ("mathkit.modular", "qr_count"),
    "choose": ("mathkit.modular", "choose"),
    "det": ("mathkit.linear", "det"),
    "shortest": ("mathkit.graphs", "shortest"),
    "expect": ("mathkit.prob", "expect"),
}


def main():
    op = sys.argv[1]
    args = json.loads(sys.stdin.read())
    modname, funcname = OP_MODULES[op]
    mod = __import__(modname, fromlist=[funcname])
    func = getattr(mod, funcname)
    sys.stdout.write(func(args))


if __name__ == "__main__":
    main()
