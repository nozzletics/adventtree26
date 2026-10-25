# Motor kit for the mech advent tree: replaces the knob under the cap with a 28BYJ-48 stepper + a 40x40 speaker.
# Runs inside the namespace of advent_tree_mech.py (exec'd into its globals dict `g`): uses P, TIERS, hull, rings,
# boolean, new_obj, prism_xy, sector, box, spline_stud, place-like helpers. Nothing of the tree itself is changed.
# All kit geometry is built in TOP-FLOOR-LOCAL coordinates (z = 0 at the floor's underside, axis = drum axis).

MK = {
    "M": 1.0, "Z_GEAR": 36, "Z_PINION": 10, "PA": 20.0, "BACKLASH": 0.12,   # gear pair (module, teeth, pressure angle, backlash per flank)
    "S_DEG": 90.0,                 # direction of the motor shaft from the axis (90 = back of the tree)
    "PHI": 115.0,                  # shaft -> motor body centre direction relative to the shaft direction (deg)
    "GEAR_W": 5.0, "PIN_W": 6.0,   # face widths
    "HUB_R": 15.0,                 # coupler hub around the spline stud
    "MOT_R": 14.0, "MOT_H": 19.0, "MOT_OFF": 8.0, "MOT_EAR": 17.5, "MOT_EAR_W": 7.0, "MOT_EAR_T": 0.8,
    "MOT_BOSS_R": 4.5, "MOT_BOSS_H": 1.5, "MOT_SHAFT_L": 10.0, "MOT_SHAFT_R": 2.5, "MOT_FLAT": 1.5,
    "MOT_COVER": (14.6, 17.6),     # wire cover: width, reach from the body centre (opposite the shaft)
    "PLATE_T": 2.0, "PLATE_R": 20.5,   # motor plate thickness, radius around the motor centre
    "AXIS_HOLE": 16.5,             # clear radius around the axis in the plate (coupler hub + wires)
    "SPK": 40.2, "SPK_D": 20.7, "SPK_HOLES": 16.0, "SPK_MAG_R": 11.0, "SPK_FRAME_T": 1.5, "SPK_HOLE_D": 3.0,
    "SPK_BASKET": (19.0, 15.5, 13.3), "SPK_CONE_R": 17.0,
    # ULN2003 driver board standing on edge (placed by hand in Blender): outward unit normal of its PCB plane,
    # plane distance from the axis, tangential offset of its centre, size 35 (tangential) x 32 (height) x 17 (deep),
    # 4 holes on 29 x 26, pilot for M3 self-tapping
    "DRV": {"u": (-0.8039, -0.5948), "p": 26.55, "s": 0.63, "zc": 18.6, "W": 35.0, "H": 32.0, "T": 17.0,
            "HX": 29.0, "HZ": 26.0, "PILOT": 2.5, "DEPTH": 4.5, "PAD": 4.0, "TRIM_L": 12.0,
            # snap clips on the left / right edges for a 3 mm board: vertical spring fins standing on the bed (flex
            # sideways), root sunk SLOT deep into the pad with a GAP slot on both sides, hook with a lead-in
            "CLIP": {"TB": 3.0, "CLR": 0.1, "LIP": 1.2, "OV": 0.8, "ARM": 1.0, "SLOT": 5.0, "GAP": 0.6}},
    # small board 22 x 19, 1 mm, standing on the bed between ribs, centred where rib 9 was
    "DRV2": {"ANG": -58.8, "p": 28.4, "s": 0.0, "BOTTOM": True, "W": 19.0, "H": 22.0, "T": 1.0, "HX": None,
             "PAD": 4.0, "TRIM_L": 0.0,
             "CLIP": {"TB": 1.0, "CLR": 0.1, "LIP": 1.2, "OV": 0.5, "ARM": 0.8, "SLOT": 2.3, "GAP": 0.6}},
    # cable hole through the tube above the small board: stadium W x H (round ends), centre height ZC
    "WIRE_WIN2": {"ANG": -58.8, "W": 19.0, "H": 10.0, "ZC": 38.0},
    # second small board 18 x 19, 1 mm, standing on the bed where rib 11 was
    "DRV3": {"ANG": 1.2, "p": 28.4, "s": 0.0, "BOTTOM": True, "W": 18.0, "H": 19.0, "T": 1.0, "HX": None,
             "PAD": 4.0, "TRIM_L": 0.0,
             "CLIP": {"TB": 1.0, "CLR": 0.1, "LIP": 1.2, "OV": 0.5, "ARM": 0.8, "SLOT": 2.3, "GAP": 0.6}},
    # round cable holes through ribs: (rib angle, radius of the centre, height, diameter)
    "RIB_HOLES": ((-88.8, 37.5, 14.0, 10.0), (-28.8, 37.5, 14.0, 10.0)),
    "RIB_SKIP": (6, 7, 9, 11),                # ribs removed round the driver board
    "SHELF_T": 2.0, "SHELF_HOLE_R": 18.0, "SHELF_Z": 51.0,    # speaker shelf (bottom face), frame sits on its top
    "POST_RIM": 47.6, "POST_T": 8.0, "POST_W": 10.0, "POST_ZV": 11.5, "POST_RT": 33.0,
    "POST_CAP_CLR": 1.5, "POST_FOOT_RI": 43.6, "POST_FOOT_Z": 8.0,   # outer face follows rim, then the cap cone   # sector posts: outer radius at the rim
    # (just inside the bayonet rim, r 48), radial thickness, angular width (deg), straight up to POST_ZV, then leaning to POST_RT
    "WASHER_T": 1.0, "WASHER_RI": 26.0, "WASHER_RO": 47.6, "SLOT_CLR": 0.35,   # stencil washer over the dial
    "POST_DEG": (61.2, 162.0, 248.4, 334.8),                  # mid-way between dial ticks -> feet key between the ticks
    "PAD_DEG": (61.2, 162.0),                                  # posts that carry the motor plate
    "SCREW_D": 1.8,                                            # pilot holes for M2 self-tapping screws
}

def mk_gear_poly(Z, m, pa, bl, steps=7):
    rp = Z * m / 2; ra = rp + m; rf = rp - 1.25 * m; rb = rp * math.cos(rad(pa))
    inv = lambda a: math.tan(a) - a
    psi_p = pi / (2 * Z) - bl / rp
    def psi(r):
        a = math.acos(min(1.0, rb / r)); return psi_p + inv(rad(pa)) - inv(a)
    r0 = max(rb, rf)
    rs = [r0 + (ra - r0) * j / steps for j in range(steps + 1)]
    pts = []
    for k in range(Z):
        c = 2 * pi * k / Z
        a0 = c - psi(r0)
        pts.append((rf * math.cos(a0), rf * math.sin(a0)))
        for r in rs: a = c - psi(r); pts.append((r * math.cos(a), r * math.sin(a)))
        for r in reversed(rs): a = c + psi(r); pts.append((r * math.cos(a), r * math.sin(a)))
        a1 = c + psi(r0)
        pts.append((rf * math.cos(a1), rf * math.sin(a1)))
    return pts

