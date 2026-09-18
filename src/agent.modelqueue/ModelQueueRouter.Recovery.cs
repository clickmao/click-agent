using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;

public sealed partial class ModelQueueRouter : IModelQueueCaller
{

    /// <summary>
    /// R373 **首轮预算策略** —— D1(空正文)/D7(半正文) 的**同源根因修复**。
    /// 真机铁证: `completion_tokens=8192` 被**推理内容独占** (reasoning_len 22633~28306, content_len=0),
    /// 旧行为 = 首轮 8192 全废 → 触发有界恢复(第 2 次调用 32768) → 同题 2~3 次调用/多花 8192 tok/多等 30~60s。
    /// 正解: **首轮就按任务类型给足预算** (推理 + 完整产物必须同框), 恢复链退化为兜底。
    /// 判据只取**确定性信号** (任务类型 + 意图标签), 不做用户文本关键词猜测 —— 避免把闲聊也抬到 32k。
    /// </summary>
    public static int InitialMaxTokens(TaskKindHint kind, string? intent)
    {
        if (kind != TaskKindHint.General) return DefaultMaxTokens;   // 压缩/标注类任务产物短, 保持 8k
        if (string.IsNullOrWhiteSpace(intent)) return DefaultMaxTokens;
        foreach (var marker in LargeOutputIntentMarkers)
            if (intent.Contains(marker, StringComparison.OrdinalIgnoreCase)) return MaxTokensEscalated;
        return DefaultMaxTokens;
    }

    /// <summary>大产物意图标记 (产物通常含整份文件/脚本 → 推理+正文必须同框)。</summary>
    private static readonly string[] LargeOutputIntentMarkers =
        { "code", "coding", "script", "program", "game", "implement", "refactor", "artifact" };

    /// <summary>R371: 抑制推理、强制正文的提示 (模型无关表述, 追加为 system 消息)。</summary>
    private const string NoReasoningNudge =
        "[系统] 直接输出最终答案正文本身, 不要输出思考/推理过程 (推理会占满输出预算, 导致正文为空)。";

