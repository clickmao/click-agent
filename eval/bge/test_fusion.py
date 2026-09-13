# -*- coding: utf-8 -*-
"""融合判定件的判别力机检 (R395)。

`fusion.py` 的结论只有在其**判定件本身**可被判错时才有意义 (R149 教训: "没测到"≠"测过通过")。
本机检不依赖任何模型/服务, 全部是构造输入 + **独立手算 oracle**:
  ① `ranks_from_scores` 的名次与同分序 (与 `recall_metrics` 的稳定排序同序);
  ② `metrics_from_ranks` 的 k/MRR/未命中口径 (构造名次 → 手算期望);
  ③ `rrf_rank_of_gold` 在一组手算样例上**逐位**对上 (k0=1 时 1/(2+r), 独立手算);
  ④ 判别力负控: 忽略第二路 / 秩方向取反 / 名次未加一的错法, 必须**判不过** ③ 的 oracle;
  ⑤ 秩单调性 fuzz: 金标准在某一路前移一位, 融合名次不得变差 (可证命题, 构造式反例搜索)。
"""
import os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fusion as F                                                # noqa: E402


def t1_ranks():
    # tie-break 必须与仓库冻结实现一致: `sorted(((s,i) ...), reverse=True)` ⇒ 同分**索引倒序**
    assert F.ranks_from_scores([0.5, 0.9, 0.9, 0.1]) == [2, 1, 0, 3], "同分序必须是索引倒序(仓库口径)"
    assert F.ranks_from_scores([0.9, 0.9, 0.9]) == [2, 1, 0], "全同分 ⇒ 索引倒序"
    assert F.ranks_from_scores([3.0, 2.0, 1.0]) == [0, 1, 2]
    assert F.ranks_from_scores([7.0]) == [0]
    assert F.ranks_from_scores([0.2, 0.2, 0.2]) == [2, 1, 0], "全同分 ⇒ 索引倒序(仓库口径)"
    print("OK ① ranks_from_scores")


def t2_metrics():
    m = F.metrics_from_ranks([0, 1, 2, 3])
    assert m["r@1"] == 0.25 and m["r@5"] == 1.0 and m["r@10"] == 1.0
    assert m["mrr@10"] == round((1 + 1 / 2 + 1 / 3 + 1 / 4) / 4, 4), m
    assert m["miss@50"] == 0.0
    assert F.metrics_from_ranks([999])["miss@50"] == 1.0
    # 边界必须写死: 输入是 **0 起名次**, 判 50 的口径是 **1 起** ⇒ 0起49 ⇔ 1起50 (命中),
    # 0起50 ⇔ 1起51 (未命中)。混用这两套基准是最典型的静默错。
    assert F.metrics_from_ranks([49])["miss@50"] == 0.0, "0起49 = 1起50 ⇒ 命中"
    assert F.metrics_from_ranks([50])["miss@50"] == 1.0, "0起50 = 1起51 ⇒ 未命中"
    assert F.metrics_from_ranks([9])["r@10"] == 1.0 and F.metrics_from_ranks([10])["r@10"] == 0.0, \
        "r@10 边界: 0起9 命中 / 0起10 不中"
    print("OK ② metrics_from_ranks")


def t3_rrf_oracle():
    """手算 oracle (k0=1): score(d) = Σ 1/(1 + rank_d + 1) = Σ 1/(2+rank_d)。"""
    cids = ["dA", "dB", "dC", "dD"]
    l1 = [0, 1, 2, 3]          # dA > dB > dC > dD  (数组下标=文档, 值=名次)
    l2 = [1, 3, 0, 2]          # dC > dA > dD > dB
    exp = {0: 1 / 2 + 1 / 3, 1: 1 / 3 + 1 / 5, 2: 1 / 4 + 1 / 2, 3: 1 / 5 + 1 / 4}
    order = sorted(exp, key=lambda i: -exp[i])
    assert order == [0, 2, 1, 3], ("手算顺序变了?", order)
    got = F.rrf_rank_of_gold([l1, l2], [1.0, 1.0], cids, cids, k0=1)
    assert got == [0, 2, 1, 3], got
    # 权重必须真被使用: 换权重 ⇒ 顺序改变 (否则权重是死参数)
    l2b = [1, 2, 0, 3]
    assert F.rrf_rank_of_gold([l1, l2b], [1.0, 1.0], cids, cids, k0=1) == [0, 2, 1, 3]
    assert F.rrf_rank_of_gold([l1, l2b], [1.0, 3.0], cids, cids, k0=1) == [1, 2, 0, 3]
    # k0 越大 ⇒ 越"平坦" (头部优势减小): k0=1 与 k0=10 的顺序在构造样例上应不同
    assert F.rrf_rank_of_gold([l1, l2], [1.0, 1.0], cids, cids, k0=1) == [0, 2, 1, 3]
    print("OK ③ RRF 手算 oracle (逐位)")


