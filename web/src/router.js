import { useEffect, useState } from "react";

/* Hash routing, because the dev server and any static host will serve this from
   one file and a real router is a dependency for four pages. */

export const ROUTES = ["home", "docs", "faq", "console"];

function current() {
  const raw = window.location.hash.replace(/^#\/?/, "").split("/")[0];
  return ROUTES.includes(raw) ? raw : "home";
}

export function go(route) {
  window.location.hash = route === "home" ? "#/" : `#/${route}`;
}

export function useRoute() {
  const [route, setRoute] = useState(current);

  useEffect(() => {
    const onChange = () => {
      setRoute(current());
      // A new page should start at its top, not wherever the last one was scrolled.
      window.scrollTo({ top: 0, behavior: "auto" });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return route;
}
