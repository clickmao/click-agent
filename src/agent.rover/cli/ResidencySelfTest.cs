using agent.rover.gguf;
using agent.rover.runtime;

namespace agent.rover.cli;

/// <summary>
/// 驻留/回收自证套件 (与 <c>check --selftest</c> 同风格): 每条断言都绑定组件真实行为
/// (配额约束 / LRU 受害者的**真释放** / 账本恒等式 / 流窗口不物化 / 显式回收精确性),
/// 并带**负向控制组**证明断言有判别力 (否则"全绿"可能只是断言恒真)。
/// 用真模型的真张量, 无模拟值; 零 shell / 零外部进程。
/// </summary>
public static class ResidencySelfTest
{
    private readonly record struct Case(string Name, bool Ok, string Detail);

    /// <summary>返回值: 0 = 全绿, 1 = 有红, 2 = 参数错, 3 = 夹具不足。</summary>
    public static int Run(string ggufPath, TextWriter o)
    {
        var cases = new List<Case>();
        using var r = GgufReader.Open(ggufPath);

        // 真张量夹具: 取最小的一批 (确定性排序: 元素数 → 名字序), 夹具不足则如实报错, 不硬凑。
        var small = r.TensorNames
            .Where(n => r.Require(n).ElementCount is > 0 and < 4_000_000)
            .OrderBy(n => r.Require(n).ElementCount).ThenBy(n => n, StringComparer.Ordinal)
            .Take(12).ToList();
        if (small.Count < 6)
        {
            o.WriteLine($"error{{kind=selftest_insufficient_tensors found={small.Count} need=6}}");
            return 3;
        }
        long BytesOf(string n) => (long)r.Require(n).ElementCount * 4;   // 物化口径 = F32 驻留字节

        o.WriteLine($"residency_selftest{{file={Path.GetFileName(ggufPath)} file_bytes={r.Mapped.Length} " +
                    $"fixture_tensors={small.Count} smallest={small[0]} smallest_bytes={BytesOf(small[0])}}}");

        // ---- S1/S2/S4/S6: 可驱逐时的预算约束 + LRU 受害者次序 + 账本恒等式 + 真释放 (判别力) ----
        {
            long budget = BytesOf(small[0]) + BytesOf(small[1]);      // 只容得下 2 个最小张量
            using var res = new TensorResidency(r, budget);
            var bufs = new List<TensorBuffer>();
            bool identityOk = true;
            for (int i = 0; i < small.Count; i++)
            {
                bufs.Add(res.AcquireF32(small[i]));
                identityOk &= res.Ledger.LoadedBytes == res.ResidentBytes + res.Ledger.ReclaimedBytes;
            }
            long maxIncoming = bufs.Max(b => b.Bytes);
            bool bound = res.ResidentBytes <= Math.Max(budget, maxIncoming);
            cases.Add(new("budget_bound_respected", bound,
                $"resident={res.ResidentBytes} budget={budget} max_incoming={maxIncoming} bound={Math.Max(budget, maxIncoming)}"));
            cases.Add(new("lru_evicts_fire", res.Ledger.EvictCount > 0,
                $"evicts={res.Ledger.EvictCount} reclaimed={res.Ledger.ReclaimedBytes}"));

            // 负向控制 (a): 受害者若是"只记账不释放", 上面的 IsFreed 必为假 ⇒ 该案例即判别力证据。
            bool firstFreed = IsFreed(bufs[0]);
            cases.Add(new("negctrl_evict_is_real_release", firstFreed,
                $"freed_span_access={(!firstFreed ? "still_readable" : "ObjectDisposedException")} evicts={res.Ledger.EvictCount}"));

            cases.Add(new("ledger_identity_loaded_eq_resident_plus_reclaimed", identityOk,
                $"loaded={res.Ledger.LoadedBytes} resident={res.ResidentBytes} reclaimed={res.Ledger.ReclaimedBytes}"));
        }

        // ---- S2: LRU 受害者次序 —— **驱逐发生的那一刻**判定 (事后看会被后续驱逐掩盖) ----
        {
            // 取三个同字节张量 (等尺寸 ⇒ 预算=2 个时恰好只逐出 1 个), 尺寸不同则如实报不可判定。
            var trio = small.GroupBy(n => BytesOf(n)).OrderBy(g => g.Key).First().Take(3).ToList();
            if (trio.Count < 3)
            {
                cases.Add(new("lru_victim_is_oldest", false,
                    $"undecidable_no_three_equal_sized_tensors_among_fixture"));
            }
            else
            {
                long budget = 2 * BytesOf(trio[0]);
                using var res = new TensorResidency(r, budget);
                var a = res.AcquireF32(trio[0]);
                var b = res.AcquireF32(trio[1]);
                var c = res.AcquireF32(trio[2]);          // 触发一次驱逐: 最久未用的 trio[0]
                bool onlyOldestFreed = IsFreed(a) && !IsFreed(b) && !IsFreed(c);
                cases.Add(new("lru_victim_is_oldest", onlyOldestFreed && res.Ledger.EvictCount == 1,
                    $"order={trio[0]}->{trio[1]}->{trio[2]} victim={trio[0]} freed={IsFreed(a)} " +
                    $"second_alive={!IsFreed(b)} third_alive={!IsFreed(c)} evicts={res.Ledger.EvictCount} " +
                    $"resident={res.ResidentCount} bytes={BytesOf(trio[0])}"));
            }
        }

        // ---- S3: pin 张量免疫驱逐 (活性最高者常驻) ----
        {
            long budget = BytesOf(small[1]);                          // 只容得下 1 个
            using var res = new TensorResidency(r, budget, new[] { small[0] });
            var pinnedBuf = res.AcquireF32(small[0]);
            for (int i = 1; i < 6; i++) res.AcquireF32(small[i]);
            cases.Add(new("pinned_never_evicted", !IsFreed(pinnedBuf) && res.Ledger.EvictCount > 0,
                $"pinned={small[0]} alive={!IsFreed(pinnedBuf)} evicts={res.Ledger.EvictCount} resident={res.ResidentCount}"));
        }

        // ---- S5: 量化权重流窗口零拷贝 ⇒ 不产生驻留 (ResidentCount/ResidentBytes 不变) ----
        {
            using var res = new TensorResidency(r, 1L << 20);
            int before = res.ResidentCount;
            long streamed0 = res.Ledger.StreamedBytes;
            var t = r.Require(small[0]);
            var w = res.StreamWindow(small[0]);
            bool noMaterialize = res.ResidentCount == before && res.ResidentBytes == 0;
            bool counted = res.Ledger.StreamedBytes - streamed0 == w.Length && w.Length == t.ByteSize;
            cases.Add(new("stream_window_no_materialize", noMaterialize && counted,
                $"resident_count={res.ResidentCount} resident_bytes={res.ResidentBytes} " +
                $"window_bytes={w.Length} tensor_bytes={t.ByteSize} streamed_delta={res.Ledger.StreamedBytes - streamed0}"));
        }

        // ---- S7 (负向控制 b): 全部 pin + 预算 1 字节 ⇒ 必须"诚实超限", 不得伪报符合预算 ----
        {
            using var res = new TensorResidency(r, 1, small.Take(4).ToArray());
            for (int i = 0; i < 4; i++) res.AcquireF32(small[i]);
            bool noEvict = res.Ledger.EvictCount == 0;
            bool overBudget = res.ResidentBytes > res.Ledger.BudgetBytes;
            cases.Add(new("negctrl_all_pinned_reports_over_budget_honestly", noEvict && overBudget,
                $"evicts={res.Ledger.EvictCount} resident={res.ResidentBytes} budget={res.Ledger.BudgetBytes} " +
                $"over={overBudget} verdict=budget_exceeded_honest"));
        }

        // ---- S8: ReclaimAll 只释放非常驻, 释放字节数精确等于非常驻驻留之和 ----
        {
            using var res = new TensorResidency(r, 0, new[] { small[0] });
            res.AcquireF32(small[0]);
            long nonPinned = 0;
            for (int i = 1; i < 5; i++) { res.AcquireF32(small[i]); nonPinned += BytesOf(small[i]); }
            long residentBefore = res.ResidentBytes;
            long freed = res.ReclaimAll();
            bool exact = freed == nonPinned && residentBefore == nonPinned + BytesOf(small[0]);
            cases.Add(new("reclaim_all_frees_exactly_unpinned", exact && res.ResidentCount == 1,
                $"freed={freed} expected_nonpinned={nonPinned} resident_before={residentBefore} " +
                $"resident_after={res.ResidentCount} pinned_kept={BytesOf(small[0])}"));
        }

        // ---- S9: 预算语义只声明一次 (0/负 = 无上限), 判定与打印都从该声明派生 ----
        {
            using var unlimited = new TensorResidency(r, 0);
            unlimited.AcquireF32(small[0]);
            unlimited.AcquireF32(small[1]);
            bool declared = unlimited.Ledger.BudgetUnlimited && unlimited.Ledger.BudgetBytes == 0;
            bool noFakeEvict = unlimited.Ledger.EvictCount == 0 && unlimited.ResidentCount == 2;
            using var bounded = new TensorResidency(r, 1L << 20);
            bool boundedDeclared = !bounded.Ledger.BudgetUnlimited && bounded.Ledger.BudgetBytes == (1L << 20);
            cases.Add(new("budget_semantics_declared_once", declared && noFakeEvict && boundedDeclared,
                $"zero_budget_unlimited={unlimited.Ledger.BudgetUnlimited} evicts_on_unlimited={unlimited.Ledger.EvictCount} " +
                $"resident_kept={unlimited.ResidentCount} positive_budget_unlimited={bounded.Ledger.BudgetUnlimited}"));
        }

        int pass = cases.Count(c => c.Ok);
        foreach (var c in cases) o.WriteLine($"selftest{{case={c.Name} ok={c.Ok} detail={c.Detail}}}");
        o.WriteLine($"selftest{{ran={cases.Count} pass={pass} fail={cases.Count - pass} tokens=0 " +
                    $"engine=residency file={Path.GetFileName(ggufPath)}}}");
        return pass == cases.Count ? 0 : 1;
    }

    /// <summary>缓冲是否**真被释放** (访问即抛 ObjectDisposedException)。只记数不释放的实现在此必红。</summary>
    private static bool IsFreed(TensorBuffer b)
    {
        try
        {
            _ = b.Span.Length;
            return false;
        }
        catch (ObjectDisposedException)
        {
            return true;
        }
    }
}
