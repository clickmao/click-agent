#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本轮 (cycle 20260914-s20260914) 数学题的自解: 生成树计数。

题目: 无向图 6 顶点 (0..5), 边 = 0-2, 0-3, 0-4, 1-3, 1-4, 1-5, 3-4, 4-5。求生成树个数。

解法: **基尔霍夫矩阵树定理** (拉普拉斯矩阵删一行一列后的行列式, 精确有理数消元)。
说明: 判定器用的是**子集枚举 + 并查集** (独立算法)。两条路径互为对账。
另附 **自身独立二次校验**: 对全部 C(8,5)=56 个 5 边子集做连通性判定 (暴力), 与本解比对。
"""

from fractions import Fraction
import itertools
import json
import sys


EDGES = [(0, 2), (0, 3), (0, 4), (1, 3), (1, 4), (1, 5), (3, 4), (4, 5)]
N = 6


def laplacian(n, edges):
    m = [[0] * n for _ in range(n)]
    for u, v in edges:
        m[u][u] += 1
        m[v][v] += 1
        m[u][v] -= 1
        m[v][u] -= 1
    return m


def det_exact(mat):
    """精确行列式 (Fraction 高斯消元, 含行交换计数)。"""
    n = len(mat)
    a = [[Fraction(x) for x in row] for row in mat]
    sign, det = 1, Fraction(1)
    for col in range(n):
        piv = next((r for r in range(col, n) if a[r][col] != 0), None)
        if piv is None:
            return 0
        if piv != col:
            a[col], a[piv] = a[piv], a[col]
            sign = -sign
        det *= a[col][col]
        inv = a[col][col]
        for r in range(col + 1, n):
            if a[r][col] == 0:
                continue
            f = a[r][col] / inv
            for c in range(col, n):
                a[r][c] -= f * a[col][c]
    return int(sign * det)


def matrix_tree(n, edges):
    lap = laplacian(n, edges)
    minor = [row[:-1] for row in lap[:-1]]      # 删最后一行一列
    return det_exact(minor)


def brute_force(n, edges):
    """独立校验: 枚举 n-1 条边子集, 并查集判连通 (与矩阵树不同的算法)。"""
    def connected(sub):
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for u, v in sub:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
        return len({find(i) for i in range(n)}) == 1

    return sum(1 for sub in itertools.combinations(edges, n - 1) if connected(sub))


def main():
    mt = matrix_tree(N, EDGES)
    bf = brute_force(N, EDGES)
    out = {"method": "kirchhoff_matrix_tree", "answer": mt, "cross_check_bruteforce": bf,
           "agree": mt == bf, "vertices": N, "edges": [list(e) for e in EDGES]}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if mt == bf else 1


if __name__ == "__main__":
    sys.exit(main())
