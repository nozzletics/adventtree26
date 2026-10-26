# nozzletics — Advent Tree MINI / NO-LOCK variant
# Same tree as the mech version (advent_tree_mech.py is loaded and reused), scaled to 70 %, WITHOUT the locking
# mechanism: no inner drum, no latches, no knob / day pointer, no dial numbers under the cap, no detent.
# Boxes are held only by the 6x3 magnets (magnet size unchanged): one magnet in each box's hub wall, one in the
# tube, all at the same height. Gap between neighbouring boxes 0.9 mm (mech 0.4 + 0.5).
# Builds into collections AdventTreeMini / ATN_*, objects prefixed "N_".
import bpy, math, os
from mathutils import Vector, Matrix

MECH_PATH = globals().get("MECH_PATH") or os.path.join(
    os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd(),
    "advent_tree_mech.py")
_run = globals().get("AT_RUN", False)
AT_RUN = False
exec(compile(open(MECH_PATH, encoding="utf-8").read(), MECH_PATH, "exec"), globals())
AT_RUN = _run

S = 0.7   # scale of the whole tree
P.update({
    "H": [56.0] * 4, "R_BOTTOM": 137.5 * S, "OVERHANG": 15.0 * S,
    "TOP_H": 110.0 * S, "TOP_TIP_R": 9.0 * S, "TOP_ROOF_GAP": 14.0,
    "TOP_RIM_R": 50.0 * S, "TOP_RIM_H": 8.0 * S,
    "CB": 8.0 * S, "CBH": 8.0 * S, "CT": 8.0 * S, "CTH": 8.0 * S,
    # trunk tube: magnets sit in its wall (pocket 3.1 deep), bore stays open for the garland cable
    "HUB_R": 8.75, "TUBE_RI": 3.5, "TUBE_SPIG_R": 5.75, "BORE_R": 3.5,   # trunk Ø17.5 (half of the first mini's Ø35)
    "HUB_LIP": False,                    # thin trunk: the hub strip of half B spans the whole box width, no lap plate
    "LATCH": False, "DETENT": False, "DRUM_SEAT": False, "TIER_SCREW": False, "CAP_ARROW": False,
    "MAG_Z": 28.0, "MAG_STAGGER": 4.0,   # NO-LOCK: magnet centre height (tier-local); neighbours alternate +-4 mm, because
                                         # six Ø6.2 pockets at one height would run into each other in the thin trunk
    "SPIG_H": 7.0, "LUG_W": (6.0, 4.0, 4.0),
    "TOP_BOSS_H": 12.5,                  # top floor boss: tube socket only
    "PULL_TAB": True, "TAB_W": 36.8 * S, "TAB_T": 2.4, "TAB_DROP": 8.0 * S, "TAB_DIMPLE": 0.0,
    "GAP": 0.9,
    "TRAY_T": 3.0, "TRAY_SET": 12.0 * S, "TRAY_MAXR": 130.0 * S, "TRAY_PLAY": 2.0,
    "NUM_MARGIN": 7.0 * S,
    "BASE_R": 110.0 * S, "BASE_H": 8.0 * S,
    "STAR_R": 36.0 * S, "STAR_RI": 15.3 * S, "STAR_T": 2.9 * S, "STAR_APEX": 9.0 * S,
    "STEM_W0": 9.7 * S, "STEM_W1": 6.0 * S, "STEM_L": 30.1 * S, "STEM_GAP": 1.3 * S, "STAR_PIN_DEPTH": 4.0,
    "BRAND_W": 82.0 * S, "CELL_STAMP_W": 16.0 * S, "BRAND_Y": -58.0 * S,
    "CABLE_GROOVE_W": 10.0 * S, "CABLE_GROOVE_D": 5.0 * S,
    "ORIGIN": (0.0, 0.0, 0.0), "PREFIX": "N_",
})
ROOT, ASM, EXP, BLD = "AdventTreeMini", "ATN_Assembly", "ATN_Exploded", "_build_n"