    /// <summary>
    /// R371 空正文恢复 (真缺陷修复): 首次调用 content 为空而 reasoning 非空 (= 推理吃满输出预算)
    /// → 升级预算 + 抑制推理再试一次; 仍空则返回**可见降级文案**并把 Success 置假 (绝不静默返回空白)。
    /// 有界: 只重试 1 次, 不做循环; 失败判定与遥测绑定 (success/empty_reply/error_kind)。
    /// </summary>
    private async Task<QueueResponse> RecoverFromEmptyContentAsync(
        ModelCatalogEntry entry, QueuePrompt prompt, QueueResponse first, EmptyBodyCause cause, CancellationToken ct)
    {
        var firstReasoning = first.ReasoningContent?.Length ?? 0;
        var firstCompletion = first.CompletionTokens;
        try
        {
            var retried = await CallEntryAsync(entry, prompt, ct,
                maxTokensOverride: MaxTokensEscalated, extraSystemSuffix: NoReasoningNudge).ConfigureAwait(false);
            var recovered = !string.IsNullOrWhiteSpace(retried.Content);
            agent.config.AgentTelemetry.Emit("llm_call_recover", "ModelQueueRouter",
                ("model", entry.Id), ("reason", "empty_content"), ("max_tokens", MaxTokensEscalated),
                // R478: 定因 + 因果 id + 首/重试 finish_reason (禁把"上游请求工具"记成"预算不足")
                ("request_id", first.RequestId), ("cause", EmptyBodyDiagnosis.CauseName(cause)),
                ("first_finish_reason", first.FinishReason ?? ""), ("retry_finish_reason", retried.FinishReason ?? ""),
                ("retry_skipped", false),
                ("first_content_len", first.Content?.Length ?? 0), ("first_reasoning_len", firstReasoning),
                ("first_completion_tokens", firstCompletion),
                ("retry_content_len", retried.Content?.Length ?? 0),
                ("retry_reasoning_len", retried.ReasoningContent?.Length ?? 0),
                ("retry_completion_tokens", retried.CompletionTokens),
                // R475 记账补齐 (R474 实测: recover 行缺 prompt/缓存字段 ⇒ 产品自记账漏 15,458 prompt tok = Arole 的 21.8%):
                // 取值**同源于 first/retried**, 禁二次估算; 未上报一律 -1 (不冒充 0)。
                ("prompt_tokens", first.PromptTokens),
                ("cache_hit_tokens", PromptCacheKpi.HitTokens(first.CacheHitTokens)),
                ("cache_miss_tokens", PromptCacheKpi.MissTokens(first.CacheMissTokens)),
                ("cache_hit_rate", PromptCacheKpi.HitRate(first.CacheHitTokens, first.CacheMissTokens)),
                ("retry_prompt_tokens", retried.PromptTokens),
                ("recovered", recovered));
            if (recovered) return retried;

            retried.Success = false;
            retried.Error = "empty_content_after_retry";
            // R414: 本条 Content 是**面向用户**的降级文案 ⇒ 必须显式标记, 否则链侧按"不可见失败"丢弃 (= 用户看到空白)
            retried.ContentIsUserFacing = true;
            // R478: 文案**由定因单源生成**并带上游真实 finish_reason (旧文案把 tool_calls 也写成"推理占满预算")
            retried.Content = EmptyBodyBannerPrefix
                + EmptyBodyDiagnosis.Banner(cause, retried.FinishReason ?? first.FinishReason);
            return retried;
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            agent.config.AgentTelemetry.Emit("llm_call_recover", "ModelQueueRouter",
                ("model", entry.Id), ("reason", "empty_content"), ("recovered", false), ("error", ex.Message),
                ("request_id", first.RequestId), ("cause", EmptyBodyDiagnosis.CauseName(cause)),
                // R475 记账补齐: 异常路径同样落 prompt/缓存取值 (同源 first), 未上报 -1。
                ("prompt_tokens", first.PromptTokens),
                ("cache_hit_tokens", PromptCacheKpi.HitTokens(first.CacheHitTokens)),
                ("cache_miss_tokens", PromptCacheKpi.MissTokens(first.CacheMissTokens)),
                ("cache_hit_rate", PromptCacheKpi.HitRate(first.CacheHitTokens, first.CacheMissTokens)));
            first.Success = false;
            first.Error = $"empty_content_retry_failed: {ex.Message}";
            first.ContentIsUserFacing = true;
            // 凭据/内部信息卫生: 可见文案**不带 ex.Message** (原始异常仍完整保留在 Error 字段, 供排查/日志)
            first.Content = EmptyBodyBannerPrefix + ", 且自动重试失败 — 请重试或切换模型。";
            return first;
        }
    }

    /// <summary>
    /// R371 D7: **截断检测** (真机 RUN3 实证: 输出预算耗尽, 正文停在半行 `start_len: int =` 却 success=true)。
    /// 判据纯语法、与模型/语言无关: 尾部是"未完结构" (= ( [ { , + - * / \ : 或未闭合三引号 / 未闭合围栏)。
    /// 为何不用 token 计数: 预算可被升级 (8192 → 32768), 只有**结构未闭合**才是与预算无关的客观截断证据。
    /// </summary>
    public static bool LooksTruncated(string? content)
    {
        if (string.IsNullOrWhiteSpace(content)) return false;
        var t = content.TrimEnd();
        if (t.Length == 0) return false;

        // R556 真缺陷修复 (证据 = R555 两窗 rc=4 + 中继 dump 请求面): 首答常是「**完整**契约 JSON + 尾随内容」。
        // 旧启发式只看末字符 ⇒ 尾随散文/第二个值以 `(` `,` `:` `{` 收尾时判"截断" ⇒ ① 多发一次全价调用
        // (~8.4k prompt, 属"不必要的 llm api 请求") ② 把续写段拼到已完整的 JSON 后面 ⇒ 严格解析在拼接点
        // 失败 (R555 w82/w84 报 "… is invalid after a single JSON value") ⇒ 整窗作废。
        // 判据 (确定性): 开头是对象/数组 ⇒ 截断证据 = **首个值是否配平闭合** (闭合 ⇒ 完整; 未闭合 ⇒ 真截断,
        // 含"断在字符串中途"这类旧启发式漏判的情形)。非结构化正文 (代码/散文) 仍走下方原有启发式。
        if (t[0] == '{' || t[0] == '[')
        {
            var depth = 0;
            var inStr = false;
            var esc = false;
            var closed = false;
            foreach (var c in t)
            {
                if (inStr)
                {
                    if (esc) esc = false;
                    else if (c == '\\') esc = true;
                    else if (c == '"') inStr = false;
                    continue;
                }
                if (c == '"') inStr = true;
                else if (c == '{' || c == '[') depth++;
                else if (c == '}' || c == ']')
                {
                    depth--;
                    if (depth <= 0) { closed = depth == 0; break; }
                }
            }
            return !closed;
        }

        // 尾部运算符 / 开括号 / 分隔符 → 语句未完 (中文全角标点不算: "说明如下：" 是完整句)
        if ("=([{,+-*/\\:".IndexOf(t[^1]) >= 0) return true;

        // 未闭合的三引号 (字符串字面量中途断掉)
        var triples = 0;
        for (var i = 0; (i = t.IndexOf("\"\"\"", i, StringComparison.Ordinal)) >= 0; i += 3) triples++;
        if (triples % 2 == 1) return true;

        // 未闭合的代码围栏
        var fences = 0;
        for (var i = 0; (i = t.IndexOf("```", i, StringComparison.Ordinal)) >= 0; i += 3) fences++;
        return fences % 2 == 1;
    }

