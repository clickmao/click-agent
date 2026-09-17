using System.Collections.Generic;

namespace agent.rover.gpu.spirv;


/// <summary>SPIR-V 结构校验问题 (机器可读码 + 字索引 + 说明)。</summary>
public sealed record SpirvIssue(string Code, int WordIndex, string Detail);
