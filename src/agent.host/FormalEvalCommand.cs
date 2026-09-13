using System;
using System.IO;
using System.Text.Json;

namespace agent.host;

/// <summary>
/// v0.23.0 exp12 · S3/S4（用户钦定：决策合规率必须可证伪）：`--formal-eval &lt;cases.jsonl&gt;` ——
/// 把判定题集**逐条喂给真实装配的判定层**（契约解析 FormalAssertionContract → 四态处置 PlanNodeFormalGate
/// → 共享源形式化内核 clickrover.formal.FormalKernel），每行输出一条判定 JSON。
///
/// 铁律：
///  1) **零 LLM / 零 daemon / 零 shell / 零外部进程 / 不写任何状态** —— 判定全在本地整数运算完成；
///  2) 与 `click-rover check --json`（纯内核层）对照 ⇒ 契约层引入的差异**可被独立观察**，不允许自证；
///  3) 题集任何一行不可解析即非零退出（不静默跳过 —— 静默跳过会让 DCR 分母失真）。
/// </summary>
public static class FormalEvalCommand
{
    /// <summary>逐条判定并输出 JSON 行。返回 0 = 全部解析成功；2 = 题集不可读/格式错。</summary>
    public static int Run(string casesPath, TextWriter outp, TextWriter errp)
    {
        string[] lines;
        try { lines = File.ReadAllLines(casesPath); }
        catch (Exception ex)
        {
            errp.WriteLine($"formal_eval: 题集不可读 {casesPath}: {ex.Message}");
            return 2;
        }

        var n = 0;
        foreach (var raw in lines)
        {
            if (string.IsNullOrWhiteSpace(raw)) continue;
            n++;

            string id;
            string? contract;
            try
            {
                using var doc = JsonDocument.Parse(raw);
                if (!doc.RootElement.TryGetProperty("id", out var idEl) || idEl.ValueKind != JsonValueKind.String)
                {
                    errp.WriteLine($"formal_eval: 第 {n} 行缺 id 字段（题集格式错）");
                    return 2;
                }
                id = idEl.GetString() ?? "";
                contract = doc.RootElement.TryGetProperty("contract", out var cEl)
                           && cEl.ValueKind == JsonValueKind.String
                    ? cEl.GetString()
                    : null;
            }
            catch (Exception ex)
            {
                errp.WriteLine($"formal_eval: 第 {n} 行 JSON 不可解析: {ex.Message}");
                return 2;
            }

            var d = agent.intent.PlanNodeFormalGate.Evaluate(contract);
            outp.WriteLine(
                "{\"id\":" + JsonStr(id) +
                ",\"disposition\":" + JsonStr(d.Disposition.ToString()) +
                ",\"verdict\":" + JsonStr(d.VerdictText) +
                ",\"reason\":" + JsonStr(d.ReasonCode) +
                ",\"allowed\":" + (d.Allowed ? "true" : "false") +
                ",\"ms\":" + d.Ms.ToString("R", System.Globalization.CultureInfo.InvariantCulture) +
                ",\"counterexample\":" + (d.Counterexample is null ? "null" : JsonStr(d.Counterexample)) +
                ",\"would_call_llm\":" + (d.WouldCallLlm ? "true" : "false") + "}");
        }

        errp.WriteLine($"formal_eval: cases={n} file={casesPath} gate_enabled={agent.intent.PlanNodeFormalGate.IsEnabled()}");
        return 0;
    }

    /// <summary>最小 JSON 字符串转义（零反射 / AOT 安全，不依赖 STJ 元数据）。</summary>
    public static string JsonStr(string s)
    {
        var sb = new System.Text.StringBuilder(s.Length + 2);
        sb.Append('"');
        foreach (var ch in s)
        {
            switch (ch)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (ch < 0x20) sb.Append("\\u").Append(((int)ch).ToString("x4"));
                    else sb.Append(ch);
                    break;
            }
        }
        sb.Append('"');
        return sb.ToString();
    }
}
