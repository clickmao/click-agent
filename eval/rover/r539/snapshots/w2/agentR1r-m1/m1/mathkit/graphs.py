"""Graph operations."""


def shortest(args):
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    src = int(args["src"])
    dst = int(args["dst"])
    n = len(matrix)
    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    done = [False] * n
    for _ in range(n):
        u = -1
        best = INF
        for i in range(n):
            if not done[i] and dist[i] < best:
                best = dist[i]
                u = i
        if u == -1:
            break
        done[u] = True
        for v in range(n):
            w = matrix[u][v]
            if w > 0 and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    if dist[dst] == INF:
        return "-1"
    return str(int(dist[dst]))
