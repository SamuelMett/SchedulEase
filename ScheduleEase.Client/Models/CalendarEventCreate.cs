using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models;

// Model for CREATING or UPDATING an event
public class CalendarEventCreate
{
    [JsonPropertyName("title")]
    public string Title { get; set; }

    [JsonPropertyName("start")]
    public DateTime Start { get; set; }

    [JsonPropertyName("end")]
    public DateTime End { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }
}