def mk_geom():
    """key positions (floor-local): shaft s, motor centre c, unit vectors d (shaft->centre), e (ear line)"""
    a = (MK["Z_GEAR"] + MK["Z_PINION"]) * MK["M"] / 2
    sd = rad(MK["S_DEG"]); s = Vector((a * math.cos(sd), a * math.sin(sd), 0))
    ph = sd + rad(MK["PHI"]); d = Vector((math.cos(ph), math.sin(ph), 0))
    c = s + d * MK["MOT_OFF"]; e = Vector((-d.y, d.x, 0))
    # outer ear = the one farther from the axis
    if (c + e * MK["MOT_EAR"]).length < (c - e * MK["MOT_EAR"]).length: e = -e
    z_gear = P["_DRUM_TOP_FL"] + P["KEY_SEAT"]          # coupler bottom (like the knob)
    z_face = z_gear + MK["MOT_SHAFT_L"]                  # shaft end flush with the coupler gear bottom
    return dict(a=a, s=s, c=c, d=d, e=e, zg=z_gear, zf=z_face)

def mk_prism_xy(name, poly, z0, z1):
    """like prism_xy, but the (very concave) gear caps are triangulated in 2D here, every triangle wound the same
    way: bmesh's ngon triangulation folded some cap triangles over (bottom with flipped, overlapping faces)"""
    from mathutils.geometry import tessellate_polygon
    tris = tessellate_polygon([[Vector((x, y, 0.0)) for x, y in poly]])
    bm = bmesh.new()
    a = [bm.verts.new((x, y, z0)) for x, y in poly]; b = [bm.verts.new((x, y, z1)) for x, y in poly]
    n = len(poly)
    for i, j, k in tris:
        (x0, y0), (x1, y1), (x2, y2) = poly[i], poly[j], poly[k]
        if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) < 0: j, k = k, j       # CCW seen from +Z
        if len({i, j, k}) < 3: continue
        bm.faces.new((a[i], a[k], a[j])); bm.faces.new((b[i], b[j], b[k]))         # bottom faces down, top up
    for j in range(n): bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me)

def mk_coupler():
    G = mk_geom(); zg = G["zg"]; W = MK["GEAR_W"]
    o = mk_prism_xy("MK_Coupler", mk_gear_poly(MK["Z_GEAR"], MK["M"], MK["PA"], MK["BACKLASH"]), 0.0, W)
    hub = rings("_hub", [(MK["HUB_R"], W - 0.5), (MK["HUB_R"], P["KEY_H"] - 0.6), (MK["HUB_R"] - 0.6, P["KEY_H"])], 96)
    boolean(o, [hub], 'UNION')
    P["_SPL_Z"] = -P["KEY_SEAT"]
    hole = spline_stud("_hole", -1.0, P["KEY_H"] + 1.0, P["KEY_CLR"])
    boolean(o, [hole], solver='EXACT')
    o.data.transform(Matrix.Translation((0, 0, zg)) @ Matrix.Rotation(rad(P["FRONT_DEG"]), 4, 'Z'))
    return o

def mk_pinion():
    G = mk_geom()
    o = mk_prism_xy("MK_Pinion", mk_gear_poly(MK["Z_PINION"], MK["M"], MK["PA"], MK["BACKLASH"]), 0.0, MK["PIN_W"])
    r, f = MK["MOT_SHAFT_R"] + 0.05, MK["MOT_FLAT"] + 0.05      # double-D bore (press fit on the shaft flats)
    n = 32; pts = []
    for j in range(n):
        a = 2 * pi * j / n; x, y = r * math.cos(a), r * math.sin(a)
        pts.append((x, max(-f, min(f, y))))
    boolean(o, [prism_xy("_dd", pts, -1, MK["PIN_W"] + 1)])
    o.data.transform(Matrix.Translation((G["s"].x, G["s"].y, G["zg"])) @ Matrix.Rotation(rad(mk_pinion_rot()), 4, 'Z'))
    return o

def mk_pinion_rot():
    """pinion rotation: a tooth gap faces the gear tooth that points at the pinion (gear tooth 0 at FRONT_DEG)"""
    k = round((MK["S_DEG"] - P["FRONT_DEG"]) * MK["Z_GEAR"] / 360.0)
    dg_ = P["FRONT_DEG"] + 360.0 * k / MK["Z_GEAR"] - MK["S_DEG"]
    return MK["S_DEG"] + 180.0 + 180.0 / MK["Z_PINION"] - dg_ * MK["Z_GEAR"] / MK["Z_PINION"]

def mk_motor():
    """reference 28BYJ-48 (not printed): body, boss, shaft, outer ear flat, inner ear bent up, wire cover"""
    G = mk_geom(); c, d, e, s, zf = G["c"], G["d"], G["e"], G["s"], G["zf"]
    body = rings("_mb", [(MK["MOT_R"], zf), (MK["MOT_R"], zf + MK["MOT_H"])], 64)
    body.data.transform(Matrix.Translation((c.x, c.y, 0)))
    boss = rings("_mbo", [(MK["MOT_BOSS_R"], zf - MK["MOT_BOSS_H"]), (MK["MOT_BOSS_R"], zf)], 32)
    r_, f_ = MK["MOT_SHAFT_R"], MK["MOT_FLAT"]
    shaft = prism_xy("_ms", [(r_ * math.cos(2 * pi * j / 32), max(-f_, min(f_, r_ * math.sin(2 * pi * j / 32)))) for j in range(32)],
                     zf - MK["MOT_SHAFT_L"], zf - MK["MOT_BOSS_H"])
    shaft.data.transform(Matrix.Rotation(rad(mk_pinion_rot()), 4, 'Z'))
    for o in (boss, shaft): o.data.transform(Matrix.Translation((s.x, s.y, 0)))
    w2 = MK["MOT_EAR_W"] / 2; T = MK["MOT_EAR_T"]
    def plate(pts, z0, z1):
        return hull("_me", [Vector((p.x, p.y, z)) for p in pts for z in (z0, z1)])
    ear_o = plate([c + e * (MK["MOT_R"] - 2) + d * y for y in (-w2, w2)] + [c + e * (MK["MOT_EAR"] + 3.5) + d * y for y in (-w2, w2)], zf, zf + T)
    # inner ear bent up 90 deg along the body
    base = c - e * (MK["MOT_R"] + 0.2)
    ear_i = hull("_mei", [base - e * t + d * y + Vector((0, 0, z)) for t in (0, T) for y in (-w2, w2) for z in (zf, zf + 7.0)])
    cw, cr = MK["MOT_COVER"]
    cover = hull("_mc", [c + d * x + e * y + Vector((0, 0, z)) for x in (MK["MOT_R"] - 3, cr) for y in (-cw / 2, cw / 2)
                         for z in (zf + 2.0, zf + MK["MOT_H"])])
    boolean(body, [boss, shaft, ear_o, ear_i, cover], 'UNION')
    body.name = "MK_Motor_28BYJ48"
    return body

