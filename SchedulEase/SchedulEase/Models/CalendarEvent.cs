namespace SchedulEase.Models;

public enum CalendarEventType { Assignment, Exam, Lecture, Deadline }

public class CalendarEvent
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Title { get; set; } = string.Empty;
    public DateOnly Date { get; set; }
    public string? Time { get; set; }
    public string? Description { get; set; }
    public double? Confidence { get; set; }
    public CalendarEventType Type { get; set; }
}