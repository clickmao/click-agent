using agent.session;
using Xunit;

namespace agent.tests;

/// <summary>
/// R370 · L2-F1 跨会话检索 (SessionHistorySearch) 单测。
/// 铁律: 每项能力都要有**真断言** (不是"跑通即通过"), 且必须有负向控制。
/// </summary>
public sealed class SessionHistorySearchTests : IDisposable
{
    private readonly string _dir;
    private readonly JsonSessionMemoryStore _store;

    public SessionHistorySearchTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "af-session-search-" + Guid.NewGuid().ToString("N")[..8]);
        _store = new JsonSessionMemoryStore(_dir);
    }

    public void Dispose()
    {
        try
        {
            if (Directory.Exists(_dir))
                Directory.Delete(_dir, recursive: true);
        }
        catch
        { /* 清理失败不影响断言 */
        }
    }

    private void Seed(string sessionId, string note, string? goal = null)
    {
        var mem = new SessionMemory();
        if (goal != null)
            mem.SetGoal(goal);
        mem.Remember(note);
        _store.Save(sessionId, mem);
    }

    private SessionHistorySearch NewSearch() => new(new SessionHistorySearch.StoreSource(_store));

    [Fact]
    public void Search_Ranks_Session_Containing_Unique_Term_First()
    {
        Seed("s-vector", "实现了 向量召回 与 嵌入缓存 两层", goal: "提升召回质量");
        Seed("s-frontend", "前端事件信封 与 通知通路 接线", goal: "前端联调");

        var hits = NewSearch().Search("向量召回 嵌入", topK: 5);

        Assert.NotEmpty(hits);
        Assert.Equal("s-vector", hits[0].SessionId);
        Assert.DoesNotContain(hits, h => h.SessionId == "s-frontend");
        Assert.True(hits[0].Score > 0);
    }

    [Fact]
    public void Search_Is_Deterministic_Across_Calls()
    {
        Seed("s-a", "教训表 归 role 模块 含提交 API");
        Seed("s-b", "教训表 与 记忆 注入 链路");
        Seed("s-c", "无关内容 像素 渲染");

        var search = NewSearch();
        var r1 = search.Search("教训表 提交 API", topK: 3);
        var r2 = search.Search("教训表 提交 API", topK: 3);

        Assert.Equal(r1.Count, r2.Count);
        for (var i = 0; i < r1.Count; i++)
        {
            Assert.Equal(r1[i].SessionId, r2[i].SessionId);
            Assert.Equal(r1[i].Score, r2[i].Score);
        }
    }

    [Fact]
    public void Empty_Or_Blank_Query_Returns_Empty()
    {
        Seed("s-a", "任意内容");
        var search = NewSearch();
        Assert.Empty(search.Search(""));
        Assert.Empty(search.Search("   "));
        Assert.Empty(search.Search("任意内容", topK: 0));
    }

    [Fact]
    public void Unrelated_Query_Returns_Empty_NegativeControl()
    {
        Seed("s-a", "向量召回 与 嵌入缓存");
        var hits = NewSearch().Search("完全不相干的外星词根zzq", topK: 5);
        Assert.Empty(hits);
    }

    [Fact]
    public void TopK_Is_Respected()
    {
        Seed("s-1", "共享标记 甲");
        Seed("s-2", "共享标记 乙");
        Seed("s-3", "共享标记 丙");
        var hits = NewSearch().Search("共享标记", topK: 2);
        Assert.Equal(2, hits.Count);
    }

    [Fact]
    public void Snippet_Is_Bounded_And_Contains_Matched_Text()
    {
        Seed("s-long", new string('前', 300) + " 关键锚点 向量重排 " + new string('后', 300));
        var hits = NewSearch().Search("向量重排", topK: 1);
        Assert.Single(hits);
        Assert.True(hits[0].Snippet.Length <= 124, $"片段长度越界: {hits[0].Snippet.Length}");
        Assert.Contains("向量重排", hits[0].Snippet);
    }

    [Fact]
    public void Idf_Downscores_Term_Shared_By_All_Sessions()
    {
        Seed("s-a", "共享词 加上 特有词甲");
        Seed("s-b", "共享词 加上 其它内容");

        var search = NewSearch();
        var unique = search.Search("特有词甲", topK: 5);
        var common = search.Search("共享词", topK: 5);

        Assert.NotEmpty(unique);
        Assert.NotEmpty(common);
        double ScoreOf(IReadOnlyList<SessionHistorySearch.Hit> hs, string id)
            => hs.Single(h => h.SessionId == id).Score;

        Assert.True(ScoreOf(unique, "s-a") > ScoreOf(common, "s-a"),
            "独有词的 IDF 权重必须高于广布词 (否则判别力退化为纯词频)");
    }

    [Fact]
    public void Search_Does_Not_Write_Any_File_ReadOnly_Guarantee()
    {
        Seed("s-a", "只读性 验证 标记");
        var sessionsDir = Path.Combine(_dir, "sessions");
        var before = Directory.GetFiles(sessionsDir).OrderBy(f => f, StringComparer.Ordinal).ToArray();
        var beforeWriteTime = before.Select(File.GetLastWriteTimeUtc).ToArray();

        var hits = NewSearch().Search("只读性 验证", topK: 5);
        Assert.NotEmpty(hits);

        var after = Directory.GetFiles(sessionsDir).OrderBy(f => f, StringComparer.Ordinal).ToArray();
        Assert.Equal(before.Length, after.Length);
        for (var i = 0; i < after.Length; i++)
            Assert.Equal(beforeWriteTime[i], File.GetLastWriteTimeUtc(after[i]));
    }

    [Fact]
    public void Document_Builder_Includes_Goal_And_Constraints()
    {
        var mem = new SessionMemory();
        mem.SetGoal("目标句: 提升召回", keyEntities: new[] { "bge-small" }, constraints: new[] { "AOT 0 IL" });
        mem.AddMilestone("评测台落地");

        var doc = SessionHistorySearch.BuildDocument(mem);

        Assert.Contains("提升召回", doc);
        Assert.Contains("bge-small", doc);
        Assert.Contains("AOT 0 IL", doc);
        Assert.Contains("评测台落地", doc);
    }

    [Fact]
    public void Missing_Session_File_Is_Skipped_Not_Thrown()
    {
        Seed("s-real", "真实会话 内容 检索");
        var search = NewSearch();
        // 枚举里混入不存在的 id (模拟并发删除/半截文件)
        var hits = new SessionHistorySearch(
            new MixedSource(new SessionHistorySearch.StoreSource(_store), "s-ghost")).Search("真实会话", topK: 5);
        Assert.Single(hits);
        Assert.Equal("s-real", hits[0].SessionId);
    }

    [Fact]
    public void Render_Empty_Hits_Is_Explicit_Not_Silent()
    {
        // R420: /recall 出口的空结果必须有可读回执 (静默空白 = 用户无法区分"无命中"与"功能坏")
        var text = SessionHistorySearch.Render(Array.Empty<SessionHistorySearch.Hit>(), "不存在词根zzq", 5);
        Assert.Contains("无命中", text);
        Assert.Contains("命中 0", text);
        Assert.Contains("不存在词根zzq", text);
    }

    [Fact]
    public void Render_Binds_Count_Order_And_Score_To_Result_Set()
    {
        // R420: 渲染是"读数"不是"文案" — 命中数/顺序/分数必须与结果集一致
        Seed("s-vector", "向量召回 与 嵌入缓存 两层", goal: "提升召回质量");
        Seed("s-other", "无关内容 像素 渲染");

        var hits = NewSearch().Search("向量召回 嵌入", topK: 5);
        Assert.Single(hits);
        var text = SessionHistorySearch.Render(hits, "向量召回 嵌入", 5);

        Assert.Contains("命中 1", text);
        Assert.Contains("s-vector", text);
        Assert.Contains("score=", text);
        Assert.Contains("向量召回", text);
        Assert.DoesNotContain("s-other", text);
    }

    [Fact]
    public void Render_Multi_Hit_Preserves_Rank_Order()
    {
        Seed("s-1", "共享标记 甲 甲 甲");
        Seed("s-2", "共享标记 乙");

        var hits = NewSearch().Search("共享标记", topK: 2);
        Assert.Equal(2, hits.Count);
        var text = SessionHistorySearch.Render(hits, "共享标记", 2);

        Assert.Contains("命中 2", text);
        Assert.True(text.IndexOf("1. " + hits[0].SessionId, StringComparison.Ordinal) <
                    text.IndexOf("2. " + hits[1].SessionId, StringComparison.Ordinal),
            "渲染顺序必须与排序结果一致 (否则读数与判据脱钩)");
    }

    // ===== R421: 否定极性 (打分对否定无感 ⇒ 词面重叠 ≠ 语义相关) =====
    // 判据 (预注册, 双向): ①肯定查询召肯定文档 ②否定查询召否定文档
    // ③否定查询**不得**召到只断言肯定命题的文档 ④召回不被打死 (正控仍召)

    [Fact]
    public void Render_Is_Line_Addressable_One_Hit_Per_Line()
    {
        // 仪器: 真机读数靠解析渲染原文取命中集; 片段与下一条命中粘成一行 ⇒ 只解析出第 1 条 (R421 实测踩到)
        Seed("s-x", "目标服务 存在 于生产环境");
        Seed("s-y", "目标服务 不存在 于生产环境");
        var search = NewSearch();
        var hits = search.Search("存在", topK: 5);
        var text = SessionHistorySearch.Render(hits, "存在", 5);
        var lines = text.Split('\n');
        var hitLines = lines.Where(l => System.Text.RegularExpressions.Regex.IsMatch(l, @"^\d+\. ")).ToList();
        foreach (var l in hitLines)
            Assert.Matches(@"^\d+\. \S+  score=\d+\.\d{4}  entries=\d+$", l);
        Assert.Equal(hits.Count, hitLines.Count);
        // 片段自成一行 (不粘到下一个排名行)
        var snippetLines = lines.Where(l => l.TrimStart().StartsWith("…")).ToList();
        Assert.Equal(hitLines.Count, snippetLines.Count);
    }

    [Fact]
    public void Polarity_FourWay_Matrix_Positive_And_Negated_Are_Not_Crossed()
    {
        Seed("s-pos", "目标服务 存在 于生产环境");
        Seed("s-neg", "目标服务 不存在 于生产环境");

        var search = NewSearch();
        var posQ = search.Search("存在", topK: 5);
        var negQ = search.Search("不存在", topK: 5);

        // ① 正控: 肯定查询仍召肯定文档 (召回未被打死)
        Assert.Contains(posQ, h => h.SessionId == "s-pos");
        // ③ 否定查询不得召到肯定文档
        Assert.DoesNotContain(negQ, h => h.SessionId == "s-pos");
        Assert.Contains(negQ, h => h.SessionId == "s-neg");
        // ② 对称方向: 肯定查询不得召到否定文档 (词面重叠的另一半)
        Assert.DoesNotContain(posQ, h => h.SessionId == "s-neg");
    }

    [Fact]
    public void Polarity_Token_Space_Is_Disjoint_Mechanism_Assertion()
    {
        var pos = SessionHistorySearch.Tokenize("存在");
        var neg = SessionHistorySearch.Tokenize("不存在");

        Assert.Equal(new[] { "存在" }, pos);
        Assert.Contains(SessionHistorySearch.NegMark + "存在", neg);
        Assert.Empty(pos.Intersect(neg, StringComparer.Ordinal));
        // 期望值逐项写死: 防止"极性前缀存在但语义未变"的假修
        Assert.Equal(2, neg.Count);
        Assert.Contains(SessionHistorySearch.NegMark + "不存", neg);
    }

    [Fact]
    public void Polarity_Real_Machine_Replay_R420_Pair_Negated_Query_Must_Not_Recall_Positive_Doc()
    {
        // 语料原文 (R420 真机命中文本, probe-0914125816-p004 / -p005 的题面)
        const string doc = "若图中存在拓扑序, 输出字典序最小的拓扑序; 若存在环";
        Seed("s-real-pos", doc);

        var search = NewSearch();
        var posQ = search.Search("存在", topK: 5);
        var negQ = search.Search("不存在", topK: 5);
        var negLongQ = search.Search("外星词根zzq不存在", topK: 5);

        // 正控: 真机原串 "存在" 仍召到该文档 (R420 读数 hits=2 的同族)
        Assert.Contains(posQ, h => h.SessionId == "s-real-pos");
        // R420 缺陷: "不存在" 召回同一批、读起来像肯定 ⇒ 本轮必须为 0
        Assert.Empty(negQ);
        Assert.Empty(negLongQ);
    }

    [Fact]
    public void Polarity_Mixed_Document_Is_Recalled_By_Both_Polarities_No_Blanket_Kill()
    {
        // 文档同时断言存在与不存在 ⇒ 两种极性查询都应召到 (证明不是一刀切把召回打死)
        Seed("s-mixed", "服务 存在 于生产环境; 但缓存 不存在 于测试环境");

        var search = NewSearch();
        var posQ = search.Search("存在", topK: 5);
        var negQ = search.Search("不存在", topK: 5);

        Assert.Contains(posQ, h => h.SessionId == "s-mixed");
        Assert.Contains(negQ, h => h.SessionId == "s-mixed");
    }

    [Fact]
    public void Polarity_Does_Not_Touch_Tokens_Without_Negation_Markers_RegressionGuard()
    {
        // 回归护栏: 无否定标记的文本, 词元表必须与修复前逐项相同 (修复作用域受控)
        Assert.Equal(new[] { "向量", "量召", "召回" }, SessionHistorySearch.Tokenize("向量召回"));
        Assert.Equal(new[] { "topo", "拓扑", "扑序" }, SessionHistorySearch.Tokenize("topo 拓扑序"));
        // 刻意排除的标记 (别): 不得因"识别"里的"别"而带极性
        Assert.Equal(new[] { "识别", "别文", "文本" }, SessionHistorySearch.Tokenize("识别文本"));
    }

    [Fact]
    public void LengthNorm_ShorterDocument_Outranks_Longer_ForSameSingleToken()
    {
        // R422: 同一词元命中、文档词元数 1/3/5 ⇒ 分数必须严格递减 (预注册方向断言, 非"跑通即通过")
        Seed("s-len1", "存在");
        Seed("s-len3", "存在 甲乙丙");
        Seed("s-len5", "存在 甲乙丙丁戊");
        Seed("s-other", "向量召回 与 嵌入缓存");

        var hits = NewSearch().Search("存在", topK: 5);

        Assert.Equal(new[] { "s-len1", "s-len3", "s-len5" }, hits.Select(h => h.SessionId).ToArray());
        Assert.True(hits[0].Score > hits[1].Score && hits[1].Score > hits[2].Score,
            $"分数必须严格递减 (R421 的并列零区分度), 实测 {hits[0].Score}/{hits[1].Score}/{hits[2].Score}");
        // 阴性对照: 归一不得把无关文档拉进来
        Assert.DoesNotContain(hits, h => h.SessionId == "s-other");
    }

    [Fact]
    public void LengthNorm_And_PolarityInvariants_HoldTogether_OnRealMachineCorpus()
    {
        // R421 冻结真机语料 + 同族更长的第二条 ⇒ 两个不变量必须**同时**成立 (成对, 防一刀切)
        Seed("s-real-pos", "若图中存在拓扑序, 输出字典序最小的拓扑序; 若存在环");
        Seed("s-real-long", "若图中存在拓扑序, 输出字典序最小的拓扑序; 若存在环; 并输出每个节点的入度与出度统计"
            + "并按字典序升序给出全部合法序列");

        var search = NewSearch();
        var posQ = search.Search("存在", topK: 5);
        var negQ = search.Search("不存在", topK: 5);

        // ① 长度归一在作用: 同词元命中的两文档分数不再并列 (R421 真机 0.5596 三份全等已消除)
        Assert.Equal(2, posQ.Count);
        Assert.NotEqual(posQ[0].Score, posQ[1].Score);
        Assert.Equal("s-real-pos", posQ[0].SessionId);
        // ② 极性不变量未被归一破坏 (R421 判据回归)
        Assert.Empty(negQ);
    }

    // ─────────────────── R423: 词元频次饱和 (分子 ×(1 + ln tf)) ───────────────────

    [Fact]
    public void Tf_EqualTokens_DifferentOccurrenceCounts_Ranked_By_ClosedForm()
    {
        // R423 主断言: 文档词元数相同 (|d|=2) 但查询词元出现次数不同 (3 vs 1) ⇒ 必须分档,
        // 且分数比值 == 1 + ln(tf) —— 闭式预测, 与实现独立可算 (防"自算错而自洽")。
        // 特征向量 (查询词元 = 存在):
        //   "存在存在存在存" → distinct bigram {存在,在存} = 2, tf(存在) = 3
        //   "存在甲"         → distinct bigram {存在,在甲} = 2, tf(存在) = 1
        Seed("s-tf3", "存在存在存在存");
        Seed("s-tf1", "存在甲");
        Seed("s-nohit", "像素 渲染 通路");

        var hits = NewSearch().Search("存在", topK: 5);

        Assert.Equal(new[] { "s-tf3", "s-tf1" }, hits.Select(h => h.SessionId).ToArray());
        var ratio = hits[0].Score / hits[1].Score;
        Assert.True(Math.Abs(ratio - (1.0 + Math.Log(3.0))) < 1e-4,
            $"词元频次比值必须等于 1+ln(tf)=2.098612, 实测 {ratio}");
        // 阴性对照: 因子 ≥ 1 不得把无命中文档拉进来 (命中集合不被放大)
        Assert.DoesNotContain(hits, h => h.SessionId == "s-nohit");
    }

    [Fact]
    public void Tf_Boundary_EqualTokensAndEqualCounts_StayTied_NotASeparableDefect()
    {
        // 边界登记 (R423 收窄宣称, 与 R422 的「诚实边界」同族): 词元数**与**查询词元出现次数
        // 皆相同的文档对, 在词袋计数信号族内**数学上不可分** ⇒ 必须并列 (退化为 sessionId 序),
        // 不得把这类并列当成"零区分度未消除"的缺陷 (真机同族样本: 两份 87 词元 / tf=2 的会话)。
        //   特征向量: "存在存在存在存" 与 "在存在存在存在" → distinct=2, tf(存在)=3 (逐项相等)
        Seed("s-dup-a", "存在存在存在存");
        Seed("s-dup-b", "在存在存在存在");

        var hits = NewSearch().Search("存在", topK: 5);

        Assert.Equal(2, hits.Count);
        Assert.Equal(hits[0].Score, hits[1].Score);
        Assert.Equal(new[] { "s-dup-a", "s-dup-b" }, hits.Select(h => h.SessionId).ToArray());
    }

    [Fact]
    public void Tf_Factor_Keeps_HitSet_And_Polarity_Invariant_Paired()
    {
        // 成对判据 (防一刀切): ① 因子 ≥1 ⇒ 命中集合与 R422 口径 (presence + 长度归一) **逐元素相同**;
        //                  ② R421 极性判别不得被频次加权破坏 —— 否定查询只命中否定文档, 不回落肯定文档。
        Seed("s-tf3", "存在存在存在存");
        Seed("s-tf1", "存在甲");
        Seed("s-quiet", "若图中存在拓扑序");
        Seed("s-neg", "服务不存在于测试环境");

        var search = NewSearch();
        var pos = search.Search("存在", topK: 5);
        var neg = search.Search("不存在", topK: 5);

        Assert.Equal(new[] { "s-quiet", "s-tf1", "s-tf3" }, pos.Select(h => h.SessionId).OrderBy(x => x, StringComparer.Ordinal).ToArray());
        Assert.DoesNotContain(pos, h => h.SessionId == "s-neg");        // 阴性对照: 否定文档不得进肯定查询
        Assert.Equal(new[] { "s-neg" }, neg.Select(h => h.SessionId).ToArray()); // 极性判别仍成立
    }

    [Fact]
    public void Tf_Saturates_And_TokenCountsHave_SingleSourceOfTruth()
    {
        Assert.Equal(1.0, SessionHistorySearch.TfSat(0));
        Assert.Equal(1.0, SessionHistorySearch.TfSat(1));
        Assert.Equal(1.0 + Math.Log(2.0), SessionHistorySearch.TfSat(2));
        // 饱和的正确形态 = **相对增益递减** (不是绝对增量递减: 对数函数的绝对增量恒等)。
        // 判据修正记录: 首版断言写"绝对增量递减"被本测试当场否证 (实测 0.693/0.693/0.693 全等)
        //   ⇒ 属**判据自身出错** ⇒ 改判据、不改实现 (不得为了让断言变绿而动被测代码)。
        var r1 = SessionHistorySearch.TfSat(2) / SessionHistorySearch.TfSat(1);
        var r2 = SessionHistorySearch.TfSat(4) / SessionHistorySearch.TfSat(2);
        var r3 = SessionHistorySearch.TfSat(8) / SessionHistorySearch.TfSat(4);
        Assert.True(r1 > r2 && r2 > r3, $"相对增益必须递减 (饱和): {r1}/{r2}/{r3}");
        Assert.True(SessionHistorySearch.TfSat(2) < 2.0 && SessionHistorySearch.TfSat(8) < 8.0,
            "次线性: 因子增长必须慢于出现次数本身");
        for (var tf = 1; tf <= 64; tf++)
            Assert.True(SessionHistorySearch.TfSat(tf) >= SessionHistorySearch.TfSat(tf - 1));

        // 口径单一真源: 计数键集 == Tokenize 词元集 (无二次分词 ⇒ 集合与频次不可能分叉)
        const string s = "向量召回 与 嵌入缓存";
        var counts = SessionHistorySearch.CountTokens(s);
        var tokens = SessionHistorySearch.Tokenize(s);
        Assert.Equal(tokens.ToHashSet(), counts.Keys.ToHashSet());
        Assert.Equal(tokens.Count, counts.Values.Sum());
        Assert.Equal(3, SessionHistorySearch.CountTokens("存在存在存在存")["存在"]);
    }

    [Fact]
    public void R423_FrozenCorpus_FeatureVector_IsMachinePinned_NotHandCounted()
    {
        // 预检数字必须**取自真机分词器**: 首版人工复算只读了长期记忆段、漏了目标/里程碑段
        // ⇒ tf 算成 2 (真值 4), 被 r423 harness 的闭式对账 C4 当场证伪。
        // 本测试把 R422 冻结语料 (三段真实落盘会话) 经 真实存储 Load + BuildDocument + CountTokens
        // 得到的特征向量钉死; harness 的闭式预测引用同组数字 ⇒ 两处同源, 且改动语料/分词器必红。
        var fixtureDir = Path.Combine(RepoRootForFixtures(), "eval", "capability", "r422", "fixture-sessions");
        Assert.True(Directory.Exists(fixtureDir), $"冻结语料缺失: {fixtureDir}");
        var expected = new Dictionary<string, (int Distinct, int Tf)>
        {
            ["cli-6bf6dc8d"] = (4, 1),
            ["probe-0914125816-p004"] = (90, 4),
            ["probe-0914125831-p005"] = (90, 4),
        };

        // 存储按 dataStoragePath/sessions 约定落盘 ⇒ 把冻结语料拷进本用例的隔离会话目录再用真实存储读回
        var sessionsDir = Path.Combine(_dir, "sessions");
        Directory.CreateDirectory(sessionsDir);
        foreach (var f in Directory.GetFiles(fixtureDir))
            File.Copy(f, Path.Combine(sessionsDir, Path.GetFileName(f)), overwrite: true);

        var ids = _store.EnumerateSessionIds();
        Assert.Equal(expected.Count, ids.Count);
        foreach (var id in ids)
        {
            var mem = _store.Load(id);
            Assert.NotNull(mem);
            var counts = SessionHistorySearch.CountTokens(SessionHistorySearch.BuildDocument(mem!));
            Assert.True(expected.ContainsKey(id), $"未登记的冻结会话: {id}");
            Assert.Equal(expected[id].Distinct, counts.Count);
            Assert.Equal(expected[id].Tf, counts.TryGetValue("存在", out var tf) ? tf : 0);
        }
    }

    private static string RepoRootForFixtures()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private sealed class MixedSource : SessionHistorySearch.ISource
    {
        private readonly SessionHistorySearch.ISource _inner;
        private readonly string _ghost;
        public MixedSource(SessionHistorySearch.ISource inner, string ghost) { _inner = inner; _ghost = ghost; }
        public IReadOnlyList<string> EnumerateSessionIds()
        {
            var ids = new List<string>(_inner.EnumerateSessionIds()) { _ghost };
            return ids;
        }
        public SessionMemory? Load(string sessionId) => _inner.Load(sessionId);
    }
}
