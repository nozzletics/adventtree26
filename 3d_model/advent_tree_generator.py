# nozzletics — Modular Christmas Tree Advent Calendar  v8 (split cells with a locating lip, hidden trays, hook mount)
# Parametric generator for Blender 4.2+ / 5.x  (1 Blender unit = 1 mm)
# Run from Blender's Text Editor (Alt+P). Edit P below and re-run: everything is rebuilt.
#
# Cell: four outer facets (sharp centre ridge + two sharp front edges), sharp side edges, 12 deg lean,
# equal chamfers at the bottom and the (closed) top. Inner wall follows the hub circle.
# Every tier's widest point overhangs the top edge of the tier below by OVERHANG (finger grip).
# A closed six-segment top tier tapers almost to a point and holds the star.
# Mount: each tier's tray (half size) is hidden in a recess under its cells and carries their weight;
# a hook near the top of each tier's post passes through a slot in the cell's hub-side wall and stops it tipping/falling out.
# Access: lift the cell ~4.4 mm (off the hook and out of the tray recess), slide it out, then pull the two
# halves apart: the cell is split along its centre ridge; half B has a lip all round its inside that plugs into half A.
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

P = {
    # tiers listed TOP -> BOTTOM (T1..T5)
    "N":   [6, 6, 6, 6],               # compartments per tier
    "H":   [80, 80, 80, 80],           # full cell height
    "R_BOTTOM": 137.5,                 # ridge radius of the bottom tier at its widest point
    "OVERHANG": 15.0,                  # widest point of a tier vs. top edge of the tier below
    "TOP_H": 110.0, "TOP_TIP_R": 9.0, "TOP_WALL": 2.0,   # decorative top tier
    "TOP_SECRET": True, "TOP_SPLIT": 2.0, "TOP_BOSS_R": 14.6,   # secret box: flat floor plate (split height), central boss onto T1
    "TOP_RIM_R": 50.0, "TOP_RIM_T": 2.0, "TOP_RIM_H": 8.0,    # rim on the floor carrying the outer bayonet (outer radius, wall, height)
    "TOP_ROOF_GAP": 20.0,                                      # hollow apex this far below the tip (room for the star socket)   # top tier = tray (floor) + bayonet cap -> secret box
    "TILT": 21.0,                      # lean of the outer surface (deg)
    "EDGE_K": 0.90,                    # edge radius / ridge radius (smaller = sharper ridge)
    "BREAK_A": 0.8,                    # side edges on the front: position as fraction of the half-angle
    "BREAK_K": 0.9625,                 # radius at those edges / ridge radius (smaller = sharper centre ridge)
    "FRONT_SAG": 0.03, "FRONT_SEG": 10,  # main front facets: arc bulge as a fraction of the facet width (0 = flat)
    "FACET_MODE": {},                  # per cell count: "flat3" = 3 front facets (flat centre), "ridge2" = 2 facets + ridge
    "ROT_BY_N": {},                    # extra rotation (deg) of tiers with this cell count, to line edges up
    "CB": 8.0, "CBH": 8.0,             # bottom chamfer: radial inset, height
    "CT": 8.0, "CTH": 8.0,             # top chamfer (same as the bottom one): radial inset, height
    "HUB_R": 17.0, "HUB_CLR": 0.4, "BORE_R": 5.0,
    "GAP": 0.4,                        # gap between neighbouring cells
    "WALL": 1.6, "FLOOR": 1.6, "ROOF": 1.6,   # = 4 lines of 0.4 mm
    "HUB_TAB": True, "HUB_TAB_M": 2.5,   # hub-wall strip with the hook slot goes to half B (margin each side of the slot)
    "LIP_ROOT_L": 2.4, "LIP_ROOT_N": 6,   # chamfered root of the lip inside half B (length, steps)
    "LIP_W": 1.2, "LIP_H": 3.0,        # lip on half B: wall thickness, how far it plugs into half A
    "LIP_CLR": 0.15,                   # lip clearance to half A's inner wall (per side)
    "TRAY_T": 4.0, "TRAY_SET": 12.0, "TRAY_MAXR": 99.0,
    "TRAY_FRAC": 0.5,                  # tray radius as a fraction of the old full-size tray
    "TRAY_CLR": 0.4,                   # radial clearance of the tray in the cell recess
    "STACK_GAP": 5.0,                  # air gap cell top -> cells above (must exceed LIFT)
    "HOOK_W": 6.0, "HOOK_T": 3.0, "HOOK_UP": 3.5, "HOOK_CLR": 0.3,   # trunk hook: width, stem, tip height, clearance
    "SPIG_R": 11.0, "SPIG_H": 10.0,    # post spigot: radius, height
    # self-tightening bayonet between posts: 3 lugs on the spigot, ramped grooves in the socket above.
    # Drop the upper part on, turn it clockwise (seen from above) LOCK_DEG: the ramp pulls it down onto
    # the shoulder and ends BAYO_PRELOAD mm past contact, so the joint is tight with no play.
    "LUG_W": (8.0, 5.0, 5.0), "LUG_DEG": (90.0, 210.0, 330.0),  # lug widths (one wide = one way only), angles
    "LUG_R": 1.6, "LUG_H": 2.5, "LUG_TOP": 1.5,   # lug radial reach, height, distance below the spigot top
    "LOCK_DEG": 40.0, "BAYO_RAMP": 0.8, "BAYO_PRELOAD": 0.3, "BAYO_CLR": 0.4,
    "CLR": 0.30,                       # fit clearance per side (spigots, rib pockets, star slot)
    "NUM_POS": "bottom", "NUM_MARGIN": 7.0,   # number position on the face: "bottom" (NUM_MARGIN mm above the chamfer) or "center"
    "NUM_DEPTH": 0.4, "NUM_RELIEF": 0.6, "NUM_SCALE": 0.5, "NUM_COLOR": "gold",   # inlay: NUM_DEPTH into the wall + NUM_RELIEF raised above the face;   # numbers: separate inlay part (AMS), flush with the surface
    "BASE_R": 110.0, "BASE_H": 8.0,
    "STAR_R": 36.0, "STAR_RI": 15.3,    # star: outer / inner point radius
    "STAR_T": 2.9, "STAR_APEX": 9.0,   # per half: flat slab thickness, height of the faceted centre
    "STEM_W0": 9.7, "STEM_W1": 6.0,    # square tapered stem (both halves together): side at the star / at the end
    "STEM_L": 30.1, "STEM_GAP": 1.3,   # stem length from the star's centre; gap between star points and the tip
    "STAR_PIN_D": 1.95, "STAR_PIN_DEPTH": 5.0,   # filament alignment pin hole in each star half (1.75 mm filament)
    "STEM_CLR": 0.0,                   # socket clearance per side: 0 = the wedge seats exactly at the design height
    "FRONT_DEG": -90.0,                # compartment 1 faces -Y (Blender front view)
    "CLOCKWISE": False,                # False = numbers read left-to-right from the front (CCW seen from above)
    "BED": (220, 220, 250),
    "BRAND": "nozzletics",               # fallback text if the stamp objects are missing
    "BRAND_STAMP": "NozzleticsStamp", "BRAND_W": 82.0,          # logo + wordmark under the base (width, mm)
    "CELL_STAMP": "NozzleticsStampSmall", "CELL_STAMP_W": 16.0,  # "n" mark on both side walls of every cell
    "STAMP_DEPTH": 0.6, "BRAND_Y": -58.0,     # logo centre under the base (moved forward, clear of the cable groove)
    "CABLE": True, "CABLE_GROOVE_W": 10.0, "CABLE_GROOVE_D": 5.0,  # garland channel: base bore + groove to the back edge, top-floor bore
    "COLORS": {"gold": (0.80, 0.60, 0.18), "green": (0.105, 0.235, 0.165), "ivory": (0.90, 0.85, 0.74),
               "terra": (0.55, 0.20, 0.15)},
    "TIER_COLOR": ["ivory", "terra", "green", "ivory"],
    "TOP_COLOR": "green",
}
pi = math.pi
def rad(d): return d * pi / 180.0
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

