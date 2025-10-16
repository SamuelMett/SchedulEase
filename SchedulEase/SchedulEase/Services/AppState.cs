using SchedulEase.Models;

namespace SchedulEase.Services;

public class AppState
{
    public List<CalendarEvent> ExtractedEvents { get; private set; } = new();
    public List<CalendarEvent> CanvasEvents { get; private set; } = new();

    public List<CalendarEvent> AllEvents => ExtractedEvents.Concat(CanvasEvents).ToList();

    public void AddExtractedEvents(IEnumerable<CalendarEvent> events)
    {
        ExtractedEvents.AddRange(events);
        NotifyStateChanged();
    }

    public void AddCanvasEvents(IEnumerable<CalendarEvent> events)
    {
        CanvasEvents.AddRange(events);
        NotifyStateChanged();
    }

    public void UpdateExtractedEvents(List<CalendarEvent> events)
    {
        ExtractedEvents = events;
        NotifyStateChanged();
    }

    public void Reset()
    {
        ExtractedEvents.Clear();
        CanvasEvents.Clear();
        NotifyStateChanged();
    }

    public event Action? OnChange;

    private void NotifyStateChanged() => OnChange?.Invoke();
}