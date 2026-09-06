using System;
using System.Collections.Generic;
using System.Linq;
using LLama;
using LLama.Common;
using LLama.Native;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;

namespace agent.llamalocal;

/// <summary>
/// v0.11.0 R103: bge embedding 模式决策 (用户钦定语义) —
///   • 进程内/共享服务已加载 LLM → bge 走 CPU 档 (GPU 资源留给 chat 推理, native 已驻留进程复用);
///   • 未加载 LLM → bge 走 GPU (vulkan) 档: loader + 可枚举设备探测, 软设备 (llvmpipe) 视为无 GPU 回落 CPU。
///   失败回落: GPU 加载/推理失败自动降 CPU (best-effort, 不阻塞召回主链)。
/// 决策结果缓存 (进程级一次) — NativeLibraryConfig 配置后不可变, 必须一次定档。
/// </summary>
public static class BgeModeDecision
{
    private static readonly object Lock = new();
    private static BgeExecutionMode? _decided;
    private static string? _reason;

    /// <summary>bge 执行档位</summary>
    public enum BgeExecutionMode
    {
        /// <summary>CPU 档 (GpuLayerCount=0, 与进程内已加载 LLM 共享 native)</summary>
        Cpu,

        /// <summary>GPU/vulkan 档 (独立 bge 场景, 加速 embedding)</summary>
        Vulkan,
    }

    /// <summary>上次决策依据 (诊断/打点)</summary>
    public static string LastReason => _reason ?? "(未决策)";

    /// <summary>
    /// 决策并缓存。llmLoaded: 本进程或共享服务是否已加载 chat LLM。
    /// </summary>
    public static BgeExecutionMode Decide(bool llmLoaded, ILogger logger)
    {
        lock (Lock)
        {
            if (_decided.HasValue)
                return _decided.Value;

            if (llmLoaded)
            {
                _decided = BgeExecutionMode.Cpu;
                _reason = "LLM 已加载 → bge CPU 档 (共享 native, GPU 留给 chat)";
            }
            else if (VulkanSupport.IsLoaderAvailable() && HasRealGpuDevice())
            {
                _decided = BgeExecutionMode.Vulkan;
                _reason = "LLM 未加载 + 真实 GPU 设备 → bge vulkan 档";
            }
            else
            {
                _decided = BgeExecutionMode.Cpu;
                _reason = VulkanSupport.IsLoaderAvailable()
                    ? "LLM 未加载 + 仅软设备 (llvmpipe) → bge CPU 档"
                    : "LLM 未加载 + 无 vulkan loader → bge CPU 档";
            }

            logger.LogInformation("[bge-mode] {Mode}: {Reason}", _decided.Value, _reason);
            return _decided.Value;
        }
    }

    /// <summary>真实 GPU (排除 llvmpipe/软实现) — 与 VulkanSupport.HasVulkanDevice 的 loader 判据互补。</summary>
    private static bool HasRealGpuDevice()
    {
        try
        {
            using var p = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = "vulkaninfo",
                Arguments = "--summary",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
            });
            if (p == null) return false;
            var output = p.StandardOutput.ReadToEnd();
            p.WaitForExit(8000);
            if (p.ExitCode != 0) return false;
            // PHYSICAL_DEVICE_TYPE_CPU = llvmpipe 软设备 → 不算 GPU
            return output.Contains("PHYSICAL_DEVICE_TYPE_DISCRETE", StringComparison.Ordinal) ||
                   output.Contains("PHYSICAL_DEVICE_TYPE_INTEGRATED", StringComparison.Ordinal);
        }
        catch
        {
            return false;
        }
    }
}

