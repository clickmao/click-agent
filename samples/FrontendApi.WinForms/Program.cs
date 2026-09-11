using System.Windows.Forms;

namespace Samples.FrontendApi.WinForms;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        // 显式初始化 (不用 ApplicationConfiguration.Initialize() — 该 API 由 SDK 自动生成, 此处避免额外生成依赖)
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new MainForm());
    }
}
