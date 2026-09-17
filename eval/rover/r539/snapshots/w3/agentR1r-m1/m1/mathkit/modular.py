def qr_count(args):
    a = args["a"]
    m = args["m"]
    return str(sum(1 for x in range(m) if (x * x - a) % m == 0))


def choose(args):
    n = args["n"]
    k = args["k"]
    mod = args["mod"]
    num = 1
    den = 1
    for i in range(k):
        num = (num * (n - i)) % mod
        den = (den * (i + 1)) % mod
    return str((num * pow(den, mod - 2, mod)) % mod)