# ------------------------------------------------------------------ derived values
TIERS = []
def lidtop(Rk, Hk):
    return Rk - (Hk - P["CTH"] - P["CBH"]) * math.tan(rad(P["TILT"])) - P["CT"]

def derive():
    TIERS.clear()
    tant = math.tan(rad(P["TILT"])); nt = len(P["H"])
    R = [0.0] * nt; R[-1] = P["R_BOTTOM"]
    for k in range(nt - 2, -1, -1):
        R[k] = lidtop(R[k + 1], P["H"][k + 1]) + P["OVERHANG"]
    P["R"] = R
    P["R_TOP"] = lidtop(R[0], P["H"][0]) + P["OVERHANG"]
    z = P["BASE_H"]; zs = [0] * nt
    for k in range(nt - 1, -1, -1):
        zs[k] = z
        z += P["H"][k] + P["STACK_GAP"]
    for k in range(nt):
        n, R, H = P["N"][k], P["R"][k], P["H"][k]
        zl = H - P["CTH"]
        TIERS.append(dict(k=k, n=n, R=R, H=H, a=pi / n, zl=zl,
                          Rm=R - (zl - P["CBH"]) * tant,
                          z0=zs[k], zm=zs[k],
                          tray_r=P["TRAY_FRAC"] * min(R - P["TRAY_SET"], P["TRAY_MAXR"]),
                          first=sum(P["N"][:k]) + 1, color=P["TIER_COLOR"][k]))
    return z   # top of the T1 hub shoulder

def r_in(): return P["HUB_R"] + P["HUB_CLR"]
def theta(t, i):
    s = -1 if P["CLOCKWISE"] else 1
    return rad(P["FRONT_DEG"] + P["ROT_BY_N"].get(t["n"], 0.0)) + s * i * 2 * pi / t["n"]

def rho_taper(t, z): return t["R"] - (z - P["CBH"]) * math.tan(rad(P["TILT"]))
def rho(t, z):
    """ridge radius of the outer surface at height z (bottom chamfer / lean / top chamfer)"""
    if z <= P["CBH"]: return t["R"] - P["CB"] * (1 - z / P["CBH"])
    if z <= t["zl"]: return rho_taper(t, z)
    return t["Rm"] - P["CT"] * (z - t["zl"]) / P["CTH"]

# ------------------------------------------------------------------ 2D cell section (local +X = outward)
def _isect(l1, l2):
    a1, b1, d1 = l1; a2, b2, d2 = l2
    det = a1 * b2 - b1 * a2
    return ((d1 * b2 - d2 * b1) / det, (a1 * d2 - a2 * d1) / det)

def _fillet(l1, l2, r, seg=8):
    c = _isect((l1[0], l1[1], l1[2] - r), (l2[0], l2[1], l2[2] - r))
    a1 = math.atan2(l1[1], l1[0]); a2 = math.atan2(l2[1], l2[0])
    while a2 < a1: a2 += 2 * pi
    return [(c[0] + r * math.cos(a1 + (a2 - a1) * i / seg), c[1] + r * math.sin(a1 + (a2 - a1) * i / seg))
            for i in range(seg + 1)]

def _line(p, q, w):
    """half-plane through p,q with outward normal (+X side), offset inward by w"""
    D = q - p; n = Vector((D.y, -D.x)).normalized()
    if n.x < 0: n = -n
    return (n.x, n.y, n.dot(p) - w), n

def lines(t, rh, w, inner_x=None):
    """outer profile: centre ridge, two front edges at +-BREAK_A*a, side edges at +-a"""
    a, g, k = t["a"], t.get("gap", P["GAP"]) / 2, P["EDGE_K"]
    mode = P["FACET_MODE"].get(t["n"])
    R0 = Vector((rh, 0)); Ep = Vector((k * rh * math.cos(a), k * rh * math.sin(a)))
    if mode == "flat3":          # flat centre facet over +-a/3, then a side facet down to the seam
        Bp = Vector((rh, rh * math.tan(a / 3)))
    elif mode == "ridge2":       # one facet from the centre ridge straight to the seam
        Bp = (R0 + Ep) / 2
    else:
        b = P["BREAK_A"] * a; kb = P["BREAK_K"]
        Bp = Vector((kb * rh * math.cos(b), kb * rh * math.sin(b)))
    f1p, n1 = _line(R0, Bp, w); f2p, n2 = _line(Bp, Ep, w) if mode != "ridge2" else _line(R0, Ep, w)
    f1m = (f1p[0], -f1p[1], f1p[2]); f2m = (f2p[0], -f2p[1], f2p[2])
    sp = (-math.sin(a), math.cos(a), -g - w)          # side +
    sm = (-math.sin(a), -math.cos(a), -g - w)         # side -
    ix = r_in() * 0.7 if inner_x is None else inner_x
    inner = (-1.0, 0.0, -ix)                          # chord inside the hub (hub cylinder is cut later)
    return dict(f1p=f1p, f1m=f1m, f2p=f2p, f2m=f2m, sp=sp, sm=sm, inner=inner, n1=n1, n2=n2, mode=mode)

