using System;

namespace agent.r1;

/// <summary>
/// R1 管道开关（结构量，非文本判据）：AGENTFRAMEWORK_R1_CONTRACT ∈ {1,on,true} ⇒ 单条路径走 R1。
/// 缺省关 ⇒ 宿主行为与既往逐字节一致（可随时回退，无隐性生效）。
/// </summary>
public static class R1ContractMode
{
    public static bool IsEnabled
    {
        get
        {
            var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_CONTRACT");
            if (string.IsNullOrWhiteSpace(v))
            {
                return false;
            }
            var t = v.Trim().ToLowerInvariant();
            return t is "1" or "on" or "true" or "yes";
        }
    }
}
