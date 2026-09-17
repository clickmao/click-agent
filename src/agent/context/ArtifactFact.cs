using System.Text;

namespace agent.context;


/// <summary>
/// R458 承接轮 (degenerate / continuation turn) 的**人性化接地**机制。
///
/// 用户令 (2026-09-15): 「一个人对另一个人突然说一句"继续"，另一个人不明所以，肯定就会反问"继续什么"」
///   ⇒ 机器味问句 ("意图不明确，你想让 agent 做什么? (如: 搜索/写文档/…)") 换成**先承接真实状态, 再反问**。
///
/// 链机制 (非关键字补丁):
///   ① 判定面: 复用**既有**意图置信度分支 (WeakIntent/TooVague 且无更具体缺口) —— 不新立关键词表;
///   ② 接地面: 只在承接轮注入本块, 内容 = **工作区真实产物** (名字/字节/首行), 逐项可机检;
///   ③ 收口面: 模型若没接地 (回复既无问句又不含任何真实产物名) ⇒ 链自身用同一批事实组装反问 (fail-closed)。
///
/// 纪律: 零反射 / 零 shell / 零正则; 只读首行; 块内出现的每个文件名必须来自扫描结果 —— 负控保证:
///   扫描为空 ⇒ 块内不得出现任何文件名, 也从不得出现未扫描到的名字。
/// </summary>
public readonly record struct ArtifactFact(string Name, long Bytes, string FirstLine);
