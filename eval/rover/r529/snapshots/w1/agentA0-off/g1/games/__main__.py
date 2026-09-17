"""CLI 入口: python3 -m games <game_id>

从标准输入读取全部文本, 调用对应模块 solve, 把返回值写到标准输出。
game_id 取值: life / sub / nim / wythoff。stderr 保持静默。
"""
import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _MODULES:
        # 非法调用: 静默失败, 非零退出
        return 2
    text = sys.stdin.read()
    out = _MODULES[argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
