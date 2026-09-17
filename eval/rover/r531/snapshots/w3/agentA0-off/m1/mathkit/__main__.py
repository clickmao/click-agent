"""CLI 入口: python3 -m mathkit <op>，从 stdin 读一个 JSON 对象，把结果写到 stdout。

用法:
    echo '{"a":11,"m":16}' | python3 -m mathkit qr_count

只允许标准库；stdout 恰好一行（答案本身），stderr 静默。
"""

import json
import sys

from . import modular, linear, graphs, prob

# op 名 -> 实现函数
_OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in _OPS:
        return 2
    raw = sys.stdin.read()
    try:
        args = json.loads(raw)
    except json.JSONDecodeError:
        return 2
    out = _OPS[argv[0]](args)
    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
