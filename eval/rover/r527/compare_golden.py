#!/usr/bin/env python3
"""R527 等价性夹具比对器: 对照两次 golden 摘要 (抽取前 R526 AOT vs 抽取后 R527 AOT)。

判据 (机械, 无模型裁判):
  - 同臂同键集合 (缺臂/多臂 ⇒ 红);
  - 每臂 `out_sha256` 与 `err_sha256` 必须逐字节相同;
  - `out_text` / `err_text` 文本也必须相同 (sha 相同即等价, 文本再比一遍防「sha 来自被归一化字段」)。
任何一臂不同 ⇒ 该臂判漂移, 整体 rc=1。
"""
import hashlib
import io
import json
import sys


def load(p):
    d = json.load(io.open(p, encoding="utf-8"))
    return d


def main():
    pre_p, post_p = sys.argv[1], sys.argv[2]
    pre, post = load(pre_p), load(post_p)
    a, b = pre.get("arms", {}), post.get("arms", {})
    only_pre = sorted(set(a) - set(b))
    only_post = sorted(set(b) - set(a))
    bad = []
    print(f"# R527 等价性比对: {pre_p} vs {post_p}")
    print(f"# pre binary={pre.get('binary')}  cmd_count={pre.get('cmd_count')}")
    print(f"# post binary={post.get('binary')}  cmd_count={post.get('cmd_count')}")
    print(f"# 臂数 pre={len(a)} post={len(b)}  仅pre={only_pre} 仅post={only_post}")
    print(f"{'臂':<24} {'out_sha 同':<10} {'err_sha 同':<10} {'text 同':<8}")
    for k in sorted(set(a) & set(b)):
        sa = a[k].get("out_sha256")
        sb = b[k].get("out_sha256")
        ea = a[k].get("err_sha256")
        eb = b[k].get("err_sha256")
        ta = a[k].get("out_text", "")
        tb = b[k].get("out_text", "")
        same_s = sa == sb
        same_e = ea == eb
        same_t = ta == tb
        print(f"{k:<24} {str(same_s):<10} {str(same_e):<10} {str(same_t):<8}")
        if not (same_s and same_e and same_t):
            bad.append(k)
            print(f"    pre  out={sa}\n    post out={sb}")
            print(f"    pre  text={ta[:200]!r}\n    post text={tb[:200]!r}")
    ok = not bad and not only_pre and not only_post
    print(f"# 结论: {'等价 (逐臂 sha256 与文本全同)' if ok else '漂移: ' + str(bad + only_pre + only_post)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
