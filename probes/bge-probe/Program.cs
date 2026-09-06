using agent.vectormemory;

using LLama.Native;

Console.OutputEncoding = System.Text.Encoding.UTF8;
NativeLibraryConfig.All.WithLogCallback((level, message) => Console.Error.Write($"[nlib:{level}] {message}"));
var modelPath = args.Length > 0 ? args[0] : "/tmp/p3probe/models/bge-q8.gguf";
Console.WriteLine($"[probe] loading {modelPath}");
var sw = System.Diagnostics.Stopwatch.StartNew();
var provider = BgeEmbeddingProvider.Create(modelPath);
Console.WriteLine($"[probe] loaded in {sw.ElapsedMilliseconds}ms dim={provider.Dimension}");

var sentences = new[] { "项目代号是 Omega", "项目代号是 Omega 队伍", "今天天气真好适合郊游", "def main(): print(1)" };
var vecs = sentences.Select(s => provider.Embed(s)).ToList();
for (var i = 0; i < sentences.Length; i++)
{
    Console.WriteLine($"[probe] \"{sentences[i]}\" first5=[{string.Join(',', vecs[i].Take(5).Select(v => v.ToString("F4")))}]");
}
// 相似度矩阵:
for (var i = 0; i < sentences.Length; i++)
for (var j = i + 1; j < sentences.Length; j++)
{
    var dot = vecs[i].Zip(vecs[j], (a, b) => (double)a * b).Sum();
    Console.WriteLine($"[probe] cos({i},{j})={dot:F4}  \"{sentences[i]}\" vs \"{sentences[j]}\"");
}
Console.WriteLine("[probe] OK");
