using agent.config;

namespace agent.modelqueue;


public sealed class BalanceScheme
{
    public string Endpoint { get; set; } = string.Empty;

    /// <summary>调研备注 (接口现状/字段说明)</summary>
    public string Note { get; set; } = string.Empty;
}
