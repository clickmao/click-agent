using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.llmservice;

namespace agent.llamalocal;


/// <summary>v0.20.1 P4-a (R344): 嵌入后端模式 — opt-in, 默认 local (用户铁律: 默认行为不变)。
/// env AGENTFRAMEWORK_BGE_MODE: "remote" → 本机 llm-service (manager/worker, 免进程内加载 bge);
/// 其他/未设 → local (进程内 BgeEmbedder, 原路径)。</summary>
public enum EmbedderModeKind { Local, Remote }
