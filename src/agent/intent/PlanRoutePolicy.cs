using System.Text.Json.Serialization;

namespace agent.intent;

/// <summary>
/// 框架自产的本地节点意图常量 (v0.22.0 exp9 D2)。
/// 注意: 这些意图**不进 IntentPromptTemplates** (不是用户意图) —— 它们只描述"本地执行器要干什么",
/// 由 LocalVerifyNodePlanner 生成节点时写入, 供路由与执行体分派使用。
/// </summary>
public static class PlanNodeIntents
{
    /// <summary>本地验证 (跑产物自测/机器判据)</summary>
    public const string VerifyLocal = "verify_local";

    /// <summary>本地文本处理 (证据汇总/格式化/统计 — 纯本地, 零 token)</summary>
    public const string TextProcessing = "text_processing";

    /// <summary>本地形式化验证 (R391 C7): clickproof 断言 → 本地内核确定性裁决, 零 token</summary>
    public const string VerifyFormal = "verify_formal";
}

/// <summary>
/// 本地执行器登记条目 (v0.22.0 exp9 D2)。
/// 判定"这步能不能本地跑"只认这张表 —— 表外/未接线的执行器一律不许判 Local。
/// </summary>
/// <param name="Id">登记 Id (节点 LocalExecutorId 取值)</param>
/// <param name="DisplayName">给人看的名字 (前端显示)</param>
/// <param name="Intents">可承接的意图</param>
/// <param name="Hint">判定依据短句 (写进 PlanNode.LocalHint, 前端可见)</param>
/// <param name="Wired">是否已接线真实实现。false = 已声明未接线 → **永不路由** (负向控制, 拒"为编排而编排")</param>
/// <param name="PostActionMarkers">文本中命中即表示"远程生成后本地可立刻做这一段"的词 (Hybrid 判定用)</param>
public sealed record LocalExecutorDescriptor(
    string Id,
    string DisplayName,
    IReadOnlyList<string> Intents,
    string Hint,
    bool Wired,
    IReadOnlyList<string> PostActionMarkers);

/// <summary>
/// 本地执行能力登记表 (v0.22.0 exp9 D2) —— 单一事实源。
///
/// 硬约束: 这张表与真实实现一一对应。
///   · Wired=true  的实现体见 PlanRunner.cs (PythonSelfTestExecutor / TextProcessExecutor / FormalVerifyExecutor), 有单测覆盖;
///   · Wired=false 的条目只作"已识别但未接线"的显式登记, 路由函数永不返回它们。
/// 这样"本地可跑"就不是口号: 表里没有 = 路由只能判 Remote = 不会假装本地能跑。
/// </summary>
public static class LocalExecutorRegistry
{
    /// <summary>跑产物自带的无头自测入口 (python3 &lt;artifact&gt; --selftest, 退出码即判据)</summary>
    public const string PythonSelfTest = "python.selftest";

    /// <summary>本地文本处理/证据汇总 (统计/格式化/摘要, 纯 CPU)</summary>
    public const string TextProcess = "text.process";

    /// <summary>本地形式化验证 (R391 C7): clickproof 断言 → 本地内核确定性裁决 (零 token / 零 shell)</summary>
    public const string FormalVerify = "formal.verify";

    /// <summary>真机按键回放 + 截图反核 (跨平台按键通道未接线 → 见 D3b)</summary>
    public const string RealMachineReplay = "realmachine.replay";

    /// <summary>本地命令路由 (/ls、/git 等 LocalCommandRouter 能力, 未接进计划节点 → D3b)</summary>
    public const string LocalCommand = "command.local";