def mk_speaker():
    """40x40 speaker per datasheet: 40.2 square frame, 4x d3 holes on 32 x 32, basket 13.3 deep from the frame face,
    magnet d22 to 20.7; frame face down on the shell top, magnet up into the cap"""
    S = MK["SPK"] / 2; z0 = MK["SHELF_Z"] + MK["SHELF_T"]; rot = Matrix.Rotation(rad(mk_shelf_rot()), 4, 'Z')
    T = MK["SPK_FRAME_T"]; rb0, rb1, hb = MK["SPK_BASKET"]
    fr = box("_sf", -S, S, -S, S, z0, z0 + T)
    bk = rings("_sb", [(rb0, z0 + T - 0.01), (rb1, z0 + hb)], 64)
    mag = rings("_sm", [(MK["SPK_MAG_R"], z0 + hb - 0.01), (MK["SPK_MAG_R"], z0 + MK["SPK_D"])], 48)
    boolean(fr, [bk, mag], 'UNION')
    hs = MK["SPK_HOLES"]; cuts = [rings("_scn", [(MK["SPK_CONE_R"], z0 - 1), (MK["SPK_CONE_R"], z0 + 0.6)], 64)]
    for x, y in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)):
        h = rings("_sh", [(MK["SPK_HOLE_D"] / 2, z0 - 1), (MK["SPK_HOLE_D"] / 2, z0 + T + 1)], 16)
        h.data.transform(Matrix.Translation((x, y, 0))); cuts.append(h)
    boolean(fr, cuts)
    fr.data.transform(rot); fr.name = "MK_Speaker40"
    return fr

def mk_shelf_rot(): return MK["POST_DEG"][0] - 45.0

def mk_cap_r(z):
    """inner radius of the cap's hollow at floor-local height z (measured: straight cone above the bayonet)"""
    return 56.1 - 0.5136 * (z - 12.0)

def mk_post_zk():
    return 12.0 + (56.1 - MK["POST_CAP_CLR"] - MK["POST_RIM"]) / 0.5136   # where the cone comes down to the rim radius

def mk_post_r(z):
    """(inner, outer) radius of the sector posts at height z: ONE straight lean from the foot profile (outer = washer /
    bayonet radius, inner just outside the dial numbers) up to the shelf, where the outer edge is POST_CAP_CLR off the cone"""
    zw = P["TOP_SPLIT"] + MK["WASHER_T"]; zt = MK["SHELF_Z"]
    ro_t = mk_cap_r(zt + MK["SHELF_T"]) - MK["POST_CAP_CLR"]
    ro = MK["POST_RIM"] + (ro_t - MK["POST_RIM"]) * (z - zw) / (zt - zw)
    return ro - (MK["POST_RIM"] - MK["POST_FOOT_RI"]), ro

def mk_post_levels():
    zw = P["TOP_SPLIT"] + MK["WASHER_T"]
    return [zw - 0.3, MK["SHELF_Z"]]

def mk_post_xy(k, z):
    """centre of post k's INNER face at height z"""
    ri, _ = mk_post_r(z); a = rad(MK["POST_DEG"][k])
    return Vector((ri * math.cos(a), ri * math.sin(a), z))

def mk_post_sector_pts(k, z, grow=0.0):
    """the foot profile (outer arc on the rim radius, radial sides, POST_W deg) moved straight inwards to height z"""
    ri0, ro0 = MK["POST_FOOT_RI"], MK["POST_RIM"]; _, ro = mk_post_r(z); sh = ro - ro0
    a0 = MK["POST_DEG"][k]; w = MK["POST_W"] / 2 + math.degrees(grow / ro0); u = Vector((math.cos(rad(a0)), math.sin(rad(a0)), 0))
    pts = []
    for j in range(7):
        a = rad(a0 - w + 2 * w * j / 6)
        for r in (ri0 - grow, ro0 + grow): pts.append(Vector((r * math.cos(a), r * math.sin(a), 0)) + u * sh + Vector((0, 0, z)))
    return pts

def mk_washer():
    """1 mm stencil washer lying on the floor over the dial: slots round every tick / number / the start dot, so the
    raised marks (DIAL_RELIEF 0.6) key it against turning and stay visible. Inner edge clear of the boss, outer edge
    just inside the bayonet rim."""
    zs = P["TOP_SPLIT"]; T = MK["WASHER_T"]; c_ = MK["SLOT_CLR"]
    o = rings("_wa", [(MK["WASHER_RO"], zs), (MK["WASHER_RO"], zs + T)], 128)
    boolean(o, [rings("_wai", [(MK["WASHER_RI"], zs - 1), (MK["WASHER_RI"], zs + T + 1)], 128)])
    r0, r1 = P["DIAL_TICK"]; rn = P["DIAL_NUM_R"]; cuts = []
    for n in range(25):
        a = rad(P["FRONT_DEG"] - P["STEP_DEG"] * n)
        v = Vector((math.cos(a), math.sin(a), 0)); u = Vector((math.sin(a), -math.cos(a), 0))
        if n == 0:
            d = rings("_wd", [(1.6 + c_ + 0.2, zs - 1), (1.6 + c_ + 0.2, zs + T + 1)], 24)
            q = v * rn; d.data.transform(Matrix.Translation((q.x, q.y, 0))); cuts.append(d); continue
        cuts.append(hull("_wt", [v * r + u * y + Vector((0, 0, z)) for r in (r0 - c_, r1 + c_) for y in (-0.7 - c_, 0.7 + c_)
                                 for z in (zs - 1, zs + T + 1)]))
        hw = (1.45 if n < 10 else 2.75) + c_
        cuts.append(hull("_wn", [v * (rn + r) + u * y + Vector((0, 0, z)) for r in (-1.8 - c_, 1.8 + c_) for y in (-hw, hw)
                                 for z in (zs - 1, zs + T + 1)]))
    boolean(o, cuts)
    return o

def mk_base():
    """washer + 4 sector posts standing on it against the bayonet rim + two pads under the motor plate.
    Prints upright, washer on the bed: posts lean ~19 deg, pads have 45 deg undersides; the shelf is separate."""
    G = mk_geom(); zw = P["TOP_SPLIT"] + MK["WASHER_T"]; zt = MK["SHELF_Z"]; zv = MK["POST_ZV"]
    parts = [mk_washer()]
    for k in range(4):
        L = mk_post_levels()
        for za, zb in zip(L[:-1], L[1:]):
            parts.append(hull("_post", mk_post_sector_pts(k, za) + mk_post_sector_pts(k, zb + (0.01 if zb < L[-1] else 0.0))))
    # pads under the motor plate: flat top at the plate's underside, 45 deg underside back into the post
    z0 = G["zf"] - MK["PLATE_T"]
    for k, dg in enumerate(MK["POST_DEG"]):
        if dg not in MK["PAD_DEG"]: continue
        p = mk_post_xy(k, z0); u = Vector((p.x, p.y, 0)).normalized(); v = Vector((-u.y, u.x, 0))
        parts.append(hull("_pad", [p + u * x + v * y + Vector((0, 0, z)) for y in (-3.0, 3.0) for x, z in
                                   ((-7.0, 0.0), (1.0, 0.0), (-7.0, -0.01), (1.0, -8.0))]))
    o = parts[0]
    boolean(o, parts[1:], 'UNION')
    cuts = []
    for k, dg in enumerate(MK["POST_DEG"]):
        if dg in MK["PAD_DEG"]:   # screw holes for the plate
            p = mk_post_xy(k, z0); u = Vector((p.x, p.y, 0)).normalized(); q = p - u * 3.5
            h = rings("_pdh", [(MK["SCREW_D"] / 2, z0 - 6), (MK["SCREW_D"] / 2, z0 + 1)], 16)
            h.data.transform(Matrix.Translation((q.x, q.y, 0))); cuts.append(h)
        q = mk_post_top_screw(k)   # pilot hole in each post top for the shelf screw
        h = rings("_pth", [(MK["SCREW_D"] / 2, zt - 7), (MK["SCREW_D"] / 2, zt + 1)], 16)
        h.data.transform(Matrix.Translation((q.x, q.y, 0))); cuts.append(h)
    boolean(o, cuts)
    o.name = "MK_Base"
    return o

