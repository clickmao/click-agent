using System.Drawing;
using System.Text.Json;
using System.Windows.Forms;

namespace Samples.FrontendApi.WinForms;

/// <summary>
/// AgentFrontendApi v1 对接 DEMO (WinForms)。
///
/// 用途: ①演示外部前端如何经 TCP 行 JSON 消费完整 agent 管线;
///       ②原始协议日志面板用于**排查 agent 内部问题** (错误码 / 限流 busy / 鉴权静默断连)。
///
/// 对应 agent 侧启动:
///   cd src/agent.host && dotnet run -- --frontend-api 47810
///   (控制台会打印 AUTH token; 或先 export AGENTFRAMEWORK_FRONTEND_TOKEN=mytoken 固定)
/// 关闭鉴权 (仅本机调试):  export AGENTFRAMEWORK_FRONTEND_AUTH=0
///
/// 已知服务端行为 (实测):
///   - 鉴权失败 = 静默断连, 无任何响应 → 本演示在首个请求失败时提示"疑似 token 错误/鉴权失败"。
///   - 全局限流 10 req/s + 并发 4 (FrontendAccessControl) → 超限回 error.code="busy"。
///   - chat.send 直通 V2 管线, 单次耗时取决于模型 (可能数十秒), 故超时给 120s。
/// </summary>
public sealed class MainForm : Form
{
    private readonly TextBox _txtHost = new() { Text = "127.0.0.1", Width = 120 };
    private readonly TextBox _txtPort = new() { Text = "47810", Width = 60 };
    private readonly TextBox _txtToken = new() { Width = 220, PlaceholderText = "AUTH token (留空=未启用鉴权)" };
    private readonly Button _btnConnect = new() { Text = "连接", Width = 70 };
    private readonly Label _lblStatus = new() { Text = "未连接", AutoSize = true, ForeColor = Color.DimGray };

    private readonly TextBox _txtSend = new() { Multiline = true, Height = 80, Dock = DockStyle.Top };
    private readonly Button _btnSend = new() { Text = "发送 chat.send", Height = 30, Dock = DockStyle.Top };
    private readonly TextBox _txtReply = new() { Multiline = true, Dock = DockStyle.Fill, ReadOnly = true, ScrollBars = ScrollBars.Vertical };

    private readonly Button _btnSnapshot = new() { Text = "state.snapshot", Height = 28, Dock = DockStyle.Top };
    private readonly Button _btnHello = new() { Text = "state.hello", Height = 28, Dock = DockStyle.Top };
    private readonly Button _btnMetaInfo = new() { Text = "meta.info", Height = 28, Dock = DockStyle.Top };
    private readonly Button _btnPing = new() { Text = "meta.ping", Height = 28, Dock = DockStyle.Top };
    private readonly TextBox _txtState = new() { Multiline = true, Dock = DockStyle.Fill, ReadOnly = true, ScrollBars = ScrollBars.Both };

    private readonly ListBox _lstLog = new() { Dock = DockStyle.Fill, IntegralHeight = false };

    private FrontendApiClient _client;

    public MainForm()
    {
        Text = "click-agent FrontendApi v1 对接 DEMO (WinForms)";
        Width = 1080;
        Height = 720;
        StartPosition = FormStartPosition.CenterScreen;
        BuildUi();
    }

