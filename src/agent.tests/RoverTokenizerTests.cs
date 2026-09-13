using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Xunit;
using agent.rover.token;

namespace agent.tests;

/// <summary>
/// R400 · rover 分词链对账测试 (oracle = huggingface tokenizers 0.23.2, 独立实现)。
///
/// 断言全部绑定**真实行为**, 且带反向负控 (R399 判定器铁律: 没有负控的通过率是空心指标):
///   ① 表快照 (脱离 4.2 GB 模型) 与 GGUF 来源同摘要;
///   ② encode / pretok / 压力批 / decode 四组夹具逐条对账 (oracle 生成, 数据落 repo);
///   ③ chat template 与 jinja2 渲染逐字节对齐;
///   ④ 负控: 乱序 merges、空 merges、空切分集、朴素整片预分词 都必须被夹具集判出来。
/// </summary>
public class RoverTokenizerTests
{
    private const string MergeShaPrefix = "cb5bed793622288a";

    private static readonly Lazy<BpeTokenizer> LazyTok = new(Load);

    private static readonly Lazy<JsonDocument> LazyManifest = new(() =>
        JsonDocument.Parse(File.ReadAllText(Path.Combine(Root, "eval", "rover", "tokref", "manifest.json"), Encoding.UTF8)));

    private static JsonDocument Manifest => LazyManifest.Value;

    private static BpeTokenizer Tok => LazyTok.Value;

