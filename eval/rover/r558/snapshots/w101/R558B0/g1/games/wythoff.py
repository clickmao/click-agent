"""Wythoff game: first player lose/win with lexicographically smallest move.

Input text format:
  line 1: a b (stones in the two piles)
Moves: remove a positive amount from any one pile, or the same positive
amount from both piles. Last stone taken wins.
Output:
  'LOSE' if the first player loses, else 'WIN i j' where (i, j) is the
  lexicographically smallest winning move over all winning moves.
"""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    lose = [[False] * (b + 1) for _ in range(a + 1)]

    for x in range(a + 1):
        for y in range(b + 1):
            if x == 0 and y == 0:
                lose[0][0] = True
                continue
            w = False
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    w = True
                    break
            if not w:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        w = True
                        break
            if not w:
                for t in range(1, min(x, y) + 1):
                    if lose[x - t][y - t]:
                        w = True
                        break
            lose[x][y] = not w

    if lose[a][b]:
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i > 0 and j == 0:
                ok = lose[a - i][b]
            elif j > 0 and i == 0:
                ok = lose[a][b - j]
            elif i == j:
                ok = lose[a - i][b - j]
            if ok:
                return "WIN " + str(i) + " " + str(j)
    return "LOSE"
