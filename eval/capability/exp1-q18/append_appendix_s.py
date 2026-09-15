#!/usr/bin/env python3
"""把附录 S 追加进 EXP1 计划文档 (幂等: 已含 '## 附录 S' 则跳过)。"""
import pathlib

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
DOC = ROOT / "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md"
APP = ROOT / "eval/capability/exp1-q18/appendix_s.md"

doc = DOC.read_text(encoding="utf-8")
app = APP.read_text(encoding="utf-8")
if "## 附录 S" in doc:
    print("APPENDIX_S_ALREADY_PRESENT -> skip")
else:
    before = len(doc)
    DOC.write_text(doc.rstrip("\n") + "\n\n" + app.rstrip("\n") + "\n", encoding="utf-8")
    after = DOC.stat().st_size
    print("APPENDIX_S_APPENDED chars", before, "->", after)
    print("readback_has_appendix_S:", "## 附录 S" in DOC.read_text(encoding="utf-8"))
    print("readback_tail:", DOC.read_text(encoding="utf-8")[-90:].replace("\n", " | "))
