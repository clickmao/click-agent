using LLama;
using LLama.Common;
using agent.templates;
using Microsoft.Extensions.Logging;

namespace agent.llamalocal;

/// <summary>
/// 本地 llama.cpp 推理槽 (v7.12): LLamaSharp 0.27 接 ILLMCaller。
/// 云端 OpenAI 未配置/失败时的本地兜底 (主备槽语义延伸);
/// 模型文件不存在时诚实报错 — 不伪造回复。
///
/// Vulkan loader 统一 (用户钦定): LLamaSharp.Backend.Vulkan 是空壳包 (零原生产物);
/// 其 libggml-vulkan.so 的 DT_NEEDED = libvulkan.so.1, 与 Silk.NET.Vulkan 加载的 loader
/// 是同一系统动态库 (readelf 实证) — 不引入任何冗余 vulkan 副本, loader 全局唯一。
/// </summary>
public sealed class LocalLlamaCaller : ILLMCaller, IDisposable
{
    private readonly ILogger<LocalLlamaCaller> _logger;
    private readonly string _modelPath;
    private readonly uint _contextSize;
    private readonly object _lock = new();

    private LLamaWeights? _weights;
    private InteractiveExecutor? _executor;
    private bool _initialized;

    public string ModelName => $"llama.cpp:{Path.GetFileName(_modelPath)}";

    public LocalLlamaCaller(ILogger<LocalLlamaCaller> logger, string modelPath, uint contextSize = 2048)
    {
        _logger = logger;
        _modelPath = modelPath;
        _contextSize = contextSize;
    }

    /// <summary>模型文件是否就绪 (CLI /status 展示)</summary>
    public static bool IsModelAvailable(string modelPath) =>
        File.Exists(modelPath) && new FileInfo(modelPath).Length > 0;

    public async Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
    {
        var response = new LLMResponse { Model = ModelName };

        if (!IsModelAvailable(_modelPath))
        {
            response.Success = false;
            response.Error = $"本地模型文件不存在: {_modelPath} — 请放置 gguf 模型或配置云端 LLM。";
            return response;
        }

        try
        {
            EnsureInitialized();
            var input = string.IsNullOrEmpty(prompt.SystemPrompt)
                ? prompt.UserMessage
                : prompt.SystemPrompt + "\n\n" + prompt.UserMessage;

            var sw = System.Diagnostics.Stopwatch.StartNew();
            var sb = new System.Text.StringBuilder();
            await foreach (var token in _executor!.InferAsync(input, new InferenceParams
            {
                TokensKeep = 0,
                MaxTokens = 512,
                AntiPrompts = new List<string> { "用户:", "User:" },
            }, ct))
            {
                sb.Append(token);
            }
            sw.Stop();

            response.Success = true;
            response.Content = sb.ToString().Trim();
            response.CompletionTokens = EstimateTokens(response.Content);
            _logger.LogInformation("本地推理完成: {Tokens} tokens in {Ms}ms",
                response.CompletionTokens, sw.ElapsedMilliseconds);
        }
        catch (OperationCanceledException)
        {
            response.Success = false;
            response.Error = "本地推理已取消。";
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "LocalLlamaCaller 推理失败");
            response.Success = false;
            response.Error = $"本地推理失败: {ex.Message}";
        }

        return response;
    }

    private void EnsureInitialized()
    {
        if (_initialized)
            return;

        lock (_lock)
        {
            if (_initialized)
                return;

            var parameters = new ModelParams(_modelPath)
            {
                ContextSize = _contextSize,
                Threads = Math.Max(2, Environment.ProcessorCount / 2),
                GpuLayerCount = 0, // CPU 后端; vulkan 后端部署时由用户环境决定
            };
            _weights = LLamaWeights.LoadFromFile(parameters);
            var context = _weights.CreateContext(parameters);
            _executor = new InteractiveExecutor(context);
            _initialized = true;
            _logger.LogInformation("本地模型加载完成: {Model}", _modelPath);
        }
    }

    private static int EstimateTokens(string text) =>
        string.IsNullOrEmpty(text) ? 0 : Math.Max(1, text.Length * 3 / 10); // 中文≈0.3 token/char 粗估

    public void Dispose()
    {
        _executor = null;
        _weights?.Dispose();
        _weights = null;
        _initialized = false;
    }
}
