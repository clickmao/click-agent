"""Graph ops.  Pure functions ``op(args: dict) -> str``."""


def shortest(args: dict) -> str:
    """Shortest path length src->dst on a weighted undirected graph.

    0 in the adjacency matrix means "no edge".  Unreachable -> -1.
    Floyd-Warshall is simplest and exact for the small n in contract.
    """
    matrix = args["matrix"]
    n = len(matrix)
    INF = float("inf")
    dist = [[INF] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0
        for j in range(n):
            w = matrix[i][j]
            if i != j and w != 0:
                dist[i][j] = min(dist[i][j], int(w))
    for k in range(n):
        for i in range(n):
            dik = dist[i][k]
            if dik == INF:
                continue
            for j in range(n):
                nd = dik + dist[k][j]
                if nd < dist[i][j]:
                    dist[i][j] = nd
    src = int(args["src"])
    dst = int(args["dst"])
    d = dist[src][dst]
    return str(-1 if d == INF else int(d))
