
def merge_intervals(iv):
    out = []
    for a, b in sorted([list(x) for x in iv], key=lambda t: (t[0], t[1])):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
