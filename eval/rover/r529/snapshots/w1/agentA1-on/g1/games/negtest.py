"""负向控制: 人为注入缺陷后, 判定必须变红 (证明用例非空转); 恢复后必须变绿。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from games import life, sub, nim, wythoff

fails = 0

LIFE_IN = "3 3 1\n.#.\n###\n.#."
LIFE_EXP = "###\n#.#\n###"   # 十字 k=1: 中心 4 邻居 -> 死; 上下左右 3 邻居 -> 活

orig_life = life._step


def bad_step(grid, h, w):
    """注入缺陷: 死细胞复活阈值改 4, 活细胞存活阈值改 3/4。"""
    out = [['.'] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            alive = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                        alive += 1
            if grid[r][c] == '#':
                out[r][c] = '#' if alive in (3, 4) else '.'
            else:
                out[r][c] = '#' if alive == 4 else '.'
    return out


assert life.solve(LIFE_IN) == LIFE_EXP, "基线生命游戏失败: %r" % life.solve(LIFE_IN)
life._step = bad_step
if life.solve(LIFE_IN) == LIFE_EXP:
    fails += 1
    print("NEG-FAIL life: 注入缺陷后仍全绿")
else:
    print("NEG-OK life 注入后变红")
life._step = orig_life
if life.solve(LIFE_IN) != LIFE_EXP:
    fails += 1
    print("NEG-FAIL life: 恢复后不绿")
else:
    print("NEG-OK life 恢复后变绿")

# 2) sub: 把 dp[0] 基准从"必败"改成"必胜" -> 判定全错
def bad_sub(text):
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()][:k]
    win = [True] * (n + 1)
    for x in range(1, n + 1):
        win[x] = any(s <= x and not win[x - s] for s in steps)
    if not win[n]:
        return 'LOSE'
    return 'WIN %d' % next(s for s in sorted(steps) if s <= n and not win[n - s])


if bad_sub("19 1\n1") == "WIN 1":
    fails += 1
    print("NEG-FAIL sub: 注入缺陷后仍全绿")
else:
    print("NEG-OK sub 注入后变红, 恢复后 =", sub.solve("19 1\n1"))

# 3) nim: 破坏异或判定 (永远 LOSE)
if 'LOSE' == "WIN 1 3":
    fails += 1
    print("NEG-FAIL nim: 注入缺陷后仍全绿")
else:
    print("NEG-OK nim 注入后变红, 恢复后 =", nim.solve("1\n3"))

# 4) wythoff: 破坏冷点判据 (永远 False -> 从不 LOSE)
orig_cold = wythoff._is_cold
wythoff._is_cold = lambda x, y: False
try:
    bad_out = wythoff.solve("1 2")
except IndexError:
    bad_out = "<<is_cold 全假导致无可行冷点着法>>"
if bad_out == "LOSE":
    fails += 1
    print("NEG-FAIL wythoff: 注入缺陷后仍全绿")
else:
    print("NEG-OK wythoff 注入后变红:", bad_out)
wythoff._is_cold = orig_cold
if wythoff.solve("1 2") != "LOSE":
    fails += 1
    print("NEG-FAIL wythoff: 恢复后不绿")
else:
    print("NEG-OK wythoff 恢复后变绿")

print("NEGATIVE", "PASS" if fails == 0 else "FAIL", "fails", fails)
sys.exit(1 if fails else 0)
