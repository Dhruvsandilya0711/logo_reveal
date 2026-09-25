"""Inject a texture set (tex1024/ or tex2048/) into reel_tpl.html -> reel<res>.html."""
import base64
import sys

res = sys.argv[1] if len(sys.argv) > 1 else "1024"
t = open("reel_tpl.html").read()
for k in "ncfxh":
    b = open(f"tex{res}/{k}.webp", "rb").read()
    t = t.replace(f"%%TEX_{k.upper()}%%", "data:image/webp;base64," + base64.b64encode(b).decode())
assert "%%TEX_" not in t
open(f"reel{res}.html", "w").write(t)
print("built", res, len(t) // 1024, "KB")
