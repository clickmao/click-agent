using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace agent.io
{
    /// <summary>
    /// 统一命令读取工具: 基于 <see cref="AgentReportReaderBase"/> 的前端侧对称读取。
    /// 读到 @cmd 行 → 解析为 <see cref="AgentCommand"/>; 其他行事件原样透传 (前端自行处理文本/流)。
    /// </summary>
    public sealed class AgentCommandReader
    {
        private readonly AgentReportReaderBase _reader;

        public AgentCommandReader(AgentReportReaderBase reader)
        {
            _reader = reader ?? throw new ArgumentNullException(nameof(reader));
        }

        /// <summary>
        /// 读下一条命令 (跳过中间的非命令事件直到 EOF)。
        /// 返回 null = 流结束。跳过的事件经 <paramref name="skipped"/> 回调透传 (可 null)。
        /// </summary>
        public AgentCommand ReadCommand(Action<ReportEvent> skipped = null)
        {
            while (true)
            {
                var ev = _reader.ReadEvent();
                if (ev == null || ev.Kind == ReportEventKind.Eof)
                    return null;
                if (ev.Kind == ReportEventKind.Command)
                {
                    var cmd = AgentCommand.Decode(ev.Payload);
                    if (cmd != null)
                        return cmd;
                }
                skipped?.Invoke(ev);
            }
        }

        /// <summary>读全部命令到流结束。</summary>
        public List<AgentCommand> ReadAllCommands()
        {
            var commands = new List<AgentCommand>();
            while (true)
            {
                var cmd = ReadCommand();
                if (cmd is null)
                    break;
                commands.Add(cmd);
            }
            return commands;
        }
    }
}
