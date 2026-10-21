"""Prometheus text from durable database observations and API-process latency."""

from collections import defaultdict
from threading import Lock
from time import monotonic

BOUNDS = (0.1, 1, 5, 30, 60, 300, 1800, float("inf"))
COUNTERS = {
    "processed": "brainrot_jobs_processed_total", "completed": "brainrot_jobs_completed_total",
    "failed": "brainrot_jobs_failed_total", "retried": "brainrot_jobs_retried_total",
    "recovered": "brainrot_jobs_recovered_total",
    "publication_published": "brainrot_publications_published_total",
    "publication_failed": "brainrot_publications_failed_total",
}


class RequestMetrics:
    def __init__(self):
        self.lock = Lock()
        self.values = {}

    def observe(self, route, method, status, seconds):
        method = method if method in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"} else "OTHER"
        key = (route, method, str(status))
        with self.lock:
            value = self.values.setdefault(key, {"count": 0, "sum": 0.0, "buckets": [0] * len(BOUNDS)})
            value["count"] += 1
            value["sum"] += seconds
            for index, bound in enumerate(BOUNDS):
                value["buckets"][index] += seconds <= bound

    def snapshot(self):
        with self.lock:
            return [(key, {**value, "buckets": list(value["buckets"])}) for key, value in self.values.items()]


REQUESTS = RequestMetrics()


class APIMetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started, status = monotonic(), 500

        async def capture(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            REQUESTS.observe(route, scope["method"], status, monotonic() - started)


def _labels(labels):
    def escape(value):
        return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    return "{" + ",".join(f'{key}="{escape(value)}"' for key, value in labels.items()) + "}"


def render(snapshot: dict, requests: RequestMetrics = REQUESTS) -> str:
    families = defaultdict(list)
    types = {}

    def sample(name, labels, value, kind="gauge"):
        types[name] = kind
        families[name].append(f"{name}{_labels(labels)} {value}")

    def histogram(name, labels, row):
        types[name] = "histogram"
        for bound, value in zip(BOUNDS, row["buckets"]):
            families[name].append(f'{name}_bucket{_labels({**labels, "le": "+Inf" if bound == float("inf") else str(bound)})} {value}')
        families[name].append(f'{name}_sum{_labels(labels)} {row["sum"]}')
        families[name].append(f'{name}_count{_labels(labels)} {row["count"]}')

    # Emit zero series too, so an idle or newly migrated installation scrapes cleanly.
    indexed = {(r["event"], r.get("pipeline"), r.get("platform")): r["value"] for r in snapshot.get("counters", [])}
    for event_name, name in COUNTERS.items():
        publication = event_name.startswith("publication_")
        for label in ("youtube", "tiktok", "instagram") if publication else ("brainrot", "repurpose", "reddit"):
            labels = {"platform" if publication else "pipeline": label}
            key = (event_name, None if publication else label, label if publication else None)
            sample(name, labels, indexed.get(key, 0), "counter")
    states = {(r["pipeline"], r["state"]): r["value"] for r in snapshot.get("states", [])}
    ready = {r["pipeline"]: r["value"] for r in snapshot.get("ready", [])}
    for pipeline in ("brainrot", "repurpose", "reddit"):
        for state in ("pending", "running", "done", "failed", "cancelled"):
            sample("brainrot_queue_depth", {"pipeline": pipeline, "state": state}, states.get((pipeline, state), 0))
        sample("brainrot_queue_ready", {"pipeline": pipeline}, ready.get(pipeline, 0))
    for row in snapshot.get("histograms", []):
        labels = {"pipeline": row["pipeline"]}
        if row["event"] == "stage_duration":
            labels["stage"] = row["stage"]
        histogram("brainrot_stage_duration_seconds" if row["event"] == "stage_duration" else "brainrot_job_duration_seconds", labels, row)
    for (route, method, status), row in requests.snapshot():
        histogram("brainrot_api_duration_seconds", {"route": route, "method": method, "status": status}, row)
    return "\n".join(line for name in sorted(families) for line in
                     [f"# HELP {name} Brainrot operational metric.", f"# TYPE {name} {types[name]}", *families[name]]) + "\n"