    public static readonly IReadOnlyList<LocalExecutorDescriptor> All =
    [
        new(PythonSelfTest, "本地跑产物自测 (--selftest)",
            [PlanNodeIntents.VerifyLocal, IntentRecognizer.Intents.TestGeneration],
            "产物自带 --selftest 无头入口 ⇒ 本地子进程跑一遍, 退出码即判据 (零 token)",
            Wired: true,
            PostActionMarkers: ["自测", "selftest", "--selftest", "校验", "验证", "编译", "跑一遍", "py_compile"]),

        new(TextProcess, "本地文本处理 / 证据汇总",
            [PlanNodeIntents.TextProcessing, PlanNodeIntents.VerifyLocal],
            "纯文本统计/格式化无需模型 ⇒ 本地 CPU 直接算 (零 token)",
            Wired: true,
            PostActionMarkers: ["统计", "格式化", "汇总", "转换", "计数", "摘要", "整理", "合并"]),

        new(FormalVerify, "本地形式化验证 (clickproof 断言)",
            [PlanNodeIntents.VerifyFormal],
            "节点携带 clickproof 断言 ⇒ 本地内核确定性裁决 (Proved/Refuted/Vacuous/Unknown 四态), 零 token",
            Wired: true,
            PostActionMarkers: []),

        new(RealMachineReplay, "真机按键回放 + 截图反核",
            [PlanNodeIntents.VerifyLocal],
            "需真机按键通道 (tmux/pty 抽象) 与截图渲染 — 未接线, 本轮不参与路由",
            Wired: false,
            PostActionMarkers: []),

        new(LocalCommand, "本地命令 (ls/git/文件操作)",
            [IntentRecognizer.Intents.FileOperation, IntentRecognizer.Intents.GitOperation],
            "LocalCommandRouter 已存在但未接进计划节点 — 未接线, 本轮不参与路由",
            Wired: false,
            PostActionMarkers: []),
    ];

    private static readonly Dictionary<string, LocalExecutorDescriptor> ById =
        All.ToDictionary(d => d.Id, StringComparer.Ordinal);

    /// <summary>意图 → 已接线执行器 (未接线/未登记 → null ⇒ 调用方必须判 Remote)</summary>
    public static LocalExecutorDescriptor? ForIntent(string intent)
    {
        foreach (var d in All)
        {
            if (!d.Wired)
                continue;
            foreach (var i in d.Intents)
            {
                if (string.Equals(i, intent, StringComparison.Ordinal))
                    return d;
            }
        }
        return null;
    }

    public static LocalExecutorDescriptor? ByIdOrNull(string? id) =>
        id is not null && ById.TryGetValue(id, out var d) ? d : null;

    /// <summary>
    /// 文本里的"远程生成后本地可立刻做"的动作 → 已接线执行器 (Hybrid 判定用)。
    /// 只返回 Wired=true 项 —— 未接线的动作词不会让节点变成 Hybrid (负向控制)。
    /// </summary>
    public static LocalExecutorDescriptor? ForPostAction(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return null;
        foreach (var d in All)
        {
            if (!d.Wired)
                continue;
            foreach (var m in d.PostActionMarkers)
            {
                if (text.Contains(m, StringComparison.OrdinalIgnoreCase))
                    return d;
            }
        }
        return null;
    }

    /// <summary>该执行器是否已接线 (路由/执行体共用同一判据 — 防"登记了但没人实现")</summary>
    public static bool IsWired(string? id) => ByIdOrNull(id)?.Wired == true;
}

/// <summary>路由判定结果 (纯函数输出; 可单测)</summary>
public sealed record RouteDecision(NodeExecutionLocation Location, string? ExecutorId, string Hint);

/// <summary>
/// 计划路由策略 (v0.22.0 exp9 D2) —— **确定性规则**, 不是 LLM 拍脑袋。
///
/// 用户口径: "查看哪个步骤可以直接本地跑, 哪个任务需要远程生成"。
/// 规则 (顺序即优先级, 全部可单测):
///   R0 参数未齐 (待澄清)         → Remote (先问清再定位置; 位置待定不占用本地资源)
///   R1 登记表无已接线执行器      → Remote (**负向控制**: 未命中不许乐观判 Local)
///   R2 生成类意图                → Remote (本地无生成能力; 产后验证由 LocalVerifyNodePlanner 追加 Local 节点)
///   R2b 生成类意图 + 文本含本地处理动作 → Hybrid (远程生成 + 本地立即跑; 不新增 LLM 调用)
///   R3 命中已接线本地执行器      → Local (零 token)
///   R4 兜底                      → Remote
/// </summary>
public static class PlanRoutePolicy
{
    /// <summary>生成类意图 (必须产出新内容) — 本地无法完成</summary>
    private static readonly HashSet<string> GenerationIntents = new(StringComparer.Ordinal)
    {
        IntentRecognizer.Intents.CodeGeneration,
        IntentRecognizer.Intents.CodeModification,
        IntentRecognizer.Intents.CodeReview,
        IntentRecognizer.Intents.TestGeneration,
        IntentRecognizer.Intents.Search,
        IntentRecognizer.Intents.MemorySearch,
        IntentRecognizer.Intents.General,
    };

