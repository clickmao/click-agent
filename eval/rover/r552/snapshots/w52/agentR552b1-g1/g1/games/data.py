"""games.data: 四款游戏的按行工具与规格常量。

本模块只提供纯解析/渲染辅助，不做任何 I/O。
所有游戏模块的 solve(text) 均以本模块的 lines(text) 拆行。
"""

from typing import List

# 生命游戏
LIFE_MIN_DIM = 1
LIFE_MAX_DIM = 20
LIFE_MIN_GENS = 0
LIFE_MAX_GENS = 20
LIFE_DEAD = '.'
LIFE_ALIVE = '#'

# 取石子子游戏（减法博弈）
SUB_MIN_N = 1
SUB_MAX_N = 80
SUB_MIN_K = 1
SUB_MAX_K = 12
SUB_MIN_STEP = 1
SUB_MAX_STEP = 12

# 多堆 Nim
NIM_MIN_HEAPS = 1
NIM_MAX_HEAPS = 4
NIM_MIN_PILE = 1
NIM_MAX_PILE = 15

# Wythoff
WYTHOFF_MIN_PILE = 1
WYTHOFF_MAX_PILE = 25


def lines(text: str) -> List[str]:
    """把 stdin 文本拆成「行」列表：先按 \\n 切分，再丢弃末尾空段。

    末尾换行只会产生一个空段，因此丢弃末尾所有空串既保留中间空行语义，
    又不让文件结尾的换行影响行数。
    """
    parts = text.split('\n')
    while parts and parts[-1] == '':
        parts.pop()
    return parts


def ints(line: str) -> List[int]:
    """把一行空白分隔的 token 解析为 int 列表。"""
    return [int(tok) for tok in line.split()]
