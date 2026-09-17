using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>本地生成对话轮 (协议自洽, 不依赖 agent 主程序集)。</summary>
public sealed record LocalChatTurn(string Role, string Content);
