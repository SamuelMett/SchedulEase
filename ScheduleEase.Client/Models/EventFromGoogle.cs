using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models;

// Model for READING events from Google (for the scheduler)
public class EventFromGoogle
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public DateTime Start { get; set; }   // ✅ Must be DateTime
    public DateTime End { get; set; }     // ✅ Must be DateTime
}