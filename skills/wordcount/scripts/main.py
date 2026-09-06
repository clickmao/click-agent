#!/usr/bin/env python3
import json, sys
# @cmd wordcount text=<urlencoded> — 入参经 SkillScriptRunner 注入 argv 或环境
text = sys.argv[1] if len(sys.argv) > 1 else ""
if not text:
    text = sys.stdin.read()
chars = len([c for c in text if not c.isspace()])
words = len(text.split())
print(json.dumps({"skill": "wordcount", "chars": chars, "words": words}, ensure_ascii=False))