def mk_post_top_screw(k):
    ri, ro = mk_post_r(MK["SHELF_Z"]); a = rad(MK["POST_DEG"][k]); r = (ri + ro) / 2
    return Vector((r * math.cos(a), r * math.sin(a), MK["SHELF_Z"]))

def mk_shelf():
    """speaker shelf (separate, prints flat): square seat + ears over the post tops (screws), centre hole for the cone,
    notch over the motor so it goes in from above"""
    zt = MK["SHELF_Z"]; S = MK["SPK"] / 2 + 2.5; rot = rad(mk_shelf_rot())
    sq = [Matrix.Rotation(rot, 3, 'Z') @ Vector((x, y, 0)) for x, y in ((-S, -S), (S, -S), (S, S), (-S, S))]
    pts = []
    for p in sq: pts += [p + Vector((0, 0, zt)), p + Vector((0, 0, zt + MK["SHELF_T"]))]
    for k in range(4):   # reach over the post tops, sized at the shelf's top face (the cone is narrower there)
        for q in mk_post_sector_pts(k, zt + MK["SHELF_T"]): pts += [q, q - Vector((0, 0, MK["SHELF_T"]))]
    o = hull("MK_Shelf", pts)
    cuts = [rings("_sh", [(MK["SHELF_HOLE_R"], zt - 1), (MK["SHELF_HOLE_R"], zt + 5)], 64)]
    hs = MK["SPK_HOLES"]
    for x, y in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)):
        p = Matrix.Rotation(rot, 3, 'Z') @ Vector((x, y, 0))
        h = rings("_shs", [(MK["SCREW_D"] / 2, zt - 1), (MK["SCREW_D"] / 2, zt + 5)], 16)
        h.data.transform(Matrix.Translation((p.x, p.y, 0))); cuts.append(h)
    for k in range(4):
        q = mk_post_top_screw(k)
        h = rings("_sps", [(1.15, zt - 1), (1.15, zt + 5)], 16); h.data.transform(Matrix.Translation((q.x, q.y, 0))); cuts.append(h)
    cuts.append(mk_motor_notch(zt - 1, zt + 5))
    boolean(o, cuts)
    return o

def mk_motor_notch(z0, z1, grow=0.8):
    """vertical prism of the motor's footprint (body, wire cover, outer ear, bent inner ear) + clearance"""
    G = mk_geom(); c, d, e = G["c"], G["d"], G["e"]; R = MK["MOT_R"] + grow; w2 = MK["MOT_EAR_W"] / 2 + grow
    pts = [c + Vector((R * math.cos(2 * pi * j / 48), R * math.sin(2 * pi * j / 48), 0)) for j in range(48)]
    cw, cr = MK["MOT_COVER"]
    pts += [c + d * x + e * y for x in (MK["MOT_R"] - 3, cr + grow) for y in (-cw / 2 - grow, cw / 2 + grow)]
    pts += [c + e * x + d * y for x in (MK["MOT_R"], MK["MOT_EAR"] + 3.5 + grow) for y in (-w2, w2)]
    pts += [c - e * x + d * y for x in (MK["MOT_R"], MK["MOT_R"] + 1.2 + grow) for y in (-w2, w2)]
    return hull("_notch", [Vector((p.x, p.y, z)) for p in pts for z in (z0, z1)])

def mk_plate():
    """motor plate: disc around the motor + tabs under the two pads; shaft/boss hole, axis clearance, ear screw,
    half-ring cradle round the body (printed flat, cradle up)"""
    G = mk_geom(); c, d, e, s, zf = G["c"], G["d"], G["e"], G["s"], G["zf"]; T = MK["PLATE_T"]; z0 = zf - T
    pts = []
    for j in range(48):
        a = 2 * pi * j / 48; q = c + Vector((MK["PLATE_R"] * math.cos(a), MK["PLATE_R"] * math.sin(a), 0)); pts += [q]
    for k, dg in enumerate(MK["POST_DEG"]):
        if dg not in MK["PAD_DEG"]: continue
        p = mk_post_xy(k, zf); u = Vector((p.x, p.y, 0)).normalized(); q = p - u * 3.5
        for j in range(12):
            a = 2 * pi * j / 12; pts.append(Vector((q.x + 3.6 * math.cos(a), q.y + 3.6 * math.sin(a), 0)))
    o = hull("MK_MotorPlate", [Vector((p.x, p.y, z)) for p in pts for z in (z0, zf)])
    cuts = [rings("_ax", [(MK["AXIS_HOLE"], z0 - 1), (MK["AXIS_HOLE"], zf + 20)], 96)]
    sh = rings("_bh", [(MK["MOT_BOSS_R"] + 0.6, z0 - 1), (MK["MOT_BOSS_R"] + 0.6, zf + 1)], 32)
    sh.data.transform(Matrix.Translation((s.x, s.y, 0))); cuts.append(sh)
    eh = rings("_eh", [(1.25, z0 - 1), (1.25, zf + 1)], 16)          # M3 self-tapping through the outer ear
    q = c + e * MK["MOT_EAR"]; eh.data.transform(Matrix.Translation((q.x, q.y, 0))); cuts.append(eh)
    for k, dg in enumerate(MK["POST_DEG"]):
        if dg not in MK["PAD_DEG"]: continue
        p = mk_post_xy(k, zf); u = Vector((p.x, p.y, 0)).normalized(); q = p - u * 3.5
        h = rings("_ph", [(1.2, z0 - 1), (1.2, zf + 1)], 16); h.data.transform(Matrix.Translation((q.x, q.y, 0))); cuts.append(h)
        # post itself passes beside the plate: keep it clear
        cuts.append(hull("_pc", mk_post_sector_pts(k, z0 - 1, 0.4) + mk_post_sector_pts(k, zf + 1, 0.4)))
    boolean(o, cuts)
    # cradle: half ring around the body on the outer side (keeps the inner side free for the wires / bent ear)
    rin, rout, hc = MK["MOT_R"] + 0.3, MK["MOT_R"] + 1.8, 9.0
    cr = rings("_cr", [(rout, zf - 0.5), (rout, zf + hc)], 64); boolean(cr, [rings("_cri", [(rin, zf - 1), (rin, zf + hc + 1)], 64)])
    cr.data.transform(Matrix.Translation((c.x, c.y, 0)))
    uc = Vector((c.x, c.y, 0)).normalized(); vc = Vector((-uc.y, uc.x, 0))
    keep = hull("_ck", [c + uc * x + vc * y + Vector((0, 0, z)) for x in (-3.0, 20) for y in (-20, 20) for z in (zf - 1, zf + hc + 1)])
    boolean(cr, [keep], 'INTERSECT')
    cw = MK["MOT_COVER"][0]
    boolean(cr, [hull("_ers", [c + e * x + d * y + Vector((0, 0, z)) for x in (10, 22) for y in (-MK["MOT_EAR_W"] / 2 - 0.6, MK["MOT_EAR_W"] / 2 + 0.6)
                                for z in (zf - 1, zf + hc + 1)])])     # room for the outer ear (full height: no bridge)
    boolean(cr, [hull("_cvs", [c + d * x + e * y + Vector((0, 0, z)) for x in (8, 22) for y in (-cw / 2 - 0.6, cw / 2 + 0.6) for z in (zf - 1, zf + hc + 1)])])
    boolean(o, [cr], 'UNION')
    return o

