from games._refs import ref_wythoff, wy_losing

for a, b in [(1, 1), (3, 3), (21, 25), (10, 9)]:
    print(a, b, "wy_losing=", wy_losing(a, b), "ref=", ref_wythoff(a, b))