def _front_arc(t, rh, w, L, n_seg=None):
    """main front facet (centre ridge -> front edge) as a circular arc bulging outward by FRONT_SAG * chord;
    an inset (w > 0) uses the concentric arc, so walls stay W thick. Returns points ridge -> front edge (+ side)."""
    a = t["a"]; b = P["BREAK_A"] * a; kb = P["BREAK_K"]
    R0 = Vector((rh, 0)); Bp = Vector((kb * rh * math.cos(b), kb * rh * math.sin(b)))
    ch = Bp - R0; c = ch.length; sag = P["FRONT_SAG"] * c
    nrm = Vector((ch.y, -ch.x)).normalized()
    if nrm.x < 0: nrm = -nrm
    rad_ = (c * c / 4 + sag * sag) / (2 * sag)
    C = (R0 + Bp) / 2 - nrm * (rad_ - sag)
    r = rad_ - w
    p0 = Vector((C.x + math.sqrt(max(r * r - C.y * C.y, 0.0)), 0.0))          # ridge on y = 0
    a2, b2, d2 = L["f2p"]; nn = Vector((a2, b2)); hh = d2 - nn.dot(C)       # circle  x  front-edge line
    tt = Vector((-nn.y, nn.x)); q = math.sqrt(max(r * r - hh * hh, 0.0))
    guess = Vector(_isect(L["f1p"], L["f2p"]))
    cands = [C + nn * hh + tt * q, C + nn * hh - tt * q]
    p1 = min(cands, key=lambda v: (v - guess).length)
    t0 = math.atan2(p0.y - C.y, p0.x - C.x); t1 = math.atan2(p1.y - C.y, p1.x - C.x)
    n = n_seg or P["FRONT_SEG"]
    return [(C.x + r * math.cos(t0 + (t1 - t0) * i / n), C.y + r * math.sin(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]

def sect(t, rh, w=0.0, inner_x=None):
    L = lines(t, rh, w, inner_x)
    seq = {"flat3": ["inner", "sm", "f2m", "f1p", "f2p", "sp"],
           "ridge2": ["inner", "sm", "f2m", "f2p", "sp"]}.get(L["mode"], ["inner", "sm", "f2m", "f1m", "f1p", "f2p", "sp"])
    pts = [_isect(L[seq[i]], L[seq[(i + 1) % len(seq)]]) for i in range(len(seq))]
    if L["mode"] or P["FRONT_SAG"] <= 0: return pts
    arc = _front_arc(t, rh, w, L)                    # ridge -> +front edge
    # pts: 0 inner/sm, 1 sm/f2m, 2 f2m/f1m (-front edge), 3 ridge, 4 f1p/f2p (+front edge), 5 f2p/sp, 6 sp/inner
    minus = [(x, -y) for x, y in reversed(arc)]      # -front edge -> ridge
    return pts[:2] + minus + arc[1:] + pts[5:]

def levels(t, spec, inner_x=None):
    """spec: list of (z, ridge radius, inset)"""
    pts = []
    for z, rh, w in spec: pts += [Vector((x, y, z)) for x, y in sect(t, rh, w, inner_x)]
    return pts

# ------------------------------------------------------------------ mesh helpers
BUILD = None
def new_obj(name, me, coll=None):
    o = bpy.data.objects.new(name, me); (coll or BUILD).objects.link(o); return o

def hull(name, pts):
    bm = bmesh.new()
    for p in pts: bm.verts.new(p)
    r = bmesh.ops.convex_hull(bm, input=bm.verts)
    junk = list({g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk: bmesh.ops.delete(bm, geom=junk, context='VERTS')
    bmesh.ops.dissolve_limit(bm, angle_limit=rad(0.05), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me)

def box_frame(name, c, u, v, n, ur, vr, nr):
    return hull(name, [c + u * a + v * b + n * e for a in ur for b in vr for e in nr])

def box(name, x0, x1, y0, y1, z0, z1):
    return box_frame(name, Vector(), X, Y, Z, (x0, x1), (y0, y1), (z0, z1))

def rings(name, rz, seg, rot=0.0):
    pts = []
    for r, z in rz:
        for i in range(seg):
            a = rot + 2 * pi * i / seg
            pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    return hull(name, pts)

def cyl(r, z0, z1, seg=128): return rings("_cyl", [(r, z0), (r, z1)], seg)

def boolean(obj, cutters, op='DIFFERENCE', solver='MANIFOLD'):
    for c in cutters:
        m = obj.modifiers.new("b", 'BOOLEAN'); m.operation = op; m.object = c
        try: m.solver = solver
        except Exception: m.solver = 'EXACT'
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear()
    old = obj.data; nm = old.name; obj.data = me
    bpy.data.meshes.remove(old); me.name = nm
    for c in cutters:
        cm = c.data; bpy.data.objects.remove(c)
        if cm.users == 0: bpy.data.meshes.remove(cm)
    return obj

def volume(o):
    bm = bmesh.new(); bm.from_mesh(o.data); v = bm.calc_volume(); bm.free(); return v

def frame_matrix(c, u, v, n):
    return Matrix(((u.x, v.x, n.x, c.x), (u.y, v.y, n.y, c.y), (u.z, v.z, n.z, c.z), (0, 0, 0, 1)))

_FONT = []
def font():
    if _FONT: return _FONT[0]
    fd = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    f = None
    for fn in ("ariblk.ttf", "arialbd.ttf", "segoeuib.ttf", "verdanab.ttf",
               "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        p = fn if os.path.isabs(fn) else os.path.join(fd, fn)
        if os.path.exists(p): f = bpy.data.fonts.load(p, check_existing=True); break
    _FONT.append(f); return f

def text_cutter(name, s, height, maxw, c, u, v, n, n0, n1):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s
    if font(): cu.font = font()
    cu.size = 10; cu.extrude = (n1 - n0) / 2; cu.resolution_u = 6
    tob = bpy.data.objects.new(name, cu); BUILD.objects.link(tob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tob.evaluated_get(dg))
    bpy.data.objects.remove(tob); bpy.data.curves.remove(cu)
    xs = [p.co.x for p in me.vertices]; ys = [p.co.y for p in me.vertices]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    sc = min(height / h, maxw / w)
    me.transform(Matrix.Translation((-(max(xs) + min(xs)) / 2, -(max(ys) + min(ys)) / 2, 0)))
    me.transform(Matrix.Diagonal((sc, sc, 1, 1)))
    me.transform(frame_matrix(c, u, v, n) @ Matrix.Translation((0, 0, (n0 + n1) / 2)))
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.002)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    return new_obj(name, me)

def stamp_cutter(name, src_name, width, c, u, v, n, n0, n1):
    """cutter from a flat stamp mesh in the .blend (XY = artwork, Z = thickness): scaled to `width`,
    laid in the frame c/u/v and spanning n0..n1 along n. Returns None if the stamp object is missing."""
    src = bpy.data.objects.get(src_name)
    if src is None or src.type != 'MESH': return None
    me = src.data.copy()
    xs = [p.co.x for p in me.vertices]; ys = [p.co.y for p in me.vertices]; zs = [p.co.z for p in me.vertices]
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2; z0, z1 = min(zs), max(zs)
    k = width / (max(xs) - min(xs))
    for p in me.vertices:
        x, y, z = (p.co.x - cx) * k, (p.co.y - cy) * k, n0 + (p.co.z - z0) / (z1 - z0) * (n1 - n0)
        p.co = c + u * x + v * y + n * z
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    return new_obj(name, me)

def side_stamps(t, H):
    """small mark debossed into both flat radial side walls (the faces the halves print on)"""
    a, g = t["a"], t.get("gap", P["GAP"]) / 2; d = P["STAMP_DEPTH"]
    zc = H / 2; r_out = P["EDGE_K"] * rho_taper(t, zc); rc = (r_in() + P["WALL"] + r_out) / 2
    out = []
    for sgn in (1, -1):                     # +a side (half B) and -a side (half A)
        rad_ = Vector((math.cos(a), sgn * math.sin(a), 0)); nrm = Vector((-math.sin(a), sgn * math.cos(a), 0))
        u = -rad_ if sgn > 0 else rad_      # reads upright when seen from outside the wall
        c = rad_ * rc + Z * zc + nrm * g
        o = stamp_cutter("_cst", P["CELL_STAMP"], P["CELL_STAMP_W"], c, u, Z, nrm, -d, 1.0)
        if o: out.append(o)
    return out

# ------------------------------------------------------------------ parts
def wall_offsets():
    W = P["WALL"]
    wb = W * math.hypot(1, P["CB"] / P["CBH"])     # horizontal inset that keeps W normal to the bottom chamfer
    wt = W / math.cos(rad(P["TILT"]))
    return wb, (wb + wt) / 2, wt

def side_frame(t):
    a = t["a"]; g = t.get("gap", P["GAP"]) / 2
    return Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0)), g

def sbox(name, t, sr, zr, nr):
    """box in the side(+) plane frame: s = radial along the side, z, n = along the side normal"""
    u, ns, g = side_frame(t)
    return box_frame(name, Vector(), u, Z, ns, sr, zr, nr)

def build_cell(t):
    H, W, zl = t["H"], P["WALL"], t["zl"]
    wb, wm, wt = wall_offsets()
    o = hull(f"Cell_T{t['k']+1}", levels(t, [(0, rho(t, 0), 0), (P["CBH"], t["R"], 0), (zl, t["Rm"], 0), (H, rho(t, H), 0)]))
    cav = hull("_cav", levels(t, [(P["FLOOR"], rho(t, P["FLOOR"]), wb), (P["CBH"] + 0.6, rho(t, P["CBH"] + 0.6), wm),
                                  (zl - 0.6, rho(t, zl - 0.6), wm), (H - P["ROOF"], rho(t, H - P["ROOF"]), wb)]))
    boolean(cav, [cyl(r_in() + W, -1, H + 5)])
    t["cavity_cm3"] = volume(cav) / 1000
    boolean(o, [cyl(r_in(), -1, H + 5), cav])
    # recess for the (hidden) tray: solid ledge above it, then the recess itself
    T = P["TRAY_T"]; rr = t["tray_r"] + P["TRAY_CLR"]
    ledge = cyl(rr + 1.6, P["FLOOR"] - 0.5, T + P["FLOOR"])
    shell = hull("_shell", levels(t, [(0, rho(t, 0), 0.6), (P["CBH"], t["R"], 0.6), (zl, t["Rm"], 0.6)]))
    boolean(ledge, [shell], 'INTERSECT')                     # kept 0.6 mm inside the outer skin (no coplanar faces)
    boolean(ledge, [cyl(r_in() + 0.6, -2, H + 5)])
    boolean(o, [ledge], 'UNION')
    pk = cyl(rr, -1, T)
    # slot in the hub-side wall for the trunk hook (open downwards so the cell lifts off it)
    hz, r_end, lift = hook_geom(t)
    hw = P["HOOK_W"] / 2 + P["HOOK_CLR"]
    slot = box("_slot", r_in() - 1.5, r_in() + W + 0.3, -hw, hw,
               hz - (r_end - r_in()) - lift - 0.3, hz + P["HOOK_T"] + P["HOOK_CLR"])
    boolean(o, [pk, slot])
    st = side_stamps(t, H)
    if st: boolean(o, st, solver='EXACT')
    t["lip"] = build_lip(t)
    return o

def build_lip(t):
    """lip all round the inside of the split face of half B; plugs LIP_H deep into half A"""
    H, W, zl = t["H"], P["WALL"], t["zl"]
    wb, wm, _ = wall_offsets(); c, w = P["LIP_CLR"], P["LIP_W"]
    fl = P["TRAY_T"] + P["FLOOR"]; rf = H - P["ROOF"]; rr = t["tray_r"] + P["TRAY_CLR"]
    def cav(d):
        # same levels as the cell cavity (offset by d), so the lip follows the real inner wall; cut off below the tray ledge
        o = hull("_lc", levels(t, [(P["FLOOR"], rho(t, P["FLOOR"]), wb + d), (P["CBH"] + 0.6, rho(t, P["CBH"] + 0.6), wm + d),
                                   (zl - 0.6, rho(t, zl - 0.6), wm + d), (rf - d, rho(t, rf - d), wb + d)]))
        # bottom follows the real floor: main floor (FLOOR) and the raised tray ledge (radius rr + 1.6, top at fl)
        return boolean(o, [cyl(r_in() + W + d, -2, H + 5), box("_floor", -500, 500, -500, 500, -500, P["FLOOR"] + d),
                           cyl(rr + 1.6 + d, -500, fl + d)])
    lip = cav(c); boolean(lip, [cav(c + w), box("_slab", -500, 500, -500, -P["LIP_H"], -500, 500),
                                box("_slab", -500, 500, 0.01, 500, -500, 500)])
    # root: joins the lip to half B's wall. Its inner face is chamfered (stepped, LIP_ROOT_L long) so that,
    # printed on the side wall with the open face up, it grows out of the wall gradually instead of overhanging
    N = P["LIP_ROOT_N"]; Lr = P["LIP_ROOT_L"]
    for i in range(N):
        d_i = (c + w) * (1 - i / N); y0, y1 = Lr * i / N, Lr * (i + 1) / N
        r_ = cav(-0.5); boolean(r_, [cav(d_i), box("_slab", -500, 500, -500, y0, -500, 500),
                                     box("_slab", -500, 500, y1, 500, -500, 500)])
        boolean(lip, [r_], 'UNION')
    hz, r_end, lift = hook_geom(t)
    z_hz = -2 if P["HUB_TAB"] else hz - (r_end - r_in()) - lift - 1.5   # with the hub tab on B, no lip along the hub wall at all
    boolean(lip, [box("_hookzone", r_in() - 2, r_end + 0.8, -20, 20, z_hz, H + 2)])
    me = lip.data; bpy.data.objects.remove(lip)
    return me

def split_cell(t, body, inlay=None):
    """cut the numbered cell along its centre plane (local y = 0); half B gets the lip; the number inlay is split too"""
    big = 500.0
    A = new_obj(body.name.replace("_Body", "_A"), body.data.copy())
    Bh = new_obj(body.name.replace("_Body", "_B"), body.data.copy())
    boolean(A, [box("_hy", -big, big, 0.0, big, -big, big)])
    boolean(Bh, [box("_hy", -big, big, -big, 0.0, -big, big)])
    boolean(Bh, [new_obj("_lip", t["lip"].copy())], 'UNION')
    if P["HUB_TAB"]:
        # the hub-wall strip around the hook slot belongs to half B, so the hook never pulls the halves apart
        S = P["HOOK_W"] / 2 + P["HOOK_CLR"] + P["HUB_TAB_M"]; c = P["LIP_CLR"]
        r0, r1 = r_in() - 2.0, r_in() + P["WALL"]
        tab = new_obj("_tab", body.data.copy())
        boolean(tab, [box("_tb", r0, r1, -S, 0.3, -big, big)], 'INTERSECT')   # overlaps B by 0.3 (no coplanar union)
        boolean(Bh, [tab], 'UNION')
        boolean(A, [box("_tn", r0, r1 + 0.3, -S - c, 0.01, -big, big)])
    A.data.name = A.name; Bh.data.name = Bh.name
    m = body.data; bpy.data.objects.remove(body); bpy.data.meshes.remove(m)
    nums = [None, None]
    if inlay is not None:
        for i, (h, y0, y1) in enumerate(((A, -big, 0.0), (Bh, 0.0, big))):
            q = new_obj(h.name + "_Num", inlay.data.copy())
            boolean(q, [box("_hy", -big, big, y0, y1, -big, big)], 'INTERSECT')
            if len(q.data.polygons): q.data.name = q.name; nums[i] = q
            else: bpy.data.meshes.remove(q.data)
        m = inlay.data; bpy.data.objects.remove(inlay); bpy.data.meshes.remove(m)
    return A, Bh, nums

def number_cell(t, base, num):
    """cuts a NUM_DEPTH recess in the shape of the number; returns (body, inlay) - the inlay fills it flush"""
    o = new_obj(f"T{t['k']+1}_C{num:02d}_Body", base.data.copy())
    th = rad(P["TILT"]); zl = t["zl"]; zc = (P["CBH"] + zl) / 2
    c = Vector((rho_taper(t, zc), 0, zc))
    n = Vector((math.cos(th), 0, math.sin(th))); v = Vector((-math.sin(th), 0, math.cos(th)))
    mode = P["FACET_MODE"].get(t["n"])
    if mode == "flat3": face_w = 2 * t["R"] * math.tan(t["a"] / 3)
    elif mode == "ridge2": face_w = 2 * P["EDGE_K"] * t["R"] * math.sin(t["a"]) * 0.8
    else: face_w = 2 * P["BREAK_K"] * t["R"] * math.sin(P["BREAK_A"] * t["a"])
    k = P["NUM_SCALE"]; ht = (zl - P["CBH"]) * 0.42 * k
    if P["NUM_POS"] == "bottom":            # number sits low on the face: NUM_MARGIN above the bottom chamfer edge
        zc = P["CBH"] + (P["NUM_MARGIN"] + ht / 2) * math.cos(th); c = Vector((rho_taper(t, zc), 0, zc))
    txt = text_cutter("_num", str(num), ht, face_w * 0.78 * k, c, Y, v, n, -10, 3)
    wd = P["NUM_DEPTH"] / math.cos(th)
    inset = hull("_inset", levels(t, [(P["CBH"] - 3, rho_taper(t, P["CBH"] - 3), wd),
                                       (zl + 3, rho_taper(t, zl + 3), wd)]))
    boolean(txt, [inset], solver='EXACT')
    inl = new_obj(f"T{t['k']+1}_C{num:02d}_Num", txt.data.copy())
    rel = P["NUM_RELIEF"]
    if rel > 0:   # raised: outer skin offset outward by NUM_RELIEF (same profile, incl. the front arcs)
        skin = hull("_skin", levels(t, [(P["CBH"] - 3, rho_taper(t, P["CBH"] - 3), -rel / math.cos(th)),
                                         (zl + 3, rho_taper(t, zl + 3), -rel / math.cos(th))]))
    else:
        skin = new_obj("_bodycopy", base.data.copy())
    boolean(inl, [skin], 'INTERSECT', solver='EXACT')
    boolean(o, [txt], solver='EXACT')
    o.data.name = o.name
    return o, inl

def _lug_box(name, ang_deg, w, r0, r1, z0, z1):
    b = box(name, r0, r1, -w / 2, w / 2, z0, z1)
    b.data.transform(Matrix.Rotation(rad(ang_deg), 4, 'Z')); return b

def spigot(z0, r=None, h=None):
    """male half of the bayonet: spigot on top of a post (shoulder at z0) with three lugs"""
    r = r or P["SPIG_R"]; h = h or P["SPIG_H"]
    zl = z0 + h - P["LUG_TOP"] - P["LUG_H"]
    parts = [rings("_spig", [(r, z0 - 0.5), (r, z0 + h - 0.8), (r - 0.6, z0 + h)], 64)]
    for a, w in zip(P["LUG_DEG"], P["LUG_W"]):
        # flat-bottomed lug: its underside is the face the ramp pulls on (1.6 mm overhang prints fine)
        parts.append(_lug_box("_lug", a, w, r - 0.5, r + P["LUG_R"], zl, zl + P["LUG_H"]))
    return parts

def socket(z0, sense=1, r=None, h=None):
    """female half (cut from the part above, its bottom face at z0): bore, entry slots and ramped grooves.
    sense=+1: locks turning clockwise (seen from above); sense=-1: locks anticlockwise"""
    r = r or P["SPIG_R"]; h = h or P["SPIG_H"]; c = P["BAYO_CLR"]
    zl = h - P["LUG_TOP"] - P["LUG_H"]                       # lug bottom relative to the shoulder
    r0, r1 = r - 0.5, r + P["LUG_R"] + c; lock = P["LOCK_DEG"]; N = 8
    cuts = [rings("_sock", [(r + 0.8, z0 - 1), (r + 0.8, z0), (r + 0.3, z0 + 0.5), (r + 0.3, z0 + h + 0.6)], 64)]
    for a, w in zip(P["LUG_DEG"], P["LUG_W"]):
        ww = w + 2 * c; s0 = a - sense * lock                # entry slot sits LOCK_DEG from the locked lug
        low = lambda j: z0 + zl - P["BAYO_RAMP"] + (P["BAYO_RAMP"] + P["BAYO_PRELOAD"]) * j / N
        top = z0 + zl + P["LUG_H"] + c                      # upper flank: flat, clear of the lug all the way
        cuts.append(_lug_box("_slot", s0, ww, r0, r1, z0 - 1, top))
        for j in range(N):
            pts = []
            for jj in (j, j + 1):
                ang = rad(s0 + sense * lock * jj / N); lo = low(jj); hi = top
                for yy in (-ww / 2, ww / 2):
                    for rr in (r0, r1):
                        for zz in (lo, hi):
                            pts.append(Vector((rr * math.cos(ang) - yy * math.sin(ang), rr * math.sin(ang) + yy * math.cos(ang), zz)))
            cuts.append(hull("_groove", pts))
    return cuts

def hook_geom(t):
    """hook stem height hz (top of the tier's post, tip just under the cell ceiling), stem end radius,
    and how far a cell must lift to clear hook + tray"""
    lift = max(P["HOOK_UP"], P["TRAY_T"]) + 0.4
    r_end = r_in() + P["WALL"] + 0.4 + 2.0
    hz = t["H"] - P["ROOF"] - 0.5 - P["HOOK_T"] - P["HOOK_UP"]
    return hz, r_end, lift

def build_carrier(t):
    T, top = P["TRAY_T"], t["H"] + P["STACK_GAP"]
    o = rings(f"T{t['k']+1}_Carrier", [(t["tray_r"], 0), (t["tray_r"], T - 0.8), (t["tray_r"] - 0.8, T)], 96)
    add = [rings("_hub", [(P["HUB_R"], T - 0.5), (P["HUB_R"], top)], 64)] + spigot(top)
    hz, r_end, _ = hook_geom(t); hw = P["HOOK_W"] / 2; r0 = P["HUB_R"] - 1.0
    for i in range(t["n"]):
        # stem with a 45 deg underside (prints without support) + upward tip inside the cell
        stem = hull("_stem", [Vector((r, y, z)) for y in (-hw, hw) for r, z in
                              ((r0, hz - (r_end - r0)), (r0, hz + P["HOOK_T"]), (r_end, hz + P["HOOK_T"]), (r_end, hz))])
        tip = box("_tip", r_end - 2.0, r_end, -hw, hw, hz + P["HOOK_T"] - 0.5, hz + P["HOOK_T"] + P["HOOK_UP"])
        for h_ in (stem, tip): h_.data.transform(Matrix.Rotation(theta(t, i), 4, 'Z'))
        add += [stem, tip]
    boolean(o, add, 'UNION')
    cut = socket(0) + [rings("_bore", [(P["BORE_R"], -1), (P["BORE_R"], top + P["SPIG_H"] + 1)], 32)]
    return boolean(o, cut)

def build_base():
    Bh, R = P["BASE_H"], P["BASE_R"]
    o = rings("Base", [(R, 0), (R, Bh - 2), (R - 2, Bh)], 96)
    boolean(o, spigot(Bh), 'UNION')
    tc = stamp_cutter("_brand", P["BRAND_STAMP"], P["BRAND_W"], Vector((0, P["BRAND_Y"], 0)), -X, Y, -Z, -P["STAMP_DEPTH"], 1.0)
    if tc is None and P["BRAND"]:
        tc = text_cutter("_brand", P["BRAND"], 11, 110, Vector((0, -30, 0)), -X, Y, -Z, -0.6, 1.0)
    if tc: boolean(o, [tc], solver='EXACT')
    if P["CABLE"]:   # garland: up through the centre, out along a groove on the underside to the back edge
        w, d = P["CABLE_GROOVE_W"] / 2, P["CABLE_GROOVE_D"]
        boolean(o, [rings("_cbore", [(P["BORE_R"], -1), (P["BORE_R"], Bh + P["SPIG_H"] + 1)], 32),
                    box("_cgroove", -w, w, 0.0, R + 5, -1, d)])
    return o

def build_top():
    """six-segment top tier: same facets/ridges as the cells, tapering almost to a point.
    TOP_SECRET: returns (cap, floor) - a shallow tray locked onto T1 and a hollow cap with a reversed bayonet
    on top of it (the space inside is a secret compartment). Otherwise one closed piece (cap, None)."""
    Hd, k, tip = P["TOP_H"], P["EDGE_K"], P["TOP_TIP_R"]
    td = dict(k=-1, n=6, R=P["R_TOP"], a=pi / 6, gap=-0.3)
    def rho_d(z):
        if z <= P["CBH"]: return td["R"] - P["CB"] * (1 - z / P["CBH"])
        return td["R"] + (tip - td["R"]) * (z - P["CBH"]) / (Hd - P["CBH"])
    segs = []
    for i in range(6):
        sg = hull("_seg", levels(td, [(0, rho_d(0), 0), (P["CBH"], td["R"], 0), (Hd, tip, 0)], inner_x=0.0))
        sg.data.transform(Matrix.Rotation(theta(td, i), 4, 'Z')); segs.append(sg)
    o = segs[0]; o.name = "TopTier"
    boolean(o, segs[1:], 'UNION')
    # seams between the dummy segments, matching the gaps between real cells
    seams = []
    for i in range(6):
        # two convex pieces (below / above the chamfer break) so the groove stays 1 mm deep everywhere
        for za, zb in ((-1, P["CBH"]), (P["CBH"], Hd + 1)):
            pts = []
            for z in (za, zb):
                rz = rho_d(min(max(z, 0), Hd)); r0 = k * rz - 1.0; r1 = rz + 5
                pts += [Vector((r, sy * 0.3, z)) for r in (r0, r1) for sy in (-1, 1)]
            sm_ = hull("_seam", pts)
            sm_.data.transform(Matrix.Rotation(theta(td, i) + td["a"], 4, 'Z')); seams.append(sm_)
    boolean(o, seams)
    # hollow inside (valley radius minus wall), closed by a 45 deg roof well below the star slot
    sl = (td["R"] - tip) / (Hd - P["CBH"])
    wv = P["TOP_WALL"] / math.cos(math.atan(sl))
    A = k * (td["R"] + sl * P["CBH"]) - wv; B = k * sl          # inner radius r(z) = A - B z
    roof = P["TOP_ROOF_GAP"] if P["TOP_SECRET"] else 14
    zc = (Hd - roof - A) / (1 - B)
    r_bot = k * rho_d(0) - P["TOP_WALL"] * 1.5; r_cb = A - B * P["CBH"]
    def hollow(z_start):
        r_s = r_bot + (r_cb - r_bot) * (z_start + 1) / (P["CBH"] + 1) if z_start < P["CBH"] else A - B * z_start
        mid = [(r_cb, P["CBH"])] if z_start < P["CBH"] else []
        return rings("_hol", [(r_s, z_start)] + mid + [(A - B * zc, zc), (0.6, zc + (A - B * zc) - 0.6)], 96)
    solid = new_obj("_solid", o.data.copy())                  # full cone, before hollowing
    solid.data.transform(Matrix.Diagonal((0.97, 0.97, 1.0, 1.0)))   # stay just inside the skin (no coplanar faces)
    if not P["TOP_SECRET"]:
        boolean(o, [hollow(-1)])
        tube = rings("_tube", [(P["HUB_R"], 0), (P["HUB_R"], Hd - 3.0)], 64)
        boolean(tube, [solid], 'INTERSECT'); boolean(o, [tube], 'UNION')
        return boolean(o, socket(0) + [star_socket(Hd)]), None
    zs, Rr, Th, Hr = P["TOP_SPLIT"], P["TOP_RIM_R"], P["TOP_RIM_T"], P["TOP_RIM_H"]
    # ---- floor: flat plate (the cone's own outline, z 0..zs) + rim with the outer bayonet lugs + central boss onto T1
    fl = new_obj("TopFloor", o.data.copy())
    boolean(fl, [box("_cut", -500, 500, -500, 500, zs, 500)])
    rim = spigot(zs, r=Rr, h=Hr)
    boolean(rim[0], [cyl(Rr - Th, zs - 1, zs + Hr + 1)])     # hollow ring, not a solid spigot
    boolean(fl, rim, 'UNION')
    boss = rings("_boss", [(P["TOP_BOSS_R"], zs - 0.5), (P["TOP_BOSS_R"], P["SPIG_H"] + 3.0)], 64)
    boolean(fl, [boss], 'UNION')
    boolean(fl, socket(0) + ([rings("_cbore", [(P["BORE_R"], -1), (P["BORE_R"], P["SPIG_H"] + 4)], 32)] if P["CABLE"] else []))
    # ---- cap: z zs..Hd, hollow cone; reversed bayonet grooves in its foot ride on the rim lugs; star socket at the tip
    boolean(o, [box("_cut", -500, 500, -500, 500, -500, zs)])
    z_in = zs + Hr + 0.6
    boolean(o, [hollow(z_in - 0.01)])
    boolean(o, socket(zs, sense=-1, r=Rr, h=Hr) + [star_socket(Hd)])
    return o, fl

def star_geom():
    R, ri, L = P["STAR_R"], P["STAR_RI"], P["STEM_L"]
    y_top = -ri + 1.0                                  # stem starts inside the star
    y_end = y_top - L
    y_tip = -R * math.sin(rad(54)) - P["STEM_GAP"]     # where the tree tip sits (just below the lower points)
    W = lambda y: P["STEM_W0"] + (P["STEM_W1"] - P["STEM_W0"]) * (y_top - y) / L
    return y_top, y_end, y_tip, W

def star_socket(z_tip):
    """tapered square hole matching the stem, 2 mm deeper than the stem so it wedges before it bottoms out"""
    y_top, y_end, y_tip, W = star_geom(); c = P["STEM_CLR"]
    pts = []
    for d in (-1.0, (y_tip - y_end) + 2.0):
        h = W(y_tip - d) / 2 + c
        pts += [Vector((sx * h, sy * h, z_tip - d)) for sx in (-1, 1) for sy in (-1, 1)]
    return hull("_ssock", pts)

def build_star_half():
    """one half of the star: flat back (split face, z = 0) with a faceted front, plus half of the square stem"""
    R, ri, T, A = P["STAR_R"], P["STAR_RI"], P["STAR_T"], P["STAR_APEX"]
    bm = bmesh.new()
    pts = [((R if i % 2 == 0 else ri) * math.cos(pi / 2 + i * pi / 5),
            (R if i % 2 == 0 else ri) * math.sin(pi / 2 + i * pi / 5)) for i in range(10)]
    b = [bm.verts.new((x, y, 0)) for x, y in pts]; f = [bm.verts.new((x, y, T)) for x, y in pts]
    ap = bm.verts.new((0, 0, A))
    bm.faces.new(list(reversed(b)))
    for i in range(10):
        j = (i + 1) % 10
        bm.faces.new([b[i], b[j], f[j], f[i]]); bm.faces.new([f[i], f[j], ap])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("StarHalf"); bm.to_mesh(me); bm.free()
    o = new_obj("StarHalf", me)
    y_top, y_end, y_tip, W = star_geom()
    stem = hull("_stem", [Vector((sx * W(y) / 2, y, z)) for y in (y_top, y_end) for sx in (-1, 1) for z in (0, W(y) / 2)])
    boolean(o, [stem], 'UNION', solver='EXACT')
    if P["STAR_PIN_D"]:   # centre hole in the flat back for a piece of filament: aligns the two halves
        boolean(o, [rings("_pin", [(P["STAR_PIN_D"] / 2, -1.0), (P["STAR_PIN_D"] / 2, P["STAR_PIN_DEPTH"])], 24)])
    return o

# ------------------------------------------------------------------ scene setup
def material(key):
    name = "PLA_" + key
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    rgb = P["COLORS"][key]; m.diffuse_color = (*rgb, 1); m.roughness = 0.85
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf: bsdf.inputs["Base Color"].default_value = (*rgb, 1); bsdf.inputs["Roughness"].default_value = 0.85
    return m

def get_coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name); (parent or bpy.context.scene.collection).children.link(c)
    return c

def wipe():
    for cn in ("AdventTree", "AT_Assembly", "AT_Exploded", "_build"):
        c = bpy.data.collections.get(cn)
        if c:
            for o in list(c.all_objects): bpy.data.objects.remove(o, do_unlink=True)
            for ch in list(c.children_recursive): bpy.data.collections.remove(ch)
            bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.curves):
        for d in list(blk):
            if d.users == 0: blk.remove(d)

