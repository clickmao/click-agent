using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;

    /// <summary>R413 前置门计数 (可观测; Judged==0 ⇒ 未判过, 不得当"通过")。</summary>
public sealed class TurnGateCounters
{
    private long _judged;
    private long _skipped;
    private long _passed;
    private long _degraded;
    private long _accountingViolations;

    private long _mechanicalPasses;

    private long _templateAcks;

    private long _skipRejected;
    // R444: 前置门 (§ Ack 前置) 相关计数 —— 省下的 r1 调用与被破坏的不变量都必须可见。
    private long _mechanicalNonAcks;
    private long _prefilterViolations;

    // R465: 纯复述族直接 Skip 计数 (零 r1 + 零远端调用)。
    private long _mechanicalRepeats;

    // R475: 纯复述族**无可回放实质答复** ⇒ 撤销 Skip 降级远端的次数 (质量优先, 必须可见)。
    private long _repeatDegrades;

    // R498 候选③: 同义改写族吸收计数 (前置门 Skip, 零 r1) 与「本地改写未完成 ⇒ 降级远端」计数。
    // 二者必须可见 —— 否则「接进了改写通道」与「改写通道恒降级」在读数上不可区分。
    private long _mechanicalParaphrases;
    private long _paraphraseDegrades;

    private long _cachePinned;
    private int _lastCachedTokens;
    private int _lastEvalTokens = -1;
    private int _lastNewTokens = -1;
    private int _lastGenTokens = -1;

    public long Judged => Interlocked.Read(ref _judged);
    public long MechanicalPasses => Interlocked.Read(ref _mechanicalPasses);
    public long TemplateAcks => Interlocked.Read(ref _templateAcks);
    public long Skipped => Interlocked.Read(ref _skipped);
    public long Passed => Interlocked.Read(ref _passed);
    public long Degraded => Interlocked.Read(ref _degraded);
    public long AccountingViolations => Interlocked.Read(ref _accountingViolations);

    /// <summary>R498: 同义改写族被前置门直接吸收的次数 (零 r1、零远端)。</summary>
    public long MechanicalParaphrases => Interlocked.Read(ref _mechanicalParaphrases);

    /// <summary>R498: 改写族**未能本地完成** (无源/守卫拒收/引擎降级) ⇒ 撤销 Skip 降级远端的次数。</summary>
    public long ParaphraseDegrades => Interlocked.Read(ref _paraphraseDegrades);

    /// <summary>R498: 记录一次改写族吸收 (前置门 Skip)。</summary>
    public void RecordMechanicalParaphrase()
    {
        Interlocked.Increment(ref _mechanicalParaphrases);
        LastBasis = "mechanical:paraphrase→local";
    }

    /// <summary>R498: 记录一次改写族降级远端 (具体原因由调用方落遥测)。</summary>
    public void RecordParaphraseDegrade() => Interlocked.Increment(ref _paraphraseDegrades);

    /// <summary>R429: 门判显式关前缀缓存的次数 (端口纪律: 被使用计数必须可观测)。</summary>
    public long CachePinned => Interlocked.Read(ref _cachePinned);

    /// <summary>R429: 最近一次门判的缓存命中数 (cache_n) — 钉死后应恒为 0。</summary>
    public int LastCachedTokens => Volatile.Read(ref _lastCachedTokens);

    /// <summary>R443: 最近一次门判的 prompt 总 token 数 (llama-server 真值; -1 = 未走 r1)。</summary>
    public int LastEvalTokens => Volatile.Read(ref _lastEvalTokens);

    /// <summary>R443: 最近一次门判的**新评估** token 数 (真值; -1 = 未走 r1)。</summary>
    public int LastNewTokens => Volatile.Read(ref _lastNewTokens);

    /// <summary>R443: 最近一次门判的**生成** token 数 (真值; -1 = 未走 r1)。</summary>
    public int LastGenTokens => Volatile.Read(ref _lastGenTokens);

