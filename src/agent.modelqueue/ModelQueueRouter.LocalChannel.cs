using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;

public sealed partial class ModelQueueRouter : IModelQueueCaller
{

    /// <summary>
    /// R413 前置门判别: 本地端口判定「本轮是否携带新增诉求」。
    /// 失败/空回/记账违规/无法解析 ⇒ <c>Decided=false</c> (调用方必须降级远端, 绝不静默跳过); 取消上抛。
    /// </summary>
    /// <summary>
    /// R450: 门判**实发 prompt** 落盘闸 —— 器具锚的唯一权威源。
    /// 动机 (R449 实测): 源码派生重建器与产品实发文本漂移 (重建 480 vs 遥测 452 字符;
    ///   seed sha 逐位相同、模板源码未变) ⇒ 拿重建 prompt 做外部效度探针会得到
    ///   **产品不产生的行为** (探针 gen=6 直接出字母 vs 产品长思考, 正控 3/7 而产品 7/7)。
    /// 契约: 未设/空 ⇒ **完全关闭** (零产品变更: 不落盘、不建目录、不读文件);
    ///   设 = 追加 JSONL 一行 {seq,len,sha16,prompt}; 任何 IO 异常吞掉(记 warning)
    ///   —— 仪器绝不改变决策路径。
    /// </summary>
    internal static void DumpGatePrompt(string prompt)
    {
        var path = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_GATE_PROMPT_DUMP");
        if (string.IsNullOrWhiteSpace(path)) return;
        try
        {
            var sha16 = Convert.ToHexString(
                System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(prompt)))[..16];
            var seq = System.Threading.Interlocked.Increment(ref _gateDumpSeq);
            // R450 修正: AOT 下 STJ 反射序列化被禁用 (实测 InvalidOperationException)
            //   ⇒ 手写 JSON 字符串转义 (零反射; 铁律: STJ Source Generator 或不用)
            var line = "{\"seq\":" + seq + ",\"len\":" + prompt.Length + ",\"sha16\":\"" + sha16 + "\",\"prompt\":\""
                       + JsonEscape(prompt) + "\"}\n";
            // R450: UTF8 必须显式 no-BOM —— `Encoding.UTF8` 建文件时会写 BOM, 下游 JSONL 解析器会炸
            System.IO.File.AppendAllText(path, line, new System.Text.UTF8Encoding(false));
        }
        catch (Exception ex)
        {
            _dumpLogger?.LogWarning(ex, "R450: 门判 prompt 落盘失败 (已忽略, 不影响决策)");
        }
    }

    private static Microsoft.Extensions.Logging.ILogger? _dumpLogger;
    private static int _gateDumpSeq;

    /// <summary>R450: 零反射 JSON 字符串转义 (AOT 安全; 覆盖 \" \\ 与 &lt;0x20 控制字符)。</summary>
    internal static string JsonEscape(string s)
    {
        var sb = new System.Text.StringBuilder(s.Length + 8);
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20)
                        sb.Append("\\u").Append(((int)c).ToString("x4"));
                    else
                        sb.Append(c);
                    break;
            }
        }
        return sb.ToString();
    }

    public async Task<TurnGateOutcome> JudgeTurnAsync(string userMessage, string? roleSeed, string? growthBlock, CancellationToken ct = default)
    {
        var port = _localPort;
        if (port is null)
        {
            TurnGate.RecordDegraded("no_local_port");
            return TurnGateOutcome.Undecided("no_local_port");
        }
        TurnGate.RecordJudged();
        TurnGate.RecordRoleSeed(roleSeed);   // R430: 先记种子指纹 (区分「种子漂移」与「引擎不确定」)
        // R431: prompt 只构造一次 —— 形状读数取自实发文本 (二次重建会与真发内容漂移)。
        var gatePrompt = TurnGateJudge.BuildPrompt(userMessage, roleSeed, growthBlock);
        TurnGate.RecordPromptShape(gatePrompt.Length, roleSeed?.Length ?? 0, growthBlock);
        DumpGatePrompt(gatePrompt);   // R450: 门判实发 prompt 落盘闸 (默认关 ⇒ 现网零变更)
        try
        {
            var outcome = await port.GenerateAsync(new LocalGenerationRequest
            {
                SessionKey = "r413:turn-gate",
                TurnIndex = 1,
                Turns = new List<LocalChatTurn> { new("user", gatePrompt) },
                // R413 实测: 8/16 token 会被 r1 思考链吃光 ⇒ 字母没出来 (raw 取证)。128 足够判别句收尾。
                MaxTokens = 512,   // 实测: 真链里思考链可达 250-350 tok (192 会截断在推理中途) ⇒ 给足上限, 解析只认闭合标记后的结论区
                // R429: 决策路径钉死缓存态 —— 同一 prompt 在「全量评估」与「部分前缀复用」下 token 序列不等
                // (传输级实测 180/97/215, 可致 S/P 翻转) ⇒ 门判不得依赖前缀缓存复用。
                CacheReuse = false,
            }, ct).ConfigureAwait(false);
            TurnGate.RecordCachePinned(outcome.CachedTokens, outcome.PromptSha16, outcome.RequestSha16, outcome.RequestFields,
                outcome.TokensEvaluated, outcome.PromptNewTokens, outcome.GeneratedTokens);

            if (!outcome.Success || string.IsNullOrWhiteSpace(outcome.Content))
            {
                TurnGate.RecordDegraded("failed_or_empty");
                return TurnGateOutcome.Undecided(outcome.Error ?? "empty_content", outcome.Content ?? string.Empty);
            }
            if (!outcome.AccountingConsistent)
            {
                TurnGate.RecordAccountingViolation("tokens_evaluated != prompt_n + cache_n");
                return TurnGateOutcome.Undecided("accounting_inconsistent", outcome.Content ?? string.Empty);
            }

            var verdict = TurnGateJudge.Parse(outcome.Content);
            if (!verdict.Decided)
            {
                TurnGate.RecordDegraded("unparsed:" + (verdict.Raw.Length > 40 ? verdict.Raw[..40] : verdict.Raw));
                return verdict;
            }
            if (verdict.Verdict == TurnGateVerdict.Skip) TurnGate.RecordSkipped();
            else TurnGate.RecordPassed();
            return verdict;
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            TurnGate.RecordDegraded("exception:" + ex.GetType().Name);
            return TurnGateOutcome.Undecided("exception:" + ex.GetType().Name);
        }
    }

    /// <summary>
    /// R426: 关系判官 (CorrectionDetector L2 微判定) 本地优先 —
    /// 本地端口已注册 且 配置 <c>local.relation_judge=true</c> (默认 false ⇒ 零回归)。
    /// </summary>
    public bool RelationJudgeEnabled => _localPort is not null && _catalog.LocalChannel.RelationJudge;

    /// <summary>R426: 关系判官计数/依据 (可观测: Local==0 ∧ Fallback&gt;0 ⇒ 本地未生效, 不靠猜)。</summary>
    public RelationJudgeCounters RelationJudge { get; } = new();

    /// <summary>
    /// R498 候选③: 本地**改写**通道计数 (内容承载的本地生成; 闸 = <see cref="LocalParaphraseChannel.EnvName"/>, 默认关)。
    /// 实例级 (与 TurnGate/RelationJudge 同形) —— 不用静态计数器。
    /// </summary>
    public LocalParaphraseCounters LocalParaphrase { get; } = new();

    /// <summary>
    /// R426: 本地关系判官 (r1)。<c>null</c> ⇒ 本地不可用/失败/记账违规/未解析出字母 ⇒
    /// 调用方**必须远端兜底** (绝不静默给结论)。
    ///
    /// 预算: 调用方 (CorrectionDetector) 给远端的是 64/128 tok — 那是远端 API 的保守值;
    /// r1 的思考链会把 64 tok 吃光 (R413 实测: 8/16 tok 截断在推理中途 ⇒ 恒未判定),
    /// 故本地**不复用**调用方预算而用 512 (与前置门同值, 实测思考链 250–350 tok)。
    /// 取消: 本路径由后台赏罚任务调用 (与远端同语义: 不随单轮 ct 取消, 否则会静默降级成 NEUTRAL)。
    /// </summary>
    public async Task<RelationJudgeOutcome?> JudgeRelationLocalAsync(
        string systemPrompt, string judgePrompt, CancellationToken ct = default)
    {
        var port = _localPort;
        if (port is null)
        {
            RelationJudge.RecordFallback("no_local_port");
            return null;
        }
        var cfg = _catalog.LocalChannel;
        // R435: 预算**保持 512** —— 实测证伪了「512 不够」的假设 (且不是承重变量):
        //   旧 prompt: 512 → 1/7 (turn5/8 思考链未闭合耗尽), 1024 → 2/7, 且 turn5 在 1024 仍耗尽
        //   ⇒ 加预算只换来 1 例、还让最坏延迟翻倍 (turn1: 32s → 86s)。
        //   新 prompt: 512 与 1024 **逐例完全同解** (6/7, 同字母) ⇒ 一旦结论区形状对了, 512 足够。
        //   证据: eval/rover/r435/probe-j2-classified.json (A0/A2/A1/A3)。
        var maxTokens = Math.Max(cfg.MaxTokens, 512);

        RelationJudge.RecordAttempt();
        try
        {
            var turns = new List<LocalChatTurn>();
            if (!string.IsNullOrEmpty(systemPrompt))
                turns.Add(new LocalChatTurn("system", systemPrompt));
            turns.Add(new LocalChatTurn("user", judgePrompt));

            var outcome = await port.GenerateAsync(new LocalGenerationRequest
            {
                SessionKey = "r426:relation-judge",
                TurnIndex = 1,
                Turns = turns,
                MaxTokens = maxTokens,
                // R429: 关系判官同为决策路径 ⇒ 同样钉死缓存态。
                CacheReuse = false,
            }, ct).ConfigureAwait(false);
            RelationJudge.RecordCachePinned();

            if (!outcome.Success || string.IsNullOrWhiteSpace(outcome.Content))
            {
                RelationJudge.RecordFallback("failed_or_empty");
                return null;
            }
            if (!outcome.AccountingConsistent)
            {
                RelationJudge.RecordAccountingViolation("tokens_evaluated != prompt_n + cache_n");
                return null;
            }
            if (!RelationLetterJudge.TryNormalize(outcome.Content, out var letter, out var parseReason))
            {
                // R435: 失败原因入计数 (可机检归因; R434 只能看到「降级了」, 看不到为什么)
                RelationJudge.RecordFallback("unparsed:" + parseReason);
                return null;
            }

            RelationJudge.RecordLocal(letter);
            return new RelationJudgeOutcome(letter, outcome.Content ?? string.Empty, outcome.GeneratedTokens,
                outcome.TokensEvaluated, outcome.PromptNewTokens);
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            RelationJudge.RecordFallback("exception:" + ex.GetType().Name);
            return null;
        }
    }

    /// <summary>被跳过轮的本地回复 (本地生成; 失败 → 固定兜底串, 保持"有回复"不变式)。</summary>
    /// <summary>
    /// R413: 被跳过轮的回复 —— **非 LLM 模板** (确定性、零 token、零延迟)。
    ///
    /// 为什么不本地生成: 真机实证 (2026-09-14 臂B) — 让 r1 生成"确认语"会退化:
    /// turn4 用户说「收到，谢谢。」它回「收到，谢谢。测试命令是什么？」(复读前文并反问),
    /// turn6 用户说「嗯。」它回「测试命令是什么？」。纯确认轮不含新信息, 生成没有信息可加,
    /// 只会引入幻觉; 模板串既安全又可机检 (用户 OOB 口径: 本地匹配 → 非 LLM 修/组装)。
    /// </summary>
    public Task<string> ComposeLocalSkipReplyAsync(string userMessage, CancellationToken ct = default)
    {
        TurnGate.RecordTemplateAck();
        return Task.FromResult(LocalSkipFallback);
    }

    /// <summary>
    /// 被跳过轮的回复模板 (非 LLM; 保证"有回复"不变式, 且不新增任何内容)。
    ///
    /// R489 文案裁决 (用户授权"需裁定的按统计学最优默认执行"): 原文案
    /// "收到，继续按当前方向推进，本轮不重新规划。" 含**动作声明** ("继续推进"/"不重新规划"),
    /// 而本地消化轮**没有做任何工作** ⇒ 该声明不被任何事实背书 (R488 质量细读把这条记为
    /// "未声明是本地 skip")。改为**纯确认语**: 只确认收到, 不承诺、不宣称已完成任何事
    /// ⇒ 语义上不可能与实质答复混淆 (冒充面归零), 且更短 (写入下一轮前缀的字节更少)。
    /// 机检面: 摘要轮次 telemetry `local_gate_skip_reply.kind == "template"` 仅在
    /// **确认类轮** (门判 mechanical:ack 族) 出现 ⇒ "本地替换只发生在确认轮"可被机检断言。
    /// </summary>
    public const string LocalSkipFallback = "收到。";

    /// <summary>
    /// R498 候选③ (R413 主线: 内容承载的本地生成通道): 用 r1 把**上一条实质答复**换一种说法改写。
    ///
    /// 与已有两条本地通道的分工 (R497 遗留的缺口正是第三条):
    ///   · 回放 (R465/R475): 原样重来 —— 「再讲一遍」;
    ///   · 模板 (R489):      纯确认语   —— 「嗯。」;
    ///   · **本方法**:        改写既有内容 —— 「换个说法」(用户要的是重述, 回放=答非所问, 模板=冒充)。
    ///
    /// 纪律 (逐条与既有本地面同源):
    ///   · 闸默认关 (<see cref="LocalParaphraseChannel.EnvName"/> != "1" ⇒ 直接 null, **零副作用**) ⇒ 生产逐位不变;
    ///   · 取消**必须上抛** (绝不把取消当降级);
    ///   · 空回/失败 ⇒ null (不得当成功, R411 口径);
    ///   · 记账恒等 (tokens_evaluated == prompt_n + cache_n) 不成立 ⇒ 结果**不采信**;
    ///   · 输出先去思考链 (<see cref="TurnGateJudge.StripThinking"/>) 再过 <see cref="LocalParaphraseChannel.Guard"/>
    ///     ⇒ 事实不守恒 / 反问 / 动作宣称新增一律**拒收** (拒绝即降级远端 = 最坏等于现状)。
    /// </summary>
    /// <returns>可用的改写正文; null ⇒ 调用方必须降级远端。</returns>
    public async Task<string?> TryComposeLocalParaphraseAsync(string sourceReply, CancellationToken ct = default)
    {
        if (!LocalParaphraseChannel.IsEnabled()) return null;
        LocalParaphrase.RecordAttempt();
        var port = _localPort;
        if (port is null)
        {
            LocalParaphrase.RecordNoPort();
            return null;
        }
        try
        {
            var maxTokens = Math.Max(_catalog.LocalChannel.MaxTokens, 512);
            var turns = new List<LocalChatTurn> { new("user", LocalParaphraseChannel.BuildPrompt(sourceReply)) };
            var outcome = await port.GenerateAsync(new LocalGenerationRequest
            {
                SessionKey = "r498:local-paraphrase",
                TurnIndex = 1,
                Turns = turns,
                MaxTokens = maxTokens,
                // 注 (R498): **不**在此钉死缓存态 —— C6 不变量 (DecisionCachePinTests) 钉住的是
                // 「全仓只有**决策**路径把 CacheReuse 置 false, 且恰为 2 处」。改写是**生成**路径,
                // 与主生成路径同语义 ⇒ 用端口默认 (CacheReuse=true)。若真机窗口证明缓存复用会污染
                // 改写质量, 下轮再钉死并**连带修订 C6** (须附正/负控读数, 不得单方面放宽判据)。
            }, ct).ConfigureAwait(false);

            if (!outcome.Success || string.IsNullOrWhiteSpace(outcome.Content))
            {
                LocalParaphrase.RecordEngineDegrade("failed_or_empty");
                return null;
            }
            if (!outcome.AccountingConsistent)
            {
                LocalParaphrase.RecordAccountingViolation("tokens_evaluated != prompt_n + cache_n");
                return null;
            }
            var stripped = TurnGateJudge.StripThinking(outcome.Content).Trim();
            var verdict = LocalParaphraseChannel.Guard(sourceReply, stripped);
            if (!verdict.Ok)
            {
                LocalParaphrase.RecordGuardReject(verdict.Reason);
                return null;
            }
            LocalParaphrase.RecordSuccess();
            return stripped;
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            LocalParaphrase.RecordEngineDegrade("exception:" + ex.GetType().Name);
            return null;
        }
    }

    /// <summary>
    /// R475: 空正文降级徽标的**公共前缀** (单源) —— 两处徽标文案均由本常量拼出,
    /// 回放守卫 (`IsReplayableReply`) 据此识别"非实质答复", 避免徽标文案改动后守卫失明。
    /// </summary>
    public const string EmptyBodyBannerPrefix = "⚠ 模型未产出正文";

    /// <summary>
    /// R475 回放守卫: 纯复述轮的本地消化 = **回放上一条 Assistant 答复原文**, 只对**实质答复**成立。
    /// 空/模板/空正文徽标 ⇒ 回放等于把失败当答复端给用户 (R474 真端点实测: R 臂 12 轮里 6 轮模板 + 3 轮用户可见横幅,
    /// 实质回答仅 3 轮, 而同轮 Arole 12/12 全实质) ⇒ 调用方**撤销 Skip 降级远端**, 不得以模板冒充。
    /// 注: 本判据作用于 **Assistant 侧历史文本**, 且只吃产品自身常量 (非新增用户轮关键词表 ⇒ 不违 R458 铁律)。
    /// </summary>
    public static bool IsReplayableReply(string? reply)
    {
        if (string.IsNullOrWhiteSpace(reply)) return false;
        var t = reply.Trim();
        if (t == LocalSkipFallback) return false;
        if (t.StartsWith(EmptyBodyBannerPrefix, StringComparison.Ordinal)) return false;
        return true;
    }
}
