using System.Text.Json.Serialization;

namespace agent.intent;

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
