"""Product presentation shared by native MSX JSON and the companion page.

MSX retains its own fonts, focus outline and grid; these are public API colors,
not CSS injected into the vendor runtime.
"""

PRODUCT = "Jellyfin MSX"
SURFACE = "#182632"
ACCENT = "#b8f16a"
INK = "#101820"
TEXT = "#f4f7fa"

PAIR_CSS = (
    """
:root{color-scheme:dark;--surface:SURFACE;--accent:ACCENT;--ink:INK;--text:TEXT}
*{box-sizing:border-box}
body{font:18px/1.55 system-ui,sans-serif;margin:0;background:var(--ink);color:var(--text)}
main{max-width:36rem;margin:clamp(1.5rem,6vh,4rem) auto;padding:0 1.5rem 2rem}
.brand{color:var(--accent);font-weight:700;letter-spacing:.04em;margin:0 0 1.5rem}
.step,.server,.help{color:#c5d2de}
.step{font-size:.9rem;margin:0 0 .4rem}
h1{font-size:clamp(1.75rem,5vw,2.25rem);line-height:1.2;margin:0 0 1rem}
p{margin:1rem 0;overflow-wrap:anywhere}
.server{font-size:.9rem}
.message{border-left:4px solid var(--accent);background:var(--surface);padding:1rem}
.message:empty{display:none}
label{display:block;font-weight:600;margin:1.3rem 0 .5rem}
input,button{width:100%;min-height:3rem;font:inherit;padding:.8rem 1rem;
border-radius:.4rem;border:1px solid #8a9bad}
input{background:var(--surface);color:var(--text)}
input::placeholder{color:#c5d2de;opacity:1}
button{margin:1.5rem 0 .5rem;background:var(--accent);color:var(--ink);
font-weight:700;border-color:var(--accent);cursor:pointer}
a,a:visited{color:var(--accent);text-underline-offset:.2em}
a{display:inline-block;padding:.3rem 0}
:focus-visible{outline:3px solid var(--accent);outline-offset:4px}
button:focus-visible{outline-color:var(--text)}
@media(max-width:400px){main{padding:0 1.1rem 1.5rem}}
""".replace("SURFACE", SURFACE)
    .replace("ACCENT", ACCENT)
    .replace("INK", INK)
    .replace("TEXT", TEXT)
)