    /// <summary>文本里是否含"远程生成后本地可立刻做"的动作 (判定 = 登记表已接线动作词命中)</summary>
    public static bool ContainsLocalPostAction(string? text) =>
        LocalExecutorRegistry.ForPostAction(text) is not null;

    /// <summary>
    /// R391(C7): 节点文本是否携带**机器可读**的形式化断言 —— 围栏提取或裸契约行。
    /// 与 FormalVerifyExecutor 的解析口径同源 (同一提取器), 避免"路由判本地、执行器却读不到"这类断链。
    /// </summary>
    public static bool CarriesFormalClaim(string? text) =>
        agent.registry.ClickProofFence.ExtractTrimmed(text) is not null || FormalVerifyExecutor.LooksLikeContract(text);

    /// <summary>单节点判定 (纯函数: 输入节点事实, 输出位置 + 执行器 + 依据)</summary>
    /// <param name="absorbLocalTextOp">
    /// true (缺省): 生成节点吸收本地文本动作 → Hybrid (处理**生成内容**)。
    /// false: 用户要处理的是**自己的原文**, 该动作已单列为无依赖本地节点 (D4) → 本节点不吸收, 走 Remote。
    /// </param>
    public static RouteDecision Decide(PlanNode node, bool absorbLocalTextOp = true)
    {
        // R0: 待澄清 → 位置待定 (保守: Remote, 不占用本地执行资源)
        if (!node.IsExecutable)
            return new RouteDecision(NodeExecutionLocation.Remote, null,
                "参数待澄清 ⇒ 位置待定 (澄清后由路由重判)");

        var isGeneration = GenerationIntents.Contains(node.Intent);

        // R391(C7): 节点**自身携带机器可读的形式化断言** (clickproof 围栏 / 裸 premise|goal|no_formal 契约行)
        //   ⇒ 这是一个可判定的本地验证节点: 本地内核确定性裁决, 零 token, 未证明不放行。
        //   判据是围栏本身而非自然语言关键词 ⇒ 不会误触发, 也不依赖模型"愿不愿意"说关键词。
        if (CarriesFormalClaim(node.Text))
            return new RouteDecision(NodeExecutionLocation.Local, LocalExecutorRegistry.FormalVerify,
                "节点携带 clickproof 形式化断言 ⇒ 本地内核确定性裁决 (零 token; 未证明绝不放行)");

        // R2c (D4b): **整段子请求**就是"在用户自己的原文上做文本处理" (无依赖 + 动作词∧原文对象词 + 非产物型 + 短句)
        //   ⇒ Local 零 token 执行, 且该子请求必须从**模型出站文本扣减** (RequestAblation), 否则模型会再算一遍
        //     = 重复计算 (真机实测: 模型报 118 / 框架确定性统计 117) ⇒ "本地先行"的零 token 收益被吃掉。
        //   反例 (含代码/产物标记、过长、有依赖) 一律落回 R2b/R2 —— 判据是纯函数, 可单测、可反向断言。
        if (LocalVerifyNodePlanner.IsPureSourceTextOp(node.Text, node.DependsOn.Count))
            return new RouteDecision(NodeExecutionLocation.Local, LocalExecutorRegistry.TextProcess,
                "整段子请求=用户原文上的文本处理 (框架确定性可算, 非生成) ⇒ 本地零 token; 已从模型出站文本扣减 (防重复计算)");

        if (isGeneration)
        {
            // R2b: 生成 + 文本含"本地可立刻做"的动作
            var post = LocalExecutorRegistry.ForPostAction(node.Text);
            if (post is not null)
            {
                // R2b-1: 本地半段是"跑产物自测" → **拆成两个节点**(本节点=远程生成, 自测由 LocalVerifyNodePlanner
                //        追加为独立 Local 节点)。理由: 前端要看清"哪步远程/哪步本地", 单节点 Hybrid 会把
                //        零 token 的本地工作藏起来; 且自测有独立执行器与独立判据。
                if (post.Id == LocalExecutorRegistry.PythonSelfTest)
                    return new RouteDecision(NodeExecutionLocation.Remote, null,
                        $"「{node.Intent}」需远程生成; 产物自测单列本地节点 (python.selftest, 零 token)");

                // R2b-2: 本地半段是文本处理类 → Hybrid (同一节点: 远程生成后本地立即处理, 不新增 LLM 调用)
                // D4 例外: 若用户要处理的是**自己的原文** (该动作已单列为无依赖本地节点), 本节点不许再吸收 —
                //          同一动作被算两次, 且 Hybrid 第二段输入是**生成内容**, 与用户目标 (原文) 不同。
                if (post.Id == LocalExecutorRegistry.TextProcess && !absorbLocalTextOp)
                    return new RouteDecision(NodeExecutionLocation.Remote, null,
                        "本地文本动作对象=用户原文 (已单列为无依赖本地节点) ⇒ 本节点只做远程生成");
                return new RouteDecision(NodeExecutionLocation.Hybrid, post.Id,
                    $"「{node.Intent}」需远程生成, 但含本地可做动作 ⇒ 生成后立即本地 {post.Id} (零 token)");
            }

            // R2: 生成类 → Remote (本地无生成能力)
            return new RouteDecision(NodeExecutionLocation.Remote, null,
                $"「{node.Intent}」需生成新内容 ⇒ 必须远程; 产后验证另增本地节点");
        }

        // R1 + R3: 登记表命中已接线执行器 → Local; 否则负向控制落 Remote
        var local = LocalExecutorRegistry.ForIntent(node.Intent);
        if (local is null)
            return new RouteDecision(NodeExecutionLocation.Remote, null,
                $"本地登记表无「{node.Intent}」的已接线执行器 ⇒ 走远程 (负向控制: 不许乐观判 Local)");

        return new RouteDecision(NodeExecutionLocation.Local, local.Id,
            $"本地执行器 {local.Id} 可承接「{node.Intent}」 ⇒ 零 token 本地执行");
    }