    public string? LastBasis { get; private set; }

    /// <summary>R430: 最近一次门判的 prompt 指纹 (空 = 后端未上报)。</summary>
    public string? LastPromptSha { get; private set; }

    /// <summary>R430: 最近一次门判的请求体指纹。</summary>
    public string? LastRequestSha { get; private set; }

    /// <summary>R430: 最近一次门判的请求关键字段摘要。</summary>
    public string? LastRequestFields { get; private set; }

    /// <summary>R430: 上一次门判实际使用的角色种子指纹 (分辨「种子漂移」与「引擎不确定」)。</summary>
    public string? LastRoleSeedSha { get; private set; }

    private int _lastPromptChars;
    private int _lastRoleSeedChars;
    private int _lastGrowthChars;
    private int _lastGrowthLines;

    /// <summary>R431: 最近一次门判**实发** prompt 的字符数 (未走 r1 = 0)。</summary>
    public int LastPromptChars => Volatile.Read(ref _lastPromptChars);

    /// <summary>R431: 最近一次门判挂的角色种子字符数 (null ⇒ 0)。</summary>
    public int LastRoleSeedChars => Volatile.Read(ref _lastRoleSeedChars);

    /// <summary>R431: 最近一次门判挂的 role 额外数据 (成长经历) 字符数 — null/空 ⇒ 0 (未挂载臂的负控读数)。</summary>
    public int LastGrowthChars => Volatile.Read(ref _lastGrowthChars);

    /// <summary>R431: 成长块渲染出的域行数 (块内 '\n' 计数; 部分行被截断时仍计入已渲染行)。</summary>
    public int LastGrowthLines => Volatile.Read(ref _lastGrowthLines);

    /// <summary>
    /// R431: 记录本次门判**实发** prompt 的形状 (长度取自实际被发出的那一份 prompt, 不做二次重建 ⇒ 无漂移)。
    /// 「挂了 role 额外数据」与「没挂」在读数上必须可区分, 否则挂载只是接口上有字段。
    /// </summary>
    public void RecordPromptShape(int promptChars, int roleSeedChars, string? growthBlock)
    {
        Volatile.Write(ref _lastPromptChars, promptChars);
        Volatile.Write(ref _lastRoleSeedChars, roleSeedChars);
        var g = growthBlock ?? string.Empty;
        Volatile.Write(ref _lastGrowthChars, g.Length);
        var lines = 0;
        foreach (var ch in g) if (ch == '\n') lines++;
        Volatile.Write(ref _lastGrowthLines, lines);
    }

    /// <summary>机械前置门命中 (零 token 直接 Pass, 未询问 r1) — 必须可观测, 否则看不出"省了判别"。</summary>
    public void RecordMechanicalPass() { Interlocked.Increment(ref _mechanicalPasses); LastBasis = "mechanical:pass→remote"; }

    /// <summary>被跳过轮使用非 LLM 模板回复 (真机实证: LLM 生成会复读/反问)。</summary>
    public void RecordTemplateAck() { Interlocked.Increment(ref _templateAcks); }

    public void RecordJudged() => Interlocked.Increment(ref _judged);
    public void RecordSkipped() { Interlocked.Increment(ref _skipped); LastBasis = "gate:skip→local"; }
    public void RecordPassed() { Interlocked.Increment(ref _passed); LastBasis = "gate:pass→remote"; }

    /// <summary>R434: r1 判 Skip 但结构上非「认可族」⇒ 降级 Pass 的次数 (被拒的省钱机会必须可观测)。</summary>
    public long SkipRejected => Interlocked.Read(ref _skipRejected);

    /// <summary>R444: 前置门命中次数 (¬Ack ⇒ 构造性必然 Pass, 未询问 r1)。</summary>
    public long MechanicalNonAcks => Interlocked.Read(ref _mechanicalNonAcks);

