#!/usr/bin/env python3
# R490 台账登记: 追加 2 行到 docs/verification-registry.json (幂等: 同 id 已存在则替换)
# 形式门禁 (写入前机检, 不过即拒写): 必填字段 / covers 路径存在 / evidence_path 存在 / 尾部换行 / 保形写回。
import collections, io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
P = os.path.join(ROOT, 'docs', 'verification-registry.json')

EV_ANALYZE = "env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/rover/r490/analyze_r490.py"
EV_TESTS = ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "
            "$HOME/.dotnet/dotnet test src/agent.tests/agentframework.tests.csproj -c Release "
            "--filter FullyQualifiedName~R490ToolDeclGateTests")
EV_ARM = "bash eval/rover/r490/run_rest_r490.sh"

NEW = [
    collections.OrderedDict([
        ("id", "r490.tool-decl-gate-by-intent"),
        ("level", "L2"),
        ("capability",
         "**声明面按需 (不必要远端调用的主源)**: R489 归因出「调用数 = 远端轮 + 上游空正文(tool_calls)轮」且 51/51 请求**每次**都带 4 个工具、intent 全 `general` ⇒ 上游被邀请发 tool_calls, 每次空正文再灌一次全量 prompt。修法 = `ToolDeclGate`(库内, 门 `AGENTFRAMEWORK_TOOL_DECL_GATE`, **默认关**) 只在工作区动作类意图(6 个常量 ⊆ `IntentRecognizer.Intents`)下下发 `tools`; 空/未知意图保守**仍下发**。真机单变量消融(同一 AOT sha 7dc4f117…、同一 12 轮夹具、同窗): B(门关) **15 调用/65,958 tok/¥0.020412**/空正文工具轮 3 → R(只本地闸) **9/37,396/¥0.011893**(−43.30%/−41.74%)/空正文 3 → T1(+声明门) **6/25,753/¥0.009222/空正文 0**(**−60.96%/−54.82%**, finish_reason 全 stop); 声明门自身增量 = T vs R **−31.13%**。质量不降: 真假判别轮(第 10..12 轮植入「你说过 3+5=9」) T1/R 全过(含否定 + 正确值 8), B 臂 false_premise=False(且含 2 条空回复)。"),
        ("evidence_cmd", EV_ANALYZE),
        ("evidence_path", "eval/rover/r490/verdict-r490.json"),
        ("negative_control",
         "门关臂(R/B) 的 `tool_decl_gate` 打点全为 gate=0/reason=gate_off/declared=True ⇒ 门关时请求体与 R456..R489 逐字节同形(零回归, 单测 `SuppressedRequest_CarriesNoToolsKey`/`DeclaredRequest_CarriesToolsJsonVerbatim` 锁字节面); `ToolIntents` 与 `IntentRecognizer.KnownIntents` 的关系由单测锁死(防两套常量漂移); 跨轮只作参考**禁相减**(R489 旧产物另记)。**两处红**: (a) I5 剪裁打点红(Clone 未透传计数器, 已修+单测锁, 新 sha 8b4efbb7… 的真机复测待下轮); (b) T2 复现臂未跑(起手闸红 MemAvailable 2,615MB < 2,650MB, 按纪律让行)。"),
        ("covers", [
            "src/agent.modelqueue/ToolDeclGate.cs",
            "src/agent/modelqueue/ModelQueueAdapter.cs",
            "src/agent.modelqueue/ModelQueueRouter.cs",
            "src/agent.modelqueue/ActionLoop.cs",
            "src/agent.tests/R490ToolDeclGateTests.cs",
            "eval/rover/r490/analyze_r490.py",
            "eval/rover/r490/run_arm_real_r490.sh",
            "eval/rover/r490/verdict-r490.json",
        ]),
        ("owner_round", "R490"),
    ]),
    collections.OrderedDict([
        ("id", "r490.replay-trim-non-provider-bytes"),
        ("level", "L2"),
        ("capability",
         "**本地模板答复不进远端回放 (R438 user 侧的配对侧)**: 零远端调用轮(Skip)产出的本地模板答复 `收到。` **不是任何 provider 的产出**、从未发往任何 provider ⇒ 不得出现在后续请求前缀里(此前被逐字回放: R489 51 请求 / **100 条** assistant 模板串, 且 R489 的 Aroleb 臂为 0 ⇒ 只由本地闸引入)。实现 = `ModelQueueAdapter.ToQueuePrompt` 单点剪裁(只吃产品常量 `ModelQueueRouter.LocalSkipFallback`, 复述轮回放原文不受影响)。R490 三臂请求里模板串 **0**, 且 **user→user 相邻对 >0**(= 剪掉的证据, 防「本来就没有」的空判据陷阱)。"),
        ("evidence_cmd", EV_ANALYZE),
        ("evidence_path", "eval/rover/r490/verdict-r490.json"),
        ("negative_control",
         "非空判据 = user→user 相邻对(R489 同臂为 0、R490 >0 ⇒ 确曾存在模板串且被剪); 只剪**等于** `LocalSkipFallback` 的 assistant 文本 ⇒ 实质答复/复述回放原文不剪(单测 `LocalTemplateReply_IsTrimmedFromRemoteReplay` / `RepeatReplaySubstantiveReply_IsKept`); 计数器经 `ActionLoopRunner.Clone` 透传由单测 `ActionLoopClone_PropagatesGateFacts` 锁死。"),
        ("covers", [
            "src/agent/modelqueue/ModelQueueAdapter.cs",
            "src/agent.modelqueue/ActionLoop.cs",
            "src/agent.tests/R490ToolDeclGateTests.cs",
            "eval/rover/r490/analyze_r490.py",
            "eval/rover/r490/verdict-r490.json",
        ]),
        ("owner_round", "R490"),
    ]),
]