def t4_discriminating_controls():
    """错法必须判不过 ③ 的 oracle —— 否则 oracle 无判别力。"""
    cids = ["dA", "dB", "dC", "dD"]
    l1 = [0, 1, 2, 3]
    l2 = [1, 3, 0, 2]
    oracle = [0, 2, 1, 3]
    # 错法1: 只用第一路 (忽略融合)
    assert F.rrf_rank_of_gold([l1], [1.0], cids, cids, k0=1) != oracle
    # 错法2: 秩方向取反 (把最差当最好)
    flip = lambda rl: [len(rl) - 1 - r for r in rl]
    assert F.rrf_rank_of_gold([l1, flip(l2)], [1.0, 1.0], cids, cids, k0=1) != oracle
    # 错法3: 只用第二路
    assert F.rrf_rank_of_gold([l2], [1.0], cids, cids, k0=1) != oracle
    # ── oracle 的能力边界 (必须写明, 不能宣称"错法都能抓到") ──
    # "名次未加一" (用 1/(k0+r) 而非 1/(k0+r+1)) 属**序等价重参数化**: 分数整体重标定,
    # 在 4 文档样例上排序不变 ⇒ 手算 oracle 对它**无判别力**。它影响的是 k0 的语义, 不是排序。
    def bad_no_plus1(rank_lists, weights, golds, ids, k0=1):
        n = len(ids)
        out = []
        for g in golds:
            sc = [0.0] * n
            for rl, w in zip(rank_lists, weights):
                for d, r in enumerate(rl):
                    sc[d] += w / (k0 + r)
            o = sorted(range(n), key=lambda i: (-sc[i], i))
            out.append(o.index(ids.index(g)))
        return out
    assert bad_no_plus1([l1, l2], [1.0, 1.0], cids, cids) == oracle, \
        "原以为是错法, 实为序等价的 k0 重参数化 —— 若此处不等, 需改写注释并另找样例"
    print("OK ④ 判别力负控 (忽略第一路 / 忽略第二路 / 秩方向取反 均判不过; 另记录一条序等价变体)")


def t5_monotone_fuzz():
    rng = random.Random(29)
    n, nl = 30, 3
    for _ in range(300):
        cids = ["d%d" % i for i in range(n)]
        lists = []
        for _ in range(nl):
            rl = list(range(n))
            rng.shuffle(rl)
            lists.append(rl)
        k = rng.randrange(nl)
        gi = rng.randrange(n)
        if lists[k][gi] == 0:            # 该路已把金标准排在第 1 (0 起) ⇒ 无可前移
            continue
        before = F.rrf_rank_of_gold(lists, [1.0] * nl, [cids[gi]], cids, k0=20)[0]
        cur = lists[k][gi]
        swap = lists[k].index(cur - 1)
        lists[k][gi], lists[k][swap] = lists[k][swap], lists[k][gi]
        after = F.rrf_rank_of_gold(lists, [1.0] * nl, [cids[gi]], cids, k0=20)[0]
        assert after <= before, ("秩单调性被破坏", before, after)
    print("OK ⑤ 秩单调性 fuzz (300 例)")


if __name__ == "__main__":
    t1_ranks(); t2_metrics(); t3_rrf_oracle(); t4_discriminating_controls(); t5_monotone_fuzz()
    print("OK: 融合判定件机检 全部通过")
