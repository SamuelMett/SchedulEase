using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models;

public class CalendarSubscription
{
    [JsonPropertyName("url")]
    public string Url { get; set; }
}