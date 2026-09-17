import heapq


def shortest(args):
    mat = args["matrix"]
    src = args["src"]
    dst = args["dst"]
    n = len(mat)
    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v in range(n):
            w = mat[u][v]
            if w > 0 and d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    return str(dist[dst]) if dist[dst] != INF else "-1"