    private void BuildUi()
    {
        // ── 连接区 ──
        var top = new Panel { Dock = DockStyle.Top, Height = 36, Padding = new Padding(6) };
        var flow = new FlowLayoutPanel { Dock = DockStyle.Fill, WrapContents = false };
        flow.Controls.AddRange(new Control[]
        {
            new Label { Text = "Host", AutoSize = true, Padding = new Padding(0, 6, 0, 0) },
            _txtHost,
            new Label { Text = "Port", AutoSize = true, Padding = new Padding(0, 6, 0, 0) },
            _txtPort,
            new Label { Text = "Token", AutoSize = true, Padding = new Padding(0, 6, 0, 0) },
            _txtToken,
            _btnConnect,
            _lblStatus,
        });
        top.Controls.Add(flow);

        // ── 中部: 左=chat 右=state/meta ──
        var mid = new Panel { Dock = DockStyle.Fill };

        var left = new Panel { Dock = DockStyle.Left, Width = 560, Padding = new Padding(6) };
        var leftTitle = new Label { Text = "chat.send (直通 V2 管线)", Dock = DockStyle.Top, Height = 20, ForeColor = Color.DarkBlue };
        _btnSend.Dock = DockStyle.Top;
        _txtSend.Dock = DockStyle.Top;
        var replyTitle = new Label { Text = "回复", Dock = DockStyle.Top, Height = 18 };
        _txtReply.Dock = DockStyle.Fill;
        var leftInner = new Panel { Dock = DockStyle.Fill };
        leftInner.Controls.Add(_txtReply);
        left.Controls.Add(leftInner);
        left.Controls.Add(replyTitle);
        left.Controls.Add(_btnSend);
        left.Controls.Add(_txtSend);
        left.Controls.Add(leftTitle);

        var right = new Panel { Dock = DockStyle.Fill, Padding = new Padding(6) };
        var rightTitle = new Label { Text = "状态 / 元域 (Raw JSON)", Dock = DockStyle.Top, Height = 20, ForeColor = Color.DarkGreen };
        var btns = new Panel { Dock = DockStyle.Top, Height = 112 };
        btns.Controls.Add(_btnPing);
        btns.Controls.Add(_btnMetaInfo);
        btns.Controls.Add(_btnHello);
        btns.Controls.Add(_btnSnapshot);
        var rightInner = new Panel { Dock = DockStyle.Fill };
        rightInner.Controls.Add(_txtState);
        right.Controls.Add(rightInner);
        right.Controls.Add(btns);
        right.Controls.Add(rightTitle);

        var splitter = new Splitter { Dock = DockStyle.Left, Width = 4 };
        mid.Controls.Add(right);
        mid.Controls.Add(splitter);
        mid.Controls.Add(left);

        // ── 底部: 协议日志 ──
        var bottom = new Panel { Dock = DockStyle.Bottom, Height = 180, Padding = new Padding(6) };
        var logTitle = new Label { Text = "协议日志 (JSON Lines) — >> 发送 / << 接收", Dock = DockStyle.Top, Height = 18, ForeColor = Color.Purple };
        var logInner = new Panel { Dock = DockStyle.Fill };
        logInner.Controls.Add(_lstLog);
        bottom.Controls.Add(logInner);
        bottom.Controls.Add(logTitle);

        Controls.Add(mid);
        Controls.Add(bottom);
        Controls.Add(top);

        _btnConnect.Click += async (_, _) => await OnConnectClicked();
        _btnSend.Click += async (_, _) => await OnSendClicked();
        _btnSnapshot.Click += async (_, _) => await CallSimple("state.snapshot");
        _btnHello.Click += async (_, _) => await CallSimple("state.hello");
        _btnMetaInfo.Click += async (_, _) => await CallSimple("meta.info");
        _btnPing.Click += async (_, _) => await CallSimple("meta.ping");
    }