    /// <summary>R444: 前置门不变量被破坏次数 (Skip ∧ ¬Ack 本应不可达) — 恒 0 才是 fail-closed。</summary>
    public long PrefilterViolations => Interlocked.Read(ref _prefilterViolations);

    /// <summary>R465: 纯复述族命中次数 (零 r1 + 零远端调用, 本地回放上一条答复原文)。</summary>
    public long MechanicalRepeats => Interlocked.Read(ref _mechanicalRepeats);

    /// <summary>R465: 前置门直接 Skip —— 纯复述族 (只要求原样重来, 无新诉求)。</summary>
    public void RecordMechanicalRepeat() { Interlocked.Increment(ref _mechanicalRepeats); LastBasis = "mechanical:repeat→local"; }

    /// <summary>R475: 纯复述族被**撤销 Skip** 的次数 (无实质上一条可回放 ⇒ 降级远端, 不得以模板冒充答复)。</summary>
    public long RepeatDegrades => Interlocked.Read(ref _repeatDegrades);

    /// <summary>R475: 纯复述轮无实质答复可回放 ⇒ 降级远端 (质量优先于省钱; 判据可见)。</summary>
    public void RecordRepeatDegrade() { Interlocked.Increment(ref _repeatDegrades); LastBasis = "gate:repeat_no_replayable_prev→remote"; }

    /// <summary>R434: r1 判 Skip 但结构确认失败 (非认可族) ⇒ 降级 Pass, 宁多走一次远端。</summary>
    public void RecordSkipRejected() { Interlocked.Increment(ref _skipRejected); LastBasis = "gate:skip_rejected_nonack→remote"; }

    /// <summary>R444: 前置门命中 (¬Ack, 零 token 直接 Pass) — 不建 prompt、不问 r1, 判决与后置否决逐位同。</summary>
    public void RecordMechanicalNonAck() { Interlocked.Increment(ref _mechanicalNonAcks); LastBasis = "mechanical:nonack→remote"; }

    /// <summary>R444: 前置门不变量被破坏 (Skip ∧ ¬Ack 竟抵达后置否决) — fail-closed 落盘, 恒 0。</summary>
    public void RecordPrefilterViolation() { Interlocked.Increment(ref _prefilterViolations); }

    public void RecordDegraded(string reason)
    {
        Interlocked.Increment(ref _degraded);
        LastBasis = "gate:degraded:" + reason + "→remote";
    }

    public void RecordAccountingViolation(string reason)
    {
        Interlocked.Increment(ref _accountingViolations);
        LastBasis = "gate:accounting_violation:" + reason + "→remote";
    }

    /// <summary>R429: 门判请求已钉死缓存态 (显式关前缀缓存 + 记录本次 cache_n)。
    /// R443: 同时记录 llama-server 上报的**真值** token 三元组 (tokens_evaluated / prompt_n / gen_n),
    /// 用于把本地 r1 成本口径从「字符/2 折算」升级为「tokenizer 真值」。</summary>
    public void RecordCachePinned(int cachedTokens, string? promptSha = null, string? requestSha = null, string? requestFields = null,
        int evalTokens = -1, int newTokens = -1, int genTokens = -1)
    {
        Interlocked.Increment(ref _cachePinned);
        Volatile.Write(ref _lastCachedTokens, cachedTokens);
        Volatile.Write(ref _lastEvalTokens, evalTokens);
        Volatile.Write(ref _lastNewTokens, newTokens);
        Volatile.Write(ref _lastGenTokens, genTokens);
        LastPromptSha = promptSha;
        LastRequestSha = requestSha;
        LastRequestFields = requestFields;
    }

    /// <summary>R430: 记录本次门判的角色种子指纹 (调用方在构造 prompt 处提供; null = 未走 r1 判别)。</summary>
    public void RecordRoleSeed(string? roleSeed)
    {
        if (roleSeed is null) return;
        LastRoleSeedSha = LocalInputFingerprint.Sha16(roleSeed);
    }
}
