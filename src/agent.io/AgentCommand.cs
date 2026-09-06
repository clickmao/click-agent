using System;
using System.Collections.Generic;
using System.Text;

namespace agent.io
{
    /// <summary>
    /// 统一前端命令 (v0.11.0 用户定案):
    /// agent → 前端方向的一致命令接口 — 【余额不足】/【思考切页】/【思考结束】/【输出追加】/【模型切换】等
    /// 全部收敛为本信封, 经 <see cref="AgentCommandWriter"/> 写出 (底层传输 Console.IO / 共享内存 / socket 任意)。
    ///
    /// 线格式 (行协议, 与 @chatbox:{json} / @stream 并存):
    ///   @cmd &lt;name&gt; key=value key2=value2
    /// 值经百分号编码 (空格/=/%/换行/回车), 手写编解码 — 零依赖 + AOT 安全 (agent.io 无 JSON 库约束)。
    /// 已知命令名常量见 <see cref="AgentCommandNames"/>; 未知命令名同样合法 (前向兼容, 前端自行忽略或处理)。
    /// </summary>
    public sealed class AgentCommand
    {
        /// <summary>命令名 (如 balance_insufficient / thinking_page_switch)。</summary>
        public string Name { get; }

        /// <summary>参数 (有序 key → value; 值已解码为原文)。</summary>
        public IReadOnlyDictionary<string, string> Params { get; }

        public AgentCommand(string name, IReadOnlyDictionary<string, string>? parameters = null)
        {
            Name = name ?? throw new ArgumentNullException(nameof(name));
            Params = parameters ?? new Dictionary<string, string>();
        }

        /// <summary>便捷取参 (缺失返回 null)。</summary>
        public string? Get(string key) =>
            Params.TryGetValue(key, out var v) ? v : null;

        /// <summary>编码为一行 (含 @cmd 前缀, 不含行尾; 参数按插入序)。</summary>
        public string Encode()
        {
            var sb = new StringBuilder(AgentReportReaderBase.CommandPrefix.Length + Name.Length + 16);
            sb.Append(AgentReportReaderBase.CommandPrefix).Append(Name);
            foreach (var kv in Params)
            {
                sb.Append(' ').Append(kv.Key).Append('=').Append(EscapeValue(kv.Value));
            }
            return sb.ToString();
        }

        /// <summary>解析一行 @cmd (成功返回命令; 格式不符返回 null — 调用方降级为文本行)。</summary>
        public static AgentCommand? Decode(string line)
        {
            if (line is null || !line.StartsWith(AgentReportReaderBase.CommandPrefix, StringComparison.Ordinal))
                return null;
            var body = line.Substring(AgentReportReaderBase.CommandPrefix.Length);
            if (body.Length == 0)
                return null;

            // 首段 = 命令名 (到第一个空格); 其余 = key=value 项
            var sp = body.IndexOf(' ');
            string name;
            string? rest;
            if (sp < 0)
            {
                name = body;
                rest = null;
            }
            else
            {
                name = body.Substring(0, sp);
                rest = body.Substring(sp + 1);
            }
            if (name.Length == 0)
                return null;

            Dictionary<string, string> parameters = new Dictionary<string, string>();
            if (!string.IsNullOrEmpty(rest))
            {
                foreach (var token in SplitTokens(rest))
                {
                    var eq = token.IndexOf('=');
                    if (eq <= 0)
                        continue; // 无 = 或空 key → 跳过 (容错, 不抛)
                    var key = UnescapeValue(token.Substring(0, eq));
                    var value = UnescapeValue(token.Substring(eq + 1));
                    parameters[key] = value;
                }
            }
            return new AgentCommand(name, parameters);
        }

        /// <summary>按空格切分 (转义空格 %20 不切)。</summary>
        private static IEnumerable<string> SplitTokens(string s)
        {
            var parts = s.Split(' ');
            return parts;
        }

        /// <summary>值转义: % → %25, 空格 → %20, = → %3D, LF → %0A, CR → %0D。</summary>
        internal static string EscapeValue(string value)
        {
            var sb = new StringBuilder(value.Length);
            foreach (var ch in value)
            {
                switch (ch)
                {
                    case '%': sb.Append("%25"); break;
                    case ' ': sb.Append("%20"); break;
                    case '=': sb.Append("%3D"); break;
                    case '\n': sb.Append("%0A"); break;
                    case '\r': sb.Append("%0D"); break;
                    default: sb.Append(ch); break;
                }
            }
            return sb.ToString();
        }

        /// <summary>值反转义 (<see cref="EscapeValue"/> 逆; 未知 % 序列原样保留 — 容错不抛)。</summary>
        internal static string UnescapeValue(string value)
        {
            if (value.IndexOf('%') < 0)
                return value;
            var sb = new StringBuilder(value.Length);
            for (int i = 0; i < value.Length; i++)
            {
                if (value[i] == '%' && i + 2 < value.Length
                    && IsHex(value[i + 1]) && IsHex(value[i + 2]))
                {
                    sb.Append((char)(HexVal(value[i + 1]) * 16 + HexVal(value[i + 2])));
                    i += 2;
                }
                else
                {
                    sb.Append(value[i]);
                }
            }
            return sb.ToString();
        }

        private static bool IsHex(char c) =>
            (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');

        private static int HexVal(char c) =>
            c <= '9' ? c - '0' : (c & 0xDF) - 'A' + 10;
    }

    /// <summary>已知命令名 (框架内约定; 扩展命令直接传新名 — 前向兼容)。</summary>
    public static class AgentCommandNames
    {
        /// <summary>余额不足 (模型已切换): model=新模型 from=原模型 remaining=剩余额度 reason=原因</summary>
        public const string BalanceInsufficient = "balance_insufficient";

        /// <summary>思考页切换 (分片推送): seq=分片序号 session=会话</summary>
        public const string ThinkingPageSwitch = "thinking_page_switch";

        /// <summary>思考结束 (前端折叠思考区): summary_length=摘要长度 session=会话</summary>
        public const string ThinkingEnd = "thinking_end";

        /// <summary>输出追加: seq=序号 session=会话</summary>
        public const string OutputAppend = "output_append";

        /// <summary>模型切换: from=原模型 to=新模型 reason=切换原因</summary>
        public const string ModelSwitch = "model_switch";

        /// <summary>Skill 脚本进度: skill=技能id message=进度文本</summary>
        public const string SkillProgress = "skill_progress";

        /// <summary>Skill 脚本完成: skill=技能id exit=退出码 duration_ms=耗时</summary>
        public const string SkillDone = "skill_done";
    }
}
