import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from games import life
# 由独立实现 (逐格 8 邻域) 手算 3x3 十字: k=1 期望全活
print(repr(life.solve("3 3 1\n.#.\n###\n.#.")))
# 用朴素参考实现对照
def ref(h, w, k, rows):
    g = [list(r) for r in rows]
    for _ in range(k):
        ng = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                a = sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                        if (dr or dc) and 0 <= r + dr < h and 0 <= c + dc < w
                        and g[r + dr][c + dc] == '#')
                ng[r][c] = '#' if (g[r][c] == '#' and a in (2, 3)) or (g[r][c] == '.' and a == 3) else '.'
        g = ng
    return '\n'.join(''.join(r) for r in g)
print(repr(ref(3, 3, 1, ['.#.', '###', '.#.'])))
