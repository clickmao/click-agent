"""tasksvc.model —— 模型/时间视图层 (仅标准库)。

本段职责 (第 2 段, 节点 n2):
  2) 时钟: 全局选项 --now <epoch 秒> 注入当前时间 (浮点或整数)。
     所有时间判定只准用该时钟, 禁止 sleep。
     未提供 --now 时必须回落到系统时钟 (time.time()), 不得报错、不得要求该选项必填。
  4) 视图: open = 未 done 且未过期; done = 已 done; expired = 已过期; all = 全部。
     过期优先于 done (互斥)。列表一律按 id 升序。

边界: 本模块只做「时钟 + 过期判定 + 视图过滤/排序」,
不解析命令行、不做 id 分配、不读写文件、不打印任何东西 (输出与退出码属 n3)。

运行自检:
    python3 -B -m tasksvc.model --selftest
自检为无头模式, 成功打印 "SELFTEST PASS N/N", 退出码 0; 失败退出码 1。
"""

from __future__ import annotations

import time

__all__ = [
    "Clock",
    "resolve_now",
    "is_expired",
    "classify",
    "in_view",
    "task_view",
    "visible_tasks",
    "select_tasks",
    "expired_ids",
    "VIEWS",
    "DEFAULT_VIEW",
]

# 合法视图名 (契约 4)。列表一律按 id 升序, 见 select_tasks。
VIEWS = ("open", "done", "expired", "all")

# list 的缺省视图 (契约 3: list [--status ...] 缺省 open)。
DEFAULT_VIEW = "open"


class Clock:
    """一次性解析的时钟: 注入值优先, 缺省回落系统时钟。

    - ``--now`` 提供时使用该固定值, 所有时间判定只读它 (禁止 sleep 等真实等待)。
    - ``--now`` 未提供时回落 ``time.time()`` 并**在构造时冻结**: 同一次命令执行内
      多次判定取到的是同一个 now, 避免命令行内部前后取值不一致。
    """

    __slots__ = ("_now", "is_injected")

    def __init__(self, now):
        # now 允许 int/float; None 表示未注入 -> 回落系统时钟。
        self.is_injected = now is not None
        self._now = float(time.time() if now is None else now)

    def now(self):
        """当前时间 (epoch 秒, float)。"""
        return self._now

    def __float__(self):
        return self._now

    def __repr__(self):
        return "Clock(now=%r, is_injected=%r)" % (self._now, self.is_injected)


def resolve_now(now=None):
    """全局选项 --now 的解析入口 -> float。

    - ``now is None`` -> ``time.time()`` (回落, 不报错, 不要求必填);
    - 否则原样转 float (int/float 皆可)。

    非法值 (非数字) 抛 ValueError, 由调用方 (cli 段) 映射为用法错。
    """
    if now is None:
        return float(time.time())
    if isinstance(now, bool):  # bool 是 int 子类, 显式排除, 避免 True 被当 1 秒
        raise ValueError("--now 必须是数字 (epoch 秒), 不接受布尔值")
    if not isinstance(now, (int, float)):
        raise ValueError("--now 必须是数字 (epoch 秒)")
    value = float(now)
    if value != value:  # NaN 自比较为假
        raise ValueError("--now 不能是 NaN")
    return value


def is_expired(task, now):
    """过期判定: now >= expires_at 即为已过期 (契约 5)。

    expires_at 为 None / 缺失 = 永不过期 -> False。
    非法 expires_at (缺失类型/非数字) 不在这里修复, 由存储层 schema 校验拦截。
    """
    expires_at = task.get("expires_at")
    if expires_at is None:
        return False
    return float(now) >= float(expires_at)


def classify(task, now):
    """把任务归入唯一视图: 'expired' | 'done' | 'open'。

    过期优先于 done (契约 4: 互斥) —— 已 done 但已过期仍归 expired。
    """
    if is_expired(task, now):
        return "expired"
    if bool(task.get("done")):
        return "done"
    return "open"


def in_view(task, now, view):
    """任务是否属于给定视图。view='all' 恒 True; 非法 view 抛 ValueError。"""
    if view not in VIEWS:
        raise ValueError("unknown view: %r" % (view,))
    if view == "all":
        return True
    return classify(task, now) == view


def task_view(task, now):
    """单个任务的视图归属 ('expired'|'done'|'open'), 供 stats 等使用。"""
    return classify(task, now)


def visible_tasks(tasks, now, view=DEFAULT_VIEW):
    """按视图过滤 + 按 id 升序排序。

    - expired: 已过期 (含已 done 但过期的), 仍存在于存储中;
    - all: 全部;
    - 排序键为 id (int), 与存储顺序无关。
    """
    if view not in VIEWS:
        raise ValueError("unknown view: %r" % (view,))
    selected = [t for t in tasks if in_view(t, now, view)]
    selected.sort(key=lambda t: int(t["id"]))
    return selected


def select_tasks(tasks, now, view=DEFAULT_VIEW):
    """``visible_tasks`` 的别名 (语义对等, 供 cli 段择一调用)。"""
    return visible_tasks(tasks, now, view)


def expired_ids(tasks, now):
    """全部已过期任务的 id (升序)。供 expire 子命令真删除 + 返回列表使用。"""
    ids = [int(t["id"]) for t in tasks if is_expired(t, now)]
    ids.sort()
    return ids


