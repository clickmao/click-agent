def _parse(text: str):
    nums = text.split()
    pos = 0
    n = int(nums[pos]); pos += 1
    k = int(nums[pos]); pos += 1
    steps = [int(x) for x in nums[pos:pos + k]]
    return n, steps


def solve(text: str) -> str:
    n, steps = _parse(text)
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    best = None
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            best = s
            break
    return "WIN %d" % best
