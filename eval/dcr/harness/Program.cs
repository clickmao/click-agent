// DCR 判定题集的**真实装配层**回放: 逐条把 contract 交给仓库真实的
// PlanNodeFormalGate.Evaluate() (→ 真实 FormalAssertionContract + 真实 click-rover 内核)。
// 用法: dotnet run -- <cases.jsonl> <out_decisions.jsonl>
using System.Text;
using System.Text.Json;
using agent.intent;

if (args.Length < 2)
{
    Console.Error.WriteLine("usage: dcrval <cases.jsonl> <out.jsonl>");
    return 2;
}

var casesPath = args[0];
var outPath = args[1];
var lines = File.ReadAllLines(casesPath).Where(l => l.Trim().Length > 0).ToArray();

int n = 0;
using (var w = new StreamWriter(outPath, false, new UTF8Encoding(false)))
{
    foreach (var line in lines)
    {
        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;
        var id = root.GetProperty("id").GetString() ?? "";
        string? contract = root.TryGetProperty("contract", out var c) && c.ValueKind != JsonValueKind.Null
            ? c.GetString()
            : null;

        var d = PlanNodeFormalGate.Evaluate(contract);

        var obj = new Dictionary<string, object?>
        {
            ["id"] = id,
            ["disposition"] = d.Disposition.ToString(),
            ["verdict"] = d.VerdictText,
            ["reason"] = d.ReasonCode,
            ["allowed"] = d.Allowed,
            ["ms"] = Math.Round(d.Ms, 3),
            ["counterexample"] = d.Counterexample,
        };
        w.WriteLine(JsonSerializer.Serialize(obj));
        n++;
    }
}
Console.WriteLine($"wrote {outPath} rows={n}");
return 0;