# ------------------------------------------------------------------ magnets: one fixed height, no rods / latches
def rod_z(i): return P["MAG_Z"] + (P["MAG_STAGGER"] if i % 2 else -P["MAG_STAGGER"])
def mag_dz(): return 0.0
def boss_range(i):
    hw = pocket_r() + P["MAG_SKIN"]; return rod_z(i) - hw, rod_z(i) + hw

_cell_boss_mech = cell_boss
def cell_boss(t, i, o):
    """mech boss + pocket, but the boss is clipped 0.3 mm inside both side faces (it is wider than the box at the thin trunk)"""
    global boolean
    _b = boolean; a, g = t["a"], t.get("gap", P["GAP"]) / 2 + 0.3
    def clip_union(obj, cutters, op='DIFFERENCE', solver='MANIFOLD'):
        if op == 'UNION' and cutters and cutters[0].name.startswith("_boss"):
            pts = []
            for sgn in (1, -1):
                u = Vector((math.cos(a), sgn * math.sin(a), 0)); n = Vector((-math.sin(a), sgn * math.cos(a), 0))
                pts += [u * r - n * g + Z * z for r in (3.0, 60.0) for z in (-5, t["H"] + 5)]
            _b(cutters[0], [hull("_wedge", pts)], 'INTERSECT')
        return _b(obj, cutters, op, solver)
    boolean = clip_union
    try: _cell_boss_mech(t, i, o)
    finally: boolean = _b

def cell_tab(t, o):
    """pull tab without the dimple"""
    tab, dim = make_tab(t, t["R"], math.tan(rad(P["TILT"])), P["CBH"] - P["TAB_DROP"], tab_width(t["R"]) / 2)
    bpy.data.objects.remove(dim)
    wb_, wm_, _ = wall_offsets()
    cav = hull("_tcv", levels(t, [(P["FLOOR"] - 0.3, rho(t, P["FLOOR"] - 0.3), wb_ - 0.3),
                                   (P["CBH"] + 0.6, rho(t, P["CBH"] + 0.6), wm_ - 0.3),
                                   (t["zl"] - 0.6, rho(t, t["zl"] - 0.6), wm_ - 0.3)]))
    boolean(tab, [cav])
    boolean(o, [tab], 'UNION')

def plain_bore(z_top):
    """tube bore TUBE_RI; above the bayonet socket a 45 deg cone narrows from the socket bore to it (no flat ceiling)"""
    ri, rs, z0 = P["TUBE_RI"], P["TUBE_SPIG_R"] + 0.3, P["SPIG_H"] + 0.6
    return [rings("_bb", [(ri, -1), (ri, z_top)], 128),
            rings("_bc", [(rs, -1), (rs, z0), (ri - 0.01, z0 + (rs - ri) + 0.01)], 128)]

def build_carrier(t, merged=False):
    """tray + tube up to the next tier, bayonet spigot on top / socket below, one 6x3 magnet pocket per box"""
    T, top = P["TRAY_T"], t["H"] + P["STACK_GAP"]
    tr = t["tray_r"] - P["TRAY_PLAY"]; rs = P["TUBE_SPIG_R"]
    o = rings(f"T{t['k']+1}_Carrier", [(tr, 0), (tr, T - 0.8), (tr - 0.8, T)], 128)
    boolean(o, [rings("_tube", [(P["HUB_R"], T - 0.5), (P["HUB_R"], top)], 128)] + spigot(top, r=rs), 'UNION')
    if merged:
        cut = [rings("_bb", [(P["TUBE_RI"], -1), (P["TUBE_RI"], top + P["SPIG_H"] + 1)], 128)]
    else:
        cut = socket(0, r=rs) + plain_bore(top + P["SPIG_H"] + 1)
        if P["BAYO_MARK"]: cut += mark_bottom()
    if P["BAYO_MARK"]: cut += mark_top(top)
    for i in range(t["n"]):
        pk = radial_cyl("_tp", pocket_r(), P["HUB_R"] - P["MAG_T"] - 0.1, P["HUB_R"] + 1, rod_z(i))
        pk.data.transform(Matrix.Rotation(theta(t, i), 4, 'Z')); cut.append(pk)
    return boolean(o, cut)

