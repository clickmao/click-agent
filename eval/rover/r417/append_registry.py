import json
import pathlib

P = pathlib.Path("/home/agentuser/AgentFramework/docs/verification-registry.json")
raw = P.read_text(encoding="utf-8")
d = json.loads(raw)
assert json.dumps(d, indent=2, ensure_ascii=False) + "\n" == raw, "roundtrip 校验失败: 禁止改写"

row = {
    "id": "r417.probe-anti-saturation",
    "level": "L4",
    "evidence_cmd": ("bash eval/rover/r417/run1_same_seed.sh && bash eval/rover/r417/run2_discrimination.sh "
                     "&& bash eval/rover/r417/run3_json.sh && python3 scripts/dev_return_digest.py"),
    "evidence_path": "data/probe/probe-r417-new-oracle.json; data/probe/probe-r417-mut-topodfs.json; data/probe/probe-r417-mut-vmnoerr.json; data/probe/probe-r417-json-oracle.json; data/probe/probe-r417-json-mut.json; data/probe/probe-r417-hard-agent.json; data/probe/probe-r417-json-agent.json",
    "negative_control": ("三族**族专属缺陷注入**（`--solver mutation:<名>`，注入源 = 正确参考解的结构性改动）："
                         "`topo_dfs`（DFS 序代替字典序最小）用例级 24/52、整题全对 **0/4**；"
                         "`vm_noerr`（去掉栈/跳转/步数错误语义）用例级 29/48、整题全对 **0/4**（timeout 2/runtime_error 2~17）；"
                         "`json_loose`（`json` 模块套用）用例级 54/72=0.75、整题全对 **0/4**。"
                         "正控成对：`oracle` 对同族同 seed 必须满分（49/49、36/36、整题全对 4/4 与 2/2）。"
                         "另：`json_mini` 每题**强制注入 1 条** `tight_gen` 用例（合 JSON 但不合本规格：低码点 uXXXX / 浮点 / NaN / 裸 TAB）"
                         "⇒ 通用 JSON 库套用式解法**确定性**拿不到整题全对，而非靠概率。"),
    "capability": ("探针反饱和（质量度量前置）：原程序 7 族对当前链已**饱和**（agent 与 oracle 同为整题全对 100%，"
                   "seed 20260913 同题复跑逐族一致）⇒ 天花板效应，不能度量质量。本轮新增 3 族 "
                   "`topo_min`（字典序最小拓扑序/环⇒-1）、`vm_run`（微型栈机与 ERR 语义）、`json_mini`（严格 JSON 规范化与非法输入ERR），"
                   "每族 ref/check **两条独立实现**双路径验算（本轮 1422 例分歧 0，不一致即拒发题），"
                   "并给出族级缺陷注入负控 + 正控成对；真机（AOT agenthost）读数为 "
                   "`topo_min`+`vm_run` 74/74 与 6/6 整题全对（**仍饱和**，如实登记）、`json_mini` 见 digest §3。"
                   "**等级依据 = 运行期行为 + 成对正负控**，不是 AOT 编译校验。"),
    "covers": [
        "eval/probe/tasks.py",
        "eval/probe/run_probe.py",
        "eval/probe/README.md",
        "scripts/dev_return_digest.py",
        "eval/rover/r417/run1_same_seed.sh",
        "eval/rover/r417/run2_discrimination.sh",
        "eval/rover/r417/run3_json.sh",
        "docs/plans/v0.38.0-r417-probe-anti-saturation.md",
    ],
    "owner_round": "R417",
}

ids = [r.get("id") for r in d["rows"]]
if row["id"] in ids:
    d["rows"][ids.index(row["id"])] = row
else:
    d["rows"].append(row)
d["updated_round"] = "R417"

out = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
P.write_text(out, encoding="utf-8")
chk = json.loads(P.read_text(encoding="utf-8"))
print("rows=%d updated=%s last=%s" % (len(chk["rows"]), chk["updated_round"], chk["rows"][-1]["id"]))
for k in sorted(row):
    v = row[k]
    print(" ", k, "=", (v if not isinstance(v, str) else v[:70]))
