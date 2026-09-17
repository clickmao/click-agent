def det(args):
    mat = [row[:] for row in args["matrix"]]
    mod = args["mod"]
    n = len(mat)
    detv = 1
    for col in range(n):
        piv = None
        for r in range(col, n):
            if mat[r][col] % mod != 0:
                piv = r
                break
        if piv is None:
            return "0"
        if piv != col:
            mat[col], mat[piv] = mat[piv], mat[col]
            detv = -detv
        detv = (detv * mat[col][col]) % mod
        inv = pow(mat[col][col] % mod, mod - 2, mod)
        for r in range(col + 1, n):
            factor = (mat[r][col] * inv) % mod
            for c in range(col, n):
                mat[r][c] = (mat[r][c] - factor * mat[col][c]) % mod
    return str(detv % mod)