/// <summary>
/// v0.11.0 R103: bge embedding 双实现调度器 (词袋兜底, bge 首选 — 用户钦定优先级)。
///   • 模式决策: BgeModeDecision (LLM 已加载→CPU, 未加载+真GPU→vulkan, 否则 CPU)
///   • bge 未就绪 (模型缺/加载败) → 词袋 hash 兜底 (R58 实现, 永不失败)
///   • 打点: bge_mode 决策 + bge_embed 延迟/维度 (PGO 语义, 供召回率对比)
/// </summary>
public sealed class EmbeddingRouter : agent.vectormemory.IEmbeddingProvider
{
    private readonly ILogger? _logger;
    private readonly string? _modelPath;
    private readonly bool _llmLoaded;
    private readonly object _lock = new();
    private agent.vectormemory.IEmbeddingProvider? _bge;
    private agent.vectormemory.IEmbeddingProvider BgeOrDefault
    {
        get
        {
            if (_bge != null) return _bge;
            lock (_lock)
            {
                if (_bge != null) return _bge;
                _bge = CreateBge() ?? new HashEmbeddingProvider();
                return _bge;
            }
        }
    }

    public EmbeddingRouter(string? modelPath, bool llmLoaded, ILogger? logger = null)
    {
        _modelPath = modelPath;
        _llmLoaded = llmLoaded;
        _logger = logger;
        agent.config.AgentTelemetry.Emit("bge_mode", "EmbeddingRouter",
            ("mode", BgeModeDecision.Decide(llmLoaded, logger ?? NullLogger.Instance).ToString()),
            ("reason", BgeModeDecision.LastReason));
    }

    public int Dimension => BgeOrDefault.Dimension;
    public string Name => BgeOrDefault.Name;

    public float[] Embed(string text)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var vec = BgeOrDefault.Embed(text);
        sw.Stop();
        agent.config.AgentTelemetry.Emit("bge_embed", "EmbeddingRouter",
            ("provider", BgeOrDefault.Name), ("dim", vec.Length), ("ms", sw.ElapsedMilliseconds));
        return vec;
    }

    private agent.vectormemory.IEmbeddingProvider? CreateBge()
    {
        if (_modelPath == null || !File.Exists(_modelPath))
        {
            _logger?.LogInformation("[bge-mode] 模型缺失 ({Path}) → 词袋兜底", _modelPath ?? "(未配置)");
            return null;
        }
        try
        {
            var mode = BgeModeDecision.Decide(_llmLoaded, _logger ?? NullLogger.Instance);
            if (mode == BgeModeDecision.BgeExecutionMode.Vulkan)
            {
                // vulkan 档: LLamaSharp native 走 ggml-vulkan (失败回落 CPU 重试)
                try
                {
                    VulkanSupport.Configure(LlamaBackendMode.Vulkan, _logger ?? NullLogger.Instance);
                    return agent.vectormemory.BgeEmbeddingProvider.Create(_modelPath, gpuLayerCount: 8);
                }
                catch (Exception ex)
                {
                    _logger?.LogWarning("[bge-mode] vulkan 加载失败 ({Msg}) → CPU 档重试", ex.Message);
                }
            }
            VulkanSupport.Configure(LlamaBackendMode.Cpu, _logger ?? NullLogger.Instance);
            return agent.vectormemory.BgeEmbeddingProvider.Create(_modelPath, gpuLayerCount: 0);
        }
        catch (Exception ex)
        {
            _logger?.LogWarning("[bge-mode] bge 初始化失败 ({Msg}) → 词袋兜底", ex.Message);
            return null;
        }
    }
}

/// <summary>词袋 hash embedding (R58 语义, 兜底永不失败) — 与 RAG GenerateEmbedding 同款逻辑。</summary>
public sealed class HashEmbeddingProvider : agent.vectormemory.IEmbeddingProvider
{
    public int Dimension => 256;
    public string Name => "hash-fallback";

    public float[] Embed(string text)
    {
        var emb = new float[256];
        foreach (var word in text.Split(' ', '，', '。', '、', '\n'))
        {
            if (word.Length == 0) continue;
            var h = Math.Abs(word.GetHashCode());
            for (int seed = 0; seed < 3; seed++)
                emb[(h + seed * 31337) % 256] += 1f;
        }
        var mag = System.Math.Sqrt(emb.Sum(e => (double)e * e));
        if (mag > 0)
            for (int i = 0; i < emb.Length; i++)
                emb[i] /= (float)mag;
        return emb;
    }
}
