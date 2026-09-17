"""mathkit 的 CLI 入口：`python3 -m mathkit <op>`。

从标准输入读取一个 JSON 对象作为参数，调用对应模块的对应函数，
把返回值写到标准输出。仅输出一行答案，无任何多余文字（stderr 亦静默）。
"""

import json
import sys

from mathkit import graphs, linear, modular, prob

# op -> 实现函数（每个 op 一个纯函数，签名 op(args: dict) -> str）
OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main(argv) -> int:
    """命令行主入口；成功返回 0，失败返回非 0（不打印任何错误文本）。"""
    if len(argv) < 2:
        return 2
    op = argv[1]
    fn = OPS.get(op)
    if fn is None:
        return 2

    raw = sys.stdin.read()
    args = json.loads(raw) if raw.strip() else {}
    out = fn(args)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