def build_magnets(t):
    """reference only (not printed): tube magnets + box magnets"""
    objs = []
    for i in range(t["n"]):
        R_ = Matrix.Rotation(theta(t, i), 4, 'Z'); md = P["MAG_D"] / 2; zm = rod_z(i)
        m1 = radial_cyl("_m1", md, P["HUB_R"] - P["MAG_T"], P["HUB_R"], zm, 32)
        m2 = radial_cyl("_m2", md, r_in() + P["MAG_SET"], r_in() + P["MAG_SET"] + P["MAG_T"], zm, 32)
        for o in (m1, m2): o.data.transform(R_)
        objs += [m1, m2]
    bm = bmesh.new()
    for o in objs: bm.from_mesh(o.data)
    me = bpy.data.meshes.new(f"T{t['k']+1}_Magnets"); bm.to_mesh(me); bm.free()
    for o in objs:
        m = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(m)
    return new_obj(f"T{t['k']+1}_Magnets", me)

def build_base():
    Bh, R = P["BASE_H"], P["BASE_R"]
    o = rings("Base", [(R, 0), (R, Bh - 2), (R - 2, Bh)], 96)
    carn = P.pop("_BASE_CAR", None)
    if P["CABLE"]:   # garland: up through the trunk, out along a groove on the underside to the back edge
        w, d = P["CABLE_GROOVE_W"] / 2, P["CABLE_GROOVE_D"]
        boolean(o, [rings("_cbore", [(P["BORE_R"], -1), (P["BORE_R"], Bh + 1)], 32),
                    box("_cgroove", -w, w, 0.0, R + 5, -1, d)])
    tc = stamp_cutter("_brand", P["BRAND_STAMP"], P["BRAND_W"], Vector((0, P["BRAND_Y"], 0)), -X, Y, -Z, -P["STAMP_DEPTH"], 1.0)
    if tc is None and P["BRAND"]:
        tc = text_cutter("_brand", P["BRAND"], 8, 70, Vector((0, P["BRAND_Y"], 0)), -X, Y, -Z, -0.6, 1.0)
    if tc: boolean(o, [tc], solver='EXACT')
    if carn:   # bottom tier's carrier is part of the base
        car = bpy.data.objects[carn]; car.data.transform(Matrix.Translation((0, 0, TIERS[-1]["z0"])))
        boolean(o, [car], 'UNION')
    return o

_build_top_mech = build_top
def build_top():
    """cap + top floor (rim bayonet for the cap, boss with the socket onto the T1 tube, plain bore) - no dial, no detent"""
    global build_dial, boolean
    keep = build_dial; _bool = boolean
    def _skip(obj, cutters, op='DIFFERENCE', solver='MANIFOLD'):   # the dial cut (EXACT) is dropped
        live = [c for c in cutters if not c.name.startswith("_nodial")]
        for c in cutters:
            if c not in live: bpy.data.objects.remove(c)
        return _bool(obj, live, op, solver) if live else obj
    boolean = _skip
    def no_dial(zs):
        d = box("_nodial", -0.1, 0.1, -0.1, 0.1, -50, -49)   # dummy cutter far below the part
        inl = box("_noinl", -0.1, 0.1, -0.1, 0.1, -50, -49)
        return d, inl
    build_dial = no_dial
    _bb = globals()["bearing_bore"]
    globals()["bearing_bore"] = lambda z_top, zb: plain_bore(z_top)
    try:
        cap, fl = _build_top_mech()
    finally:
        build_dial = keep; boolean = _bool; globals()["bearing_bore"] = _bb
    n = fl.pop("dial_inlay", None)
    if n and bpy.data.objects.get(n):
        ob = bpy.data.objects[n]; m = ob.data; bpy.data.objects.remove(ob); bpy.data.meshes.remove(m)
    return cap, fl

def _colls():
    global BUILD
    root = get_coll(ROOT); asm = get_coll(ASM, root); BUILD = get_coll(BLD)
    return root, asm

def _place(o, coll, M, color, kind, print_M):
    place(o, coll, M, color, kind, print_M); o["variant"] = "nolock"