    /// <summary>续写去重: 去掉续写段开头与已输出尾部**重叠**的部分 (模型常把断点前几个字符重打一遍)。</summary>
    public static string MergeContinuation(string head, string tail)
    {
        if (tail.Length == 0) return head;
        var max = Math.Min(MaxOverlapChars, Math.Min(head.Length, tail.Length));
        for (var len = max; len >= MinOverlapChars; len--)
        {
            var overlapped = head.AsSpan(head.Length - len);
            if (!overlapped.SequenceEqual(tail.AsSpan(0, len))) continue;
            // 纯空白重叠不算证据: 缩进/换行在断点两侧本来就相同, 删掉会吃掉真实缩进
            if (!ContainsNonSpace(overlapped)) continue;
            return head + tail[len..];
        }
        return head + tail;
    }

    private const int MinOverlapChars = 6;   // 6 起: 覆盖 `print(` 这类真实断点重复
    private const int MaxOverlapChars = 200;

    private static bool ContainsNonSpace(ReadOnlySpan<char> s)
    {
        foreach (var c in s) if (!char.IsWhiteSpace(c)) return true;
        return false;
    }

    /// <summary>截断续写提示 (模型无关表述): 给出断点, 只要求补剩余部分。</summary>
    private const string TruncatedNudge =
        "[系统] 上一轮回答在输出预算处被**截断**了 (不是写完了)。请**只输出断点之后的剩余内容**, 从断点处直接续写: "
        + "不要重复断点之前的任何字符, 不要重开场白/标题, 不要解释, 不要重开代码围栏。";

    /// <summary>
    /// R371 D7 修复: 截断正文 → 升预算 + 断点提示**续写一次**, 语法去重重拼;
    /// 续写失败/仍截断则保留原文并如实上报 (success 不置假: 半份实现仍可用, 但 truncated 事实必须可见)。
    /// </summary>
    private async Task<QueueResponse> RecoverFromTruncatedAsync(
        ModelCatalogEntry entry, QueuePrompt prompt, QueueResponse first, CancellationToken ct)
    {
        var head = first.Content ?? string.Empty;
        var tailShown = head.Length <= 40 ? head : head[^40..];
        try
        {
            var retried = await CallEntryAsync(entry, prompt, ct,
                maxTokensOverride: MaxTokensEscalated, extraSystemSuffix: TruncatedNudge).ConfigureAwait(false);
            var added = (retried.Content ?? string.Empty).TrimEnd();
            var merged = added.Length == 0 ? head : MergeContinuation(head, retried.Content!);
            var stillTruncated = LooksTruncated(merged);
            agent.config.AgentTelemetry.Emit("llm_call_continue", "ModelQueueRouter",
                ("model", entry.Id), ("reason", "truncated"), ("max_tokens", MaxTokensEscalated),
                ("before_len", head.Length), ("added_len", added.Length), ("after_len", merged.Length),
                ("first_completion_tokens", first.CompletionTokens),
                ("retry_completion_tokens", retried.CompletionTokens),
                ("still_truncated", stillTruncated), ("recovered", added.Length > 0 && !stillTruncated),
                ("tail_before", tailShown));
            if (added.Length == 0) return first;
            first.Content = merged;
            return first;
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            agent.config.AgentTelemetry.Emit("llm_call_continue", "ModelQueueRouter",
                ("model", entry.Id), ("reason", "truncated"), ("recovered", false), ("error", ex.Message));
            return first;
        }
    }