    /// <summary>把判定写回整张计划的节点 (Builder/调用方在 Build 后调用一次)</summary>
    public static void Apply(TaskPlan plan, bool absorbLocalTextOp = true)
    {
        foreach (var n in plan.Nodes)
            ApplyNode(n, absorbLocalTextOp);
    }

    /// <summary>把判定写回单个节点</summary>
    public static RouteDecision ApplyNode(PlanNode node, bool absorbLocalTextOp = true)
    {
        var d = Decide(node, absorbLocalTextOp);
        node.Location = d.Location;
        node.LocalExecutorId = d.ExecutorId;
        node.LocalHint = d.Hint;

        // D4b: 出站扣减标记与位置判定**同一条规则** (IsPureSourceTextOp) —— 不允许两处口径各判一次。
        // 非纯原文级节点一律清零 (幂等: 路由可重复调用)。
        node.IsLocalizedRequest = d.Location == NodeExecutionLocation.Local
            && d.ExecutorId == LocalExecutorRegistry.TextProcess
            && LocalVerifyNodePlanner.IsPureSourceTextOp(node.Text, node.DependsOn.Count);
        return d;
    }
}

/// <summary>
/// 本地验证节点规划器 (v0.22.0 exp9 D2) —— 为"远程生成产物"的节点追加**确定性**本地节点。
///
/// 为什么不是"为编排而编排": 这些节点对应的正是过去由人工/探针在环外做的事
/// (落盘后跑 --selftest、汇总证据), 现在变成计划内、零 token、可观测的一等节点。
/// 硬约束: 只追加 LocalExecutorRegistry 中 **Wired=true** 的执行器节点 —— 未接线的能力不会被写进计划。
/// </summary>
public static class LocalVerifyNodePlanner
{
    /// <summary>需要产后本地验证的生成类意图 (产物型)</summary>
    private static readonly HashSet<string> ArtifactProducingIntents = new(StringComparer.Ordinal)
    {
        IntentRecognizer.Intents.CodeGeneration,
        IntentRecognizer.Intents.CodeModification,
        IntentRecognizer.Intents.TestGeneration,
    };

