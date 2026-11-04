"""Reads guion.txt + estimated line timings and writes video/index.html (graphics only, no voice).

Usage: python build.py [seconds]   (default 8 = first-8-seconds test)
Line starts come from LINES below; swap them for transcript times when a voice exists.
"""
import html
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0

# (start, end) seconds per guion.txt line; estimated at ~2.6 words/s until a voice exists.
LINES = [(0.0, 3.2), (3.4, 6.4), (6.6, 11.0)]
text = [l for l in (HERE / "guion.txt").read_text(encoding="utf-8").splitlines() if l.strip()]


def captions():
    out = []
    for n, (line, (a, b)) in enumerate(zip(text, LINES)):
        words = line.split()
        total = sum(len(w) + 1 for w in words)
        t, groups = a, [words[i:i + 3] for i in range(0, len(words), 3)]
        for g, grp in enumerate(groups):
            span = (b - a) * sum(len(w) + 1 for w in grp) / total
            s, e = t, min(t + span, DUR)
            t += span
            if s >= DUR:
                break
            key = max(grp, key=len)
            body = " ".join(f'<span class="key">{html.escape(w)}</span>' if w == key else html.escape(w) for w in grp)
            out.append(f'<div id="cap-{n}-{g}" class="clip cap" data-start="{s:.2f}" data-duration="{e - s - 0.03:.2f}" data-track-index="9">{body}</div>')
    return "\n      ".join(out)


POT = """<svg class="pot" viewBox="0 0 440 400" width="440" height="400">
  <g class="lid"><rect x="30" y="70" width="380" height="50" rx="25" fill="#aeb7c4"/><rect x="190" y="30" width="60" height="50" rx="14" fill="#6b7686"/></g>
  <rect x="55" y="120" width="330" height="230" rx="40" fill="#dfe5ee"/>
  <rect x="5" y="190" width="55" height="34" rx="14" fill="#8793a4"/><rect x="380" y="190" width="55" height="34" rx="14" fill="#8793a4"/>
  <g class="eyes"><circle cx="165" cy="235" r="22" fill="#fff"/><circle cx="275" cy="235" r="22" fill="#fff"/>
  <circle cx="170" cy="238" r="11" fill="#10141c"/><circle cx="280" cy="238" r="11" fill="#10141c"/></g>
  <path d="M185 292 Q220 318 255 292" stroke="#10141c" stroke-width="9" fill="none" stroke-linecap="round"/>
</svg>"""

THERMO = """<div class="card thermo"><div class="tube"><div class="mercury"></div></div><div class="deg"><span class="num">20</span><small>°C</small></div></div>"""

STEAM_A = "\n".join(f'<div class="puff" style="left:{150 + i * 55}px"></div>' for i in range(5))
STEAM_B = "\n".join(f'<div class="puff" style="left:{150 + i * 55}px"></div>' for i in range(6))

PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
:root { --ground:#07090d; --ink:#fff; --good:#22c55e; --bad:#ef4444; --accent:#fbbf24; --font:'Inter',sans-serif; }
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:1080px; height:1920px; overflow:hidden; background:var(--ground); font-family:var(--font); }
#root { position:absolute; inset:0; overflow:hidden; }
#bg { position:absolute; inset:0; background:
  radial-gradient(ellipse 90% 40% at 50% 100%, rgba(251,146,60,.38), transparent 70%),
  linear-gradient(rgba(255,255,255,.05) 2px, transparent 2px) 0 0/90px 90px,
  linear-gradient(90deg, rgba(255,255,255,.05) 2px, transparent 2px) 0 0/90px 90px; }