def mk_build(offset=(0.0, -600.0, 0.0)):
    """build the kit + context copies (top floor without detent, T1 drum top, cap) in collection ATM_MotorKit"""
    root = bpy.data.collections.get("ATM_MotorKit")
    if root:
        objs = list(root.all_objects)
        if root.name in bpy.context.scene.collection.children: bpy.context.scene.collection.children.unlink(root)
        bpy.context.view_layer.update(); bpy.data.batch_remove(objs); bpy.data.collections.remove(root); bpy.context.view_layer.update()
    root = bpy.data.collections.new("ATM_MotorKit"); bpy.context.scene.collection.children.link(root)
    _colls()
    tz = derive()
    t1 = TIERS[0]
    P["_DRUM_TOP_FL"] = drum_top(t1) - (t1["H"] + P["STACK_GAP"])      # drum top above the floor underside
    M = Matrix.Translation(P["ORIGIN"]) @ Matrix.Translation(offset) @ Matrix.Translation((0, 0, tz))
    out = {}
    for fn, color, kind, pm in ((mk_coupler, "gold", "mk_gear", Matrix()), (mk_pinion, "gold", "mk_gear", Matrix()),
                                (mk_base, "ivory", "mk_frame", Matrix()), (mk_shelf, "ivory", "mk_frame", Matrix()),
                                (mk_plate, "ivory", "mk_plate", Matrix()),
                                (mk_motor, "steel", "mk_ref", Matrix()), (mk_speaker, "steel", "mk_ref", Matrix())):
        o = fn(); heal(o)
        for cc in list(o.users_collection): cc.objects.unlink(o)
        root.objects.link(o); o.matrix_world = M
        o.data.materials.clear(); o.data.materials.append(material(color)); o.color = (*P["COLORS"][color], 1)
        o["part_kind"] = kind; o["print_matrix"] = [x for row in pm for x in row]
        out[o.name] = o
    return out, M, tz


def mk_build_all(offset=(0.0, -600.0, 0.0)):
    """kit + top floor without click springs + context copies (T1 drum, cap as hidden wire)"""
    out, M, tz = mk_build(offset)
    kitc = bpy.data.collections["ATM_MotorKit"]; O = bpy.data.objects
    P["DETENT"] = False
    try:
        cap, fl = build_top()
    finally:
        P["DETENT"] = True
    dinl = O[fl["dial_inlay"]]; del fl["dial_inlay"]
    m = cap.data; bpy.data.objects.remove(cap); bpy.data.meshes.remove(m)
    heal(fl); join_inlay(fl, dinl)
    for c in list(fl.users_collection): c.objects.unlink(fl)
    kitc.objects.link(fl); fl.name = "MK_TopFloor_NoDetent"; fl.data.name = fl.name
    fl.data.materials[0] = material(P["TOP_COLOR"]); fl.color = (*P["COLORS"][P["TOP_COLOR"]], 1)
    fl.matrix_world = M; fl["part_kind"] = "mk_floor"; fl["print_matrix"] = [x for row in Matrix() for x in row]
    for n, nm in (("M_T1_Drum", "MK_ctx_T1_Drum"), ("M_TopTier", "MK_ctx_Cap")):
        s_ = O[n]; c = s_.copy(); c.data = s_.data.copy(); kitc.objects.link(c); c.name = nm
        c.matrix_world = Matrix.Translation(offset) @ s_.matrix_world
        for k in ("print_matrix", "part_kind", "tier"):
            if k in c: del c[k]
        c["part_kind"] = "mk_ctx"
    O["MK_ctx_Cap"].display_type = 'WIRE'; O["MK_ctx_Cap"].hide_set(True)
    b = bpy.data.collections.get(BLD)
    if b:
        for o in list(b.objects): bpy.data.objects.remove(o)
        bpy.data.collections.remove(b)
    return out, M, tz


def mk_ledge_ring(rin, rout, ztop, T):
    """flat ring rin..rout, top at ztop, T thick at the free inner edge, underside rising at 45 deg from the wall
    (rout) to the inner edge, so it prints standing without supports"""
    zb = ztop - T - (rout - rin)
    o = rings("_lr", [(rout, zb), (rout, ztop)], 128)
    air = rings("_lra", [(0.0, ztop - T), (rin, ztop - T), (rin + (ztop - T - (zb - 1)), zb - 1), (0.0, zb - 1)], 128)
    boolean(o, [rings("_lri", [(rin, zb - 1), (rin, ztop + 1)], 128), air])
    return o

def mk_wire_window():
    """window through the pocket wall at the end of the motor's wire cover, for the cable; pointed 45 deg roof so
    it prints standing without a bridge"""
    G = mk_geom(); c, d, e, zf = G["c"], G["d"], G["e"], G["zf"]
    w = MK.get("WIRE_WIN_W", 10.0) / 2; zb = zf + MK.get("WIRE_WIN_Z0", 2.0); zt = zf + MK.get("WIRE_WIN_Z1", 13.0)
    x0 = MK["MOT_R"] - 1.0; x1 = MK["MOT_COVER"][1] + 12.0
    pts = []
    for x in (x0, x1):
        for y, z in ((-w, zb), (w, zb), (-w, zt), (w, zt), (0.0, zt + w)):
            q = c + d * x + e * y; pts.append(Vector((q.x, q.y, z)))
    return hull("_wwin", pts)