    /// <summary>
    /// 代码/脚本类任务标记 (确定性, 非 LLM 判定)。
    /// 依据 = 静态前缀契约本身: 产物型任务必须落盘可执行脚本且带 `--selftest` 无头入口
    /// (`SessionBaseline.cs:53`), 因此"这步产后必然有一个可本地跑的产物"是**框架已知事实**, 不是猜测。
    /// </summary>
    private static readonly string[] CodeTaskMarkers =
    [
        "python", "py脚本", "脚本", "程序", "代码", "函数", "算法", "游戏", "game", "script",
        "贪吃蛇", "扫雷", "俄罗斯方块", "命令行", "cli",
    ];

    internal static bool LooksLikeCodeTask(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return false;
        var t = text.ToLowerInvariant();
        return CodeTaskMarkers.Any(m => t.Contains(m, StringComparison.Ordinal));
    }

    /// <summary>
    /// 为计划追加本地节点 (幂等)。
    /// 触发 = 产物型意图 **或** 文本是代码/脚本类任务; 追加内容 = **只追加有消费方的节点**: 本地跑 --selftest
    /// 取退出码 (消费方 = 计划审计/前端/验收判据)。
    /// 刻意不追加"证据文本汇总"这类无消费方节点 —— 无消费方 = 为编排而编排 (见计划 §4 约束 1/5)。
    /// </summary>
    public static IReadOnlyList<PlanNode> AppendFor(TaskPlan plan)
    {
        var added = new List<PlanNode>();
        if (!LocalExecutorRegistry.IsWired(LocalExecutorRegistry.PythonSelfTest))
            return added;

        // 快照遍历: 追加过程中会改 Nodes
        foreach (var gen in plan.Nodes.ToArray())
        {
            // 只给"需要模型产内容"的节点追加验证节点:
            //   · 框架自产的本地节点 (verify_local/text_processing) 不再被追加 (防"验证的验证"递归)
            //   · 已判 Local/Hybrid 的节点其本地半段已由其自身承担
            if (gen.Intent is PlanNodeIntents.VerifyLocal or PlanNodeIntents.TextProcessing)
                continue;
            if (gen.Location != NodeExecutionLocation.Remote)
                continue;
            if (!ArtifactProducingIntents.Contains(gen.Intent) && !LooksLikeCodeTask(gen.Text))
                continue;

            // 幂等: 已有依赖它的同执行器验证节点 → 跳过
            if (HasNode(plan, gen.Id, LocalExecutorRegistry.PythonSelfTest))
                continue;

            var verify = new PlanNode
            {
                Text = $"本地跑「{gen.Text}」产物的无头自测 (--selftest) 取退出码",
                Intent = PlanNodeIntents.VerifyLocal,
                DependsOn = [gen.Id],
            };
            plan.Nodes.Add(verify);
            added.Add(verify);
        }

        if (added.Count > 0)
            TaskPlanBuilder.ComputeLevelsAndParallelGroups(plan);

        return added;
    }

    /// <summary>
    /// 用户是否要求对**自己的原文/需求**做本地可算的文本处理 (v0.22.0 exp9 D4)。
    /// 判定 = 动作词 ∧ 对象词 双命中 (确定性, 非 LLM 判定)。
    /// 为什么单列: 这类任务的输入 (用户原文) 在模型还没生成前就已在手 ⇒ 属**无依赖本地节点**,
    /// 可与远程生成**真并行先行**; 而"统计生成出来的代码行数"依赖远程产物, 是另一类 (Hybrid/验证节点)。
    /// </summary>
    private static readonly string[] SourceTextOpMarkers =
        ["统计", "计数", "字数", "行数", "词频", "摘要", "格式化", "汇总", "字符数", "词数"];

    private static readonly string[] SourceTextTargetMarkers =
        ["需求", "原文", "这段话", "我写", "我说的", "描述", "提示词", "输入文本", "问题描述", "本文"];

