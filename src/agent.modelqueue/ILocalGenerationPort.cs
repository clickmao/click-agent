using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>
/// R413: 本地生成执行面端口 (可替换 — 产品只依赖本接口, 不依赖任何具体推理后端程序集)。
///
/// 定位 (用户 2026-09-14 口径): 本地生成是「重新整理所有能力 → 精炼合理化链管道 → 提高 KPI」
/// 计划中的一个节点, **与 R351 无关** — R351 移除的是旧的「本地 LLM 使用」路径 (全走远端 API),
/// 不构成对新增 r1 本地生成的禁令。
///
/// 契约纪律 (R408): 实现必须是「进程 + HTTP」形态, 零 P/Invoke; <see cref="IsAvailable"/> 是
/// **真实探测** (模型文件存在 ∧ 二进制可解析), 探测不确定一律 false — 「没测到」≠「通过」。
/// </summary>
public interface ILocalGenerationPort
{
    /// <summary>真实就绪探测 (不得猜; 探测失败 → false)。</summary>
    bool IsAvailable { get; }

    /// <summary>执行面标识 (记账/可观测用, 如 "llama.cpp")。</summary>
    string BackendId { get; }

    /// <summary>生成一轮。失败必须回 <c>Success=false</c> + <c>Error</c> (不得抛穿调用方)。</summary>
    Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default);

    /// <summary>
    /// R465: 预热 —— 把长驻推理服务的**权重装载**提前到宿主启动期, 使它不再落在用户可见的门控轮路径上。
    /// 默认空实现 (测试桩/无本地后端无需实现)。纪律: 预热失败**不得抛穿** (只记账, 供遥测读取)。
    /// </summary>
    Task WarmupAsync(CancellationToken ct = default) => Task.CompletedTask;

    /// <summary>R465: 预热是否成功过 (未预热/失败 ⇒ false); 仅观测用。</summary>
    bool WarmupOk => false;
}
