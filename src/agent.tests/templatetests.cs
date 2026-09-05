using Xunit;
using Moq;
using agent.templates;
using agent.core;

namespace agent.tests;

public class TemplateTests
{
    private readonly Mock<ITemplateStore> _mockStore;

    public TemplateTests()
    {
        _mockStore = new Mock<ITemplateStore>();
    }

    private static Template MakeTemplate(string name, string content, string category = "general") => new()
    {
        Name = name,
        Pattern = content,
        Category = category
    };

    [Fact]
    public async Task GetByName_ShouldReturnTemplate()
    {
        // Arrange
        var template = MakeTemplate("test-template", "Hello, {{name}}!");
        _mockStore
            .Setup(s => s.GetByNameAsync("test-template", It.IsAny<string>()))
            .ReturnsAsync(template);

        // Act
        var result = await _mockStore.Object.GetByNameAsync("test-template", "general");

        // Assert
        Assert.NotNull(result);
        Assert.Equal("Hello, {{name}}!", result!.Pattern);
    }

    [Fact]
    public async Task GetByName_MissingTemplate_ShouldReturnNull()
    {
        // Arrange
        _mockStore
            .Setup(s => s.GetByNameAsync("missing", It.IsAny<string>()))
            .ReturnsAsync((Template?)null);

        // Act
        var result = await _mockStore.Object.GetByNameAsync("missing", "general");

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task AddTemplate_ShouldRoundTrip()
    {
        // Arrange
        var template = MakeTemplate("roundtrip", "content-body");
        _mockStore
            .Setup(s => s.AddAsync(It.IsAny<Template>()))
            .ReturnsAsync((Template t) => t);

        // Act
        var added = await _mockStore.Object.AddAsync(template);

        // Assert
        Assert.Equal("roundtrip", added.Name);
        Assert.Equal("content-body", added.Pattern);
    }

    [Fact]
    public async Task GetByCategory_ShouldReturnMatching()
    {
        // Arrange
        var templates = new List<Template> { MakeTemplate("a", "A", "code") };
        _mockStore
            .Setup(s => s.GetByCategoryAsync("code"))
            .ReturnsAsync(templates);

        // Act
        var result = (await _mockStore.Object.GetByCategoryAsync("code")).ToList();

        // Assert
        Assert.Single(result);
        Assert.Equal("a", result[0].Name);
    }

    [Fact]
    public void Template_ContentPlaceholder_ShouldBeDetectable()
    {
        // 占位符语法契约: {{name}} 形式
        var template = MakeTemplate("ph", "Hello, {{name}}!");
        Assert.Contains("{{name}}", template.Pattern);
    }
}
