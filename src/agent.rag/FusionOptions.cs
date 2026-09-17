using System;
using System.Collections.Generic;

namespace agent.rag;


/// <summary>
/// R404 (用户钦定): 检索融合 —— "优化后的 bge" 的落地形态 (端口化)。
///
/// 依据 (冻结集 1299 语料 / 120 查询, 证据 eval/bge/, 报告 docs/reports/bge/):
///   • 单路 dense-small (链上真身 = 25.2MB bge-small-zh-v1.5 q8)  r@10 0.6333
///   • 单路词法路 (字符二元组 Jaccard)                             r@10 0.7500
///   • **RRF(词法 + dense-small, k0=10, w=1:1) ← 本类·产品口径**   r@10 0.7833  (+18 条查询, 配对 p=4e-05)
///   • [评测对照·非产品] 单路 dense-base (110MB)                   r@10 0.7417
///   • [评测对照·非产品] RRF(词法 + dense-base, 同超参)             r@10 0.8500  (+13 条 vs dense-base 本身)
///     —— 该权重已按用户令(2026-09-14)从本机删除; 其向量缓存保留 ⇒ 读数仍可从缓存复现, 但不能再跑前向。
///   • 三路 union 上界 (含 dense-small)                            r@10 0.8667  ⇒ 融合已吃 98%, 同族第三路零增益
///
/// 口径纪律: 词法打分与 RRF 算术与 eval/bge/fusion.py **逐式对齐**(独立实现交叉对账),
/// 任何"看起来更好"的改动都必须先过该冻结集 —— 机检 src/agent.tests/RagFusionTests.cs。
///
/// AOT: 零反射 / 零 shell / 零外部进程; 计数可查 (routes_used / dim_skipped / fallback —— 防空心判定)。
/// </summary>
public sealed class FusionOptions
{
    public bool Enabled { get; set; } = true;

    /// <summary>RRF 平滑常数 (冻结值 10; 网格实验证明 k0∈{1,5,60} 与权重扰动最多 +1 条且 r@1 反降)。</summary>
    public int K0 { get; set; } = 10;

    public double DenseWeight { get; set; } = 1.0;
    public double LexicalWeight { get; set; } = 1.0;
}