def place(o, coll, M, color, kind, print_M):
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o); o.matrix_world = M
    o.data.materials.clear(); o.data.materials.append(material(color))
    o.color = (*P["COLORS"][color], 1)
    o["part_kind"] = kind
    nm = o.name
    if nm.startswith("T") and nm[1].isdigit(): o["tier"] = int(nm[1])
    o["print_matrix"] = [x for row in print_M for x in row]

def join_inlay(h, q):
    """merge the number inlay into the half's mesh as a separate shell with material slot 1 (NUM_COLOR):
    one object per half, so slicers / 3MF keep the number with its cell; colour is per face"""
    h.data.materials.append(material(P["NUM_COLOR"]))
    bm = bmesh.new(); bm.from_mesh(h.data)
    for f in bm.faces: f.material_index = 0
    n0 = len(bm.faces)
    bm.from_mesh(q.data)                                 # same local frame (both built at identity)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]: f.material_index = 1
    bm.to_mesh(h.data); bm.free()
    m = q.data; bpy.data.objects.remove(q); bpy.data.meshes.remove(m)
    h["has_number"] = True

def build_all():
    global BUILD
    wipe()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 0.001
    sc.unit_settings.length_unit = 'MILLIMETERS'
    root = get_coll("AdventTree"); asm = get_coll("AT_Assembly", root)
    BUILD = get_coll("_build")
    top_z = derive()
    # half A lies on its split face; half B (with the lip) lies on its flat radial side wall
    # both halves print on their flat radial side wall, open (split) side up - no supports
    for t in TIERS:
        tc = get_coll(f"T{t['k']+1}_{t['n']}x", asm)
        base = build_cell(t)
        for i in range(t["n"]):
            num = t["first"] + i
            Mw = Matrix.Translation((0, 0, t["zm"])) @ Matrix.Rotation(theta(t, i), 4, 'Z')
            hA, hB, (nA, nB) = split_cell(t, *number_cell(t, base, num))
            a_ = t["a"]
            print_A = frame_matrix(Vector(), Z, Vector((math.cos(a_), -math.sin(a_), 0)),
                                   Vector((math.sin(a_), math.cos(a_), 0))).inverted()
            place(hA, tc, Mw, t["color"], "module", print_A); hA["compartment"] = num; hA["half"] = "A"
            print_B = Matrix.Rotation(pi, 4, 'X') @ frame_matrix(Vector(), Z, Vector((math.cos(a_), math.sin(a_), 0)),
                                                                Vector((-math.sin(a_), math.cos(a_), 0))).inverted()
            place(hB, tc, Mw, t["color"], "module", print_B); hB["compartment"] = num; hB["half"] = "B"
            for h, q in ((hA, nA), (hB, nB)):
                if q is not None: join_inlay(h, q)      # number inlay = 2nd shell of the half, gold material slot
        m = base.data; bpy.data.objects.remove(base); bpy.data.meshes.remove(m); bpy.data.meshes.remove(t["lip"])
        car = build_carrier(t)
        place(car, tc, Matrix.Translation((0, 0, t["z0"])), t["color"], "carrier", Matrix())
    core = get_coll("Core", asm)
    place(build_base(), core, Matrix(), "green", "base", Matrix())
    cap, tfl = build_top()
    place(cap, core, Matrix.Translation((0, 0, top_z)), P["TOP_COLOR"], "top", Matrix())
    if tfl: place(tfl, core, Matrix.Translation((0, 0, top_z)), P["TOP_COLOR"], "topfloor", Matrix())
    sh = build_star_half(); _, _, y_tip, _ = star_geom(); zt_ = top_z + P["TOP_H"] - y_tip
    Mf = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, zt_), (0, 0, 0, 1)))      # front half, faces -Y
    Mb = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, zt_), (0, 0, 0, 1)))      # back half, mirrored
    sb = new_obj("Star_Back", sh.data); sh.name = "Star_Front"
    place(sh, core, Mf, "ivory", "star", Matrix()); place(sb, core, Mb, "ivory", "star", Matrix())
    # exploded copy (linked data), shifted to the right
    exp = get_coll("AT_Exploded", root)
    for o in list(asm.all_objects):
        if o.parent: continue
        e = o.copy(); exp.objects.link(e); e.name = o.name + "_X"
        k = o.get("tier"); kind = o["part_kind"]
        nt = len(P["H"]); dz = 0
        if k: dz = (nt - k) * 105 + 30
        elif kind == "top": dz = nt * 105 + 70
        elif kind == "topfloor": dz = nt * 105 + 25
        elif kind == "star": dz = nt * 105 + 110
        out = {"module": 30}.get(kind, 0)
        th = o.matrix_world.to_euler().z
        off = Vector((math.cos(th) * out, math.sin(th) * out, dz)) + Vector((340, 0, 0))
        if o.get("half"): off += Vector((-math.sin(th), math.cos(th), 0)) * (12 if o["half"] == "B" else -12)
        e.matrix_world = Matrix.Translation(off) @ o.matrix_world
    for o in list(asm.all_objects):
        if not o.parent: continue
        e = o.copy(); exp.objects.link(e); e.name = o.name + "_X"
        e.parent = bpy.data.objects[o.parent.name + "_X"]; e.matrix_parent_inverse = Matrix(); e.matrix_basis = Matrix()
    bpy.data.collections.remove(BUILD)
    return top_z

if __name__ == "__main__" or globals().get("AT_RUN", False):
    TOP_Z = build_all()
