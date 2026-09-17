using System.Text;
using System.Text.Json;

namespace agent.frontendapi;


/// <summary>menu 问询选项 (前端可直接渲染为菜单项)。</summary>
public sealed record AskOption(string Value, string Label, bool Recommended);
