using System;
using System.Collections.Generic;
using System.Globalization;
using System.Numerics;

namespace agent.rover.formal;


/// <summary>受限形式语言 (可判定片段) 的公式与解析器。
/// 语法: expr := or 或 := and ('||' and)* 合 := unary ('&amp;&amp;' unary)* 一元 := '!' 一元 | '(' expr ')' | 比较
/// 比较 := 线性 (cmp) 线性，cmp ∈ &lt;= &gt;= &lt; &gt; == !=；线性 := (±项)(±项)*，项 := 数字 | 变量 | 数字*变量。
/// 刻意不支持除法/非线性/量词 ⇒ 判定器可做**精确整数**推理, 且永不说假 Proved。</summary>
public abstract class F
{
    public sealed class Atom : F { public readonly Constraint C; public Atom(Constraint c) { C = c; } }
    public sealed class And : F { public readonly List<F> Items = new(); }
    public sealed class Or : F { public readonly List<F> Items = new(); }
    public sealed class True : F { }
    public sealed class False : F { }
}
