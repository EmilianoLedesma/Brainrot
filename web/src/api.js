const BASE = import.meta.env.VITE_API_URL;
const KEY = import.meta.env.VITE_API_KEY;

export async function api(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-API-Key": KEY, ...options.headers },
  });
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  return res.json();
}