def mk_driver_frame(D=None):
    D = dict(D or MK["DRV"])
    if "ANG" in D: D["u"] = (math.cos(rad(D["ANG"])), math.sin(rad(D["ANG"])))
    if D.get("BOTTOM"): D["zc"] = P["TOP_SPLIT"] + P["DIAL_RELIEF"] + D["H"] / 2      # board stands on the bed level
    u = Vector((D["u"][0], D["u"][1], 0)).normalized(); t = Vector((-u.y, u.x, 0))
    return D, u, t, u * D["p"] + t * D.get("s", 0.0)

def mk_driver_board(D=None, name="MK_Driver_ULN2003"):
    """reference block of a board"""
    D, u, t, c0 = mk_driver_frame(D); z = Vector((0, 0, 1))
    o = box_frame(name, c0 + z * D["zc"], u, t, z, (0, D["T"]), (-D["W"] / 2, D["W"] / 2), (-D["H"] / 2, D["H"] / 2))
    return o

def mk_driver_mount(o, D=None):
    """flat vertical pad for the driver board: the wall is filled up to / cut back to the board plane over the
    board footprint (+PAD margin), ribs inside the board volume removed, 4 pilot holes"""
    D, u, t, c0 = mk_driver_frame(D); z = Vector((0, 0, 1)); m = D["PAD"]
    z0 = P["TOP_SPLIT"] + P["DIAL_RELIEF"]; ri = P["TUBE_SPIG_R"] + P["LUG_R"] + P["BAYO_CLR"] + 1.6 + MK.get("SHELL_BORE_CLR", 0.3)
    zb = z0; zt = D["zc"] + D["H"] / 2; C = D.get("CLIP")
    zpt = zt
    pad = box_frame("_dpad", c0, u, t, z, (-12.0, 0.0), (-D["W"] / 2 - m, D["W"] / 2 + m), (zb, zpt))
    boolean(pad, [rings("_dbore", [(ri, zb - 1), (ri, zpt + 1)], 128)])
    boolean(o, [pad], 'UNION')
    zr = zt + 0.3; L = 40.0; w2 = D["W"] / 2 + 0.3          # roof rises 45 deg away from the pad: rib stubs above print
    cut = hull("_dcut", [c0 + u * x + t * y + z * h for y in (-w2, w2) for x, h in ((0, zb - 1), (L, zb - 1), (0, zr), (L, zr + L))])
    cuts = [cut]
    if D.get("TRIM_L"):                 # rib on the -t side cut flush with the board plane: room for the wires
        y0 = -D["W"] / 2 - 0.3; y1 = y0 - D["TRIM_L"]; z1 = MK["SHELF_Z"] + MK["SHELF_T"]
        cuts.append(box_frame("_dtrim", c0, u, t, z, (0.0, 40.0), (y1, y0 + 0.01), (zb - 1, z1 + 1)))
    for sx in ((-1, 1) if D.get("HX") else ()):
        for sz in (-1, 1):
            q = c0 + t * (sx * D["HX"] / 2) + z * (D["zc"] + sz * D["HZ"] / 2)
            r = D["PILOT"] / 2                                   # teardrop: horizontal hole prints without support
            h = hull("_dh", [Vector((r * math.cos(2 * pi * j / 16), r * math.sin(2 * pi * j / 16), zz)) for j in range(16)
                             for zz in (-D["DEPTH"], 1.0)] + [Vector((0, r * 1.414, zz)) for zz in (-D["DEPTH"], 1.0)])
            R = Matrix.Identity(3); R.col[0] = t; R.col[1] = z; R.col[2] = u      # hole axis along u
            h.data.transform(Matrix.Translation(q) @ R.to_4x4()); cuts.append(h)
    if C:                                                       # free the spring fins: slot on both sides of each root
        e0 = D["W"] / 2 + C["CLR"]; e1 = e0 + C["ARM"]
        for sx in (-1, 1):
            cuts.append(box_frame("_dslot", c0, u, t, z, (-C["SLOT"] - C["GAP"], 0.01),
                                  sorted((sx * (e0 - C["GAP"]), sx * (e1 + C["GAP"]))), (zb - 1, zt)))
    boolean(o, cuts)
    if C: boolean(o, mk_driver_clips(D, u, t, c0, z0), 'UNION')

def mk_driver_clips(D, u, t, c0, z0):
    """left / right spring fins, profile in (u = out of the pad plane, e = distance from the board centre line),
    extruded vertically from the bed to the board top: no overhang anywhere"""
    C = D["CLIP"]; z = Vector((0, 0, 1)); zt = D["zc"] + D["H"] / 2
    e0 = D["W"] / 2 + C["CLR"]; e1 = e0 + C["ARM"]; ui = C["TB"] + C["CLR"]; uo = ui + C["LIP"]
    ur = -C["SLOT"] - C["GAP"] - 0.6                            # root reaches past the slot bottom into the pad
    fin = [(ur, e0), (ur, e1), (uo, e1), (uo, e0)]
    hook = [(ui, e0 - C["OV"]), (ui, e0 + 0.05), (uo, e0 + 0.05), (uo, e0)]      # lead-in: board edge pushes the fin out
    out = []
    ri = P["TUBE_SPIG_R"] + P["LUG_R"] + P["BAYO_CLR"] + 1.6 + MK.get("SHELL_BORE_CLR", 0.3)
    for sx in (-1, 1):
        for nm, poly in (("_cfin", fin), ("_chook", hook)):
            out.append(hull(nm, [c0 + u * x + t * (sx * e) + z * h for x, e in poly for h in (z0, zt)]))
    for f in out[::2]: boolean(f, [rings("_cfb", [(ri, z0 - 1), (ri, zt + 1)], 128)])   # never into the bore
    return out

def mk_drop_islands(o, keep_min=5.0):
    """delete loose slivers (boolean leftovers) smaller than keep_min mm^3"""
    bm = bmesh.new(); bm.from_mesh(o.data); seen = set(); kill = []
    for v in bm.verts:
        if v in seen: continue
        comp = []; st = [v]; seen.add(v)
        while st:
            x = st.pop(); comp.append(x)
            for ed in x.link_edges:
                y = ed.other_vert(x)
                if y not in seen: seen.add(y); st.append(y)
        faces = {f for x in comp for f in x.link_faces}
        vol = abs(sum(f.calc_center_median().dot(f.normal) * f.calc_area() for f in faces) / 3.0)
        if vol < keep_min: kill += comp
    if kill: bmesh.ops.delete(bm, geom=kill, context='VERTS')
    b2 = bm.copy()
    bmesh.ops.dissolve_degenerate(b2, edges=b2.edges[:], dist=0.002)          # zero-area slivers from the booleans
    (b2 if not any(not e.is_manifold for e in b2.edges) else bm).to_mesh(o.data)
    b2.free(); bm.free()

def mk_tube_slot(Wd):
    """radial stadium-shaped hole through the tube wall"""
    a = rad(Wd["ANG"]); u = Vector((math.cos(a), math.sin(a), 0)); t = Vector((-u.y, u.x, 0)); z = Vector((0, 0, 1))
    r = Wd["H"] / 2; hw = Wd["W"] / 2 - r; pts = []
    for sx in (-1, 1):
        for j in range(17):
            q = -pi / 2 + pi * j / 16
            for x in (22.0, 32.0):
                pts.append(u * x + t * (sx * (hw + r * math.cos(q))) + z * (Wd["ZC"] + r * math.sin(q)))
    return hull("_tslot", pts)

