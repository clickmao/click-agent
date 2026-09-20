import sys


def _read(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    return lines


def solve(text: str) -> str:
    lines = _read(text)
    if not lines:
        return ''
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()[:m]))
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(len(piles)):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'


def main():
    data = sys.stdin.read()
    sys.stdout.write(solve(data))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
