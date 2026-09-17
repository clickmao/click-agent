using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;

public sealed partial class ModelQueueRouter : IModelQueueCaller
{

    public async Task<QueueResponse> CallAsync(QueuePrompt prompt, TaskKindHint kind, string intent, CancellationToken ct = default)
    {
        // R413: 本地生成通道 (计划节点: 重新整理所有能力 → 精炼合理化链管道 → 提高 KPI)。
        // R351 (用户钦定) 移除的是**旧的「本地 LLM 使用」路径** (全走远端 API), 与本通道无关 —
        // 新增 r1 本地生成是计划内节点 (用户 2026-09-14 口径纠正)。
        // 判据 (预注册): 通道就绪 ∧ 非带图 ∧ 种类允许 ∧ prompt 不超限 ∧ 端口真实可用。
        var localDecision = LocalChannelPolicy.Evaluate(prompt, kind, _catalog.LocalChannel, _localPort);
        if (localDecision.Allowed)
        {
            var local = await TryLocalAsync(prompt, kind, ct).ConfigureAwait(false);
            if (local is not null)
                return local;
            // 失败/记账违规 ⇒ 已计数并落 LocalChannelLastBasis, 继续走远端 (降级永不静默)
        }
        else
        {
            LocalChannel.RecordReject(localDecision.ReasonText);
            LocalChannelLastBasis = $"local:rejected:{localDecision.ReasonText}";
        }

        // R351 (用户钦定): 旧的本地 LLM 推理通道移除 — 远端调用全部经 API (远端目录)。
        // 需求1 混合调度: 手动/粘性优先 → 通道优先级 (远端目录)
        var sticky = _catalog.Find(_manualOverride ?? _activeModelId);
        var entry = sticky
                    ?? _policy.Select(null, kind, intent,
                        prompt.EstimatedTokens, prompt.EstimatedTokens / 3, _catalog)
                    ?? SelectByChannelPriority(kind, intent, prompt.EstimatedTokens);
        // R356-c: 选模依据实时可观测 (snapshot/state 消费; sticky 命中原来不更新 → 恒显 init)
        LastSelectionBasis = sticky is not null
            ? $"sticky:{entry!.Id}"
            : $"auto:{entry?.Id ?? "(none)"}";
        if (entry is null)
        {
            // R457 链机制: 无候选/缺凭据必须"可见失败" —— 此前只填 Error 不标面向用户,
            // 经 UserFacingFailureContent 折成空串 ⇒ 用户看到静默空回复 (R456 首跑实测)。
            var missingKeys = _catalog.Models
                .Where(m => !string.IsNullOrEmpty(m.ApiKeyEnv)
                            && string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv)))
                .Select(m => m.ApiKeyEnv!).Distinct().OrderBy(x => x, StringComparer.Ordinal).ToArray();
            var detail = _catalog.Models.Count == 0
                ? "模型目录为空: 请在 config/base/models.yaml 配置至少一个模型"
                : missingKeys.Length > 0
                    ? "目录内 " + _catalog.Models.Count + " 个模型全部不可用: 环境变量未设置 ("
                      + string.Join(", ", missingKeys) + ")"
                    : "目录内 " + _catalog.Models.Count + " 个模型均未命中当前请求的选模条件";
            LastSelectionBasis = "auto:(none)";
            agent.config.AgentTelemetry.Emit("model_unavailable", "ModelQueueRouter",
                ("models", _catalog.Models.Count), ("missing_keys", missingKeys.Length),
                ("kind", kind.ToString()));
            return new QueueResponse
            {
                Success = false,
                Error = detail,
                Content = "⚠ 无可用模型 — " + detail + "。请设置对应环境变量后重试。",
                ContentIsUserFacing = true,
                Model = "(none)",
            };
        }

        // v0.12.0 A3 (真缺陷 64): 带图请求必须落在 image_input 模型 —
        // 手动/粘性/策略选中 text-only 模型 (glm-4-plus/deepseek 等) 时重路由到首个可用视觉模型
        // (视觉模型 key 可用性同 policy 判据; 无视觉候选 → 保持原 entry, 让 API 错误如实暴露)。
        if (prompt.ImageUrls.Count > 0 && !entry.Capabilities.ImageInput)
        {
            var vision = _catalog.Models.FirstOrDefault(m =>
                m.Capabilities.ImageInput &&
                (m.ApiKeyEnv is null ||
                 !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv))));
            if (vision is not null)
            {
                Switches.Add(new ModelSwitchRecord
                    { From = entry.Id, To = vision.Id, Reason = "vision_required" });
                LastSelectionBasis = $"vision_required:{vision.Id} (原 {entry.Id} 无 image_input, 带图请求)";
                _logger.LogWarning("ModelQueue: {From} 无 image_input 且请求带图 → 重路由 {To}", entry.Id, vision.Id);
                entry = vision;
            }
        }

        // v0.11.0 R115 (真缺陷 43): TokenUsageService.InitializeAsync 此前无调用点 — 余额快照
        // 恒空 → EstimateBalance 恒 (null,true) → MIN_BALANCE 阈值切模整条链路死代码。
        // 惰性 fire-once 启动同步 (后台, 不阻断首调用; 失败静默走"余额未知不判定"语义)。
        if (_tokenUsage is not null)
        {
            var syncTask = _balanceSyncOnce.EnsureStartedAsync(_tokenUsage);
            try { await syncTask.WaitAsync(TimeSpan.FromSeconds(3), ct).ConfigureAwait(false); }
            catch (TimeoutException) { /* 首同步 >3s 不阻断对话, 本轮按余额未知处理 */ }
        }

        // v0.10.0: 余额预估检查 — 不足 → 切换其他模型 + flags:余额不足 提示
        if (_tokenUsage is not null)
        {
            var (remaining, sufficient) = _tokenUsage.EstimateBalance(entry.Provider, prompt.EstimatedTokens);
            if (!sufficient)
            {
                var alt = SelectAlternativeByBalance(entry, prompt.EstimatedTokens);
                if (alt is not null && alt.Id != entry.Id)
                {
                    Switches.Add(new ModelSwitchRecord
                        { From = entry.Id, To = alt.Id, Reason = "insufficient_balance" });
                    _activeModelId = alt.Id;
                    LastSelectionBasis = $"balance_fallback:{alt.Id} ({entry.Id} 余额不足)";
                    LastBalanceFlag = $"model:{alt.Id} flags:余额不足 (原 {entry.Id} 预估余额 ${remaining:F2})";
                    _logger.LogWarning("ModelQueue: {From} 余额不足 (${Remain:F2}) → 切换 {To}",
                        entry.Id, remaining ?? 0, alt.Id);
                    entry = alt;
                }
                else
                {
                    // 无备选 → 继续原模型但带上提示
                    LastBalanceFlag = $"model:{entry.Id} flags:余额不足 (预估剩余 ${remaining:F2}, 无备选继续)";
                    _logger.LogWarning("ModelQueue: {Id} 余额不足但无备选 — 继续原模型", entry.Id);
                }
            }
        }

        // v0.11.0 R129 (PGO v2 D3): 热路径计时 — llm_call 真耗时 (成功/失败均打), 与 wall 的差值
        // 即排队/路由开销; 依据 assembly 打点既有 ms 风格 (IndustrialAgentV2.cs:383)。
        var llmSw = System.Diagnostics.Stopwatch.StartNew();
        try
        {
            // R373: 首轮预算按任务类型给足 (真机 D1/D7 同源根因: 推理与正文共享 max_tokens)
            var firstBudget = InitialMaxTokens(kind, intent);
            var resp = await CallEntryAsync(entry, prompt, ct, firstBudget).ConfigureAwait(false);
            // R371 真缺陷 (空正文): 推理模型把输出预算全花在思维链 → content 空但 success=true,
            // 用户侧表现为"执行 ~30s 后回复空白" (E2E 铁证: completion 8192/8192, content_len=0, reasoning_len=22633,
            // loop_turn reply_chars=0 且 success=true)。旧修 (R19: max_tokens 2000→8192) 只是抬高天花板 —
            // 推理可吃满任意上限 → 改为"检测 + 有界恢复 + 诚实降级"。
            // R478 (承 R477 真机 20/20 空正文调用): 先**定因**再处置 —— 上游 finish_reason=tool_calls 时
            // 旧逻辑既白跑一次 32k 预算重试, 又把成因误诊为"推理占满输出预算"。判据只取协议字段 (机制面)。
            var emptyCause = EmptyBodyDiagnosis.Classify(resp.FinishReason, resp.ToolCalls?.Count ?? 0,
                resp.ReasoningContent?.Length ?? 0);
            if (string.IsNullOrWhiteSpace(resp.Content))
            {
                if (EmptyBodyDiagnosis.RoutableToActionLoop(emptyCause, resp.ToolCalls?.Count ?? 0, ActionLoopRunner.IsEnabled()))
                {
                    // 协议级动作请求 ∧ 工具执行面已启用 ⇒ 保留 tool_calls 上抛交动作环 (重试不可能产出正文: 省 1 次调用)
                    agent.config.AgentTelemetry.Emit("llm_call_empty_body", "ModelQueueRouter",
                        ("request_id", resp.RequestId), ("cause", EmptyBodyDiagnosis.CauseName(emptyCause)),
                        ("finish_reason", resp.FinishReason ?? ""), ("tool_calls_n", resp.ToolCalls!.Count),
                        ("retry_skipped", true), ("routed_to", "action_loop"), ("turn", prompt.TurnIndex));
                }
                else if (emptyCause == EmptyBodyCause.ToolCall)
                {
                    // 工具执行面未启用 ⇒ 诚实文案 (带上游真实 finish_reason) + 显式失败, 且**不再重试**
                    agent.config.AgentTelemetry.Emit("llm_call_empty_body", "ModelQueueRouter",
                        ("request_id", resp.RequestId), ("cause", EmptyBodyDiagnosis.CauseName(emptyCause)),
                        ("finish_reason", resp.FinishReason ?? ""), ("tool_calls_n", resp.ToolCalls?.Count ?? 0),
                        ("retry_skipped", true), ("routed_to", "user_banner"), ("turn", prompt.TurnIndex));
                    resp.Success = false;
                    resp.Error = "empty_body_tool_calls_not_executed";
                    resp.ContentIsUserFacing = true;
                    resp.Content = EmptyBodyBannerPrefix + EmptyBodyDiagnosis.Banner(emptyCause, resp.FinishReason);
                }
                else if (emptyCause == EmptyBodyCause.LengthExhausted || !string.IsNullOrWhiteSpace(resp.ReasoningContent))
                {
                    resp = await RecoverFromEmptyContentAsync(entry, prompt, resp, emptyCause, ct).ConfigureAwait(false);
                }
            }
            // R371 D7 真缺陷 (真机 RUN3 实证): 正文被输出预算**截断** (completion=8192 上限, content=1209 字符,
            // 断在 `start_len: int =` 的半行) 却 success=true → 用户拿到半份实现, 且 artifact 命中率看起来只是"抖动"。
            // 判据纯语法 (与模型无关): 尾部是未完结构 (= ( [ { , + - * / \ : 或未闭合三引号/围栏)。
            // 处置: 有界**续写一次** (升预算 + 明确断点提示) → 去重重拼; 失败则保留原文 (绝不假装完整)。
            if (LooksTruncated(resp.Content))
                resp = await RecoverFromTruncatedAsync(entry, prompt, resp, ct).ConfigureAwait(false);
            llmSw.Stop();
            lock (_lock)
            {
                _consecutiveFailures = 0;
                // v0.11.0 R89 (真缺陷 36): auto 选模成功后同步粘性 id — 原 _activeModelId 只在
                // failover/手动切换时更新, /model 与 /balance 查询时 ActiveModel getter
                // 落到目录首项 (gpt-4o), 与实际调用模型 (glm) 不一致 (真机 /model 实证)。
                if (_manualOverride is null) _activeModelId = entry.Id;
            }
            // v0.10.0: 用量本地累计
            _tokenUsage?.RecordUsage(resp.Model, entry.Provider, resp.PromptTokens, resp.CompletionTokens);
            // R377: prompt 缓存命中率 KPI (未上报 → -1, 与"命中 0"区分)
            var cacheKv = PromptCacheKpi.Fields(resp.CacheHitTokens, resp.CacheMissTokens);
            // R380 (用户钦定**口径修订**, 首要 KPI): 命中率只算"需要命中的部分" —— 本轮新增不计入
            //  (新增是首次发送, 必然不命中; 计入分母会把"前缀复用度"与"本轮新发量"混为一谈 → 指标被稀释)。
            //  有效命中率 = hit / min(本轮 prompt, 上一轮已发 prompt); 会话首轮无"需要命中"部分 → -1。
            var sessKey = prompt.SessionId ?? string.Empty;
            var lastPrompt = 0;
            if (sessKey.Length > 0 && _lastPromptTokens.TryGetValue(sessKey, out var lp)) lastPrompt = lp;
            var effKv = PromptCacheKpi.EffectiveFields(resp.CacheHitTokens, resp.PromptTokens, LastPromptTokensFor(sessKey));
            // R470: 归因通道 (只增不改) —— 真实流量无同会话前驱 ⇒ 命中属 shared_prefix, 既有 -1 通道看不见
            var chanKv = PromptCacheKpi.ChannelFields(resp.CacheHitTokens, resp.CacheMissTokens, resp.PromptTokens, LastPromptTokensFor(sessKey));
            var effRate = (double)(effKv[1].Value ?? -1d);
            // R476: 分档判定面 (只增不改) —— 单值 97% 对长轮结构性不可达 (R469) ⇒ 逐调用落
            // 档/上限/目标/余量/判定 + 口径标记 (growth 是用户轮的上偏代理, 禁当实测用户轮档)。
            var bandKv = PromptCacheRedline.BandFields(prompt.TurnIndex, (int)(effKv[0].Value ?? 0), resp.PromptTokens, effRate);
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider),
                // R379: 逐轮归属 (红线判据: 多轮第 2 轮起命中率 ≥ PromptCacheRedline.Threshold, 现 97%) — 无此字段则无法把 KPI 追到"第几轮"
                ("agent_session", prompt.SessionId ?? ""), ("turn", prompt.TurnIndex),
                ("prompt_tokens", resp.PromptTokens), ("completion_tokens", resp.CompletionTokens),
                ("total_tokens", resp.TokensUsed), ("success", resp.Success),
                ("empty_reply", string.IsNullOrEmpty(resp.Content)),
                // R478: 逐调用因果 id + 空正文定因 (R477 教训: 无 finish_reason 就只剩"猜成因")
                ("request_id", resp.RequestId),
                ("finish_reason", resp.FinishReason ?? ""),
                ("tool_calls_n", resp.ToolCalls?.Count ?? 0),
                ("empty_cause", EmptyBodyDiagnosis.CauseName(EmptyBodyDiagnosis.Classify(resp.FinishReason,
                    resp.ToolCalls?.Count ?? 0, resp.ReasoningContent?.Length ?? 0))),
                ("error_kind", resp.Error ?? ""),
                // v0.11.0 R19: 内容长度诊断 (C03 曾现 completion 2000 tok 但回复渲染空 — 定位内容丢在链路哪段)
                ("content_len", resp.Content?.Length ?? 0),
                // v0.21.1: 推理模型思考链长度诊断 (reasoning_content 是否被真实返回 / 占多少)
                ("reasoning_len", resp.ReasoningContent?.Length ?? 0),
                // R371 D7: 每次调用都记录是否**结构未闭合** (截断) — 无此字段, "半份实现"只能靠人肉看输出才发现
                ("truncated", LooksTruncated(resp.Content)),
                // R373 归因铁律 (R372 教训): 命中/失败必须能追溯到**机制** — 记录首轮预算与意图,
                // 否则"预算策略是否真生效"又只能靠猜 (本轮真机首跑即踩: 适配器硬编码 intent 使策略成死代码)。
                ("first_budget", firstBudget), ("intent", intent ?? ""),
                // v0.11.0 R129 (D3): LLM 真耗时 ms
                ("ms", llmSw.ElapsedMilliseconds),
                // R496 候选⑦: 台账挂载面并入**逐调用**行 (R495 只在 tool_decl_gate 上 ⇒ 远程调用轴看不见挂载代价)。
                // 挂载关 ⇒ 0/空串 (与 R490..R495 逐字节同形); 真值只以指纹出现 (候选①)。
                ("ledger_mount", prompt.Mount.On ? "1" : "0"),
                ("ledger_n", prompt.Mount.N),
                ("ledger_chars", prompt.Mount.Text.Length),
                ("ledger_code8", prompt.Mount.On ? LocalDecisionLedger.Code8(prompt.Mount.Code) : ""),
                ("ledger_key_id", prompt.Mount.On ? LocalDecisionLedger.KeyId() : ""),
                cacheKv[0], cacheKv[1], cacheKv[2], effKv[0], effKv[1], chanKv[0], chanKv[1], chanKv[2],
                bandKv[0], bandKv[1], bandKv[2], bandKv[3], bandKv[4], bandKv[5], bandKv[6]);
            // R380 (+R379 逐轮归属) 红线闸门 —— 用户逐字: "一旦越过红线必然检查问题为什么发生并修复"。
            // 越线不得只记数字: 必须同时落盘**可执行诊断**(按 R379 实测四类破坏点排序) + 响亮告警。
            if (sessKey.Length > 0)
            {
                if (_lastPromptTokens.Count > 512) _lastPromptTokens.Clear();   // 有界: 防长驻进程无界增长
                _lastPromptTokens[sessKey] = resp.PromptTokens;
            }
            var cacheable = (int)(effKv[0].Value ?? 0);
            if (PromptCacheRedline.Violated(prompt.TurnIndex, cacheable, effRate))
            {
                var diag = PromptCacheRedline.Diagnose(prompt.TurnIndex, resp.PromptTokens, cacheable,
                    PromptCacheKpi.HitTokens(resp.CacheHitTokens), PromptCacheKpi.MissTokens(resp.CacheMissTokens), lastPrompt);
                _logger.LogWarning("ModelQueue: prompt 缓存红线越线 — {Diag}", diag);
                agent.config.AgentTelemetry.Emit("cache_redline_violation", "ModelQueueRouter",
                    ("agent_session", sessKey), ("turn", prompt.TurnIndex),
                    ("effective_hit_rate", effRate), ("cacheable_tokens", cacheable),
                    ("hit", PromptCacheKpi.HitTokens(resp.CacheHitTokens)),
                    ("miss", PromptCacheKpi.MissTokens(resp.CacheMissTokens)),
                    ("prompt_tokens", resp.PromptTokens), ("last_prompt_tokens", lastPrompt),
                    ("threshold", PromptCacheRedline.Threshold), ("diagnosis", diag),
                    ("band_verdict", PromptCacheRedline.JudgeByGrowth(prompt.TurnIndex, cacheable, resp.PromptTokens, effRate)),
                    ("band_ceiling", Math.Round(PromptCacheRedline.CeilingFromGrowth(cacheable, resp.PromptTokens - cacheable), 4)),
                    ("band_target", Math.Round(PromptCacheRedline.TargetFromGrowth(cacheable, resp.PromptTokens - cacheable), 4)));
            }
            // 阈值再同步 (fire-and-forget, 不阻塞主链)
            if (_tokenUsage is not null && _tokenUsage.NeedsResync(entry.Provider))
                _ = _tokenUsage.TryResyncAsync(entry.Provider, CancellationToken.None);
            return resp;
        }
        catch (HttpRequestException ex)
        {
            llmSw.Stop();
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider), ("success", false), ("error_kind", "http"), ("error", ex.Message),
                ("ms", llmSw.ElapsedMilliseconds));
            return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, $"网络错误: {ex.Message}").ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            // HttpClient 超时 (非用户取消) = 瞬态
            llmSw.Stop();
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider), ("success", false), ("error_kind", "timeout"),
                ("ms", llmSw.ElapsedMilliseconds));
            return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, "请求超时").ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            // 用户取消永不触发模型切换 (C.4 验收)
            throw;
        }
    }
}
