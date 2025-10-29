using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models;

public class AiAnalysisResult
{
    [JsonPropertyName("summary")]
    public string Summary { get; set; }

    [JsonPropertyName("events")]
    public List<ScheduledEvent> Events { get; set; }
}