    private static int _reqDumpSeq;

    /// <summary>
    /// R378 (缓存命中率归因): 把发给提供方的请求体原样落盘, 目录由 env AGENTFRAMEWORK_DUMP_REQUEST 指定。
    /// 用途: 两次调用的最长公共前缀 = 提供方实际可缓存的上界; 据此定位"第一个分歧字节"。
    /// 默认关闭 (未设 env 时零开销), 失败静默且不影响主链。
    /// </summary>
    private static void DumpRequestIfRequested(string body)
    {
        var dir = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_DUMP_REQUEST");
        if (string.IsNullOrWhiteSpace(dir)) return;
        try
        {
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
            var n = System.Threading.Interlocked.Increment(ref _reqDumpSeq);
            var stamp = DateTime.UtcNow.ToString("HHmmss_fff", System.Globalization.CultureInfo.InvariantCulture);
            var path = Path.Combine(dir, "req_" + stamp + "_" + n.ToString("00", System.Globalization.CultureInfo.InvariantCulture) + ".json");
            File.WriteAllText(path, body, new System.Text.UTF8Encoding(false));
        }
        catch
        {
            // 诊断通道: 任何失败都不应影响主链
        }
    }

    /// <summary>R478: 逐调用序号 (进程内单调; 仅归因用, 不参与任何判定)。</summary>
    private long _callSeq;

    private async Task<QueueResponse> CallEntryAsync(ModelCatalogEntry entry, QueuePrompt prompt, CancellationToken ct,
        int? maxTokensOverride = null, string? extraSystemSuffix = null)
    {
        // R478: 逐调用 id 生成点 = 唯一入口 (成功/缺凭据/降级三路共用同一值 ⇒ 可因果 join)
        var requestId = string.Concat(entry.Id, "#",
            System.Threading.Interlocked.Increment(ref _callSeq).ToString(System.Globalization.CultureInfo.InvariantCulture),
            "@", DateTimeOffset.UtcNow.ToUnixTimeMilliseconds().ToString(System.Globalization.CultureInfo.InvariantCulture));
        // R351: 全通道 key 走环境变量 (官方内存通道已移除; 凭据铁律不变)
        var apiKey = Environment.GetEnvironmentVariable(entry.ApiKeyEnv);
        if (string.IsNullOrEmpty(apiKey))
        {
            // R457 链机制: 缺凭据 ⇒ 必须"可见失败" (此前只填 Error 不标面向用户,
            // 经 UserFacingFailureContent 折成空串 ⇒ 该轮 reply_len=0 静默; 真机负控 C3 实测)。
            agent.config.AgentTelemetry.Emit("model_unavailable", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider),
                ("missing_key", entry.ApiKeyEnv ?? "(未声明)"), ("kind", "api_key_env_missing"));
            return new QueueResponse
            {
                RequestId = requestId,
                Success = false,
                Model = entry.Id,
                Error = $"环境变量 {entry.ApiKeyEnv} 未设置 (模型 {entry.Id} 的 API Key 来源)",
                Content = $"⚠ 未配置模型凭据 — 环境变量 {entry.ApiKeyEnv} 未设置, 无法调用 {entry.Id}。请设置该环境变量后重试。",
                ContentIsUserFacing = true,
            };
        }