# --------------------------------------------------------------------------
# 无头自检: python3 -B -m tasksvc.model --selftest
# 覆盖: 时钟回落/注入/非必填、边界 now == expires_at、过期优先于 done、
#       四种视图、id 升序、无 ttl、非法视图负向控制。
# --------------------------------------------------------------------------
def _make(tid, done=False, expires_at=None):
    return {
        "id": tid,
        "text": "t%d" % tid,
        "done": bool(done),
        "created_at": 0.0,
        "expires_at": expires_at,
    }


def _selftest():
    cases = []

    def check(name, cond):
        cases.append((name, bool(cond)))

    # 1. --now 未提供 -> 回落系统时钟, 不报错, 是数字
    t0 = time.time()
    sys_now = resolve_now(None)
    check("clock fallback to time.time()", isinstance(sys_now, float) and sys_now >= t0 - 1.0)

    # 2. --now 注入 int / float 均生效
    check("clock injected int", resolve_now(1000) == 1000.0)
    check("clock injected float", resolve_now(1000.5) == 1000.5)

    # 3. 非法 --now -> ValueError (负向控制, cli 段据此判用法错)
    bad = 0
    for v in (True, "abc", None if False else object(), float("nan")):
        try:
            resolve_now(v)
        except ValueError:
            bad += 1
    check("clock rejects non-numeric --now (4/4)", bad == 4)

    # 4. Clock 冻结: 无注入时冻结系统时间, 两次 now() 相等
    c = Clock(None)
    check("Clock freezes default now", c.now() == c.now() and c.is_injected is False)
    check("Clock injected flag", Clock(5).now() == 5.0 and Clock(5).is_injected is True)

    now = 100.0
    no_ttl = _make(1, expires_at=None)
    future = _make(2, expires_at=100.1)
    boundary = _make(3, expires_at=100.0)      # now == expires_at -> 已过期
    past = _make(4, expires_at=99.999)
    done_open_future = _make(5, done=True, expires_at=100.1)
    done_expired = _make(6, done=True, expires_at=100.0)

    # 5. now >= expires_at 即过期; == 边界必须命中
    check("now >= expires_at strictly (==)", is_expired(boundary, now) is True)
    check("now < expires_at not expired", is_expired(future, now) is False)
    check("no ttl never expires", is_expired(no_ttl, now) is False)
    check("past expired", is_expired(past, now) is True)

    # 6. 过期优先于 done (互斥)
    check("expired beats done", classify(done_expired, now) == "expired")
    check("done but not expired -> done", classify(done_open_future, now) == "done")
    check("open classify", classify(no_ttl, now) == "open")

    tasks = [no_ttl, future, boundary, past, done_open_future, done_expired]

    # 7. 四种视图
    open_ids = [t["id"] for t in visible_tasks(tasks, now, "open")]
    done_ids = [t["id"] for t in visible_tasks(tasks, now, "done")]
    exp_ids = [t["id"] for t in visible_tasks(tasks, now, "expired")]
    all_ids = [t["id"] for t in visible_tasks(tasks, now, "all")]
    check("view open == [1,2]", open_ids == [1, 2])
    check("view done == [5]", done_ids == [5])
    check("view expired == [3,4,6]", exp_ids == [3, 4, 6])
    check("view all == 1..6", all_ids == [1, 2, 3, 4, 5, 6])
    check("views are mutually exclusive", set(open_ids) & set(done_ids) == set()
          and set(exp_ids) & set(done_ids) == set() and set(exp_ids) & set(open_ids) == set())

    # 8. 缺省视图 = open
    check("default view is open", [t["id"] for t in visible_tasks(tasks, now)] == open_ids)
    check("DEFAULT_VIEW == open", DEFAULT_VIEW == "open")

    # 9. 排序与输入顺序无关 (乱序输入仍按 id 升序)
    shuffled = [past, done_expired, future, no_ttl, boundary, done_open_future]
    check("sorted by id regardless of input order",
          [t["id"] for t in visible_tasks(shuffled, now, "all")] == [1, 2, 3, 4, 5, 6])

    # 10. expired_ids 供 expire 子命令使用
    check("expired_ids == [3,4,6]", expired_ids(tasks, now) == [3, 4, 6])

    # 11. 负向控制: 非法视图必须抛错, 不得静默当 all 处理
    raised = 0
    for v in ("bogus", "", "Open", None):
        try:
            visible_tasks(tasks, now, v)
        except ValueError:
            raised += 1
    check("invalid view rejected (4/4)", raised == 4)

    passed = sum(1 for _, ok in cases if ok)
    total = len(cases)
    for name, ok in cases:
        if not ok:
            print("FAIL: %s" % name)
    if passed == total:
        print("SELFTEST PASS %d/%d" % (passed, total))
        return 0
    print("SELFTEST FAIL %d/%d" % (passed, total))
    return 1


if __name__ == "__main__":  # pragma: no cover
    import sys

    if "--selftest" in sys.argv[1:]:
        sys.exit(_selftest())
    sys.stderr.write("usage: python3 -B -m tasksvc.model --selftest\n")
    sys.exit(2)
