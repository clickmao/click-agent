// R102 probe: 词袋 hash vs bge 向量 — 同集同查询对比
using agent.vectormemory;

var docs = new[]
{
    "AgentFramework 使用 Yamlify 解析 YAML 配置, 零反射约束下 AOT 编译通过",
    "会话记忆 SessionMemory 采用 JSONL 追加写, 会话结束合并画像",
    "模型队列支持余额阈值自动切换, MIN_BALANCE 低于阈值触发 failover",
    "技能调度 SkillDispatcher 按语义匹配度选择虚拟技能, 失败返回 error JSON",
    "RAG 召回管线支持词面打分与内容命中下限, content_hit floor 0.45",
    "隔离任务由 IsolatedTaskRunner 执行, 与主上下文零共享",
    "任务循环 TaskLoop 支持子任务细分与并发 subagent 派分",
    "评测基建 run_round.py 支持 quick 模式与 JSON 校验器",
};

var queries = new[]
{
    ("YAML 解析用什么库", 0),
    ("余额不足会怎样", 2),
    ("技能失败了怎么处理", 3),
    ("隔离任务执行器叫什么", 5),
    ("评测脚本怎么跑", 7),
    ("记忆是怎么存的", 1),
};

// 词袋 hash embedding (RAG 同款逻辑):
static float[] HashEmbed(string text)
{
    var emb = new float[256];
    foreach (var word in text.Split(' ', '，', '。', '、'))
    {
        if (word.Length == 0) continue;
        var h = Math.Abs(word.GetHashCode());
        for (int seed = 0; seed < 3; seed++)
            emb[(h + seed * 31337) % 256] += 1f;
    }
    var mag = Math.Sqrt(emb.Sum(e => (double)e * e));
    if (mag > 0) for (int i = 0; i < emb.Length; i++) emb[i] /= (float)mag;
    return emb;
}

static double Cos(float[] a, float[] b)
{
    double dot = 0; for (int i = 0; i < Math.Min(a.Length, b.Length); i++) dot += (double)a[i] * b[i];
    return dot;
}

var bge = BgeEmbeddingProvider.Create(args.Length > 0 ? args[0] : "/tmp/p3probe/models/bge-q8.gguf");
Console.WriteLine($"[recall-probe] bge dim={bge.Dimension}");

int hashHit = 0, bgeHit = 0;
foreach (var (q, expect) in queries)
{
    var hq = HashEmbed(q); var bq = bge.Embed(q);
    var hScores = docs.Select((d, i) => (i, s: Cos(hq, HashEmbed(d)))).OrderByDescending(x => x.s).ToList();
    var bScores = docs.Select((d, i) => (i, s: Cos(bq, bge.Embed(d)))).OrderByDescending(x => x.s).ToList();
    var hTop = hScores[0].i; var bTop = bScores[0].i;
    if (hTop == expect) hashHit++;
    if (bTop == expect) bgeHit++;
    Console.WriteLine($"[recall-probe] Q=\"{q}\"");
    Console.WriteLine($"  hash: top={hTop} ({hScores[0].s:F3}) expect={expect} {(hTop == expect ? "HIT" : "MISS")}");
    Console.WriteLine($"  bge : top={bTop} ({bScores[0].s:F3}) expect={expect} {(bTop == expect ? "HIT" : "MISS")}");
}
Console.WriteLine($"[recall-probe] RESULT hash={hashHit}/{queries.Length} bge={bgeHit}/{queries.Length}");