        var client = _httpClientFactory.CreateClient("modelqueue");
        var targetEndpoint = prompt.ImageUrls.Count > 0 ? VisionPayload.ToChatEndpoint(entry.Endpoint) : entry.Endpoint;
        var messages = BuildMessages(prompt, extraSystemSuffix);
        var request = new QueueChatRequest { Model = entry.Id, Messages = messages, ReasoningEffort = prompt.ReasoningEffort, ToolsJson = prompt.ToolsJson };
        // R490 声明面按需 + 回放剪裁: 逐调用打点 (可机检「非工具意图调用不带 tools」)
        {
            var gateOn = ToolDeclGate.IsEnabled();
            var chGateOn = ToolDeclGate.IsChannelGateEnabled();
            var declared = !string.IsNullOrEmpty(prompt.ToolsJson);
            agent.config.AgentTelemetry.Emit("tool_decl_gate", "ModelQueueRouter",
                ("declared", declared),
                ("gate", gateOn ? "1" : "0"),
                // R494 通道轴: 隔离通道标记 + 通道轴开关 + 轴上判据 (打点与实发面同寿命)
                ("channel_gate", chGateOn ? "1" : "0"),
                ("isolated_channel", prompt.IsolatedChannel),
                ("intent", prompt.Intent ?? "(null)"),
                ("reason", ToolDeclGate.DecideReason(prompt.Intent, gateOn, prompt.IsolatedChannel, chGateOn)),
                ("replay_trimmed", prompt.ReplayTrimmedLocalTemplates),
                ("replay_user_trimmed", prompt.ReplayTrimmedLocalUserTurns),
                ("replay_pair_gate", ReplayPairTrim.Stamp()),
                // R495 台账挂载面: 与 BuildMessages 同一 prompt 对象 ⇒ 打点与实发面同源
                // (判据器另有独立通道: 中继归档的请求体字节 —— 两路必须一致, 不一致即打点脱钩)。
                // R496 候选⑦ (R495 审计发现: 台账面只在 tool_decl_gate 点上 ⇒ 同一行看不到远程调用轴):
                // 逐调用面 (llm_call) 同步补上同样五个字段; R496 候选①: 打点面**不再含真值** ——
                // `ledger_code` (LCM-…) 换成 `ledger_code8` (sha8(码)) + `ledger_key_id` (sha8(密钥)),
                // 二者都推不回码/密钥, 但判据器可核「实发面 ↔ 打点面 ↔ 落盘面」指纹一致。
                ("ledger_mount", prompt.Mount.On ? "1" : "0"),
                ("ledger_n", prompt.Mount.N),
                ("ledger_chars", prompt.Mount.Text.Length),
                ("ledger_code8", prompt.Mount.On ? LocalDecisionLedger.Code8(prompt.Mount.Code) : ""),
                ("ledger_key_id", prompt.Mount.On ? LocalDecisionLedger.KeyId() : ""),
                ("ledger_session8", prompt.Mount.Session8),
                ("turn", prompt.TurnIndex));
        }
        if (maxTokensOverride is int mt && mt > 0) request.MaxTokens = mt;
        var requestBody = SerializeChatRequest(request);
        // R378 归因: 请求体按需落盘 (env AGENTFRAMEWORK_DUMP_REQUEST=目录) —— 缓存命中率前缀分歧点可测
        DumpRequestIfRequested(requestBody);
        using var http = new HttpRequestMessage(HttpMethod.Post, targetEndpoint)
        {
            Content = new StringContent(requestBody, System.Text.Encoding.UTF8, "application/json"),
        };
        http.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", apiKey);

