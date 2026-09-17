using System.Collections.Generic;

namespace agent.r1;

/// <summary>
/// R1 管道 · 由题面机械抽取出的公开用例集合。
/// <see cref="CommandPrefix"/> = 题面里含占位符的命令模板去掉占位符后的前缀（如 <c>python3 -m games </c>），
/// 逐例命令 = 前缀 + 该例所属分组 id。
/// </summary>
public sealed record PublicExampleSet(string CommandPrefix, IReadOnlyList<PublicExample> Examples);