    internal static bool AsksSourceTextOp(string? sourceText)
    {
        if (string.IsNullOrWhiteSpace(sourceText))
            return false;
        return SourceTextOpMarkers.Any(m => sourceText.Contains(m, StringComparison.OrdinalIgnoreCase))
            && SourceTextTargetMarkers.Any(m => sourceText.Contains(m, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>纯原文级文本处理子请求的最大字数 (超过则说明该片段还裹着别的诉求 ⇒ 不许整体扣减)</summary>
    internal const int PureSourceOpMaxChars = 60;

    /// <summary>
    /// 该节点是否为「纯原文级文本处理子请求」(v0.22.0 exp9 D4b, 纯函数):
    ///   ① 无依赖 (输入=本轮原文, 不需要任何前序产物)
    ///   ② 动作词 ∧ 原文对象词双命中 (AsksSourceTextOp —— 复用 D4 同一判据, 不另立口径)
    ///   ③ 非产物型 (无 python/脚本/游戏… 标记 ⇒ 不是"写一个统计字数的程序")
    ///   ④ 短句 (≤ PureSourceOpMaxChars ⇒ 整段就是这一步, 不是"写贪吃蛇并统计字数"这种混合诉求)
    /// 四条全中 ⇒ 框架可**独立完成**这一步: 走 Local 且从模型出站文本扣减。
    /// </summary>
    internal static bool IsPureSourceTextOp(string? text, int dependsOnCount)
    {
        if (dependsOnCount != 0 || !AsksSourceTextOp(text) || LooksLikeCodeTask(text))
            return false;
        return (text ?? string.Empty).Trim().Length <= PureSourceOpMaxChars;
    }

    /// <summary>
    /// 追加"无依赖本地文本处理"节点 (D4 本地先行的真实载体): 输入 = 本轮用户原文。
    /// 消费方 = 计划审计 / 前端事件 (D5) / KPI (D6) 与用户要的那个统计结果本身 —— 不是为编排而编排。
    /// 幂等: 已有同执行器的无依赖节点则不重复追加。
    /// </summary>
    public static IReadOnlyList<PlanNode> AppendSourceTextProcessor(TaskPlan plan, string sourceText)
    {
        var added = new List<PlanNode>();
        if (!LocalExecutorRegistry.IsWired(LocalExecutorRegistry.TextProcess))
            return added;
        if (!AsksSourceTextOp(sourceText))
            return added;
        if (plan.Nodes.Any(n => n.LocalExecutorId == LocalExecutorRegistry.TextProcess && n.DependsOn.Count == 0))
            return added;

        var preview = sourceText.Length <= 40 ? sourceText : sourceText[..40] + "…";
        var node = new PlanNode
        {
            Text = $"本地处理用户原文 (输入=本轮原文, 统计/汇总): {preview}",
            Intent = PlanNodeIntents.TextProcessing,
            DependsOn = [],
        };
        plan.Nodes.Add(node);
        added.Add(node);
        return added;
    }

    private static bool HasNode(TaskPlan plan, string dependsOnId, string executorId) =>
        plan.Nodes.Any(n => n.LocalExecutorId == executorId && n.DependsOn.Contains(dependsOnId));
}

/// <summary>
/// 计划构建门面 (v0.22.0 exp9 D1+D2 对外单入口):
/// Build → 路由判定 → 追加本地验证节点 → (可选) 序列化给前端。
/// 调用方只需记住这一个入口, 防"忘了调路由"的断链再现。
/// </summary>
public static class RoutedPlanBuilder
{
    /// <summary>构建带执行位置的计划 (幂等: 重复调用不会重复追加本地节点)</summary>
    public static TaskPlan Build(string sourceText, IReadOnlyList<IntentDecomposer.SubTask> subTasks)
    {
        var plan = TaskPlanBuilder.Build(sourceText, subTasks);

        // D4: 用户要求处理"**自己的原文**"时, 该文本动作单列为无依赖本地节点 (输入在手 ⇒ 可先于远程生成跑),
        //     且生成节点不再吸收它 (Hybrid 第二段输入是生成内容, 目标不同 ⇒ 不许混算)。
        var separateLocalText = LocalVerifyNodePlanner.AsksSourceTextOp(sourceText);
        var absorbLocalTextOp = !separateLocalText;

        PlanRoutePolicy.Apply(plan, absorbLocalTextOp);
        var before = plan.Nodes.Count;
        LocalVerifyNodePlanner.AppendFor(plan);
        if (separateLocalText)
            LocalVerifyNodePlanner.AppendSourceTextProcessor(plan, sourceText);
        if (plan.Nodes.Count != before)
            TaskPlanBuilder.ComputeLevelsAndParallelGroups(plan);
        PlanRoutePolicy.Apply(plan, absorbLocalTextOp);
        return plan;
    }
}
