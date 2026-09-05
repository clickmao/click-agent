using Microsoft.Extensions.Logging;

namespace agent.userinteraction;

/// <summary>
/// 控制台用户交互实现（实现 IUserInteraction 接口）
/// </summary>
public class ConsoleUserInteraction : IUserInteraction
{
    private readonly ILogger<ConsoleUserInteraction> _logger;

    public ConsoleUserInteraction(ILogger<ConsoleUserInteraction> logger)
    {
        _logger = logger;
    }

    public Task<ConfirmationResult> RequestConfirmationAsync(
        UserConfirmRequest request,
        CancellationToken ct = default)
    {
        Console.WriteLine($"\n{request.Message}");

        if (!string.IsNullOrEmpty(request.Details))
        {
            Console.WriteLine(request.Details);
        }

        // 显示选项
        for (int i = 0; i < request.Options.Count; i++)
        {
            var option = request.Options[i];
            var marker = option.IsRecommended ? " (推荐)" : "";
            Console.WriteLine($"  {i + 1}. [{option.Label}]{marker} {option.Description}");
        }

        Console.Write("请选择选项序号: ");
        var input = Console.ReadLine()?.Trim();

        var result = new ConfirmationResult
        {
            RequestId = request.Id,
            UserInput = input,
            Timestamp = DateTime.UtcNow
        };

        // 解析序号选择
        if (int.TryParse(input, out var index) && index >= 1 && index <= request.Options.Count)
        {
            var selected = request.Options[index - 1];
            result.SelectedOptionId = selected.Id;
            result.Approved = selected.IsRecommended || request.Options.IndexOf(selected) == 0;
        }
        else
        {
            // 按标签匹配
            var matched = request.Options.FirstOrDefault(o =>
                string.Equals(o.Label, input, StringComparison.OrdinalIgnoreCase));
            if (matched != null)
            {
                result.SelectedOptionId = matched.Id;
                result.Approved = matched.IsRecommended;
            }
        }

        return Task.FromResult(result);
    }

    public Task ShowProgressAsync(ProgressInfo info)
    {
        var percent = info.Progress * 100;
        var bar = new string('#', (int)(percent / 5));
        var remaining = new string('.', 20 - bar.Length);

        Console.Write($"\r[{bar}{remaining}] {percent:F0}% - {info.CurrentStep}");

        if (percent >= 100)
        {
            Console.WriteLine();
        }

        return Task.CompletedTask;
    }

    public Task ShowMessageAsync(MessageInfo info)
    {
        var prefix = info.Type switch
        {
            MessageInfoType.Info => "[INFO]",
            MessageInfoType.Warning => "[WARN]",
            MessageInfoType.Error => "[ERROR]",
            MessageInfoType.Success => "[OK]",
            MessageInfoType.Debug => "[DEBUG]",
            _ => "[MSG]"
        };

        var color = info.Type switch
        {
            MessageInfoType.Warning => ConsoleColor.Yellow,
            MessageInfoType.Error => ConsoleColor.Red,
            MessageInfoType.Success => ConsoleColor.Green,
            MessageInfoType.Debug => ConsoleColor.Gray,
            _ => ConsoleColor.White
        };

        var originalColor = Console.ForegroundColor;
        Console.ForegroundColor = color;

        Console.WriteLine($"{prefix} {info.Content}");

        Console.ForegroundColor = originalColor;

        return Task.CompletedTask;
    }

    public async Task<string> GetUserInputAsync(InputRequest request, CancellationToken ct = default)
    {
        if (!string.IsNullOrEmpty(request.Prompt))
        {
            Console.WriteLine(request.Prompt);
        }

        if (!string.IsNullOrEmpty(request.DefaultValue))
        {
            Console.Write($"(默认: {request.DefaultValue}) ");
        }

        var input = Console.ReadLine();

        if (string.IsNullOrEmpty(input) && !string.IsNullOrEmpty(request.DefaultValue))
        {
            input = request.DefaultValue;
        }

        return await Task.FromResult(input ?? string.Empty);
    }

    public Task ShowSearchResultsAsync(IEnumerable<search.SearchResult> results)
    {
        Console.WriteLine("\n=== Search Results ===\n");

        var resultList = results.Take(10).ToList();

        for (int i = 0; i < resultList.Count; i++)
        {
            var result = resultList[i];
            Console.WriteLine($"{i + 1}. {result.Title}");
            Console.WriteLine($"   {result.Snippet}");
            Console.WriteLine();
        }

        return Task.CompletedTask;
    }

    public Task ShowTemplateListAsync(IEnumerable<templates.Template> templates)
    {
        Console.WriteLine("\n=== Available Templates ===\n");

        foreach (var template in templates)
        {
            Console.WriteLine($"- {template.Name}: {template.Description}");
        }

        return Task.CompletedTask;
    }
}
