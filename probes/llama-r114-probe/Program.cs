// v0.11.0 R114 探针: Silk.NET 式单入口加载 (fork NativeLibraryUtils R114 快路径) 真机验证
// ① bge embed (CPU) ② chat LLM (qwen, CPU) ③ 加载日志应出现 "R114 single-entry load"
// ④ /proc/self/maps 应含 libggml-vulkan + libvulkan (同一套 vulkan 库, 无变体复制)
using agent.llamalocal;
using agent.templates;

var log = new List<string>();

// ── ① bge embed (CPU 直连) ──
var bgePath = "/home/agentuser/models/bge-small-en-v1.5-q4_k_m.gguf";
if (!File.Exists(bgePath))
{
    Console.WriteLine("SKIP: bge 模型缺失");
    return 1;
}
// 挂加载器日志 (NativeLibraryConfig 全局) — 捕获 R114 快路径证据
var loadLog = new List<string>();
LLama.Native.NativeLibraryConfig.All.WithLogCallback((level, msg) => loadLog.Add($"[{level}] {msg}"));
var bge = new BgeEmbedder(bgePath);
var sw = System.Diagnostics.Stopwatch.StartNew();
var v1 = await bge.EmbedAsync("quick sort algorithm");
var v2 = await bge.EmbedAsync("binary search tree");
var v3 = await bge.EmbedAsync("chocolate cake recipe");
sw.Stop();
Console.WriteLine($"[bge-cpu] dim={v1.Length} wall={sw.ElapsedMilliseconds}ms " +
    $"cos(v1,v2)={Cos(v1, v2):F3} cos(v1,v3)={Cos(v1, v3):F3}");
bge.Dispose();

// ── ② chat LLM (qwen, 进程内直连) ──
var qwenPath = "/home/agentuser/models/qwen2.5-0.5b-instruct-q4_k_m.gguf";
if (File.Exists(qwenPath))
{
    var caller = new LocalLlamaCaller(
        Microsoft.Extensions.Logging.Abstractions.NullLogger<LocalLlamaCaller>.Instance,
        qwenPath, contextSize: 1024, backendMode: LlamaBackendMode.Auto, gpuLayers: 0);
    var prompt = new Prompt { SystemPrompt = "You are a calculator. Answer with just the number.", UserMessage = "2+2=?" };
    var sw2 = System.Diagnostics.Stopwatch.StartNew();
    var resp = await caller.CallAsync(prompt);
    sw2.Stop();
    Console.WriteLine($"[chat-cpu] success={resp.Success} model={resp.Model} reply={resp.Content?.Trim()} error={resp.Error} wall={sw2.ElapsedMilliseconds}ms");
}

// ── ③④ 加载证据: native 模块清单 ──
var loaded = new HashSet<string>();
foreach (var line in File.ReadLines("/proc/self/maps"))
{
    var name = line.Substring(line.LastIndexOf('/') + 1);
    if (name.Contains("libggml") || name.Contains("libllama") || name.Contains("libvulkan"))
        loaded.Add(name);
}
Console.WriteLine("[native] " + string.Join(", ", loaded.OrderBy(x => x)));
Console.WriteLine(loaded.Any(x => x.Contains("vulkan")) ? "VULKAN-LOADED ✓" : "VULKAN-MISSING ✗");
foreach (var l in loadLog)
    if (l.Contains("R114") || l.Contains("single-entry") || l.Contains("Loading library"))
        Console.WriteLine("[loader] " + l.Trim());
return 0;

static double Cos(float[] a, float[] b)
{
    double dot = 0, na = 0, nb = 0;
    for (var i = 0; i < a.Length && i < b.Length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
    return dot / (Math.Sqrt(na) * Math.Sqrt(nb) + 1e-9);
}
