using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using LLama;
using LLama.Common;
using LLama.Native;
using Microsoft.Extensions.Logging;

namespace agent.llamalocal;

/// <summary>
/// v0.11.0 R103: 本地 LLM 守护服务 — 进程内独占加载一次 chat 模型 (LLamaWeights) + bge embedding,
/// 多个 CLI 实例通过 Unix domain socket 共享。解决"多实例各自加载 LLM 导致显存/内存翻倍"问题。
///
/// 生命周期: agenthost --llm-service 启动 → 绑定 data/llm.sock → 循环 accept →
///   每连接顺序处理 (llama.cpp 推理本身非线程安全, 串行化 = 正确性优先, 并发由客户端排队)。
/// 互斥: 同 data 目录只允许一个服务 — socket 文件存在且可连即拒绝二次启动 (原子检测)。
/// </summary>
public sealed class LlmServiceHost
{
    private readonly ILogger _logger;
    private readonly string _socketPath;
    private readonly string _chatModelPath;
    private readonly string? _bgeModelPath;
    private readonly uint _contextSize;
    private readonly uint _gpuLayers;
    private readonly LlamaBackendMode _backendMode;
    private readonly LlmServiceProtocol _protocol = new();

    public LlmServiceHost(ILogger logger, string socketPath, string chatModelPath,
        string? bgeModelPath, uint contextSize, uint gpuLayers, LlamaBackendMode backendMode)
    {
        _logger = logger;
        _socketPath = socketPath;
        _chatModelPath = chatModelPath;
        _bgeModelPath = bgeModelPath;
        _contextSize = contextSize;
        _gpuLayers = gpuLayers;
        _backendMode = backendMode;
    }

