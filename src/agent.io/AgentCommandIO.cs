using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace agent.io
{
    /// <summary>
    /// 统一命令写出工具 (v0.11.0 用户定案): 基于 <see cref="AgentRequestWriterBase"/> 的
    /// agent → 前端一致命令接口 — 所有面向前端的命令 (余额不足/思考切页/输出追加/模型切换/Skill 进度)
    /// 统一经本类一行写出, 不再各自拼协议。
    ///
    /// 用法 (以余额不足为例):
    /// <code>
    /// var commands = new AgentCommandWriter(new AgentRequestWriter(stdout));
    /// commands.Send(AgentCommandNames.BalanceInsufficient,
    ///     ("model", altModel), ("from", primaryModel), ("remaining", "$1.24"));
    /// // 线上: @cmd balance_insufficient model=altModel from=primaryModel remaining=%241.24
    /// </code>
    /// 底层传输由构造注入的 writer 决定 (Console.IO / 共享内存 / socket 三实现任一)。
    /// 线程安全: 内部 lock — 多通道并发推送 (LogRouter 主链 + TokenUsage 异步同步) 不交叉。
    /// </summary>
    public sealed class AgentCommandWriter
    {
        private readonly AgentRequestWriterBase _writer;
        private readonly object _lock = new object();

        public AgentCommandWriter(AgentRequestWriterBase writer)
        {
            _writer = writer ?? throw new ArgumentNullException(nameof(writer));
        }

        /// <summary>发送一条命令 (参数对按传入序写出; value/value2 可空 — 空值不出现在线上)。</summary>
        public void Send(string name, params (string Key, string? Value)[] parameters)
        {
            if (string.IsNullOrEmpty(name))
                return;
            var dict = new Dictionary<string, string>();
            if (parameters != null)
            {
                foreach (var (key, value) in parameters)
                {
                    if (!string.IsNullOrEmpty(key) && value != null)
                        dict[key] = value;
                }
            }
            Send(new AgentCommand(name, dict));
        }

        /// <summary>发送一条已构造命令。</summary>
        public void Send(AgentCommand command)
        {
            if (command == null)
                return;
            lock (_lock)
            {
                _writer.WriteLineCorePublic(command.Encode());
            }
        }
    }
}
