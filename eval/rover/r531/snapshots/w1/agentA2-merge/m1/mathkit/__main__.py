"""mathkit CLI 入口: ``python3 -m mathkit <op>``。

从标准输入读取一个 JSON 对象作为参数, 调用对应模块的对应函数,
把返回值 (末尾不带换行) 写到标准输出。仅允许标准库;
不得向 stdout/stderr 打印任何多余文字。
"""

import json
import sys

from mathkit import graphs, linear, modular, prob

# op 名 -> 处理函数
_OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main(argv: list) -> int:
    if len(argv) != 2 or argv[1] not in _OPS:
        # 静默失败: 契约要求 stderr 亦须静默
        return 2
    op = argv[1]
    raw = sys.stdin.read()
    try:
        args = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 2
    result = _OPS[op](args)
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
