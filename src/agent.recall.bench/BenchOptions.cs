// R480: 独立文本召回模块 —— 测量器具 (真实语料质量臂 + 同比例压缩规模臂 + 增量保鲜臂)。
// 纪律: 所有数字来自本进程真实执行; 合成语料一律在 JSON 里标 "synthetic": true, 不与真实语料混算。
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using agent.recall;

namespace agent.recall.bench;


internal sealed class BenchOptions
{
    public string Corpus = "eval/bge/fixtures/corpus.jsonl";
    public string Queries = "eval/bge/fixtures/queries.jsonl";
    public string Out = "eval/recall/bench.json";
    public string WorkRoot = "";
    public string RefreshRoot = "docs";
    public int K = 10;
    public int[] Scales = { 1, 10, 100 };
    public int Seed = 20260916;
}
