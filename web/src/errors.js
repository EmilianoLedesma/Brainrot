// Diagnostic text stays in API responses for DevTools. Only approved copy is
// rendered, including for unknown failures; never echo an upstream error string.
export function userError(error, copy, stage) {
  if (!error) return null;
  if (error.status === 409) return stage === "retry" ? copy.retryUnavailable : copy.publishing;
  if (error.status === 404) return copy.missing;
  if (error.status === 401 || error.status === 403) return copy.access;
  if (error.status === 422) return copy.input;
  if (error.status >= 500) return copy.connection;

  const detail = typeof error === "string" ? error : error.message || "";
  if (stage === "publish") return copy.publishingFailed;
  if (stage === "tts" || /WSServerHandshakeError|speech\.platform|edge.?tts|NoAudioReceived/i.test(detail)) return copy.narration;
  if (stage === "background" || /background[_ ]?clips?|missing background/i.test(detail)) return copy.background;
  if (/timeout|timed out/i.test(detail) || error.name === "TimeoutError") return copy.timeout;
  if (/CLI missing|local model CLI exited|subscription login|usage limits|rate.?limit/i.test(detail)) return copy.model;
  if (/connection|network|fetch|ReadError|ConnectError/i.test(detail)) return copy.connection;
  if (stage === "render") return copy.render;
  if (stage === "download" || stage === "transcribe") return copy.source;
  return copy.failed;
}