        using var resp = await client.SendAsync(http, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"HTTP {(int)resp.StatusCode}: {Truncate(body, 200)}");
        }

        var parsed = JsonSerializer.Deserialize(body, ModelQueueJsonContext.Default.OpenAIChatResponse);
        var choice = parsed?.Choices?.FirstOrDefault();
        var content = choice?.Message?.Content ?? string.Empty;
        // v0.21.1: 推理模型思考链捕获 (DeepSeek deepseek-flash/reasoner 实测返回 reasoning_content)
        var reasoning = choice?.Message?.ReasoningContent;
        // R456 解析面: tool_calls → 链上动作请求 (无 tool_calls 时为 null, 行为与旧版一致)
        List<ActionToolCall>? toolCalls = null;
        if (choice?.Message?.ToolCalls is { Count: > 0 } raw)
        {
            toolCalls = new List<ActionToolCall>(raw.Count);
            foreach (var tc in raw)
                toolCalls.Add(new ActionToolCall
                {
                    Id = tc.Id ?? string.Empty,
                    Name = tc.Function?.Name ?? string.Empty,
                    ArgumentsJson = string.IsNullOrEmpty(tc.Function?.Arguments) ? "{}" : tc.Function!.Arguments!,
                });
        }
        return new QueueResponse
        {
            RequestId = requestId,
            Content = content,
            Success = true,
            Model = entry.Id,
            PromptTokens = parsed?.Usage?.PromptTokens ?? 0,
            TokensUsed = parsed?.Usage?.TotalTokens ?? 0,
            CacheHitTokens = parsed?.Usage?.PromptCacheHitTokens,
            CacheMissTokens = parsed?.Usage?.PromptCacheMissTokens,
            ReasoningContent = reasoning,
            ToolCalls = toolCalls,
            FinishReason = choice?.FinishReason,
        };
    }

    /// <summary>
    /// R379: 消息列表装配 (自 CallEntryAsync 抽出, 供缓存前缀不变式机检直接消费, 无需网络)。
    /// 顺序契约: system(会话内恒定字节) → context(system, 本轮) → history(追加式全量回放) → user(本轮)
    ///   → [extraSystemSuffix]。
    /// ⚠ extraSystemSuffix 必须追加在末尾: 任何把它前置到 system 首位的改动都会切断已缓存前缀
    ///   (MultiTurnCachePrefixTests 负向控制会红)。同理 system 一旦发出, 会话内不得再变。
    /// </summary>
    internal static List<QueueChatMessage> BuildMessages(QueuePrompt prompt, string? extraSystemSuffix = null)
    {
        var messages = new List<QueueChatMessage>();
        if (!string.IsNullOrEmpty(prompt.SystemPrompt))
            messages.Add(new QueueChatMessage { Role = "system", Content = prompt.SystemPrompt });
        if (!string.IsNullOrEmpty(prompt.ContextPrompt))
            messages.Add(new QueueChatMessage
            {
                Role = "system",
                Content = $"以下是你可以参考的相关上下文信息，请结合这些信息回答用户问题：\n\n{prompt.ContextPrompt}"
            });
        foreach (var msg in prompt.History)
            messages.Add(new QueueChatMessage { Role = msg.Role, Content = msg.Content });
        // v0.12.0 A2: 带图 user 消息 → parts[] 多段 (text + image_url × N)
        if (prompt.ImageUrls.Count > 0)
        {
            var parts = new List<QueueContentPart> { new() { Type = "text", Text = prompt.UserMessage } };
            // v0.12.0 A3 (真缺陷 63): 本地路径 → base64 data URL (云端无法读本地文件, 真机 400/1210 实证)
            parts.AddRange(prompt.ImageUrls.Select(u => new QueueContentPart
            {
                Type = "image_url",
                ImageUrl = new QueueImageUrl { Url = VisionPayload.ToDataUrl(u) },
            }));
            messages.Add(new QueueChatMessage { Role = "user", Content = prompt.UserMessage, ContentParts = parts });
        }
        else
        {
            messages.Add(new QueueChatMessage { Role = "user", Content = prompt.UserMessage });
        }

        // v0.12.0 A3 (真缺陷 64): coding 端点不收图像 (HTTP 400 1210 真机实证) —
        // 带图请求改写标准 v4 chat 端点 (glm-5.3-flash 视觉走 v4, data URL 真机已验 1445tok)。
        // R495 本地决策台账挂载: 只在**尾部**追加 (user 之后) ⇒ 前缀面逐字节不变; 关 ⇒ 零字节。
        if (prompt.Mount.On)
            messages.Add(new QueueChatMessage { Role = "system", Content = prompt.Mount.Text });
        if (!string.IsNullOrWhiteSpace(extraSystemSuffix))
            messages.Add(new QueueChatMessage { Role = "system", Content = extraSystemSuffix });
        // R456 回灌面: 动作环追加消息 (assistant(tool_calls)/tool(...)) 一律在**最尾部** ——
        // 前缀 system/context/history/user/extra 逐字节不变 ⇒ provider 缓存前缀单调增长 (R377 红线)。
        foreach (var pm in prompt.PostUser)
            messages.Add(new QueueChatMessage
            {
                Role = pm.Role,
                Content = pm.Content,
                ToolCalls = pm.ToolCalls,
                ToolCallId = pm.ToolCallId,
            });
        return messages;
    }

    private static string Truncate(string s, int max) =>
        s.Length <= max ? s : s[..max] + "…";
}