    /// <summary>
    /// 另一实例是否已在跑 (socket 可连 = 存活)。启动方据此决定"加入已有服务"还是"自建"。
    /// </summary>
    public static bool IsAlive(string socketPath)
    {
        try
        {
            using var probe = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            var ep = new UnixDomainSocketEndPoint(socketPath);
            var ar = probe.BeginConnect(ep, null, null);
            if (!ar.AsyncWaitHandle.WaitOne(800))
                return false;
            probe.EndConnect(ar);
            return true;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>阻塞运行 (宿主进程生命周期)。返回 Task 仅便于 async 上下文。</summary>
    public async Task RunAsync(CancellationToken ct)
    {
        // 残留 socket 文件清理 (IsAlive=false 时的 stale file)
        if (File.Exists(_socketPath))
        {
            if (IsAlive(_socketPath))
                throw new InvalidOperationException($"LLM 服务已在运行: {_socketPath} — 禁止二次加载模型 (多实例共享语义)。");
            File.Delete(_socketPath);
        }

        var effective = VulkanSupport.Configure(_backendMode, _logger);
        _logger.LogInformation("LLM 服务: backend={Mode}, chat={Chat}, bge={Bge}",
            effective, _chatModelPath, _bgeModelPath ?? "(无)");

        // 模型只加载一次 (本服务进程内)
        var chatParams = new ModelParams(_chatModelPath)
        {
            ContextSize = _contextSize,
            Threads = Math.Max(2, Environment.ProcessorCount / 2),
            GpuLayerCount = effective == LlamaBackendMode.Vulkan ? (int)_gpuLayers : 0,
        };
        using var weights = LLamaWeights.LoadFromFile(chatParams);
        var executor = new InteractiveExecutor(weights.CreateContext(chatParams));

        // bge embedding (进程内已加载 LLM → 共享 native, bge 走 CPU 档计算 — 用户钦定的共享语义)
        agent.vectormemory.BgeEmbeddingProvider? bge = null;
        if (_bgeModelPath != null && File.Exists(_bgeModelPath))
        {
            bge = agent.vectormemory.BgeEmbeddingProvider.Create(_bgeModelPath, gpuLayerCount: 0);
            _logger.LogInformation("bge 就绪: dim={Dim}", bge.Dimension);
        }

        using var lsock = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
        lsock.Bind(new UnixDomainSocketEndPoint(_socketPath));
        lsock.Listen(8);
        _logger.LogInformation("LLM 服务监听: {Socket} — CLI 实例共享此模型实例", _socketPath);

        while (!ct.IsCancellationRequested)
        {
            var client = await lsock.AcceptAsync(ct);
            // 串行处理: llama.cpp context 非线程安全; 排队语义对多 CLI 实例公平
            try
            {
                using (client)
                {
                    var stream = new NetworkStream(client, ownsSocket: false);
                    var req = _protocol.ReadRequest(stream);
                    if (req == null) continue;
                    var resp = Handle(req, executor, bge);
                    _protocol.WriteResponse(stream, resp);
                }
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                _logger.LogWarning("LLM 服务连接处理失败: {Msg}", ex.Message);
            }
        }
    }

    private LlmServiceProtocol.Response Handle(LlmServiceProtocol.Request req,
        InteractiveExecutor executor, agent.vectormemory.BgeEmbeddingProvider? bge)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        try
        {
            switch (req.Op)
            {
                case LlmServiceProtocol.OpPing:
                    return new LlmServiceProtocol.Response { Ok = true, Content = "pong", Ms = 0, Model = "service" };

                case LlmServiceProtocol.OpEmbed:
                    if (bge == null)
                        return new LlmServiceProtocol.Response { Ok = false, Error = "bge 模型未配置/未就绪" };
                    var vec = bge.Embed(req.Text ?? "");
                    return new LlmServiceProtocol.Response
                    {
                        Ok = true,
                        // 向量以 CSV 编码进 content (协议层不引入第三 DTO — 帧协议保持 2 消息形态)
                        Content = string.Join(',', vec),
                        Tokens = vec.Length,
                        Ms = sw.ElapsedMilliseconds,
                        Model = "bge-local",
                    };

                case LlmServiceProtocol.OpChat:
                default:
                    // v0.11.0 R104: ChatML 模板 (Qwen2.5/ChatML 系指令模型需结构化 prompt 才有可用输出;
                    // 裸拼接实测 0.5B 输出复读垃圾 — 00:2x 真机实证)。anti-prompt 含 im_end 正确截停。
                    var input = $"<|im_start|>system\n{req.System ?? "你是有用的助手。"}<|im_end|>\n<|im_start|>user\n{req.Text ?? ""}<|im_end|>\n<|im_start|>assistant\n";
                    var sb = new System.Text.StringBuilder();
                    foreach (var token in executor.InferAsync(input, new InferenceParams
                    {
                        TokensKeep = 0,
                        MaxTokens = req.MaxTokens > 0 ? req.MaxTokens : 512,
                        AntiPrompts = new List<string> { "<|im_end|>", "用户:", "User:" },
                    }).WaitToCompletion())
                        sb.Append(token);
                    var content = sb.ToString().Trim();
                    return new LlmServiceProtocol.Response
                    {
                        Ok = true,
                        Content = content,
                        Tokens = Math.Max(1, content.Length * 3 / 10),
                        Ms = sw.ElapsedMilliseconds,
                        Model = $"llama.cpp:{Path.GetFileName(_chatModelPath)}",
                    };
            }
        }
        catch (Exception ex)
        {
            return new LlmServiceProtocol.Response { Ok = false, Error = $"服务处理失败: {ex.Message}" };
        }
    }
}

/// <summary>扩展: IAsyncEnumerable&lt;string&gt; 同步收集 (服务串行语义下无异步价值, 避免 state machine 开销)。</summary>
internal static class InferExtensions
{
    public static IEnumerable<string> WaitToCompletion(this System.Collections.Generic.IAsyncEnumerable<string> source)
    {
        var enumerator = source.GetAsyncEnumerator(CancellationToken.None);
        try
        {
            while (enumerator.MoveNextAsync().AsTask().GetAwaiter().GetResult())
                yield return enumerator.Current;
        }
        finally
        {
            enumerator.DisposeAsync().AsTask().GetAwaiter().GetResult();
        }
    }
}
