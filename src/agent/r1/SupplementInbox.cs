using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using agent.rag;

namespace agent.r1;

/// <summary>
/// 用户补充台账：长任务运行中投递进来的「有关当前任务」的信息（用户提供的相关信息）。
///
/// 职责三条：
///   ① 去重投递（Enqueue / Harvest）—— 同一条只登记一次；
///   ② 按**当前步骤文本**打分挑选该在哪一次远端调用里插（SelectFor）—— 打分器走既有 <see cref="IRerankScorer"/> 接口，
///      可换成本地模型实现（用不用召回/llm 打分对这一层是透明的）；
///   ③ 记账消费（MarkConsumed）—— 插过的移出待插队列，**不重复注入、也不静默吞掉**（Consumed 可读可报）。
///
/// 时机（「合理时机」的可执行落点）：时机锚 = **每次远端返回之后**收割（Harvest），**下一次调用之前**取用（SelectFor）。
/// 即「llm 返回后补充用户提供的信息，随下一次调用进入上下文」。
///
/// 缓存纪律：补充只作为 prompt 的**可变区/尾部块**出现
/// （契约面 <c>StructuredPrompt.BuildUserMessage</c> 的 user 轮；长任务面 <see cref="SupplementBlock"/> 的提示尾块），
/// 恒定前缀/公共头字节不变 ⇒ 前缀缓存（CachePrompt）与恒前缀 ≥97% 口径不受影响。
///
/// 拒收纪律：打分低于阈值 ⇒ 本轮不插，留在待插队列等更匹配的步骤（禁「猜位置」）。
/// </summary>
public sealed class SupplementInbox
{
    private readonly List<string> _pending = new List<string>();
    private readonly List<string> _consumed = new List<string>();
    private readonly IRerankScorer _scorer;
    private readonly double _threshold;
    private readonly Func<IReadOnlyList<string>>? _source;

    public SupplementInbox(IRerankScorer scorer, double threshold, Func<IReadOnlyList<string>>? source = null)
    {
        _scorer = scorer ?? throw new ArgumentNullException(nameof(scorer));
        _threshold = threshold;
        _source = source;
    }

    /// <summary>待插条数。</summary>
    public int PendingCount => _pending.Count;

    /// <summary>已插入消费的条数。</summary>
    public int ConsumedCount => _consumed.Count;

    /// <summary>待插补充（只读视图）。</summary>
    public IReadOnlyList<string> Pending => _pending;

    /// <summary>已消费补充（只读视图，用于汇报/机检，不吞证据）。</summary>
    public IReadOnlyList<string> Consumed => _consumed;

    /// <summary>投递一条补充；空白忽略，与已投递/已消费重复（忽略大小写与首尾空白）返回 false。</summary>
    public bool Enqueue(string? supplement)
    {
        if (string.IsNullOrWhiteSpace(supplement))
        {
            return false;
        }

        var text = supplement.Trim();
        for (var i = 0; i < _pending.Count; i++)
        {
            if (string.Equals(_pending[i], text, StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }
        }

        for (var i = 0; i < _consumed.Count; i++)
        {
            if (string.Equals(_consumed[i], text, StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }
        }

        _pending.Add(text);
        return true;
    }

    /// <summary>从来源收割新到的补充，返回新增条数。时机 = 每次远端返回之后。</summary>
    public int Harvest()
    {
        if (_source is null)
        {
            return 0;
        }

        IReadOnlyList<string> items;
        try
        {
            items = _source();
        }
        catch (IOException)
        {
            return 0;
        }

        if (items is null)
        {
            return 0;
        }

        var added = 0;
        for (var i = 0; i < items.Count; i++)
        {
            if (Enqueue(items[i]))
            {
                added++;
            }
        }

        return added;
    }

    /// <summary>
    /// 按步骤文本打分挑选本轮要插的补充：分数降序、低于阈值一律不插、最多 <paramref name="max"/> 条。
    /// 本方法**不消费**（由调用方在确实写入 prompt 后调 <see cref="MarkConsumed"/>），因此失败重试不会丢补充。
    /// </summary>
    public IReadOnlyList<string> SelectFor(string? stepQuery, int max = 2)
    {
        if (_pending.Count == 0 || max <= 0 || string.IsNullOrWhiteSpace(stepQuery))
        {
            return Array.Empty<string>();
        }

        var candidates = new List<RerankCandidate>(_pending.Count);
        for (var i = 0; i < _pending.Count; i++)
        {
            candidates.Add(new RerankCandidate(i.ToString(CultureInfo.InvariantCulture), _pending[i], 0.0));
        }

        var order = RerankStage.OrderIndices(candidates, stepQuery, _scorer);
        var picked = new List<string>();
        for (var k = 0; k < order.Length && picked.Count < max; k++)
        {
            var idx = order[k];
            if (idx < 0 || idx >= _pending.Count)
            {
                continue;
            }

            if (_scorer.Score(stepQuery, _pending[idx], 0.0) < _threshold)
            {
                break;
            }

            picked.Add(_pending[idx]);
        }

        return picked;
    }

    /// <summary>记账：选中的补充移出待插队列（同一条不再重复注入）。返回实际消费条数。</summary>
    public int MarkConsumed(IReadOnlyList<string>? selected)
    {
        if (selected is null || selected.Count == 0)
        {
            return 0;
        }

        var moved = 0;
        for (var i = 0; i < selected.Count; i++)
        {
            var text = selected[i];
            if (string.IsNullOrWhiteSpace(text))
            {
                continue;
            }

            var at = _pending.IndexOf(text.Trim());
            if (at < 0)
            {
                continue;
            }

            _pending.RemoveAt(at);
            _consumed.Add(text.Trim());
            moved++;
        }

        return moved;
    }

    /// <summary>文件投递箱来源：一行一条，空行与 # 开头注释忽略；读不到（无文件/IO 错）视为空。</summary>
    public static Func<IReadOnlyList<string>> DropFileSource(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            throw new ArgumentException("path 不能为空", nameof(path));
        }

        var full = Path.GetFullPath(path);
        return () =>
        {
            try
            {
                if (!File.Exists(full))
                {
                    return Array.Empty<string>();
                }

                return File.ReadAllLines(full, Encoding.UTF8);
            }
            catch (IOException)
            {
                return Array.Empty<string>();
            }
        };
    }

    /// <summary>阈值（env 覆盖，缺省 0.05 的粗门槛；打分器为词法基线，可换 llm 打分实现）。</summary>
    public static double ThresholdFromEnvironment(string variable, double fallback)
    {
        var raw = Environment.GetEnvironmentVariable(variable);
        if (!string.IsNullOrWhiteSpace(raw)
            && double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var parsed)
            && parsed >= 0.0)
        {
            return parsed;
        }

        return fallback;
    }
}
