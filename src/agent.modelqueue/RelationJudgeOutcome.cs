using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>R426: 本地关系判官结论 (字母 ∈ {C,A,N}; 交给 CorrectionDetector 的解析面, 不另立语义)。</summary>
public sealed record RelationJudgeOutcome(string Letter, string Raw, int CompletionTokens, int PromptTokens = -1, int PromptNewTokens = -1);
