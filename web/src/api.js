const BASE = import.meta.env.VITE_API_URL;
const KEY = import.meta.env.VITE_API_KEY;

export async function api(path, options = {}) {
  const { timeoutMs = 15000, ...requestOptions } = options;
  // Each poll gets its own deadline. A stalled fetch must not stop later polls.
  const signal = AbortSignal.any([AbortSignal.timeout(timeoutMs), ...(requestOptions.signal ? [requestOptions.signal] : [])]);
  const res = await fetch(BASE + path, {
    ...requestOptions, signal,
    headers: { "Content-Type": "application/json", "X-API-Key": KEY, ...requestOptions.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body || res.statusText;
    try { message = JSON.parse(body).detail || message; } catch { /* plain-text errors */ }
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }
  return res.status === 204 ? null : res.json();
}