def mk_rib_hole(ang, r, zc, dia):
    a = rad(ang); u = Vector((math.cos(a), math.sin(a), 0)); t = Vector((-u.y, u.x, 0))
    pts = [u * (r + dia / 2 * math.cos(2 * pi * j / 32)) + Vector((0, 0, zc + dia / 2 * math.sin(2 * pi * j / 32))) + t * y
           for j in range(32) for y in (-3.0, 3.0)]
    return hull("_rhole", pts)

def mk_bore_skin(o):
    """smooth central bore: re-fill a BORE_SKIN thick skin round the bore (closes slot / pad cuts that broke
    through), except where the bore is opened on purpose (motor pocket, pinion well, boss hole, cable hole)"""
    G = mk_geom(); s, zf = G["s"], G["zf"]
    z0 = P["TOP_SPLIT"] + P["DIAL_RELIEF"]; z1 = MK["SHELF_Z"] + MK["SHELF_T"]
    ri = P["TUBE_SPIG_R"] + P["LUG_R"] + P["BAYO_CLR"] + 1.6 + MK.get("SHELL_BORE_CLR", 0.3)
    sk = rings("_skin", [(ri + MK.get("BORE_SKIN", 0.6), z0), (ri + MK.get("BORE_SKIN", 0.6), z1)], 128)
    keep = [rings("_skin_i", [(ri, z0 - 1), (ri, z1 + 1)], 128), mk_motor_notch(zf, z1 + 1)]
    pr = MK["Z_PINION"] * MK["M"] / 2 + MK["M"] + 1.0
    pw = rings("_skpw", [(pr, G["zg"] - 0.5), (pr, zf + 0.1)], 48); pw.data.transform(Matrix.Translation((s.x, s.y, 0))); keep.append(pw)
    bh = rings("_skbh", [(MK["MOT_BOSS_R"] + 0.6, zf - MK["PLATE_T"] - 1), (MK["MOT_BOSS_R"] + 0.6, zf + 1)], 32)
    bh.data.transform(Matrix.Translation((s.x, s.y, 0))); keep.append(bh)
    if MK.get("WIRE_WIN2"): keep.append(mk_tube_slot(MK["WIRE_WIN2"]))
    boolean(sk, keep)
    boolean(o, [sk], 'UNION')

def mk_shell():
    """one-piece motor housing over the dial: stepped wall (rim radius, then the cap cone), central bore of the
    top-floor boss, motor pocket from the top with two side stops, pinion well, motor platform round the axis,
    speaker platform on top (cone hole, 4 screw holes), pilot hole for the outer motor ear"""
    G = mk_geom(); c, d, e, zf, s = G["c"], G["d"], G["e"], G["zf"], G["s"]
    z0 = P["TOP_SPLIT"] + P["DIAL_RELIEF"]; z1 = MK["SHELF_Z"] + MK["SHELF_T"]
    ro = MK["WASHER_RO"]; ri = P["TUBE_SPIG_R"] + P["LUG_R"] + P["BAYO_CLR"] + 1.6 + MK.get("SHELL_BORE_CLR", 0.3); clr = MK["POST_CAP_CLR"]
    zk = 12.0 + (56.1 - clr - ro) / 0.5136
    def outer():
        return rings("_so", [(ro, z0), (ro, zk), (mk_cap_r(z1) - clr, z1), (0.0, z0), (0.0, z1)], 128)
    o = outer()
    boolean(o, [rings("_in", [(ri, z0 - 1), (ri, z1 + 1)], 128)])
    # motor platform: ring round the axis under the motor face, 45 deg underside, clear of the coupler gear
    rp = MK["Z_GEAR"] * MK["M"] / 2 + MK["M"] + 1.0; T = MK["PLATE_T"]
    plat = mk_ledge_ring(rp, ri + 0.3, zf, T)
    if MK.get("PLAT_UNDER_MOTOR", True):       # keep the motor platform only under the motor's own footprint
        boolean(plat, [mk_motor_notch(zf - 30, zf + 1, grow=0.0)], 'INTERSECT')
    # speaker platform on top: fills the bore down to the cone hole, 45 deg underside
    T2 = MK["SHELF_T"]; rh = MK["SHELF_HOLE_R"]
    spk = mk_ledge_ring(rh, ri + 0.3, z1, T2)
    boolean(o, [plat, spk], 'UNION')
    cuts = [mk_motor_notch(zf, z1 + 1)]
    pr = MK["Z_PINION"] * MK["M"] / 2 + MK["M"] + 1.0
    pw = rings("_pw", [(pr, G["zg"] - 0.5), (pr, zf + 0.1)], 48); pw.data.transform(Matrix.Translation((s.x, s.y, 0))); cuts.append(pw)
    bh = rings("_bh", [(MK["MOT_BOSS_R"] + 0.6, zf - T - 1), (MK["MOT_BOSS_R"] + 0.6, zf + 1)], 32)
    bh.data.transform(Matrix.Translation((s.x, s.y, 0))); cuts.append(bh)
    q = c + e * MK["MOT_EAR"]                                   # outer ear: M3 self-tapping pilot
    eh = rings("_eh", [(1.25, zf - 6), (1.25, zf + 1)], 16); eh.data.transform(Matrix.Translation((q.x, q.y, 0))); cuts.append(eh)
    rot = rad(mk_shelf_rot()); hs = MK["SPK_HOLES"]
    for x, y in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)):    # speaker frame screws (M2 self-tapping)
        p = Matrix.Rotation(rot, 3, 'Z') @ Vector((x, y, 0))
        h = rings("_shs", [(MK["SCREW_D"] / 2, z1 - 5), (MK["SCREW_D"] / 2, z1 + 1)], 16)
        h.data.transform(Matrix.Translation((p.x, p.y, 0))); cuts.append(h)
    boolean(o, cuts)
    # side stops for the motor body, trimmed to where the housing has material
    R = MK["MOT_R"]; r_touch = R + 0.15; r_back = R + 0.8 + 0.6
    ribs = []
    for ang in (45.0, 135.0, -45.0, -135.0):
        a = rad(ang); u = d * math.cos(a) + e * math.sin(a); v = Vector((-u.y, u.x, 0)); pts = []
        for y in (-1.5, 1.5):
            for r, z in ((r_back, zf), (r_touch, zf), (r_touch, z1 - 1.5), (R + 0.8, z1 - 0.01), (r_back, z1 - 0.01)):
                q = c + u * r + v * y; pts.append(Vector((q.x, q.y, z)))
        rb = hull("_rib", pts)
        env = outer(); boolean(env, [rings("_in2", [(ri, z0 - 1), (ri, z1 + 1)], 128)])
        boolean(rb, [env], 'INTERSECT')
        if len(rb.data.polygons): ribs.append(rb)
        else: bpy.data.meshes.remove(rb.data)
    if ribs: boolean(o, ribs, 'UNION')
    if MK.get("SHELL_TOP_LEDGE", True):
        mk_shell_ledge(o, outer, ri)
        rot = rad(mk_shelf_rot()); hs = MK["SPK_HOLES"]; cuts = []
        for x, y in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)):
            p = Matrix.Rotation(rot, 3, 'Z') @ Vector((x, y, 0))
            h = rings("_shs", [(MK["SCREW_D"] / 2, z1 - 5), (MK["SCREW_D"] / 2, z1 + 1)], 16)
            h.data.transform(Matrix.Translation((p.x, p.y, 0))); cuts.append(h)
        boolean(o, cuts)
    if MK.get("WIRE_WIN", True): boolean(o, [mk_wire_window()])
    if MK.get("SHELL_LIGHT", True): mk_shell_lighten(o)
    for key in ("DRV", "DRV2", "DRV3"):
        if MK.get(key): mk_driver_mount(o, MK[key])
    if MK.get("WIRE_WIN2"): boolean(o, [mk_tube_slot(MK["WIRE_WIN2"])])
    if MK.get("RIB_HOLES"): boolean(o, [mk_rib_hole(*h) for h in MK["RIB_HOLES"]])
    if MK.get("BORE_SKIN", 0.6) > 0: mk_bore_skin(o)
    mk_drop_islands(o)
    o.name = "MK_Shell"
    return o

