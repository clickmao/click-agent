"""康威生命游戏 (Conway's Game of Life) 的 k 代演化。

solve(text) -> str
  入参 text = 完整 stdin 文本:
    第一行: H W k
    随后 H 行, 每行 W 个字符, 只含 '.' 与 '#'
  返回: 演化 k 代后的网格 (H 行), 末尾不带换行。
"""


def _step(grid, H, W):
    """单代同时更新, 8 邻域, 网格外视为死格。"""
    new = []
    for i in range(H):
        row = grid[i]
        out = []
        for j in range(W):
            cnt = 0
            for di in (-1, 0, 1):
                ni = i + di
                if ni < 0 or ni >= H:
                    continue
                nrow = grid[ni]
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    nj = j + dj
                    if nj < 0 or nj >= W:
                        continue
                    if nrow[nj] == '#':
                        cnt += 1
            alive = row[j] == '#'
            if alive:
                out.append('#' if (cnt == 2 or cnt == 3) else '.')
            else:
                out.append('#' if cnt == 3 else '.')
        new.append(''.join(out))
    return new


def solve(text: str) -> str:
    lines = text.split('\n')
    # 容忍末尾空行
    while lines and lines[-1] == '':
        lines.pop()
    H, W, k = (int(x) for x in lines[0].split())
    grid = [lines[1 + i] for i in range(H)]
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(grid)
