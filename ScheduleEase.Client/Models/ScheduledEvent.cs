using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models;

// This is a single event extracted by the AI
public class ScheduledEvent
{
    [JsonPropertyName("title")]
    public string Title { get; set; }

    [JsonPropertyName("start_date")]
    public string StartDate { get; set; }

    [JsonPropertyName("end_date")]
    public string? EndDate { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }
}