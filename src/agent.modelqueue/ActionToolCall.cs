using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>
/// R456 动作环 (Action Loop) —— 链机制修复: 声明面 / 解析面 / 执行面 / 回灌面。
/// 背景 (R455 源码级诊断, docs/reports/agent-chain-diagnosis-r455.md):
///   远端请求**无 tools 字段**、全仓**无人解析 tool_calls** ⇒ 模型只能以纯文本「承诺/澄清」,
///   可执行任务在链上无出口 ⇒ 用户轮数↑ 而产物 0 (R455 套件实测 0/4 产物, 计划 P1)。
/// 设计约束 (承重):
///   C1 机制非补丁: 不出现任何「用户话术关键词 → 动作」的分支; 出口 = 协议字段 (tools/tool_calls)。
///   C2 缓存前缀单调: 每步只在**尾部**追加 (assistant(tool_calls) → tool(...)), 前缀 system/context/history/user 不变。
///   C3 AOT: 零反射 —— 手写 Utf8JsonWriter 序列化; 解析复用既有 source-gen DTO。
///   C4 端口化: 执行面 = <see cref="IActionPort"/> (可替换); 本文件不含任何文件/进程 IO。
/// </summary>
public sealed class ActionToolCall
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    /// <summary>function.arguments 原文 (JSON 字符串体; 非法 JSON 也原样保留, 由执行面判定)。</summary>
    public string ArgumentsJson { get; set; } = "{}";
}
