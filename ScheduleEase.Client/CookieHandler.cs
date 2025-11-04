using Microsoft.AspNetCore.Components.WebAssembly.Http;

namespace ScheduleEase.Client;

// This class intercepts every outgoing HTTP request
public class CookieHandler : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        // This is the magic property that tells the browser's fetch API
        // to include credentials (cookies) for cross-origin requests.
        request.SetBrowserRequestCredentials(BrowserRequestCredentials.Include);

        return await base.SendAsync(request, cancellationToken);
    }
}