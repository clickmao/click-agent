"""Linear algebra ops (pure functions, op(args: dict) -> str)."""


def det(args: dict) -> str:
    """Determinant of an integer matrix, as a non-negative residue mod `mod`.

    Uses fraction-free-ish Gaussian elimination over the integers, then
    reduces the resulting determinant modulo `mod`.  Branching on zero
    pivots with row swaps keeps the determinant sign correct.
    """
    rows = [list(map(int, row)) for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(rows)
    if n == 0:
        return str(1 % mod)

    sign = 1
    value = 1
    cur = [row[:] for row in rows]
    for col in range(n):
        pivot = None
        for r in range(col, n):
            if cur[r][col] != 0:
                pivot = r
                break
        if pivot is None:
            return "0"
        if pivot != col:
            cur[col], cur[pivot] = cur[pivot], cur[col]
            sign = -sign
        pv = cur[col][col]
        value *= pv
        # Eliminate below the pivot (integer arithmetic).
        for r in range(col + 1, n):
            factor = cur[r][col]
            if factor == 0:
                continue
            cur[r] = [cur[r][c] * pv - cur[col][c] * factor for c in range(n)]
        # Keep the matrix bounded: divide the row by the previous pivot.
        for r in range(col + 1, n):
            g = pv
            row = cur[r]
            if all(v % g == 0 for v in row):
                cur[r] = [v // g for v in row]

    result = sign * value
    return str(result % mod)
