using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using agent.core;
using agent.memory;
using agent.templates;
using agent.search;
using agent.session;
using agent.pipeline;
using agent.tokencompression;
using agent.context;
using agent.rag;
using agent.datastore;
using agent.codegen;
using agent.workspace;
using agent.vectormemory;
using agent.recovery;
using agent.keywordannotation;
using agent.tendency;

namespace agent;


/// <summary>
/// 主Agent实现
/// </summary>
public class MainAgent : AgentBase
{
    public MainAgent(
        ILogger<MainAgent> logger,
        IEnumerable<IMessageHandler> handlers) : base(logger, handlers)
    {
        Name = "MainAgent";
    }
    
    protected override Task<AgentResponse> OnProcessAsync(Message message, CancellationToken ct)
    {
        // 主Agent处理逻辑
        var response = new AgentResponse
        {
            Content = $"Processed: {message.Content}",
            Success = true,
            Type = MessageType.Text
        };
        
        return Task.FromResult(response);
    }
}