def mk_motor_foot(za, zb, ga, gb):
    """true (non-convex) motor footprint as separate convex pieces, clearance ga at za growing to gb at zb:
    body cylinder, wire cover, outer ear, bent inner ear"""
    G = mk_geom(); c, d, e = G["c"], G["d"], G["e"]; R = MK["MOT_R"]; cw, cr = MK["MOT_COVER"]; w = MK["MOT_EAR_W"] / 2
    def lvl(z, gr):
        body = [c + Vector(((R + gr) * math.cos(2 * pi * j / 48), (R + gr) * math.sin(2 * pi * j / 48), 0)) for j in range(48)]
        cov = [c + d * x + e * y for x in (R - 3, cr + gr) for y in (-cw / 2 - gr, cw / 2 + gr)]
        eo = [c + e * x + d * y for x in (R, MK["MOT_EAR"] + 3.5 + gr) for y in (-w - gr, w + gr)]
        ei = [c - e * x + d * y for x in (R, R + 1.2 + gr) for y in (-w - gr, w + gr)]
        return [[Vector((p.x, p.y, z)) for p in L] for L in (body, cov, eo, ei)]
    A, B = lvl(za, ga), lvl(zb, gb)
    return [hull("_foot", a + b) for a, b in zip(A, B)]

def mk_shell_ledge(o, outer, ri):
    """2 mm ledge at the top of the motor pocket wherever the pocket (a convex hull) is wider than the motor really is;
    carries the 4th speaker screw. Underside is a 45 deg gusset so it prints standing, motor still drops in from above"""
    G = mk_geom(); zf = G["zf"]; z1 = MK["SHELF_Z"] + MK["SHELF_T"]; T = MK.get("LEDGE_T", 2.0); g = 0.8
    rh = MK["SHELF_HOLE_R"]; zl = z1 - T
    f = mk_motor_notch(zf + 0.01, z1 - 0.01)
    env = outer(); boolean(env, [rings("_lh", [(rh, zf - 1), (rh, z1 + 1)], 128)])
    boolean(f, [env], 'INTERSECT')
    cuts = mk_motor_foot(zl, z1 + 1, g, g) + mk_motor_foot(zl + 0.001, zf - 0.5, g, g + (zl - zf) + 0.5)
    cuts.append(rings("_lair", [(0.0, zf - 1), (ri + 0.3, zf - 1), (ri + 0.3, zl - (ri + 0.3 - rh)), (rh, zl), (0.0, zl)], 128))
    boolean(f, cuts)
    if len(f.data.polygons): boolean(o, [f], 'UNION')

def mk_shell_lighten(o):
    """hollow the thick wall: bottom-open annular cavity (2 mm skins: outer, inner, top) split into sectors by
    radial ribs; solid kept round the motor pocket, pinion well and every screw hole"""
    G = mk_geom(); c, e, s = G["c"], G["e"], G["s"]
    z0 = P["TOP_SPLIT"] + P["DIAL_RELIEF"]; z1 = MK["SHELF_Z"] + MK["SHELF_T"]
    ro = MK["WASHER_RO"]; ri = P["TUBE_SPIG_R"] + P["LUG_R"] + P["BAYO_CLR"] + 1.6 + MK.get("SHELL_BORE_CLR", 0.3); clr = MK["POST_CAP_CLR"]
    zk = 12.0 + (56.1 - clr - ro) / 0.5136; k = (ro - (mk_cap_r(z1) - clr)) / (z1 - zk)
    W = MK.get("SHELL_WALL", 2.0); RIB = MK.get("SHELL_RIB", 2.0); NR = MK.get("SHELL_NRIB", 12)
    off = W * math.sqrt(1 + k * k); zt = z1 - W
    zc = zk - (off - W) / k
    if MK.get("SHELL_OPEN", True):    # through voids: no outer or top skin, only inner wall + ribs + solid zones
        cav = rings("_cav", [(ro + 3, z0 - 1), (ro + 3, z1 + 1), (ri + W, z1 + 1), (ri + W, z0 - 1)], 128)
    else:
        cav = rings("_cav", [(ro - W, z0 - 1), (ro - W, zc), (ro - off - k * (zt - zk), zt), (ri + W, zt), (ri + W, z0 - 1)], 128)
    boolean(cav, [rings("_cavi", [(ri + W, z0 - 2), (ri + W, z1 + 2)], 128)])
    keep = [mk_motor_notch(z0 - 2, z1 + 2, grow=0.8 + W)]
    pr = MK["Z_PINION"] * MK["M"] / 2 + MK["M"] + 1.0 + W
    h = rings("_kpw", [(pr, z0 - 2), (pr, z1 + 2)], 48); h.data.transform(Matrix.Translation((s.x, s.y, 0))); keep.append(h)
    rot = rad(mk_shelf_rot()); hs = MK["SPK_HOLES"]
    for x, y in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)):
        p = Matrix.Rotation(rot, 3, 'Z') @ Vector((x, y, 0))
        h = rings("_kss", [(MK["SCREW_D"] / 2 + W, z0 - 2), (MK["SCREW_D"] / 2 + W, z1 + 2)], 24)
        h.data.transform(Matrix.Translation((p.x, p.y, 0))); keep.append(h)
    for j in range(NR):
        if j in MK.get("RIB_SKIP", ()): continue
        a = rot + 2 * pi * (j + 0.5) / NR; u = Vector((math.cos(a), math.sin(a), 0)); v = Vector((-u.y, u.x, 0))
        keep.append(box_frame("_krib", Vector(), u, v, Vector((0, 0, 1)), (ri - 1, ro + 1), (-RIB / 2, RIB / 2), (z0 - 2, z1 + 2)))
    boolean(cav, keep)
    boolean(o, [cav])