def build_tier(k):
    derive(); _, asm = _colls(); t = TIERS[k]
    tc = get_coll(f"ATN_T{k+1}_{t['n']}x", asm)
    base = build_cell(t)
    for i in range(t["n"]):
        num = t["first"] + i
        Mw = Matrix.Translation((0, 0, t["zm"])) @ Matrix.Rotation(theta(t, i), 4, 'Z')
        hA, hB, (nA, nB) = split_cell(t, *number_cell(t, base, num))
        a_ = t["a"]
        print_A = frame_matrix(Vector(), Z, Vector((math.cos(a_), -math.sin(a_), 0)),
                               Vector((math.sin(a_), math.cos(a_), 0))).inverted()
        print_B = Matrix.Rotation(pi, 4, 'X') @ frame_matrix(Vector(), Z, Vector((math.cos(a_), math.sin(a_), 0)),
                                                            Vector((-math.sin(a_), math.cos(a_), 0))).inverted()
        _place(hA, tc, Mw, t["color"], "module", print_A); hA["compartment"] = num; hA["half"] = "A"
        _place(hB, tc, Mw, t["color"], "module", print_B); hB["compartment"] = num; hB["half"] = "B"
        for h, q in ((hA, nA), (hB, nB)):
            if q is not None: join_inlay(h, q)
        t.pop("boss_z", None)
    m = base.data; bpy.data.objects.remove(base); bpy.data.meshes.remove(m); bpy.data.meshes.remove(t["lip"])
    M0 = Matrix.Translation((0, 0, t["z0"]))
    if P["BASE_MERGE"] and k == len(P["H"]) - 1:
        car = build_carrier(t, merged=True); P["_BASE_CAR"] = car.name
    else:
        _place(build_carrier(t), tc, M0, t["color"], "carrier", Matrix())
    _place(build_magnets(t), tc, M0, "steel", "hardware", Matrix())

def build_core():
    top_z = derive(); _, asm = _colls()
    core = get_coll("ATN_Core", asm)
    _place(build_base(), core, Matrix(), "green", "base", Matrix())
    cap, tfl = build_top()
    _place(cap, core, Matrix.Translation((0, 0, top_z)), P["TOP_COLOR"], "top", Matrix())
    _place(tfl, core, Matrix.Translation((0, 0, top_z)), P["TOP_COLOR"], "topfloor", Matrix())
    sh = build_star_half(); _, _, y_tip, _ = star_geom(); zt_ = top_z + P["TOP_H"] - y_tip
    Mf = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, zt_), (0, 0, 0, 1)))
    Mb = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, zt_), (0, 0, 0, 1)))
    sb = new_obj("Star_Back", sh.data); sh.name = "Star_Front"
    _place(sh, core, Mf, "gold", "star", Matrix()); _place(sb, core, Mb, "gold", "star", Matrix())
    return top_z

def build_exploded():
    derive(); root, asm = _colls()
    old = bpy.data.collections.get(EXP)
    if old:
        bpy.data.batch_remove(list(old.all_objects)); bpy.data.collections.remove(old)
    exp = get_coll(EXP, root); nt = len(P["H"]); step = 105 * S
    for o in list(asm.all_objects):
        e = o.copy(); exp.objects.link(e); e.name = o.name + "_X"
        k = o.get("tier"); kind = o["part_kind"]; dz = 0
        if k: dz = (nt - k) * step + (0 if k == nt else 20)
        elif kind == "top": dz = nt * step + 50
        elif kind == "topfloor": dz = nt * step + 18
        elif kind == "star": dz = nt * step + 80
        out = {"module": 22}.get(kind, 0)
        th = o.matrix_world.to_euler().z
        off = Vector((math.cos(th) * out, math.sin(th) * out, dz)) + Vector((240, 0, 0))
        if o.get("half"): off += Vector((-math.sin(th), math.cos(th), 0)) * (8 if o["half"] == "B" else -8)
        e.matrix_world = Matrix.Translation(off) @ o.matrix_world
    b = bpy.data.collections.get(BLD)
    if b:
        for o in list(b.objects): bpy.data.objects.remove(o)
        bpy.data.collections.remove(b)

def build_all():
    top_z = build_begin()
    for k in range(len(P["H"])): build_tier(k)
    build_core(); build_exploded()
    return top_z

if AT_RUN:
    TOP_Z = build_all()
