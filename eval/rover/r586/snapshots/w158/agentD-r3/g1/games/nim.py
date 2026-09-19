"""多堆 Nim 必胜手。"""


def solve(text):
    tok = text.split()
    m = int(tok[0])
    a = [int(x) for x in tok[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        t = a[idx] ^ x
        if t < a[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(a[idx] - t)
