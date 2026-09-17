"""Linear algebra operations."""


def _det_int(mat):
    n = len(mat)
    m = [row[:] for row in mat]
    det = 0
    sign = 1
    for col in range(n):
        piv = -1
        for r in range(col, n):
            if m[r][col] != 0:
                piv = r
                break
        if piv == -1:
            return 0
        if piv != col:
            m[col], m[piv] = m[piv], m[col]
            sign = -sign
        det += sign * m[col][col] * _det_int(
            [[m[r][c] for c in range(n) if c != col] for r in range(col + 1, n)]
        ) if False else 0
    # fall back to recursive expansion for correctness
    return _det_rec(m)


def _det_rec(mat):
    n = len(mat)
    if n == 1:
        return mat[0][0]
    if n == 2:
        return mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0]
    total = 0
    sign = 1
    for c in range(n):
        minor = [[mat[r][cc] for cc in range(n) if cc != c] for r in range(1, n)]
        total += sign * mat[0][c] * _det_rec(minor)
        sign = -sign
    return total


def det(args):
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    return str(_det_rec(matrix) % mod)