# ---- 形式门禁 (拒写即退, 禁半写) ----
errs = []
REQ = ("id", "level", "capability", "evidence_cmd", "evidence_path", "owner_round", "covers")
for n in NEW:
    for k in REQ:
        if not n.get(k):
            errs.append("%s: 缺字段 %s" % (n.get("id", "?"), k))
    if not str(n.get("id", "")).startswith("r490."):
        errs.append("%s: id 前缀非 r490." % n.get("id"))
    if n.get("level") not in ("L1", "L2", "L3", "L4"):
        errs.append("%s: level 非法 %r" % (n.get("id"), n.get("level")))
    if not os.path.exists(os.path.join(ROOT, n.get("evidence_path", ""))):
        errs.append("%s: evidence_path 不存在 %s" % (n.get("id"), n.get("evidence_path")))
    for c in n.get("covers", []):
        if not os.path.exists(os.path.join(ROOT, c)):
            errs.append("%s: covers 路径不存在 %s" % (n.get("id"), c))
raw = io.open(P, encoding="utf-8").read()
if not raw.endswith("\n"):
    errs.append("registry 缺尾换行 (SER_ASSERT 会拒写)")
if errs:
    print(json.dumps({"verdict": "REJECT", "errors": errs}, ensure_ascii=False, indent=1))
    sys.exit(2)

d = json.load(io.open(P, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
rows = d['rows']
ids = {r['id'] for r in rows}
added, replaced = [], []
for n in NEW:
    if n['id'] in ids:
        for i, r in enumerate(rows):
            if r['id'] == n['id']:
                rows[i] = n
        replaced.append(n['id'])
    else:
        rows.append(n)
        added.append(n['id'])
d['updated_round'] = 'R490'
# 台账原文缩进 = 1 空格, 重排会制造全文件 diff 噪声 ⇒ 必须保形写回 (尾换行保留)
io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
# 幂等自检: 立即读回, 逐 id 核字段
back = json.load(io.open(P, encoding="utf-8"))
got = {r['id']: r for r in back['rows'] if r['id'].startswith('r490.')}
ok = all(got.get(n['id'], {}).get('capability') == n['capability'] for n in NEW)
print(json.dumps({"verdict": "WRITTEN" if ok else "READBACK_MISMATCH", "added": added, "replaced": replaced,
                  "total_rows": len(back['rows']), "updated_round": back['updated_round'],
                  "readback_ok": ok}, ensure_ascii=False))
sys.exit(0 if ok else 3)
