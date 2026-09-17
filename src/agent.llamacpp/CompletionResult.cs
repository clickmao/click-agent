using System.Net.Http.Json;
using System.Text.Json;
using agent.modelqueue;   // R430: LocalInputFingerprint (共享层; 不引入反向依赖)

namespace agent.llamacpp;


/// <summary>生成结果 (含原始 token id —— 数值对账的锚点)。</summary>
public sealed record CompletionResult(
    string Content,
    int[] Tokens,
    int PromptTokens,
    int PredictedTokens,
    double PredictedPerSecond,
    double PromptPerSecond,
    int CachedTokens,
    string RawJson,
    // R430: 判定输入指纹 (只观测, 不影响生成) — 逐轮读数不同时先机械区分「输入不同」与「引擎不确定」。
    string PromptSha16 = "",
    string RequestSha16 = "",
    string RequestFields = "");
