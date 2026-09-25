"""Turn the published concept-board page into a frame renderer for the reel.

Input:  base.html  (the published "Cognitrixx mark, lit" page, textures embedded)
Output: reel_tpl.html  (same renderer, textures replaced by %%TEX_*%% placeholders,
        boot-up / spark / beam-thickness / camera hooks, and a window.__r3() harness)

The first block of edits is the patch from the previous session (boot-up reveals
with a bright leading front, adjustable beam thickness, alpha output, harness).
The second block adds what the "Assembly" shot list needs on top of it.
"""
import re
import sys

src = sys.argv[1] if len(sys.argv) > 1 else "base.html"
t = open(src).read()


def rep(a, b, n=1):
    global t
    assert t.count(a) >= 1, "MISSING: " + a[:100]
    t = t.replace(a, b, n)


# textures -> placeholders
t = re.sub(r'const TEX = \{ n:"[^"]+", c:"[^"]+", f:"[^"]+", x:"[^"]+", h:"[^"]+" \};',
           'const TEX = { n:"%%TEX_N%%", c:"%%TEX_C%%", f:"%%TEX_F%%", x:"%%TEX_X%%", h:"%%TEX_H%%" };', t)
assert "%%TEX_N%%" in t

# ---------------------------------------------------------------- previous session
# RELIEF: boot-up reveals with a bright leading front
rep('uniform float uDepth, uYaw, uPitch, uPersp, uAO, uKeyFall;',
    '''uniform float uDepth, uYaw, uPitch, uPersp, uAO, uKeyFall, uBootNet, uBootTrace, uBootDots, uCoreFlash, uSpark;
uniform float uSweepPos, uSweepAmt, uMetalOn;
float bootR(float b, float rmax){ return mix(-0.10, rmax, b); }
float bootM(float b, float d, float rmax){ float r = bootR(b, rmax); return smoothstep(r + 0.03, r - 0.03, d); }
float bootL(float b, float d, float rmax){ float r = bootR(b, rmax); return exp(-pow((d - r)/0.045, 2.0))*step(0.002, b)*step(b, 0.998); }''')
rep('vec3 coreEmit = draft ? vec3(0.0) : uCoreCol*uCoreGlow*uGlow*(exp(-dh*dh/0.0009) + 0.16*exp(-dh*dh/0.012));',
    'vec3 coreEmit = draft ? vec3(0.0) : uCoreCol*uCoreGlow*uGlow*(1.0 + 6.0*uCoreFlash)*(exp(-dh*dh/0.0009) + (0.16 + 0.5*uCoreFlash)*exp(-dh*dh/(0.012 + 0.03*uCoreFlash)));')
rep('''    float nf = dot(w, uNetFam);
    float links = smoothstep(0.04, 0.42, v)*nf;
    float nodes = smoothstep(0.62, 0.95, v)*nf;''',
    '''    float nfam = dot(w, uNetFam);
    float nf = nfam*bootM(uBootNet, dh, 1.18);
    float nlead = bootL(uBootNet, dh, 1.18);
    float links = smoothstep(0.04, 0.42, v)*nf;
    float nodes = smoothstep(0.62, 0.95, v)*nf;
    vec3 spk = vec3(0.92, 0.95, 1.0)*uSpark*nfam*(smoothstep(0.62, 0.95, v)*nlead*6.0 + smoothstep(0.04, 0.42, v)*nlead*1.6);
    col += spk*uGlow; bright += spk*0.9;''')
rep('''    float t = tx.b;
    col *= 1.0 - 0.6*t*uTrace;''',
    '''    vec2 qa = vec2(-0.0488, -0.7676);
    float da = length(q - qa);
    float traw = tx.b;
    float t = traw*bootM(uBootTrace, da, 1.46);
    float tlead = bootL(uBootTrace, da, 1.46);
    vec3 tsp = vec3(0.85, 0.97, 1.0)*traw*tlead*5.0*uSpark*uTrace;
    col += tsp*uGlow; bright += tsp*0.9;
    col *= 1.0 - 0.6*t*uTrace;''')
rep('''    float hl = hh.r, hf = hh.g;''',
    '''    float hraw = hh.r;
    float hl = hraw*bootM(uBootDots, dh, 1.02), hf = hh.g;
    float hlead = bootL(uBootDots, dh, 1.02);
    vec3 hsp = vec3(1.0, 0.9, 1.0)*hraw*hlead*5.5*uSpark*uHead;
    col += hsp*uGlow; bright += hsp*0.9;''')
rep('set("uAO", m.ao || 0); set("uKeyFall", m.keyFall || 0);',
    'set("uAO", m.ao || 0); set("uKeyFall", m.keyFall || 0);\n  set("uBootNet", m.bootNet ?? 1); set("uBootTrace", m.bootTrace ?? 1); set("uBootDots", m.bootDots ?? 1); set("uCoreFlash", m.coreFlash || 0); set("uSpark", m.spark ?? 1);\n  set("uSweepPos", m.sweepPos ?? -9); set("uSweepAmt", m.sweepAmt || 0); set("uMetalOn", m.metalOn ?? 1);')

# TRICK: adjustable beam thickness, ortho, alpha output
rep('const float L = 2.0; const float H = 0.33; const float RND = 0.075;',
    'const float L = 2.0; uniform float uBeamH; const float RND = 0.075;\n#define H uBeamH')
