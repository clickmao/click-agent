#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R517: 生成 3 节点串行计划 (无本地节点, 适配 R516 产物证据机制) + 写范围文件。"""
import json, os, re

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r517")
os.makedirs(OUT, exist_ok=True)
ts = json.load(open(os.path.join(REPO, "eval/rover/r513/taskset-r513.json"), encoding="utf-8"))
prompt = next(t for t in ts["tasks"] if t["tid"] == "p4")["prompt"]
flat = " ".join(prompt.split())
parts = re.split(r"(?=(?:\s|^)\d{1,2}[)）.、])", flat)
head = parts[0].strip()
rules = {}
for p in parts[1:]:
    m = re.match(r"\s*(\d{1,2})[)）.、]\s*(.*)", p, re.S)
    if m:
        rules[int(m.group(1))] = m.group(2).strip()

def rules_of(*ids):
    return " ".join("%d) %s" % (i, rules[i]) for i in sorted(ids) if i in rules)

scope = ("硬性文件范围: {files}。tasksvc/ 下**其他文件由其他节点负责** —— 禁止创建/修改/删除它们; "
         "需要接口定义时**只读**已存在的文件; 不要运行整包端到端测试; 不要写 README/说明文件。")

nodes = [
    ("n1", "", "tasksvc/__init__.py, tasksvc/store.py",
     "长任务 p4 第 1 段。工作区根下创建 tasksvc 包。" + scope.format(files="tasksvc/__init__.py 与 tasksvc/store.py")
     + " 本段职责 = 存储层: " + rules_of(1, 9, 10) + " 契约总述: " + head),
    ("n2", "n1", "tasksvc/model.py",
     "长任务 p4 第 2 段。tasksvc 包已存在。" + scope.format(files="tasksvc/model.py")
     + " 本段职责 = 数据模型与时间/视图: " + rules_of(2, 4) + " 契约总述: " + head),
    ("n3", "n2", "tasksvc/cli.py",
     "长任务 p4 第 3 段 (整合段)。tasksvc 包已存在。" + scope.format(files="tasksvc/cli.py")
     + " 本段职责 = 命令入口: " + rules_of(3, 5, 6, 7, 8)
     + " 必须 import 已存在的 tasksvc/store.py 与 tasksvc/model.py, 不得重写它们。契约总述: " + head),
]
lines = ["# R517 计划 v3 (3 节点串行; 无本地节点 —— 适配 R516『节点成功必须绑产物证据』)",
         "# id | 依赖 | 位置 | 执行器 | 文本"]
sc = ["# R517 写范围声明 (R516 NodeScopeFile DSL): nodeId | 路径[,路径]  —— 每节点单行, 逗号分隔"]
for nid, dep, files, text in nodes:
    lines.append(" | ".join([nid, dep, "remote", "", text]))
    sc.append("%s | %s" % (nid, ", ".join(x.strip() for x in files.split(","))))
open(os.path.join(OUT, "plan-p4-v3.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
open(os.path.join(OUT, "scope-p4.txt"), "w", encoding="utf-8").write("\n".join(sc) + "\n")
print("PLAN_SHA12", __import__("hashlib").sha256(open(os.path.join(OUT, "plan-p4-v3.txt"), "rb").read()).hexdigest()[:12])
print("PROMPT_SHA12", __import__("hashlib").sha256(prompt.encode()).hexdigest()[:12])
print("nodes", len(nodes))
