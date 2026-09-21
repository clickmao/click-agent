def solve(text: str) -> str:
    """康威生命游戏: 返回第 k 代的网格文本 (行以 \\n 连接, 末尾不带换行)。"""
    lines = text.split("\n")
    first = lines[0].split()
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])
    rows = lines[1:1 + h]
    cells = set()
    for r in range(h):
        row = rows[r]
        for c in range(w):
            if c < len(row) and row[c] == "#":
                cells.add((r, c))
    for _ in range(k):
        nxt = set()
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        if (r + dr, c + dc) in cells:
                            n += 1
                if (r, c) in cells:
                    if n == 2 or n == 3:
                        nxt.add((r, c))
                else:
                    if n == 3:
                        nxt.add((r, c))
        cells = nxt
    return "\n".join(
        "".join("#" if (r, c) in cells else "." for c in range(w)) for r in range(h)
    )
