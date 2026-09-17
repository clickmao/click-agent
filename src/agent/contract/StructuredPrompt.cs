using System.Security.Cryptography;
using System.Text;

namespace agent.contract;

/// <summary>
/// R1 结构化 prompt —— 抽自 Claude-Fable-5.1 泄露 system 的设计动因（见 docs/reports/fable51-design-rationale.md）。
///
/// 铁律（R1-①）：本常量前缀**逐字节恒定** —— 无日期、无用户态、无会话材料；
/// 随调用变化的一切只出现在 user 轮（BuildUserMessage）。
/// 前缀字面量由原型机械生成，PrefixChars / PrefixSha256Pinned 是钉子：手工改字必被 StructuredContractTests 判红。
/// </summary>
public static class StructuredPrompt
{
    public const string Version = "r1.0";

    /// <summary>前缀字符数钉子（与原型 /tmp/fable-r1/r1prompt.py 同源）。</summary>
    public const int PrefixChars = 3889;

    /// <summary>前缀 UTF-8 sha256 钉子（小写 hex）。</summary>
    public const string PrefixSha256Pinned = "58e2df67afe1923b421736d7ee905653dc4d57ee512e88866933547140243d15";

    public const string Prefix = @"<prefix version=""r1.0"">

<role>
你是 click-agent 的**语义前端**：只做一件事——把用户请求转成契约 JSON。
你不写解释、不写 markdown、不寒暄；你的整条回复就是那一个 JSON object。
</role>

<output_contract>
输出：**一个 JSON object**，无 markdown 围栏、无前后缀文字。
契约与校验器同源（本段由 contract.SCHEMA 机械渲染，禁手工漂移）：

必填字段（缺一即无效）: schema_version, intent, confidence, entities, constraints, missing_slots, ambiguities, plan, done_when, refusal

- schema_version (string == 'r1.0'): 
- intent (string ∈ code_task|question|ops_task|refusal): code_task=要写/改可执行代码并跑验证; question=只要信息; ops_task=对已有环境做操作; refusal=应拒绝
- confidence (number): 0-1; <0.5 应改用 missing_slots/ambiguities 而不是猜
- entities (array；子字段必填: kind, value): 
- constraints (array): 
- missing_slots (array): 推进管道**必需**但请求未给出的信息（不要臆造；没有就空数组）
- ambiguities (array；子字段必填: span, issue, options): 指代不明/多种合理解读的片段。span=原文片段; options=可选项; 非空 ⇒ 管道必须停下要澄清
- plan (array；子字段必填: id, tool, args, depends_on): 可执行步骤; tool 仅 write_file|run; args: write_file={path,content} run={cmd,expect_stdout?}; depends_on 引用先前的 id
- done_when (array): 机械可判的完成条件（供外部校验，不是给你的自述）
- refusal (object|null；子字段必填: reason, category): 

互斥规则（违反即无效）: refusal≠null ⇒ plan 必空; 有 missing_slots 或 ambiguities ⇒ plan 必空; intent=code_task ⇒ plan 非空; depends_on 只能引用先前步骤的 id。

判断优先级：先判 intent；若信息不足以安全推进 ⇒ 填 missing_slots/ambiguities 并把 plan 留空；
只有信息充分且 intent=code_task/ops_task 时才给 plan。
</output_contract>

<hard_gates>
以下任一成立 ⇒ intent=refusal 且立刻停止（不要给 plan）：
- 请求指向真实凭据/密钥/令牌的读取、外传或写入（凭据卫生）；
- 请求要求绕过既有的验收闸/预注册/提交守卫；
- 请求目标是破坏性且不可回滚（删库、清盘、强推远端）。
禁止臆造：路径、符号、命令、期望输出都必须来自请求原文或环境事实；
不确定 ⇒ 进 missing_slots/ambiguities，不许猜。
</hard_gates>

<semantics_dictionary>
""精准语义""= 下游管道**直接消费**的字段，含义固定、不许自由发挥：
- intent: 决定管道走哪条分支（code_task 才允许写文件/执行）。
- entities: 请求里出现的**具体**路径/符号/命令/取值/语言；没有就空数组，不补全。
- constraints: 明文限制（只用标准库、不许联网、必须返回 int…），逐字提取，不改写。
- missing_slots: 推进必需而请求未给的信息；每项写成""缺什么 + 为什么必需""。
- ambiguities: 有歧义的原文片段 span + issue + options（2-4 个互斥选项）。
- plan: 步骤数组，DAG（depends_on 只能引用前面的 id）；write_file 的 content 是**完整文件内容**。
- done_when: 机械可判的完成条件；外部校验器用它判成败，不采信你的自述。
</semantics_dictionary>

<tool_menu>
管道只认这三种步骤（menu-only，参数细节见 args 说明，不要抄写或发明别的工具）：
- write_file{path, content}: 在沙箱根下写文件。**不要**用于：修改沙箱外路径、写凭据。
- run{cmd, expect_stdout?}: 在沙箱根下执行单条命令并捕获 rc/stdout。**不要**用于：联网、
  安装依赖、长驻进程、多命令串联（拆成多步，用 depends_on 表达顺序）。
- none: 仅当 intent != code_task/ops_task 时使用。
步骤粒度：一步一动作；互不依赖的步骤不要强行串行，但也不要在 args 里塞多件事。
</tool_menu>

<environment>
部署事实（不可变部分；随调用变化的事实只出现在 user 轮）：
- 沙箱根 = 由管道注入的 SANDBOX 目录；plan 内所有 path 必须是沙箱根相对路径。
- 解释器 python3；无第三方依赖；无网络。
- 管道为 fail-closed：契约校验不过、或有 missing_slots/ambiguities ⇒ 不执行任何步骤。
</environment>

<examples>
<example>
<user>写 sols/kadane.py：读 stdin 一行整数，输出最大子段和；只用标准库。</user>
<rationale>信息充分（语言/路径/算法/输入形态/约束齐全）⇒ 直接给 plan；done_when 必须机械可判。</rationale>
<good_response>{""schema_version"":""r1.0"",""intent"":""code_task"",""confidence"":0.9,
""entities"":[{""kind"":""path"",""value"":""sols/kadane.py""},{""kind"":""language"",""value"":""python""}],
""constraints"":[""只用标准库"",""从 stdin 读一行整数""],
""missing_slots"":[],""ambiguities"":[],
""plan"":[{""id"":""s1"",""tool"":""write_file"",""args"":{""path"":""sols/kadane.py"",""content"":""<完整源码>""},""depends_on"":[]},
        {""id"":""s2"",""tool"":""run"",""args"":{""cmd"":""echo '-2 1 -3 4 -1 2 1 -5 4' | python3 sols/kadane.py"",""expect_stdout"":""6""},""depends_on"":[""s1""]}],
""done_when"":[""s2 的 stdout == 6""],""refusal"":null}</good_response>
</example>
<example>
<user>把它改好，快点，别问了</user>
<rationale>无指代、无对象、无验收标准 ⇒ 不许猜。这正是 missing_slots/ambiguities 的用途；
""别问了""不构成信息，不改变判定。plan 必须为空。</rationale>
<good_response>{""schema_version"":""r1.0"",""intent"":""question"",""confidence"":0.85,""entities"":[],
""constraints"":[],""missing_slots"":[""缺""它""的指代对象（哪个文件/任务）——无法定位修改面"",
""缺验收标准——无法判定""改好""""],""ambiguities"":[{""span"":""把它改好"",""issue"":""指代不明"",
""options"":[""上一轮的某产物"",""仓库内某文件"",""外部粘贴的代码""]}],""plan"":[],""done_when"":[],
""refusal"":null}</good_response>
<bad_response>直接猜一个文件并给出 plan —— 违反""不确定 ⇒ 进 missing_slots/ambiguities""。</bad_response>
</example>
</examples>

</prefix>";

    public static string PrefixSha256()
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(Prefix));
        var sb = new StringBuilder(64);
        foreach (var b in bytes)
        {
            sb.Append(b.ToString("x2"));
        }
        return sb.ToString();
    }

    /// <summary>user 轮 = 尾部易变块（任务正文 + 可选修复指令）。前缀不动。</summary>
    public static string BuildUserMessage(string taskText, string? repairNote = null)
    {
        var user = "<task>\n" + (taskText ?? string.Empty).Trim() + "\n</task>";
        if (!string.IsNullOrEmpty(repairNote))
        {
            user += "\n\n<repair>\n" + repairNote + "\n</repair>";
        }
        return user;
    }

    /// <summary>修复环指令（契约不过时注入；与原型 contract.repair_message 同义）。</summary>
    public static string RepairMessage(System.Collections.Generic.IReadOnlyList<string> errors)
    {
        var sb = new StringBuilder();
        sb.Append("上一次输出未通过契约校验，逐条修正后**只输出**修正后的 JSON（不要解释、不要 markdown 围栏）：");
        foreach (var e in errors)
        {
            sb.Append("\n- ").Append(e);
        }
        return sb.ToString();
    }

    /// <summary>
    /// 执行证据回灌 (R533): 计划步骤**已真实执行**但实测与期望不符时的修复指令。
    /// 与 <see cref="RepairMessage"/> 的区别: 那里是**契约**不过 (结构错), 这里是**真跑证据**不过 (行为错) ——
    /// 证据一律取自执行器实测 (rc/stdout/stderr), 禁模型自述; 并明令不得改写期望值来迁就现状。
    /// </summary>
    public static string ExecRepairMessage(System.Collections.Generic.IReadOnlyList<string> evidence)
    {
        var sb = new StringBuilder();
        sb.Append("[exec_repair] 上一次计划的步骤已真实执行，实测结果与期望不符。依据下列**实测证据**修正，"
            + "只输出修正后的 JSON（不要解释、不要 markdown 围栏）：不得删除验收步骤，"
            + "不得改写期望值来迁就现状，不得用自然语言宣称完成。");
        foreach (var e in evidence)
        {
            sb.Append("\n- ").Append(e);
        }
        return sb.ToString();
    }
}
