using System.Linq;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>模型校验结果 (C.6.5 — JSON 输出)</summary>
public sealed class ModelVerifyResult
{
    public string Command { get; set; } = "model_verify";
    public string Model { get; set; } = string.Empty;
    public bool Ok { get; set; }

    /// <summary>HTTP 状态码 (0 = 网络/ DNS 失败)</summary>
    public int HttpStatusCode { get; set; }

    /// <summary>判定说明 (401/403 = 地址正确+鉴权拒绝 = 合法; 404/DNS = 参数错误)</summary>
    public string Verdict { get; set; } = string.Empty;

    public string? Error { get; set; }
}
