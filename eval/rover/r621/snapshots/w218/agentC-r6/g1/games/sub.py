"""Subtraction game: whoever takes the last stone wins."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = (int(t) for t in lines[idx].split()[:2])
    idx += 1
    steps = []
    while len(steps) < k and idx < len(lines):
        steps.extend(int(t) for t in lines[idx].split())
        idx += 1
    steps = sorted(set(steps))

    win = [False] * (n + 1)
    for x in range(1, n + 1):
        win[x] = any(s <= x and not win[x - s] for s in steps)

    if not win[n]:
        return 'LOSE'
    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    if best is None:
        return 'LOSE'
    return 'WIN %d' % best