#cam { position:absolute; left:0; top:0; width:1080px; height:1920px; transform-origin:540px 900px; }
#world { position:absolute; left:0; top:0; width:2400px; height:1920px; }
.station { position:absolute; top:0; width:1080px; height:1920px; }
.pot { overflow:visible; position:absolute; left:80px; top:620px; }
.thermo { position:absolute; left:740px; top:560px; width:200px; height:640px; padding:36px 0; display:flex; flex-direction:column; align-items:center; justify-content:space-between; }
.card { background:#fff; border-radius:44px; color:#10141c; }
.tube { position:relative; width:56px; flex:1; border-radius:28px; background:#e5e7eb; overflow:hidden; }
.mercury { position:absolute; left:0; right:0; bottom:0; height:100%; background:var(--bad); transform-origin:50% 100%; transform:scaleY(.04); }
.deg { margin-top:18px; font-weight:900; font-size:64px; line-height:1; }
.deg small { font-size:36px; margin-left:4px; }
#s1 .deg small { display:none; }
.pill { position:absolute; left:130px; top:1200px; padding:22px 44px; border-radius:60px; font-weight:900; font-size:56px; color:#fff; white-space:nowrap; }
.pill.bad { background:var(--bad); } .pill.good { background:var(--good); color:#10141c; }
.puff { position:absolute; top:640px; width:70px; height:70px; border-radius:50%; background:rgba(255,255,255,.85); opacity:0; }
#path { position:absolute; left:0; top:0; width:2400px; height:1920px; }
.flame { position:absolute; left:250px; top:1040px; width:120px; height:120px; color:#fb923c; transform-origin:50% 100%; }
.cap { z-index:5; position:absolute; left:60px; right:60px; top:260px; text-align:center; font-weight:900; font-size:92px; line-height:1.1; color:#fff; text-shadow:0 4px 0 rgba(0,0,0,.5); }
.cap .key { background:var(--accent); color:#10141c; padding:0 18px; border-radius:20px; text-shadow:none; }
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="1080" data-height="1920">
  <div id="bg"></div>
  <div id="cam">
    <div id="world">
      <svg id="path" viewBox="0 0 2400 1920"><path id="trail" d="M540 1360 C 760 1500, 1100 1500, 1500 1360" fill="none" stroke="#fbbf24" stroke-width="14" stroke-linecap="round" stroke-dasharray="1 30"/></svg>
      <div id="s1" class="station" style="left:0">
        __POT__
        __THERMO__
        __STEAM_A__
        <div id="pill1" class="pill bad">MÁS CALIENTE</div>
      </div>
      <div id="s2" class="station" style="left:960px">
        __POT__
        __THERMO__
        __STEAM_B__
        <svg id="flame" class="flame" viewBox="0 0 24 24" fill="#fb923c" stroke="#fdba74" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>
        <div id="pill2" class="pill good">NO PASA DE 100</div>
      </div>
    </div>
  </div>
  __CAPS__
</div>
<script>
const tl = gsap.timeline({ paused: true });
const S1 = "#s1", S2 = "#s2";
const num = (sel, to, at, dur, ease) => { const o = { v: 20 }; tl.to(o, { v: to, duration: dur, ease, onUpdate: () => document.querySelector(sel + " .num").textContent = Math.round(o.v) }, at); };
// 0.0 hook: pot drops in with a camera punch, mercury shoots up
tl.fromTo("#cam", { scale: 1.25 }, { scale: 1, duration: 0.6, ease: "power3.out" }, 0)
  .fromTo(S1 + " .pot", { y: -480 }, { y: 0, duration: 0.55, ease: "bounce.out" }, 0)
  .fromTo(S1 + " .thermo", { x: 400, opacity: 0 }, { x: 0, opacity: 1, duration: 0.4, ease: "back.out(1.6)" }, 0.25)
  .to(S1 + " .mercury", { scaleY: 0.96, duration: 0.8, ease: "power3.out" }, 0.7);
document.querySelector(S1 + " .num").textContent = "▲";
tl.fromTo("#pill1", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)", transformOrigin: "left center" }, 1.5);
// idle life: lid jiggle, steam, blinks
tl.to(S1 + " .lid", { y: -8, duration: 0.18, yoyo: true, repeat: 9, ease: "sine.inOut" }, 1.0);
tl.to(S1 + " .eyes", { scaleY: 0.1, transformOrigin: "50% 50%", duration: 0.08, yoyo: true, repeat: 1 }, 2.0);
document.querySelectorAll(S1 + " .puff").forEach((p, i) => {
  tl.fromTo(p, { y: 0, opacity: 0, scale: 0.4 }, { y: -150, opacity: 0.9, scale: 1.3, duration: 1.0, ease: "power1.out", yoyo: true, repeat: 1 }, 1.0 + i * 0.35);
});
// 3.2 camera travel with trail
tl.to("#world", { x: -960, duration: 1.0, ease: "power2.inOut" }, 3.2)
  .fromTo("#bg", { backgroundPosition: "0px 0px, 0px 0px, 0px 0px" }, { backgroundPosition: "0px 0px, -290px 0px, -290px 0px", duration: 1.0, ease: "power2.inOut" }, 3.2)
  .fromTo("#cam", { filter: "blur(0px)" }, { filter: "blur(6px)", duration: 0.5, yoyo: true, repeat: 1, ease: "sine.inOut" }, 3.2)
  .fromTo("#trail", { opacity: 0 }, { opacity: 1, duration: 0.2 }, 3.2);
// 4.2 pot 2: lid lifts, steam, mercury stops at 100
tl.fromTo(S2 + " .pot", { y: 40, scale: 0.9 }, { y: 0, scale: 1, duration: 0.4, ease: "back.out(2)" }, 4.2)
  .to(S2 + " .lid", { y: -140, rotation: -14, transformOrigin: "50% 100%", duration: 0.35, ease: "back.out(2)" }, 4.4)
  .fromTo(S2 + " .thermo", { x: 300, opacity: 0 }, { x: 0, opacity: 1, duration: 0.35, ease: "back.out(1.6)" }, 4.3)
  .to(S2 + " .mercury", { scaleY: 0.5, duration: 0.7, ease: "power2.out" }, 4.8);
num(S2, 100, 4.8, 0.7, "power2.out");
tl.fromTo("#pill2", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)", transformOrigin: "left center" }, 5.6);
tl.to(S2 + " .eyes", { scaleY: 0.1, transformOrigin: "50% 50%", duration: 0.08, yoyo: true, repeat: 1 }, 5.8);
document.querySelectorAll(S2 + " .puff").forEach((p, i) => {
  tl.fromTo(p, { y: 0, opacity: 0, scale: 0.4 }, { y: -170, opacity: 0.9, scale: 1.4, duration: 1.1, ease: "power1.out", yoyo: true, repeat: 1 }, 4.7 + i * 0.4);
});
// 6.6 flame grows, mercury barely moves
tl.fromTo("#flame", { scale: 0.3, opacity: 0 }, { scale: 1.5, opacity: 1, duration: 0.8, ease: "back.out(1.8)" }, 6.6)
  .to("#flame", { scaleY: 1.7, duration: 0.2, yoyo: true, repeat: 3, ease: "sine.inOut" }, 7.4)
  .to(S2 + " .mercury", { scaleY: 0.52, duration: 0.5, yoyo: true, repeat: 1 }, 7.0);
window.__timelines["main"] = tl;
</script>
</body>
</html>
"""

page = (PAGE.replace("__DUR__", f"{DUR:g}").replace("__CAPS__", captions())
        .replace("__POT__", POT).replace("__THERMO__", THERMO)
        .replace("__STEAM_A__", STEAM_A).replace("__STEAM_B__", STEAM_B))
(HERE / "video" / "index.html").write_text(page, encoding="utf-8")
print(f"wrote video/index.html, {DUR:g}s, {len(text)} lines")
