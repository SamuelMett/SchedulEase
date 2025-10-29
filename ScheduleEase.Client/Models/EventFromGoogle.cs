using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models;

// Model for READING events from Google (for the scheduler)
public class EventFromGoogle
{
    [JsonPropertyName("id")]
    public string Id { get; set; }

    [JsonPropertyName("title")]
    public string Title { get; set; }

    [JsonPropertyName("start")]
    public string Start { get; set; } // Keep as string for RadzenScheduler

    [JsonPropertyName("end")]
    public string End { get; set; } // Keep as string for RadzenScheduler
}