rep('    const ortho = 1.8;', '    const ortho = this.ortho || 1.8;')
rep('      set("uTime", time); set("uOrtho", ortho); set("uTrick"',
    '      set("uBeamH", this.beamH || 0.33); set("uPan", this.pan || [0, 0]); set("uTime", time); set("uOrtho", ortho); set("uTrick"')
rep('set("uHaloR", 0.5); set("uAlpha", 0); set("uShadow", 0); set("uDrop", 0);',
    'set("uHaloR", 0.5); set("uAlpha", this.alphaOut ? 1 : 0); set("uShadow", 0); set("uDrop", 0);')

# ---------------------------------------------------------------- this session
# TRICK: screen-space pan so the reel can frame the beams anywhere
rep('uniform vec2 uRes, uCoreP; uniform float uTime, uOrtho, uTrick, uFlash, uSep;',
    'uniform vec2 uRes, uCoreP, uPan; uniform float uTime, uOrtho, uTrick, uFlash, uSep;')
rep('vec3 roW = uPivot + uCamRight*p.x*2.0*uOrtho + uCamUp*(p.y-0.086)*2.0*uOrtho + uCamDir*14.0;',
    'vec3 roW = uPivot + uCamRight*(p.x-uPan.x)*2.0*uOrtho + uCamUp*(p.y-0.086-uPan.y)*2.0*uOrtho + uCamDir*14.0;')
rep('const coreP = [', 'const coreP0 = [')
rep('    const r = this.right, u = this.up, d = this.dir;\n',
    '    const coreP = [coreP0[0] + (this.pan || [0, 0])[0], coreP0[1] + (this.pan || [0, 0])[1]];\n    const r = this.right, u = this.up, d = this.dir;\n')

# RELIEF: one light sweep across the metal, and a metal fade for build-ups
rep('''  col += coreEmit*0.22;
  bright += min(max(col - vec3(0.9), vec3(0.0))*0.35, vec3(1.2)) + coreEmit*0.5;''',
    '''  if (uSweepAmt > 0.001) {
    float sx = dot(q, normalize(vec2(1.0, -0.42))) - uSweepPos;
    float band = exp(-sx*sx/0.0045)*(0.35 + 0.65*facing + 0.9*smoothstep(0.2, 0.9, edge));
    vec3 sw = vec3(0.86, 0.84, 1.0)*band*uSweepAmt;
    col += sw; bright += sw*0.45;
  }
  col *= uMetalOn;
  col += coreEmit*0.22;
  bright += min(max(col - vec3(0.9), vec3(0.0))*0.35, vec3(1.2)) + coreEmit*0.5;''')

# fractional "full" so the settled logo can keep a faint living pulse
rep('set("uFull", this.full ? 1 : 0)', 'set("uFull", typeof this.full === "number" ? this.full : (this.full ? 1 : 0))')

# remember the floor line so the compositor can place reflections
rep('const lay = this.layout(cssW, cssH); this.lastLayout = lay;',
    'const lay = this.layout(cssW, cssH); this.lastLayout = lay; this.lastFloor = null;')
rep('    const tex = this.tex;\n    this.p.draw(',
    '    this.lastFloor = [floorY, apexX];\n    const tex = this.tex;\n    this.p.draw(')

# ---------------------------------------------------------------- harness
rep('  const t0 = performance.now();', '''  if (location.hash.includes("reel")) {
    window.__r3 = (kind, o) => {
      if (kind === "trick") {
        const tr = views[2].v, P = PRESETS.minddots, M = PRESETS.mind, k = o.lit ?? 1, ck = o.coreK ?? 1;
        tr.p.fixed = [o.w, o.h]; tr.beamH = o.beamH || 0.44; tr.ortho = o.ortho; tr.alphaOut = true; tr.pan = o.pan || [0, 0];
        tr.mat = { ...M, famR: P.famR, famG: P.famG, famB: P.famB, silverB: 0,
          keyCol: M.keyCol.map((v) => v*k*1.15), rimCol: [0.62, 0.02, 1.0].map((v) => v*k*2.0),
          ambTop: M.ambTop.map((v) => v*k), ambBot: M.ambBot.map((v) => v*k), envInt: M.envInt*k,
          coreCol: P.coreCol.map((v) => v*ck), coreGlow: o.coreGlow ?? 2.2, edgeInt: 0.5*k, ...(o.over || {}) };
        tr.q = o.q; tr.sep = o.sep; tr.flash = o.flash || 0;
        tr.dragging = true; tr.play = null; tr.wasBroken = false; tr.last = performance.now();
        tr.frame(performance.now(), o.t);
        return tr.canvas.toDataURL("image/png");
      }
      stage.p.fixed = [o.w, o.h]; stage.loop = 0; stage.full = typeof o.full === "number" ? o.full : !!o.full; stage.glow = o.glow ?? 1; stage.alphaOut = true;
      stage.opts.layout = () => ({ center: o.center, scale: o.scale });
      stage.mat = { ...PRESETS.minddots, ...(o.over || {}) };
      stage.tween = null; stage.pointerActive = true;
      stage.light = [...o.light]; stage.lightTarget = [...o.light];
      stage.frame(performance.now(), o.t);
      window.__floor = stage.lastFloor;
      return stage.canvas.toDataURL("image/png");
    };
    window.__done = true;
    return;
  }
  const t0 = performance.now();''')

open("reel_tpl.html", "w").write(t)
print("template ok", len(t))
