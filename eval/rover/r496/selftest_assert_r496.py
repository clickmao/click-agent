#!/usr/bin/env python3
# R496 判据器修订自检: 正控 (真挂载块) 必须命中; 负控 (工具面块头回显) 必须不命中。
# 用**真实夹具字节** (calls-Br496.jsonl 里 seq=25 的 tool 消息) 作负控输入 ⇒ 非人造样本。
import importlib.util, json, os, sys

D = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("af", os.path.join(D, "assert_face_r496.py"))
af = importlib.util.module_from_spec(spec); spec.loader.exec_module(af)

POS = {"seq": 1, "messages": [
    {"role": "system", "content": "你是一个智能助手。\n" + af.MOUNT_HEADER +
     "\nsession=abcdef12 reason=本地真值 site=n=<n> n=3 code=LCM-abc123def456\n最近决策: pass@t2 (12字)\n"}]}
NC_TOOL = {"seq": 2, "messages": [
    {"role": "tool", "content": '/home/agentuser/AgentFramework/src/agent.modelqueue/LocalDecisionLedger.cs:57:    public const string MountHeader = "' + af.MOUNT_HEADER + '";[核验✗ 越界路径, 已拒绝)]'}]}
NC_SYS_NOSTRUCT = {"seq": 3, "messages": [
    {"role": "system", "content": "说明: " + af.MOUNT_HEADER + " 这个块头是本地台账的标记 (无结构行)"}]}

cases = [("pc_true_mount", POS, (1, 1, 0)), ("nc_tool_echo", NC_TOOL, (0, 0, 1)), ("nc_sys_no_struct", NC_SYS_NOSTRUCT, (0, 0, 1))]
bad = 0
for name, row, want in cases:
    h, pairs, byp = af.mount_of(row)
    got = (h, len(pairs), byp)
    ok = (got == want)
    bad += 0 if ok else 1
    print("%-18s want=%s got=%s ok=%s pairs=%s" % (name, want, got, ok, pairs))

# 真实夹具回归: B 臂 34 条远端请求体 ⇒ 0 真挂载块, 5 条工具面回显
p = os.path.join(D, "calls-Br496.jsonl")
if os.path.exists(p):
    calls = [json.loads(l) for l in open(p, encoding="utf-8-sig") if l.strip()]
    agg = [af.mount_of(r) for r in calls]
    print("real_B: calls=%d true_mount=%d bypass_header=%d" % (
        len(calls), sum(1 for h, _, _ in agg if h), sum(1 for _, _, b in agg if b)))

# 隔离通道分类控制 (真实夹具字节): T1 的 seq=5 = 微步骤隔离问询 ⇒ is_isolated 必须 True
p2 = os.path.join(D, "calls-T1r496.jsonl")
if os.path.exists(p2):
    c1 = [json.loads(l) for l in open(p2, encoding="utf-8-sig") if l.strip()]
    seq5 = [x for x in c1 if x.get("seq") == 5]
    other = [x for x in c1 if x.get("seq") != 5]
    ok5 = bool(seq5) and af.is_isolated(seq5[0])
    ok_other = sum(1 for x in other if af.is_isolated(x))
    print("real_T1: seq5_isolated=%s 其余隔离条数=%d (期望 seq5 True / 其余 0)" % (ok5, ok_other))
    bad += 0 if (ok5 and ok_other == 0) else 1
print("selftest", "PASS" if bad == 0 else "FAIL")
sys.exit(0 if bad == 0 else 13)
