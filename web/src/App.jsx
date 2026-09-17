import React, { useCallback, useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL;
const KEY = import.meta.env.VITE_API_KEY;

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-API-Key": KEY, ...options.headers },
  });
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  return res.json();
}

/** Re-fetch on an interval. Supabase Realtime would need SELECT policies for `anon`,
 *  and the anon key is public, so the job list polls through the API instead. */
function usePoll(path, intervalMs) {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  const refresh = useCallback(() => {
    api(path).then(
      (d) => {
        setData(d);
        setError(null);
      },
      (e) => setError(e.message),
    );
  }, [path]);

  useEffect(() => {
    refresh();
    if (!intervalMs) return;
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [refresh, intervalMs]);

  return { data, error, refresh };
}

function Trigger() {
  const [kind, setKind] = useState("brainrot");
  const [value, setValue] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setResult(null);
    const body = kind === "brainrot" ? { kind, topic: value } : { kind, youtube_url: value };
    try {
      const { id } = await api("/jobs", { method: "POST", body: JSON.stringify(body) });
      setResult({ ok: true, text: `queued job ${id}` });
      setValue("");
    } catch (e) {
      setResult({ ok: false, text: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <label>
        Kind
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="brainrot">brainrot — from a topic</option>
          <option value="repurpose">repurpose — from a YouTube link</option>
        </select>
      </label>
      <label>
        {kind === "brainrot" ? "Topic" : "YouTube URL"}
        <input
          required
          value={value}
          onChange={(e) => setValue(e.target.value)}
          type={kind === "brainrot" ? "text" : "url"}
          placeholder={kind === "brainrot" ? "roman empire facts" : "https://youtube.com/watch?v=..."}
        />
      </label>
      <button disabled={busy}>{busy ? "submitting..." : "Create job"}</button>
      {result && <p className={result.ok ? "muted" : "error"}>{result.text}</p>}
    </form>
  );
}

function label(job) {
  return job.params?.topic || job.params?.youtube_url || "—";
}

function Jobs() {
  const { data, error } = usePoll("/jobs", 2000);

  if (error) return <p className="error">{error}</p>;
  if (!data.length) return <p className="muted">No jobs yet.</p>;

  return (
    <table>
      <thead>
        <tr>
          <th>Kind</th>
          <th>Input</th>
          <th>Status</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {data.map((job) => (
          <tr key={job.id}>
            <td>{job.kind}</td>
            <td>
              {label(job)}
              {job.error && <div className="error">{job.error}</div>}
            </td>
            <td className={`status status-${job.status}`}>{job.status}</td>
            <td className="muted">{new Date(job.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Gallery() {
  // Signed URLs expire in an hour, so refresh well inside that window.
  const { data, error } = usePoll("/gallery", 15 * 60 * 1000);

  if (error) return <p className="error">{error}</p>;
  if (!data.length) return <p className="muted">Nothing rendered yet.</p>;

  return (
    <div className="gallery">
      {data.map((item) => (
        <figure key={`${item.source}-${item.id}`} style={{ margin: 0 }}>
          <video src={item.url} controls preload="metadata" />
          <figcaption>
            {item.title} <span className="muted">({item.source})</span>
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

const TABS = {
  trigger: ["New job", Trigger],
  jobs: ["Jobs", Jobs],
  gallery: ["Gallery", Gallery],
};

export default function App() {
  const [tab, setTab] = useState("trigger");
  const Screen = TABS[tab][1];

  return (
    <main>
      <h1>brainrot</h1>
      <nav>
        {Object.entries(TABS).map(([id, [title]]) => (
          <button key={id} aria-current={id === tab} onClick={() => setTab(id)}>
            {title}
          </button>
        ))}
      </nav>
      <Screen />
    </main>
  );
}
