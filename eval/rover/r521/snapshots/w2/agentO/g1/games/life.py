"""games/life.py — 康威生命游戏 (Conway's Game of Life)。

输入 (text, 整体来自 STDIN):
    第一行: R C steps
    随后 R 行, 每行 C 个字符的网格; 活细胞字符: '#' '*' '1' 'x' 'X' 'o' 'O', 其余为死。

输出: evolutions 之后的 R 行网格字符串, '#' 表示活, '.' 表示死。
边界: 视界外一律视为死细胞 (无环绕)。
规则: B3/S23 —— 活细胞邻居 2 或 3 存活; 死细胞邻居恰为 3 时复活。
"""

from __future__ import annotations

ALIVE_CHARS = frozenset("#*1xXoO")

_EMPTY = ""


def _parse(text):
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    if not lines:
        return 0, 0, 0, []
    head = lines[0].split()
    if len(head) < 2:
        return 0, 0, 0, []
    rows = int(head[0])
    cols = int(head[1])
    steps = int(head[2]) if len(head) >= 3 else 0
    if steps < 0:
        steps = 0
    grid = []
    for r in range(rows):
        raw = lines[1 + r] if 1 + r < len(lines) else ""
        row = [(1 if ch in ALIVE_CHARS else 0) for ch in raw[:cols]]
        if len(row) < cols:  # 补齐短行
            row.extend([0] * (cols - len(row)))
        grid.append(row)
    return rows, cols, steps, grid


def _step(grid, rows, cols):
    out = []
    for r in range(rows):
        row = grid[r]
        prev = grid[r - 1] if r > 0 else None
        nxt = grid[r + 1] if r + 1 < rows else None
        new = [0] * cols
        for c in range(cols):
            n = 0
            if prev is not None:
                if c > 0:
                    n += prev[c - 1]
                n += prev[c]
                if c + 1 < cols:
                    n += prev[c + 1]
            if c > 0:
                n += row[c - 1]
            if c + 1 < cols:
                n += row[c + 1]
            if nxt is not None:
                if c > 0:
                    n += nxt[c - 1]
                n += nxt[c]
                if c + 1 < cols:
                    n += nxt[c + 1]
            alive = row[c] == 1
            new[c] = 1 if (n == 3 or (alive and n == 2)) else 0
        out.append(new)
    return out


def solve(text):
    """康威生命游戏演化。返回 R 个字符串 ('#' 活 / '.' 死)。"""
    rows, cols, steps, grid = _parse(text)
    if rows == 0 or cols == 0:
        return []
    for _ in range(steps):
        grid = _step(grid, rows, cols)
    return ["".join("#" if v else "." for v in row) for row in grid]


# ---------------------------------------------------------------- selftest --
def _selftest():
    # 1) 空网格 / 零步: 原样
    assert solve("") == []
    assert solve("2 2 0\n.#\n#.") == [".#", "#."]

    # 2) blinker: 1 步竖直, 2 步回到水平 (周期 2)
    blinker = "3 3 0\n...\n###\n..."
    assert solve(blinker) == ["...", "###", "..."]
    v = solve("3 3 1\n...\n###\n...")
    assert v == [".#.", ".#.", ".#."], v
    h = solve("3 3 2\n...\n###\n...")
    assert h == ["...", "###", "..."], h

    # 3) block (静物) 演化 5 步不变
    block = "4 4 0\n....\n.##.\n.##.\n...."
    assert solve("4 4 5\n....\n.##.\n.##.\n....") == solve(block)

    # 4) 短行补齐 / 未知字符视作死
    assert solve("1 3 0\n#") == ["#.."]
    assert solve("1 3 0\n?ab") == ["..."]

    # 5) 无环绕: 单格死亡 (邻居 0)
    assert solve("1 1 1\n#") == ["."]

    print("PASS")
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(_selftest())
    sys.stdout.write("\n".join(solve(sys.stdin.read())))
