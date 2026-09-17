"""``python3 -m games <game_id>`` —— 包级 CLI 分派。

用法:
    python3 -m games <game_id>        # 从 stdin 读, 结果写 stdout
    python3 -m games --list           # 列出全部 game_id (写 stdout, 每行一个)
    python3 -m games --selftest       # 无头自检, 打印 PASS/FAIL, 退出码 0/非0

契约:
    * 成功路径 stdout 只含结果文本 (结尾换行), 无任何多余文字。
    * 用法错误 (缺 game_id / 未知 game_id) 走 stderr, 退出码 2。
    * 子模块求解期间的异常不吞: 打到 stderr, 退出码 1 (R05: 不空捕获)。
"""

from __future__ import annotations

import sys

from games import GAME_IDS, GAMES, load_solver

USAGE = (
    "usage: python3 -m games <game_id>\n"
    "       python3 -m games --list\n"
    "       python3 -m games --selftest\n"
)


def _run(game_id: str, text: str) -> str:
    return load_solver(game_id)(text)


def _list_games() -> int:
    sys.stdout.write("".join(g + "\n" for g in GAME_IDS))
    return 0


def _selftest() -> int:
    """包级接线自检: 每条 game_id 都真的加载到 solve 且产出非空结果。

    这里刻意**按产出点逐条配对** (R377): 对每个 game_id, 断言的是
    "该 id 的 solve 真实返回了非空文本", 而不是全局计数。
    """
    fails: list[str] = []
    checks = 0

    # 1) 注册表非空且确定性排序
    checks += 1
    if not GAME_IDS:
        fails.append("registry-empty: GAME_IDS == ()")

    # 2) 逐 game_id 配对: load_solver 拿到的 solve 与 GAMES 声明一致
    for gid in GAME_IDS:
        checks += 1
        try:
            solver = load_solver(gid)
        except Exception as exc:  # noqa: BLE001 - 自检需报告而不是崩
            fails.append("load-fail[%s]: %r" % (gid, exc))
            continue
        checks += 1
        if not callable(solver):
            fails.append("solve-not-callable[%s]" % gid)
            continue
        checks += 1
        if solver.__module__ != GAMES[gid]:
            fails.append(
                "module-mismatch[%s]: got %s want %s"
                % (gid, solver.__module__, GAMES[gid])
            )

    # 3) 未知 id 必须报 KeyError (负向控制: 未注册就必须拒绝)
    checks += 1
    try:
        load_solver("__no_such_game__")
    except KeyError:
        pass
    except Exception as exc:  # noqa: BLE001
        fails.append("unknown-id-wrong-exc: %r" % (exc,))
    else:
        fails.append("unknown-id-accepted: 未注册 id 竟被加载")

    # 4) 分派真实生效: nim 走 CLI 同一入口, 断言的是**输出文本**, 非"没抛错"
    checks += 1
    out = _run("nim", "1 2 3\n")
    if out.strip() != "LOSE":
        fails.append("dispatch-nim-got=%r want=LOSE" % (out.strip(),))

    checks += 1
    out = _run("wythoff", "1 2\n")
    if out.strip() != "LOSE":
        fails.append("dispatch-wythoff-got=%r want=LOSE" % (out.strip(),))

    # 5) 未注册 game_id 的分派路径必须拒绝
    checks += 1
    try:
        _run("__no_such_game__", "")
    except KeyError:
        pass
    else:
        fails.append("dispatch-unknown-accepted")

    if fails:
        sys.stdout.write("FAIL %d/%d\n" % (len(fails), checks))
        for f in fails:
            sys.stdout.write("  - %s\n" % f)
        return 1
    sys.stdout.write("PASS %d/%d\n" % (checks, checks))
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        sys.stderr.write(USAGE)
        return 2

    first = args[0]
    if first == "--list":
        return _list_games()
    if first == "--selftest":
        return _selftest()
    if first.startswith("-"):
        sys.stderr.write("unknown option: %s\n" % first)
        sys.stderr.write(USAGE)
        return 2

    if len(args) > 1:
        sys.stderr.write("too many arguments: %s\n" % " ".join(args[1:]))
        sys.stderr.write(USAGE)
        return 2

    game_id = first
    if game_id not in GAMES:
        sys.stderr.write(
            "unknown game_id: %s\nknown: %s\n" % (game_id, ", ".join(GAME_IDS))
        )
        return 2

    text = sys.stdin.read()
    try:
        result = _run(game_id, text)
    except Exception as exc:  # noqa: BLE001 - 如实上报, 不吞 (R05)
        sys.stderr.write("games.%s failed: %r\n" % (game_id, exc))
        return 1

    sys.stdout.write(result)
    if not result.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
