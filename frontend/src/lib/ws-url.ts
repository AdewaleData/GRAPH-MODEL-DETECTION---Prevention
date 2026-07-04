/** Convert HTTP(S) API URL to WebSocket URL. */
export function toWsUrl(httpUrl: string): string {
  return httpUrl.replace(/^https:\/\//i, "wss://").replace(/^http:\/\//i, "ws://");
}