    private async Task OnConnectClicked()
    {
        if (_client != null && _client.IsConnected)
        {
            _client.Dispose();
            _client = null;
            SetStatus("已断开", Color.DimGray);
            _btnConnect.Text = "连接";
            return;
        }

        _btnConnect.Enabled = false;
        SetStatus("连接中…", Color.Orange);
        try
        {
            var c = new FrontendApiClient();
            c.LineReceived += (dir, line) => BeginInvoke(new Action(() => Log(dir, line)));
            c.EventReceived += (name, payload) => BeginInvoke(new Action(() => Log("<<", $"[event] {name} {payload}")));
            c.Disconnected += why => BeginInvoke(new Action(() =>
            {
                SetStatus(why, Color.DarkRed);
                _btnConnect.Text = "连接";
            }));

            if (!int.TryParse(_txtPort.Text, out var port))
            {
                SetStatus("端口非法", Color.DarkRed);
                return;
            }
            await c.ConnectAsync(_txtHost.Text.Trim(), port);
            if (!string.IsNullOrWhiteSpace(_txtToken.Text))
                await c.SendAuthAsync(_txtToken.Text.Trim());

            _client = c;
            SetStatus("已连接" + (string.IsNullOrWhiteSpace(_txtToken.Text) ? " (未发 auth 行)" : " (已发 auth)"), Color.DarkGreen);
            _btnConnect.Text = "断开";
        }
        catch (Exception ex)
        {
            SetStatus("连接失败: " + ex.Message, Color.DarkRed);
            _btnConnect.Enabled = true;
            return;
        }
        _btnConnect.Enabled = true;
    }

    private async Task OnSendClicked()
    {
        var text = _txtSend.Text.Trim();
        if (string.IsNullOrEmpty(text)) return;
        if (!EnsureConnected()) return;

        _btnSend.Enabled = false;
        _txtReply.Text = "等待回复 (chat.send 直通 V2 管线, 可能数十秒)…";
        try
        {
            var resp = await _client.SendAsync("chat.send", new { text });
            if (resp.Ok)
            {
                using var doc = JsonDocument.Parse(resp.Payload);
                var reply = doc.RootElement.TryGetProperty("reply", out var r) ? (r.GetString() ?? "") : "(无 reply 字段)";
                var ok = doc.RootElement.TryGetProperty("success", out var s) && s.GetBoolean();
                _txtReply.Text = $"[success={ok}]\r\n{reply}";
            }
            else
            {
                _txtReply.Text = $"错误: {resp.ErrorCode} — {resp.ErrorMessage}";
                if (resp.ErrorCode == "busy")
                    _txtReply.Text += "\r\n(服务端限流 10 req/s 或并发 4 超限 — 稍后重试)";
            }
        }
        catch (Exception ex)
        {
            _txtReply.Text = "失败: " + ex.Message + "\r\n(若连接立刻断开且首行发了 auth → 疑似 token 错误: 鉴权失败服务端静默断连)";
        }
        finally
        {
            _btnSend.Enabled = true;
        }
    }

    private async Task CallSimple(string api)
    {
        if (!EnsureConnected()) return;
        try
        {
            var resp = await _client.SendAsync(api, "{}", 15000);
            _txtState.Text = resp.Ok
                ? Prettify(resp.Payload)
                : $"错误: {resp.ErrorCode} — {resp.ErrorMessage}";
        }
        catch (Exception ex)
        {
            _txtState.Text = "失败: " + ex.Message +
                "\r\n(若此前刚发 auth 行且无响应 → 疑似鉴权失败, 服务端静默断连)";
        }
    }

    private bool EnsureConnected()
    {
        if (_client != null && _client.IsConnected) return true;
        MessageBox.Show(this, "请先连接 agent (启动: dotnet run -- --frontend-api 47810)", "未连接",
            MessageBoxButtons.OK, MessageBoxIcon.Information);
        return false;
    }

    private void SetStatus(string text, Color color)
    {
        _lblStatus.Text = text;
        _lblStatus.ForeColor = color;
    }

    private void Log(string dir, string line)
    {
        if (_lstLog.Items.Count > 500) _lstLog.Items.RemoveAt(0);
        var trimmed = line.Length > 400 ? line.Substring(0, 400) + "…" : line;
        _lstLog.Items.Add($"{DateTime.Now:HH:mm:ss} {dir} {trimmed}");
        _lstLog.TopIndex = _lstLog.Items.Count - 1;
    }

    private static string Prettify(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            return JsonSerializer.Serialize(doc.RootElement, new JsonSerializerOptions { WriteIndented = true });
        }
        catch { return json; }
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        _client?.Dispose();
        base.OnFormClosing(e);
    }
}
