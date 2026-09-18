"""康威生命游戏: 演化 k 代。

输入格式:
    第一行: H W k  (1<=H,W<=20, 0<=k<=20)
    随后 H 行, 每行 W 个字符, '.'=死 '#'=活

规则: 每代同时更新, 8 邻域, 界外视为死格;
      活细胞邻居数 2 或 3 存活; 死细胞邻居数恰为 3 时复活。
输出: 第 k 代网格, H 行, 每行 W 个字符 (末尾不带换行)。
"""


def _step(grid, h, w):
    """按生命游戏规则演化一代, 返回新网格 (list[list[str]])。"""
    nxt = [["." for _ in range(w)] for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                        n += 1
            if grid[r][c] == "#":
                nxt[r][c] = "#" if n in (2, 3) else "."
            else:
                nxt[r][c] = "#" if n == 3 else "."
    return nxt


def solve(text: str) -> str:
    """纯函数: 入参=完整 stdin 文本, 返回=应写出的 stdout 文本 (不带末尾换行)。"""
    lines = text.splitlines()
    # 跳过首部空行 (防御性), 定位参数行
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1

    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ""
        idx += 1
        row = row.ljust(w, ".")[:w]
        grid.append(list(row))

    for _ in range(k):
        grid = _step(grid, h, w)

    return "\n".join("".join(row) for row in grid)