    private static string Root
    {
        get
        {
            DirectoryInfo? dir = new(AppContext.BaseDirectory);
            while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "eval", "rover", "tokref", "manifest.json")))
            {
                dir = dir.Parent;
            }

            return dir?.FullName ?? throw new InvalidOperationException("找不到仓库根 (eval/rover/tokref/manifest.json)");
        }
    }

    private static string Tokref(params string[] parts) => Path.Combine([Root, "eval", "rover", "tokref", .. parts]);

    private static BpeTokenizer Load()
    {
        Assert.True(TableSnapshot.TryLoad(Path.Combine(Root, "eval", "rover", "tokref", "tables"), out BpeTokenizer? tk, out string prov, out string err),
            $"表快照装载失败: {err}");
        Assert.NotNull(tk);
        return tk!;
    }

    private static List<JsonDocument> Rows(string file)
    {
        List<JsonDocument> rows = [];
        foreach (string line in File.ReadLines(file, Encoding.UTF8))
        {
            if (line.Trim().Length > 0)
            {
                rows.Add(JsonDocument.Parse(line));
            }
        }

        return rows;
    }

    // ── ① 资产与来源一致性 ────────────────────────────────────────────────

    [Fact]
    public void Assets_SelfCheck_AllPass()
    {
        Assert.True(ByteUnicode.SelfCheck(out string d1), d1);
        Assert.True(Pretokenizer.SelfCheck(out string d2), d2);
        Assert.True(ChatTemplate.SelfCheck(out string d3), d3);
        Assert.Equal(BpeTokenizer.DigestLines(TokenizerAssets.SplitTokens), TokenizerAssets.SplitTokensDigest);
        Assert.Equal(BpeTokenizer.DigestLines(TokenizerAssets.SpecialTokens), TokenizerAssets.SpecialTokensDigest);
        Assert.Equal(18, TokenizerAssets.SplitTokens.Length);
        Assert.Equal(3, TokenizerAssets.SpecialTokens.Length);
    }

    [Fact]
    public void TableSnapshot_MatchesGgufSource()
    {
        Assert.Equal(102400, Tok.VocabSize);
        Assert.Equal(99757, Tok.MergeCount);
        Assert.StartsWith(MergeShaPrefix, Tok.MergesSha256, StringComparison.Ordinal);

        // 与 GGUF 登记的合并表摘要逐位一致 (跨实现对账锚点)
        using JsonDocument meta = JsonDocument.Parse(File.ReadAllText(Path.Combine(Root, "eval", "rover", "tokref", "tables", "meta.json"), Encoding.UTF8));
        Assert.Equal(meta.RootElement.GetProperty("merges_sha256").GetString(), Tok.MergesSha256);
        Assert.Equal(102400, meta.RootElement.GetProperty("n_tokens").GetInt32());
        Assert.Equal(99757, meta.RootElement.GetProperty("n_merges").GetInt32());
        Assert.Equal(18, meta.RootElement.GetProperty("n_control").GetInt32());
        Assert.Equal(2382, meta.RootElement.GetProperty("n_unused").GetInt32());
        Assert.Equal(100000, meta.RootElement.GetProperty("n_normal").GetInt32());

        // 夹具条数登记值 (缺字段即失败, 不静默)
        Assert.Equal(199, Manifest.RootElement.GetProperty("fixtures").GetInt32());
        Assert.Equal(2000, Manifest.RootElement.GetProperty("stress_fixtures").GetInt32());
        Assert.Equal(405, Manifest.RootElement.GetProperty("decode_fixtures").GetInt32());
    }

    // ── ② 四组夹具逐条对账 ────────────────────────────────────────────────

    [Fact]
    public void Encode_MatchesOracle_199()
    {
        List<JsonDocument> rows = Rows(Tokref("fixtures.jsonl"));
        Assert.Equal(Manifest.RootElement.GetProperty("fixtures").GetInt32(), rows.Count);

        List<string> bad = [];
        foreach (JsonDocument d in rows)
        {
            string text = d.RootElement.GetProperty("text").GetString()!;
            int[] want = [.. d.RootElement.GetProperty("ids").EnumerateArray().Select(x => x.GetInt32())];
            List<int> got = Tok.Encode(text);
            if (!got.SequenceEqual(want))
            {
                bad.Add($"i={d.RootElement.GetProperty("i").GetInt32()} want={want.Length} got={got.Count}");
            }
        }

        Assert.Empty(bad);
    }

    [Fact]
    public void Pretok_MatchesOracle_199()
    {
        List<JsonDocument> rows = Rows(Tokref("pretok_fixtures.jsonl"));
        Assert.Equal(199, rows.Count);

        List<string> bad = [];
        foreach (JsonDocument d in rows)
        {
            string text = d.RootElement.GetProperty("text").GetString()!;
            string[] want = [.. d.RootElement.GetProperty("pieces").EnumerateArray().Select(x => x.GetString()!)];
            List<string> got = Tok.Pieces(text);
            if (!got.SequenceEqual(want, StringComparer.Ordinal))
            {
                bad.Add($"i={d.RootElement.GetProperty("i").GetInt32()} want_n={want.Length} got_n={got.Count}");
            }
        }

        Assert.Empty(bad);
    }

    [Fact]
    public void Stress_MatchesOracle_2000()
    {
        List<JsonDocument> rows = Rows(Tokref("stress_fixtures.jsonl"));
        Assert.Equal(Manifest.RootElement.GetProperty("stress_fixtures").GetInt32(), rows.Count);

        int badIds = 0;
        int badPieces = 0;
        foreach (JsonDocument d in rows)
        {
            string text = d.RootElement.GetProperty("text").GetString()!;
            int[] wantIds = [.. d.RootElement.GetProperty("ids").EnumerateArray().Select(x => x.GetInt32())];
            if (!Tok.Encode(text).SequenceEqual(wantIds))
            {
                badIds++;
            }

            string[] wantPieces = [.. d.RootElement.GetProperty("pieces").EnumerateArray().Select(x => x.GetString()!)];
            if (!Tok.Pieces(text).SequenceEqual(wantPieces, StringComparer.Ordinal))
            {
                badPieces++;
            }
        }

        Assert.Equal(0, badIds);
        Assert.Equal(0, badPieces);
    }

    [Fact]
    public void Decode_MatchesOracle_405()
    {
        List<JsonDocument> rows = Rows(Tokref("decode_fixtures.jsonl"));
        Assert.Equal(Manifest.RootElement.GetProperty("decode_fixtures").GetInt32(), rows.Count);

        int bad = 0;
        foreach (JsonDocument d in rows)
        {
            List<int> ids = [.. d.RootElement.GetProperty("ids").EnumerateArray().Select(x => x.GetInt32())];
            if (Tok.Decode(ids) != d.RootElement.GetProperty("text").GetString()
                || Tok.Decode(ids, skipSpecialTokens: false) != d.RootElement.GetProperty("text_raw").GetString())
            {
                bad++;
            }
        }

        Assert.Equal(0, bad);
    }

    [Fact]
    public void ChatTemplate_MatchesJinja2Golden_12()
    {
        List<JsonDocument> rows = Rows(Tokref("chat_golden.jsonl"));
        Assert.Equal(ChatTemplate.GoldenCount, rows.Count);

        int bad = 0;
        foreach (JsonDocument d in rows)
        {
            List<ChatMessage> msgs = [];
            foreach (JsonElement m in d.RootElement.GetProperty("messages").EnumerateArray())
            {
                msgs.Add(new ChatMessage(m.GetProperty("role").GetString()!, m.GetProperty("content").GetString()!));
            }

            string got = ChatTemplate.Render(msgs, d.RootElement.GetProperty("add_generation_prompt").GetBoolean());
            if (got != d.RootElement.GetProperty("rendered").GetString())
            {
                bad++;
            }
        }

        Assert.Equal(0, bad);

        // 不支持分支必须显式拒绝 (不得静默降级)
        Assert.Throws<NotSupportedException>(() => ChatTemplate.Render([new ChatMessage("tool", "x")], true));
    }

    [Fact]
    public void Decode_RoundTrip_AllFixtureTexts()
    {
        foreach (JsonDocument d in Rows(Tokref("stress_fixtures.jsonl")))
        {
            string text = d.RootElement.GetProperty("text").GetString()!;
            Assert.Equal(text, Tok.Decode(Tok.Encode(text), skipSpecialTokens: false));
        }
    }

    // ── ④ 反向负控 ───────────────────────────────────────────────────────

    [Fact]
    public void NegativeControl_MergeTableVariants_AreDetected()
    {
        // 实测下界 (2026-09-14 · 压力批 2000 条, 依赖合并样本 1814 条):
        //   shuffled 41.5% / reversed 56.9% / empty 95.3% 被检出。
        // 阈值取保守下界 (30%/40%/90%) —— 低于此即判定夹具对合并表敏感度不足。
        (string Name, List<string> Merges, int FloorPct)[] variants =
        [
            ("shuffled", MergesShuffled(), 30),
            ("reversed", [.. Enumerable.Reverse(Merges())], 40),
            ("empty", [], 90),
        ];
        foreach ((string name, List<string> mv, int floorPct) in variants)
        {
            (int dep, int caught) = MergeDependentCatchRate(BuildWith(mv), "stress_fixtures.jsonl");
            Assert.True(dep >= 1000, $"{name}: 依赖合并样本仅 {dep} 条");
            Assert.True(caught * 100 >= dep * floorPct, $"{name}: 仅 {caught}/{dep} 被检出 (下界 {floorPct}%)");
        }

        // 199 条夹具集上必须至少被检出 (锁定小批量行为, 不做比例断言)
        (int depSmall, int caughtSmall) = MergeDependentCatchRate(BuildWith(MergesShuffled()));
        Assert.True(depSmall >= 15, $"夹具集依赖合并样本仅 {depSmall} 条");
        Assert.True(caughtSmall > 0, "夹具集对合并表零敏感");
    }

    [Fact]
    public void NegativeControl_EmptySplitTokens_MustBreakSpecialText()
    {
        BpeTokenizer noSplit = BuildWith([], splitTokens: []);
        const string text = "a<｜end▁of▁sentence｜>b";
        Assert.Equal(3, Tok.Encode(text).Count); // a | <｜end▁of▁sentence｜> | b (切分集生效 ⇒ 3 个 id)
        Assert.NotEqual(Tok.Encode(text), noSplit.Encode(text));
        Assert.True(noSplit.Encode(text).Count > 3, "空切分集下特殊符号应被拆成多片");
    }

    [Fact]
    public void NegativeControl_NaiveWholeTextPretokenizer_MustBeDiscriminated()
    {
        // 朴素实现 (整段文本一片, 不做预分词) 在夹具集上的通过率必须显著低 ⇒ 夹具集有判别力。
        // 实测 (2026-09-14): 199 条中 137 条为多片 ⇒ 朴素路线被判别 137 条 (下界取 100)。
        int naivePass = 0;
        int total = 0;
        foreach (JsonDocument d in Rows(Tokref("pretok_fixtures.jsonl")))
        {
            string text = d.RootElement.GetProperty("text").GetString()!;
            string[] want = [.. d.RootElement.GetProperty("pieces").EnumerateArray().Select(x => x.GetString()!)];
            string[] naive = [ByteUnicode.Encode(text)];
            total++;
            if (naive.SequenceEqual(want, StringComparer.Ordinal))
            {
                naivePass++;
            }
        }

        Assert.Equal(199, total);
        Assert.True(total - naivePass >= 100, $"朴素预分词仅被判别 {total - naivePass}/{total} 条 ⇒ 夹具集判别力不足");
    }

    [Fact]
    public void Decode_SkipsExactlySpecialTokens()
    {
        // 跳过集 = 3 (special=true), 其余控制符号 (如 <｜fim▁hole｜> = 100002) 不得被跳过
        Assert.Equal(string.Empty, Tok.Decode([100000]));
        Assert.Equal(string.Empty, Tok.Decode([100001]));
        Assert.Equal(string.Empty, Tok.Decode([100008]));
        Assert.NotEqual(string.Empty, Tok.Decode([100002]));
        Assert.NotEqual(string.Empty, Tok.Decode([100006]));
    }

    [Fact]
    public void Encode_InvalidUtf8ByteChars_AreUnreachable()
    {
        // 13 个非法 UTF-8 起始字节的字节级字符不在词表 ⇒ 任何合法 C# 字符串都不会产生它们
        foreach (byte b in new byte[] { 0xC0, 0xC1, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF })
        {
            char c = ByteUnicode.ToChar(b);
            List<int> ids = Tok.Encode(c.ToString());
            Assert.NotEmpty(ids);
        }

        Assert.Equal("汉字 héllo ½ ① \U00010400", Tok.Decode(Tok.Encode("汉字 héllo ½ ① \U00010400")));
    }

    // ── 切分/特殊符号表随模型走 (R402 可移植性: 编译期 DeepSeek 表不得是唯一来源) ──

    [Fact]
    public void DeriveFromTypes_SeparatesControlAndUserDefined()
    {
        List<string> tokens = ["a", "<|ctrl|>", "<|user|>", "<unused>"];
        List<int> types = [1, 3, 4, 5];
        Assert.True(BpeTokenizer.TryDeriveFromTypes(tokens, types, out List<string> split, out List<string> special));
        Assert.Equal(["<|ctrl|>", "<|user|>"], split);
        Assert.Equal(["<|ctrl|>"], special);
    }

    [Fact]
    public void DeriveFromTypes_NegativeControls()
    {
        // ① 类型表长度不符 ⇒ false + 空表 (绝不回退编译期 DeepSeek 表: 那些符号不在别的词表内)
        Assert.False(BpeTokenizer.TryDeriveFromTypes(["a"], [], out List<string> s1, out List<string> p1));
        Assert.Empty(s1);
        Assert.Empty(p1);

        // ② 纯普通词表 (无 added token) ⇒ false + 空表
        Assert.False(BpeTokenizer.TryDeriveFromTypes(["a", "b"], [1, 1], out List<string> s2, out List<string> p2));
        Assert.Empty(s2);
        Assert.Empty(p2);

        // ③ 空词表 ⇒ false
        Assert.False(BpeTokenizer.TryDeriveFromTypes([], [], out List<string> s3, out List<string> p3));
        Assert.Empty(s3);
        Assert.Empty(p3);
    }

    [Fact]
    public void DerivedSplitTableIsHonoredByEncode()
    {
        string[] builtin = TokenizerAssets.SplitTokens;
        string longTok = builtin.OrderByDescending(t => t.Length).First();
        string shortTok = builtin.OrderBy(t => t.Length).First();
        Assert.NotEqual(longTok.Length, shortTok.Length);

        // 长符号放在实例表 index 1: 旧实现按编译期表取长度 (index 1 = 别的符号) ⇒ 前进错位
        BpeTokenizer tk = BuildWith(Merges(), [shortTok, longTok]);
        Assert.Equal(2, tk.SplitCount);
        Assert.Single(tk.Encode(longTok));
    }

    // ── helpers ──────────────────────────────────────────────────────────

    private static List<string> Merges()
        => [.. File.ReadLines(Path.Combine(Root, "eval", "rover", "tokref", "tables", "merges.txt"), Encoding.UTF8)];

    private static List<string> MergesShuffled()
    {
        List<string> merges = [.. File.ReadLines(Path.Combine(Root, "eval", "rover", "tokref", "tables", "merges.txt"), Encoding.UTF8)];
        // 确定性乱序 (集合不变, 只打乱 rank): 用 sha256 前 8 字节排序
        return [.. merges.OrderBy(m => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(m)))[..16], StringComparer.Ordinal)];
    }

    private static BpeTokenizer BuildWith(List<string> merges, IReadOnlyList<string>? splitTokens = null)
    {
        List<string> tokens = [];
        List<int> types = [];
        using FileStream fs = File.OpenRead(Path.Combine(Root, "eval", "rover", "tokref", "tables", "tokens.jsonl.gz"));
        using System.IO.Compression.GZipStream gz = new(fs, System.IO.Compression.CompressionMode.Decompress);
        using StreamReader sr = new(gz, Encoding.UTF8);
        string? line;
        while ((line = sr.ReadLine()) != null)
        {
            if (line.Length == 0)
            {
                continue;
            }

            using JsonDocument d = JsonDocument.Parse(line);
            tokens.Add(d.RootElement.GetProperty("t").GetString()!);
            types.Add(d.RootElement.GetProperty("type").GetInt32());
        }

        return new BpeTokenizer(tokens, types, merges, splitTokens ?? TokenizerAssets.SplitTokens);
    }

    /// <summary>
    /// 依赖合并表的样本 (= 至少一个片段被切成 ≥2 个 token) 上, 变体分词器改变了多少条。
    /// 整片命中词表 (快路径) 的文本与合并表无关, 计入只会稀释判别力 —— 故按依赖集统计。
    /// </summary>
    private static (int Dependent, int Caught) MergeDependentCatchRate(BpeTokenizer variant, string file = "fixtures.jsonl")
    {
        int dep = 0;
        int caught = 0;
        foreach (JsonDocument d in Rows(Tokref(file)))
        {
            string text = d.RootElement.GetProperty("text").GetString()!;
            List<int> baseline = Tok.Encode(text);
            if (baseline.Count <= Tok.Pieces(text).Count)
            {
                continue; // 未用到合并
            }

            dep++;
            if (!variant.Encode(text).SequenceEqual(baseline))
            {
                caught++;
            }
        }

        return (dep, caught);
    }
}
