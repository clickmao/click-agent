using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.action;
using agent.modelqueue;
using Xunit;
namespace agent.tests;


/// <summary>
/// R498 候选④: 文件面「越界必拒」的**结构正控** (P1 边界注入缺陷必红)。
///
/// R497 遗留: 文件面的越界拒绝是**无闸常量** (Resolve 无条件拒), 于是「越界必拒」只能被断言成
/// 恒真 —— 把 Resolve 的整段越界检查删掉, 旧的负样本用例仍可能因「文件不存在」而红, 红因与被测
/// 行为无因果绑定 (无正控的断言 = 无判别力)。本轮把 Resolve 接到命令面**同一个**闸常量
/// (<see cref="WorkspaceActionPort.BoundaryEnvName"/>, 默认开), 于是有了**缺陷注入臂**:
///   闸=1 (默认) ⇒ 越界读必须**拒绝**且**不得回显字节**;
///   闸=0 (注入)  ⇒ 同一调用必须**成功并回显** —— 这一条绿, 上一条才不是恒真。
/// 同时保留反向负控 (闸=1 + 区内路径必须照常工作), 防「一刀切全拒」也能骗过前两条。
///
/// 隔离: 该测试写**进程级**环境变量 ⇒ 与其它集合不并行 (<c>DisableParallelization = true</c>)。
/// </summary>
[CollectionDefinition("action-boundary-env", DisableParallelization = true)]
public sealed class ActionBoundaryEnvCollection
{
    public const string Name = "action-boundary-env";
}
