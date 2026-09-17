from math import gcd


def expect(args):
    red = args["red"]
    blue = args["blue"]
    draw = args["draw"]
    num = red * draw
    den = red + blue
    g = gcd(num, den)
    return str(num // g) + "/" + str(den // g)
