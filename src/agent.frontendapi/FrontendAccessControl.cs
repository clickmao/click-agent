using System.Security.Cryptography;
using System.Threading;

namespace agent.frontendapi;

/// <summary>
/// R358 (工业级补齐 #2/#3): FrontendApi 访问控制 — 共享 token 鉴权 + 令牌桶限流 + 并发上限。
/// 鉴权: 客户端首行必须是 HELLO 行 {"type":"auth","token":"..."}; token 来源
///   ① env AGENTFRAMEWORK_FRONTEND_TOKEN (部署注入, 优先) ② 启动时随机生成 (打印到 host 日志, 仅本机用户可见)。
/// 限流: 全局令牌桶 (默认 10 req/s, 桶容量 20) — 每请求取 1 token, 取不到回 busy 错误码。
/// 并发: 全局并发请求数上限 (默认 4), 超限同样回 busy。
/// 语义铁律: auth 前只接受 auth 行; 鉴权失败直接断连 (不响应, 防枚举探测)。
/// </summary>
public sealed class FrontendAccessControl
{
    private readonly byte[]? _token; // null = 未配置鉴权 (仅显式 AGENTFRAMEWORK_FRONTEND_AUTH=0 才允许)
    private readonly int _requestsPerSecond;
    private readonly int _burstCapacity;
    private readonly int _maxConcurrent;

    private readonly object _lock = new();
    private long _tokens;            // 当前令牌数 (定点 ×1000 防浮点)
    private long _lastRefillTicks;
    private int _inFlight;

    public FrontendAccessControl(int requestsPerSecond = 10, int burstCapacity = 20, int maxConcurrent = 4,
        bool? authDisabledOverride = null, string? tokenOverride = null)
    {
        _requestsPerSecond = requestsPerSecond;
        _burstCapacity = burstCapacity;
        _maxConcurrent = maxConcurrent;
        _tokens = burstCapacity * 1000L;
        _lastRefillTicks = Environment.TickCount64;

        var envToken = tokenOverride ?? Environment.GetEnvironmentVariable("AGENTFRAMEWORK_FRONTEND_TOKEN");
        var authDisabled = authDisabledOverride ?? Environment.GetEnvironmentVariable("AGENTFRAMEWORK_FRONTEND_AUTH") == "0";
        if (authDisabled)
        {
            _token = null; // 显式关闭 (仅限本机回环调试场景, 部署文档注明风险)
        }
        else if (!string.IsNullOrEmpty(envToken))
        {
            _token = System.Text.Encoding.UTF8.GetBytes(envToken);
            _isRandomToken = false;
        }
        else
        {
            _token = RandomNumberGenerator.GetBytes(32); // 随机生成 — 由 host 打印 hex
            _isRandomToken = true;
        }
    }

    private readonly bool _isRandomToken; // 随机生成 → 展示/校验都用 hex; env 注入 → 原文

    /// <summary>生成的/注入的 token (随机=hex; env 注入=原文; host 启动时打印一次)。</summary>
    public string TokenHex => _token is null ? "(auth=0 已关闭)" : _isRandomToken ? Convert.ToHexString(_token) : System.Text.Encoding.UTF8.GetString(_token);

    public bool AuthEnabled => _token is not null;

    /// <summary>校验客户端 auth 行 token; true = 通过 (定长时间比较防时序)。
    /// 随机 token 客户端拿到 hex 展示 → hex 解码比较; env 注入 token → 原文比较。</summary>
    public bool ValidateToken(string? provided)
    {
        if (_token is null || string.IsNullOrEmpty(provided)) return _token is null;
        if (_isRandomToken)
        {
            try
            {
                var hexBytes = Convert.FromHexString(provided);
                return CryptographicOperations.FixedTimeEquals(_token, hexBytes);
            }
            catch (FormatException) { return false; }
        }
        return CryptographicOperations.FixedTimeEquals(
            _token, System.Text.Encoding.UTF8.GetBytes(provided));
    }


    /// <summary>请求准入: 取令牌 + 占并发槽。false = 超限 (调用方回 busy)。</summary>
    public bool TryAcquire()
    {
        lock (_lock)
        {
            RefillLocked();
            if (_tokens < 1000) return false;      // 令牌不足
            if (_inFlight >= _maxConcurrent) return false;
            _tokens -= 1000;
            _inFlight++;
            return true;
        }
    }

    /// <summary>请求完成: 释放并发槽。</summary>
    public void Release()
    {
        lock (_lock) { _inFlight--; }
    }

    private void RefillLocked()
    {
        var now = Environment.TickCount64;
        var elapsedMs = Math.Max(0, now - _lastRefillTicks);
        if (elapsedMs > 0)
        {
            _tokens = Math.Min(_burstCapacity * 1000L, _tokens + elapsedMs * _requestsPerSecond);
            _lastRefillTicks = now;
        }
    }
}
