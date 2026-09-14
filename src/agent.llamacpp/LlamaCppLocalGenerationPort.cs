using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using agent.modelqueue;

namespace agent.llamacpp;

/// <summary>
/// R413: <see cref="ILocalGenerationPort"/> 的 llama.cpp 实现 —— 长驻 llama-server (进程 + HTTP, 零 P/Invoke)。
///
/// 分层纪律: 端口接口在 agent.modelqueue (产品路由只依赖接口), 实现在本程序集 ⇒
/// agent.modelqueue 不反向依赖任何推理后端; 换后端 (别的 HTTP server / 假实现) 只换本类。
/// 渲染纪律 (R409): 提示串必经 <see cref="ILocalPromptRenderer"/> (由 <see cref="LlamaCppTextGenerator"/>
/// 内部保证, 本类**不得**自行拼 chat template)。
/// </summary>
public sealed class LlamaCppLocalGenerationPort : ILocalGenerationPort, IAsyncDisposable
{
    private readonly LlamaCppTextGenerator _generator;

    public LlamaCppLocalGenerationPort(LlamaCppGeneratorOptions options)
    {
        _generator = new LlamaCppTextGenerator(options);
    }

    public string BackendId => "llama.cpp";

    /// <summary>真实探测: gguf 存在 ∧ 二进制可解析 (委托生成器, 不猜)。</summary>
    public bool IsAvailable => _generator.IsAvailable;

    /// <summary>长驻 server 进程启动次数 (可观测; 0 = 从未启动 ⇒ 会计入"未使用")。</summary>
    public long ProcessStarts => _generator.ProcessStarts;

    public async Task<LocalGenerationOutcome> GenerateAsync(
        LocalGenerationRequest request, CancellationToken ct = default)
    {
        var sw = Stopwatch.StartNew();
        try
        {
            var turns = request.Turns
                .Select(t => new ChatTurn(t.Role, t.Content))
                .ToList();
            if (turns.Count == 0)
                return new LocalGenerationOutcome { Success = false, Error = "empty_turns" };

            var result = await _generator
                .GenerateTurnAsync(
                    turns,
                    sessionKey: request.SessionKey,
                    turnIndex: request.TurnIndex,
                    maxTokens: request.MaxTokens,
                    reuse: CompletionReuse.Session,
                    ct: ct)
                .ConfigureAwait(false);

            sw.Stop();
            // 口径 (R411 钉死): PromptTokens = tokens_evaluated = **总长**; 新算数 = 总长 − 命中。
            var total = result.PromptTokens;
            var cached = Math.Max(0, result.CachedTokens);
            return new LocalGenerationOutcome
            {
                Success = true,
                Content = result.Content ?? string.Empty,
                TokensEvaluated = total,
                PromptNewTokens = LlamaCppTextGenerator.RecomputedTokens(total, cached),
                CachedTokens = cached,
                GeneratedTokens = result.Tokens.Length,
                ElapsedMs = sw.ElapsedMilliseconds,
                Model = "local:llama.cpp",
            };
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            sw.Stop();
            // 失败必须如实回传 (调用方据此降级远端; 绝不返回"成功但空")
            return new LocalGenerationOutcome
            {
                Success = false,
                Error = $"local_failed:{ex.GetType().Name}",
                ElapsedMs = sw.ElapsedMilliseconds,
                Model = "local:llama.cpp",
            };
        }
    }

    public ValueTask DisposeAsync() => _generator.DisposeAsync();
}
