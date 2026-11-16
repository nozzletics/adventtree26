# Motor kit R2: extra reduction stage, the drum stays as it is.
#   motor pinion Z10 -> LOOSE gear Z36 (the old coupler gear, now turning freely on the drum gear's hub)
#   -> compound idler beside them: Z28 (meshes the loose gear) + Z14 (below it) -> DRUM gear Z50 (on the spline stud)
#   ratio 36/10 * 28/36 * 50/14 = 10.0 (old kit 3.6), same turning direction.
# Runs in the namespace of advent_tree_mech.py + advent_tree_motor.py (exec this file after both).
# Builds a COPY of ATM_MotorKit as ATM_MotorKit_R2 (shifted by R2_SHIFT); the original kit is not touched.
# Motor raised R2 so the drum gear (below) clears the shaft end; speaker shelf raised with it.

R2 = {
    "ZL": 36, "ZI1": 28, "ZI2": 14, "ZD": 50, "M": 1.0,     # 36/10 * 28/36 * 50/14 = 10.0; one day (14.4 deg of drum) = 51.43 deg of idler = 1/7 turn
    "IDLER_DEG": 45.0,                 # direction of the idler axle from the drum axis
    "D_W": 3.5, "GAP": 0.0,            # drum gear face width; axial gap drum gear -> loose gear (0 = Z36 lies flat on Z48, no collar)
    "L_W": 5.0, "I1_W": 5.0,
    "HUB_R": 15.1, "BORE_CLR": 0.1,    # drum-gear hub = axle of the loose Z36; bore 0.1 mm larger per side (dia 30.4 on 30.2) so it turns freely
    "SNAP": 0.2, "SNAP_PLAY": 0.15, "SNAP_LEAD": 0.6,   # snap bead on the hub over the Z36: radial step, axial play, lead-in height
    "COLLAR_R": 16.5,                  # thrust collar under the loose gear (clear of the pinion tips at r 17)
    "PIN_W": 6.0, "PIN_UNDER": 0.5,    # pinion width; gap between the drum gear top and the pinion
    "SHAFT_IN": 0.0,                   # shaft end flush with the pinion bottom (through bore)
    "SHELF_LESS": 1.4,                 # speaker shelf goes up 1.4 less than the motor (0.5 left above the motor, was 1.9)
    # printed idler axle (lies flat on the bed: one 0.5 mm flat along it), as thick as the Z14 allows (1.6 mm wall left)
    "AXLE_D": 8.0, "AXLE_FLAT": 0.5, "AXLE_LOW": 0.1, "AXLE_FREE": 0.3, "AXLE_TOP": 0.4,   # hole = D + this (below / idler / above)
    "AXLE_COL_R": 6.0, "AXLE_HOLE_Z0": 9.6, "AXLE_L": 35.0,
    "HUB_ABOVE": 2.0,                  # drum-gear hub (axle of the loose Z36) reaches this far above the Z36
    "POCKET_CLR": 1.0, "POCKET_FLOOR": 20.0,
    "SHIFT": (0.0, -300.0, 0.0),       # R2 copy placed this far from the original kit
}

def r2_z():
    """floor-local heights"""
    zh = P["_DRUM_TOP_FL"] + P["KEY_SEAT"]              # drum-gear bottom (where the old coupler sat)
    zd1 = zh + R2["D_W"]; zl0 = zd1 + R2["GAP"]; zl1 = zl0 + R2["L_W"]
    zp0 = zd1 + R2["PIN_UNDER"]; zp1 = zp0 + R2["PIN_W"]
    zf = zp0 + R2["SHAFT_IN"] + MK["MOT_SHAFT_L"]        # motor face: shaft end SHAFT_IN above the pinion bottom
    return dict(zh=zh, zd1=zd1, zl0=zl0, zl1=zl1, zp0=zp0, zp1=zp1, zf=zf, hub_top=max(zh + P["KEY_H"], zl1 + R2["HUB_ABOVE"]))

_mk_geom_orig = mk_geom
def mk_geom():
    """same layout as the original kit, but heights from r2_z(): zg = pinion bottom, zf = raised motor face"""
    G = _mk_geom_orig(); Z = r2_z()
    G["zg"] = Z["zp0"]; G["zf"] = Z["zf"]
    return G

def r2_idler_c():
    a = rad(R2["IDLER_DEG"]); cd = R2["M"] * (R2["ZL"] + R2["ZI1"]) / 2
    return Vector((cd * math.cos(a), cd * math.sin(a), 0)), cd

def r2_mesh_rot(ZA, rotA, beta, ZB):
    """rotation of gear B (tooth 0 direction, deg) so a tooth gap of B faces the tooth of A nearest the line A->B
    (A tooth 0 at rotA, B centre in direction beta from A); same rule as mk_pinion_rot"""
    k = round((beta - rotA) * ZA / 360.0); dg_ = rotA + 360.0 * k / ZA - beta
    return beta + 180.0 + 180.0 / ZB - dg_ * ZA / ZB

def r2_rots():
    rotL = P["FRONT_DEG"]
    rotI1 = r2_mesh_rot(R2["ZL"], rotL, R2["IDLER_DEG"], R2["ZI1"])
    rotI2 = rotI1                                         # one part: tooth 0 of both at the same angle
    rotD = r2_mesh_rot(R2["ZI2"], rotI2, R2["IDLER_DEG"] + 180.0, R2["ZD"])
    return rotL, rotI1, rotI2, rotD

def mk_pinion_rot():
    """pinion against the LOOSE gear (tooth 0 at FRONT_DEG)"""
    return r2_mesh_rot(R2["ZL"], P["FRONT_DEG"], MK["S_DEG"], MK["Z_PINION"])

def gear(name, Z, z0, z1, rot):
    pts = []
    for p in mk_gear_poly(Z, R2["M"], MK["PA"], MK["BACKLASH"]):   # Z48: root circle > base circle -> duplicate points
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 1e-4: pts.append(p)
    if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-4: pts.pop()
    o = mk_prism_xy(name, pts, z0, z1)
    o.data.transform(Matrix.Rotation(rad(rot), 4, 'Z')); return o

def r2_drum_gear():
    """Z48 on the drum's spline stud (wedges like the knob) + thrust collar + hub carrying the loose gear"""
    Z = r2_z(); rotD = r2_rots()[3]
    o = gear("MK2_DrumGear_Z%d" % R2["ZD"], R2["ZD"], Z["zh"], Z["zd1"], rotD)
    col = rings("_col", [(R2["COLLAR_R"], Z["zd1"] - 0.5), (R2["COLLAR_R"], Z["zl0"])], 96)
    hub = rings("_hub", [(R2["HUB_R"], Z["zd1"] - 0.5), (R2["HUB_R"], Z["hub_top"] - 0.3), (R2["HUB_R"] - 0.3, Z["hub_top"])], 96)
    if R2.get("SNAP"):   # bead just above the Z36: 45 deg underside holds it down, gentle lead-in on top lets it push over
        r, k = R2["HUB_R"], R2["SNAP"]; z0 = Z["zl1"] + R2["SNAP_PLAY"]
        bead = rings("_snap", [(r - 0.3, z0 - 0.3), (r, z0), (r + k, z0 + k), (r + k, z0 + k + 0.3), (r, z0 + 2 * k + 0.3 + R2["SNAP_LEAD"]), (r - 0.3, z0 + 2 * k + 0.6 + R2["SNAP_LEAD"])], 96)
        boolean(hub, [bead], 'UNION')
    boolean(o, ([col] if R2["GAP"] > 0 else []) + [hub], 'UNION')
    P["_SPL_Z"] = -P["KEY_SEAT"]
    hole = spline_stud("_hole", -1.0, P["KEY_H"] + 1.0, P["KEY_CLR"])
    hole.data.transform(Matrix.Translation((0, 0, Z["zh"])) @ Matrix.Rotation(rad(P["FRONT_DEG"]), 4, 'Z'))
    boolean(o, [hole], solver='EXACT')
    # hub taller than the stud: keep the top open (no thin roof over the spline hole)
    rt = P["SPL_RR"] * P["SPL_TAPER"] - 0.3
    boolean(o, [rings("_hto", [(rt, Z["zh"] + P["KEY_H"] - 0.5), (rt, Z["hub_top"] + 1)], 64)])
    if R2.get("MARKS"):   # assembly mark: groove on the top face pointing at the idler axle (outside the Z36)
        a = rad(R2["IDLER_DEG"]); u = Vector((math.cos(a), math.sin(a), 0)); v = Vector((-u.y, u.x, 0)); zt_ = Z["zd1"]
        r0, r1 = R2["M"] * R2["ZL"] / 2 + 1.5, R2["M"] * (R2["ZD"] / 2 - 1.25) - 0.4
        g_ = hull("_mk", [u * r + v * y + Vector((0, 0, z)) for r in (r0, r1) for y, z in ((-0.5, zt_ + 0.1), (0.5, zt_ + 0.1), (0.0, zt_ - 0.5))])
        boolean(o, [g_])
    return o

def r2_loose_gear():
    """the old Z36 gear, now free on the drum gear's hub (meshes the motor pinion and the idler's Z24)"""
    Z = r2_z()
    o = gear("MK2_LooseGear_Z36", R2["ZL"], Z["zl0"], Z["zl1"], r2_rots()[0])
    boolean(o, [rings("_lb", [(R2["HUB_R"] + R2["BORE_CLR"], Z["zl0"] - 1), (R2["HUB_R"] + R2["BORE_CLR"], Z["zl1"] + 1)], 96)])
    return o

def r2_idler():
    """compound idler: Z12 at the drum-gear level, Z24 at the loose-gear level, one part, turns on a 3 mm pin"""
    Z = r2_z(); c, _ = r2_idler_c(); _, r1, r2_, _ = r2_rots()
    lo = gear("MK2_Idler_Z%d_Z%d" % (R2["ZI1"], R2["ZI2"]), R2["ZI2"], Z["zh"], Z["zd1"], r2_)
    up = gear("_i1", R2["ZI1"], Z["zl0"], Z["zl0"] + R2["I1_W"], r1)
    sp = rings("_isp", [(R2["M"] * R2["ZI2"] / 2 - 1.25 * R2["M"], Z["zd1"] - 0.3), (R2["M"] * R2["ZI2"] / 2 - 1.25 * R2["M"], Z["zl0"] + 0.3)], 48)
    boolean(lo, [up, sp], 'UNION')
    ra = (R2["AXLE_D"] + R2["AXLE_FREE"]) / 2
    cuts = [rings("_ib", [(ra, Z["zh"] - 1), (ra, Z["zl0"] + R2["I1_W"] + 1)], 32)]
    E = R2.get("ENC")
    u_ = c.normalized(); ph = math.atan2(u_.x, -u_.y)          # sensor direction (tangential, same as in the shell); one
    # hole sits on the beam in this pose (drum on the start / a day stop); N = 25 * Z_I2 / Z_D holes -> one per day
    if R2.get("MARKS"):   # assembly mark on the Z28 top: groove pointing at the drum axis (inside the hole ring)
        w = -u_; v = Vector((-w.y, w.x, 0)); zt_ = Z["zl0"] + R2["I1_W"]
        r0, r1 = R2["SPACER_OD"] / 2 + 0.4, E["R"] - E["D"] / 2 - 0.6 if E else 8.0
        cuts_m = [hull("_mk", [w * r + v * y + Vector((0, 0, z)) for r in (r0, r1) for y, z in ((-0.5, zt_ + 0.1), (0.5, zt_ + 0.1), (0.0, zt_ - 0.5))])]
    else: cuts_m = []
    if E:   # encoder holes through the Z26 web (between the Z14 tips and the Z26 roots): IR beam passes -> pulses
        for k in range(E["N"]):
            a_ = ph + 2 * pi * k / E["N"]; hd = E["D"] / 2
            if E.get("SECTOR"):   # ring-sector window: radial sides, arcs R -+ D/2, SECTOR mm wide at R
                hw = E["SECTOR"] / 2 / E["R"]; zz = (Z["zh"] - 1, Z["zl0"] + R2["I1_W"] + 1)
                h = hull("_enc", [Vector((r * math.cos(a_ + t_), r * math.sin(a_ + t_), z)) for r in (E["R"] - hd, E["R"] + hd)
                                  for t_ in [-hw + 2 * hw * j / 4 for j in range(5)] for z in zz])
            elif E.get("SQUARE"):   # square window, sides radial / tangential
                h = box("_enc", -hd, hd, -hd, hd, Z["zh"] - 1, Z["zl0"] + R2["I1_W"] + 1)
                h.data.transform(Matrix.Translation((E["R"] * math.cos(a_), E["R"] * math.sin(a_), 0)) @ Matrix.Rotation(a_, 4, 'Z'))
            else:
                h = rings("_enc", [(hd, Z["zh"] - 1), (hd, Z["zl0"] + R2["I1_W"] + 1)], 24)
                h.data.transform(Matrix.Translation((E["R"] * math.cos(a_), E["R"] * math.sin(a_), 0)))
            cuts.append(h)
    boolean(lo, cuts + cuts_m)
    lo.data.transform(Matrix.Translation(c))
    return lo

def r2_axle_ref():
    Z = r2_z(); c, _ = r2_idler_c(); z0 = R2["AXLE_HOLE_Z0"]
    r = R2["AXLE_D"] / 2; f = r - R2["AXLE_FLAT"]; n = 48
    pts = [(r * math.cos(2 * pi * j / n), max(-f, r * math.sin(2 * pi * j / n))) for j in range(n)]
    o = prism_xy("MK2_IdlerAxle_D8", pts, z0, z0 + R2["AXLE_L"])
    o.data.transform(Matrix.Translation(c)); return o

R2.update({"SPACER_OD": 11.0, "SPACER_PLAY": 0.2})
# optical encoder on the idler: N holes in the Z26 web, 5 mm IR LED above / 5 mm IR receiver below (in the shell)
R2["MARKS"] = True                            # assembly marks on the drum gear and the idler (one-pulse-per-day phase)
R2["ENC"] = {"N": 14, "R": 10.4, "D": 2.8, "SECTOR": 1.4,   # 14 ring-sector windows (radial 2.8, 1.4 wide at R = half the old square): one on every day stop + one half-way
                              # holes: count, radius from the idler axle, diameter
             "LED_D": 5.1, "FLANGE_D": 5.9, "LED_L": 8.6,  # 5 mm LED / receiver: bore, flange bore, body length to the flange
             "AP_D": 2.0, "AP_MIN": 0.8, "RX_GAP": 0.6,    # beam aperture; material over the roof; receiver tip below the Z14
             "WALL": 1.2, "LEAD_SLOT": (3.0, 8.0), "FL_T": 1.0}   # flange thickness (LED_L = tip to flange bottom + flange)         # holder wall; side slot for the receiver leads (w, h)

def r2_spacer():
    """loose sleeve on the idler axle between the idler and the column above: keeps the idler from riding up.
    Flat bottom on the idler hub (play SPACER_PLAY), 45 deg conical top that matches the column's underside"""
    Z = r2_z(); c, _ = r2_idler_c(); cl = R2["POCKET_CLR"]
    r_up = R2["M"] * (R2["ZI1"] / 2 + 1) + cl; zt = Z["zl0"] + R2["I1_W"] + 0.5
    ro = R2["SPACER_OD"] / 2; ri = (R2["AXLE_D"] + R2["AXLE_TOP"]) / 2
    z0 = Z["zl0"] + R2["I1_W"]                                  # idler top
    zb = z0 + R2["SPACER_PLAY"]
    cone = lambda r: zt + (r_up - r) - R2["SPACER_PLAY"]        # column underside (45 deg) minus play
    o = rings("MK2_IdlerSpacer", [(ro, zb), (ro, cone(ro)), (ri + 0.6, cone(ri + 0.6))], 48)
    boolean(o, [rings("_sb", [(ri, zb - 1), (ri, cone(ri) + 1)], 48)])
    o.data.transform(Matrix.Translation(c))
    return o

def r2_shell():
    """original shell (motor pocket, ledge etc. follow the raised motor via mk_geom) + idler pocket + axle column"""
    keep = MK["DRV"]; keep2 = MK["DRV2"]
    MK["DRV"] = r2_drv1()                                    # ULN2003 clips + position (R2 only)
    keepW = MK.get("SHELL_WALL", 2.0); MK["SHELL_WALL"] = R2.get("SHELL_WALL", keepW)
    keep3 = MK["DRV3"]
    MK["DRV2"] = r2_drv2(); MK["DRV3"] = r2_drv3()
    try: o = mk_shell()
    finally: MK["DRV"] = keep; MK["DRV2"] = keep2; MK["DRV3"] = keep3; MK["SHELL_WALL"] = keepW
    Z = r2_z(); c, cd = r2_idler_c(); z1 = MK["SHELF_Z"] + MK["SHELF_T"]; z0 = P["TOP_SPLIT"] + P["DIAL_RELIEF"]
    # solid column round the axle (the lightened shell is mostly air there), kept inside the shell envelope
    col = rings("_acol", [(R2["AXLE_COL_R"], z0), (R2["AXLE_COL_R"], z1)], 48); col.data.transform(Matrix.Translation(c))
    ro = MK["WASHER_RO"]; clr = MK["POST_CAP_CLR"]; zk = 12.0 + (56.1 - clr - ro) / 0.5136
    env = rings("_aenv", [(ro, z0 - 1), (ro, zk), (mk_cap_r(z1) - clr, z1), (0.0, z1), (0.0, z0 - 1)], 128)
    boolean(col, [env], 'INTERSECT')                                  # never outside the shell (cap clearance)
    ri = P["TUBE_SPIG_R"] + P["LUG_R"] + P["BAYO_CLR"] + 1.6 + MK.get("SHELL_BORE_CLR", 0.3)
    boolean(col, [rings("_abore", [(ri, z0 - 2), (ri, z1 + 2)], 128)])   # never into the bore (top-floor boss)
    boolean(o, [col], 'UNION')
    cl = R2["POCKET_CLR"]; zf_ = R2["POCKET_FLOOR"]
    r_lo = R2["M"] * (R2["ZI2"] / 2 + 1) + cl; r_up = R2["M"] * (R2["ZI1"] / 2 + 1) + cl
    zs = Z["zl0"] - 0.5; zt = Z["zl0"] + R2["I1_W"] + 0.5
    # the idler goes in from the bore: the pocket is a slot from its seat towards the axis (both gear rims pass the
    # bore wall); 45 deg roofs everywhere, the axle column above the seat is restored afterwards
    ci = c * ((cd - R2.get("SLIDE", 12.0)) / cd)
    def rpts(rz, seg, at):
        return [Vector((at.x + r * math.cos(2 * pi * j / seg), at.y + r * math.sin(2 * pi * j / seg), z)) for r, z in rz for j in range(seg)]
    lo_rz = [(r_lo, zf_), (r_lo, zs + 0.01)]; up_rz = [(r_up, zs), (r_up, zt), (0.01, zt + r_up)]
    lo = hull("_pk_lo", rpts(lo_rz, 48, c) + rpts(lo_rz, 48, ci))
    up = hull("_pk_up", rpts(up_rz, 64, c) + rpts(up_rz, 64, ci))
    # column above the seat as it was (conical 45 deg underside from the seat roof only)
    zc0 = zt; colr = rings("_acr", [(R2["AXLE_COL_R"], zc0), (R2["AXLE_COL_R"], z1)], 48); colr.data.transform(Matrix.Translation(c))
    env2 = rings("_aenv2", [(ro, z0 - 1), (ro, zk), (mk_cap_r(z1) - clr, z1), (0.0, z1), (0.0, z0 - 1)], 128)
    boolean(colr, [env2], 'INTERSECT')
    boolean(colr, [rings("_abore2", [(ri, z0 - 2), (ri, z1 + 2)], 128), hull("_cone_c", rpts(up_rz, 64, c))])
    # axle holes: press fit below the pocket, free from the top (pin goes in from above)
    rp = (R2["AXLE_D"] + R2["AXLE_LOW"]) / 2; rf = (R2["AXLE_D"] + R2["AXLE_TOP"]) / 2
    h1 = rings("_ah1", [(rp, R2["AXLE_HOLE_Z0"]), (rp, zf_ + 0.1)], 24)
    h2 = rings("_ah2", [(rf, zt), (rf, z1 + 1)], 24)
    for x in (h1, h2): x.data.transform(Matrix.Translation(c))
    # drum gear: clearance ring in the bore at its level
    dr = R2["M"] * (R2["ZD"] / 2 + 1) + R2.get("D_CLR", cl)
    rib = P["TUBE_SPIG_R"] + P["LUG_R"] + P["BAYO_CLR"] + 1.6 + MK.get("SHELL_BORE_CLR", 0.3)
    # ... and all the way down to the foot: the shell is lowered over the drum gear (its tips are wider than the bore)
    rpass = max(rib, R2["M"] * (R2["ZD"] / 2 + 1) + R2.get("PASS_CLR", 0.5))
    dg = rings("_dgr", [(rpass, z0 - 1), (dr, Z["zh"] - 0.5), (dr, Z["zd1"] + 0.5), (rib - 0.2, Z["zd1"] + 0.5 + (dr - rib) + 0.2)], 128)   # 45 deg top
    E = R2.get("ENC"); ecuts = []
    if E:   # IR LED above the Z26 (pointing down), IR receiver below it, both 5 mm, on one vertical line through the holes
        u_ = c.normalized(); pe = c + Vector((-u_.y, u_.x, 0)) * E["R"]
        W = E["WALL"]; rh = E["LED_D"] / 2; ro_ = rh + W; rfl = E["FLANGE_D"] / 2; L = E["LED_L"]; ra_ = E["AP_D"] / 2
        roof = lambda rr: zt + r_up - rr                       # pocket roof (45 deg cone round the idler) at distance rr
        z_led = roof(E["R"] - rh) + E["AP_MIN"]                 # LED tip: full seat ring above the roof
        z_rx = Z["zh"] - E["RX_GAP"]                            # receiver tip: below the Z14 (it turns right next to it)
        FT = E["FL_T"]
        top = rings("_eled", [(ro_, zs), (ro_, z_led + L - FT)], 48)          # flange sits on the holder top
        bot = rings("_erx", [(ro_, z0), (ro_, zs)], 48)
        for x in (top, bot): x.data.transform(Matrix.Translation(pe))
        boolean(o, [top, bot], 'UNION')
        sw, sh_ = E["LEAD_SLOT"]; zst = z_rx - (L - FT)                       # receiver flange step
        k45 = rh - ra_
        parts = [rings("_eh1", [(rh, z_led), (rh, z1 + 2)], 32),                            # LED from above; leads up through
                 rings("_eh1b", [(rfl + 0.3, z_led + L - FT), (rfl + 0.3, z1 + 2)], 32),     # room for the flange above the holder
                 rings("_eh2", [(ra_, zs - 1), (ra_, z_led + 0.01)], 24),                    # beam aperture through the roof
                 rings("_eh3", [(rfl, z0 - 1), (rfl, zst), (rh, zst + (rfl - rh))], 32),     # receiver flange bore, 45 deg step
                 rings("_eh4", [(rh, zst - 0.01), (rh, z_rx + 0.3 - k45), (ra_, z_rx + 0.3)], 32),   # receiver body, 45 deg cone over the dome
                 rings("_eh5", [(ra_, z_rx - 0.5), (ra_, zs + 1)], 24)]                      # beam aperture up to the pocket
        for x in parts: x.data.transform(Matrix.Translation(pe))
        uo = Vector((pe.x, pe.y, 0)).normalized(); vo = Vector((-uo.y, uo.x, 0))   # receiver leads out sideways, gable top
        parts.append(hull("_elead", [pe + uo * x + vo * y + Vector((0, 0, z)) for x in (0.0, ro_ + 1)
                                     for y, z in ((-sw / 2, z0 - 1), (sw / 2, z0 - 1), (-sw / 2, z0 + sh_), (sw / 2, z0 + sh_), (0.0, z0 + sh_ + sw / 2))]))
        ecuts = parts
        o["enc_axis"] = [pe.x, pe.y]; o["enc_led_tip"] = z_led; o["enc_rx_tip"] = z_rx
    boolean(o, [lo, up, dg])
    boolean(o, [colr], 'UNION')
    boolean(o, [h1, h2] + ecuts)
    mk_drop_islands(o)
    if R2.get("EARS"): r2_ears(o)
    o.name = "MK2_Shell"
    return o

R2["DRV_CLIP"] = {"OV": 1.6, "TB": 2.5, "SLOT": 4.5}   # fin slots 0.5 shallower: 1.5 mm wall to the bore      # ULN2003 snap clips: hook reaches 2x further over the board (0.8 -> 1.6), board slot 3 -> 2.5
# Z50 needs the bore opened to r 27 (r 26.5 below it): inner wall 2.6 and all boards moved out to 28.5 from the axis
# -> at least 1.5 mm of wall everywhere between the bore and a board / the voids
R2["D_CLR"] = 0.5                              # radial clearance round the Z50 tips in the bore (r 26.5 everywhere)
R2["SHELL_WALL"] = 2.1                         # inner wall 25.9 -> 28.0: 1.5 mm left outside the Z50 clearance
R2["DRV_SET"] = {"p": 28.0, "DEPTH": 3.0}      # ULN2003 plane (was 26.55): 1.5 mm pad behind it; pilot holes 3.0 deep (was 4.5)

def r2_drv1():
    D = dict(MK["DRV"], **R2.get("DRV_SET", {})); D["CLIP"] = dict(MK["DRV"]["CLIP"], **R2.get("DRV_CLIP", {}))
    return D

R2["DRV2_SET"] = {"W": 18.0, "T": 1.5, "p": 29.6}   # p: clip slots end 1.5 mm outside the Z50 clearance (was 28.4)       # small 22x19 board (R2): 1 mm narrower slot, 1.5 mm thick board
R2["DRV2_CLIP"] = {"OV": 1.0, "TB": 1.5}     # its hooks reach 2x further over the board (0.5 -> 1.0)

def r2_drv2():
    D = dict(MK["DRV2"], **R2.get("DRV2_SET", {})); D["CLIP"] = dict(MK["DRV2"]["CLIP"], **R2.get("DRV2_CLIP", {}))
    return D

R2["DRV3_SET"] = {"T": 1.5, "p": 29.6}                   # small 18x19 board (R2): 1.5 mm thick board
R2["DRV3_CLIP"] = {"OV": 1.0, "TB": 1.5}     # its hooks reach 2x further over the board (0.5 -> 1.0)

def r2_drv3():
    D = dict(MK["DRV3"], **R2.get("DRV3_SET", {})); D["CLIP"] = dict(MK["DRV3"]["CLIP"], **R2.get("DRV3_CLIP", {}))
    return D

R2.update({"EARS": True, "EAR_R": (39.0, 46.5), "EAR_W": 7.0, "EAR_T": 2.5, "EAR_HOLE": 2.4})   # M2 screw ears at the rib feet

def _vol(o):
    bm = bmesh.new(); bm.from_mesh(o.data); v = abs(bm.calc_volume()); bm.free(); return v

def r2_ears(o):
    """flat screw ear at the foot of every rib (on the bed side, z0), on whichever side is free; M2 clearance hole"""
    from mathutils.bvhtree import BVHTree
    z0 = P["TOP_SPLIT"] + P["DIAL_RELIEF"]; r0, r1 = R2["EAR_R"]; W, T = R2["EAR_W"], R2["EAR_T"]
    RIB = MK.get("SHELL_RIB", 2.0); NR = MK.get("SHELL_NRIB", 12); rot = rad(mk_shelf_rot())
    bm = bmesh.new(); bm.from_mesh(o.data); tree = BVHTree.FromBMesh(bm)
    def solid(p):
        loc, nrm, i, d = tree.find_nearest(p)
        return loc is not None and (p - loc).dot(nrm) < 0
    refs = [mk_driver_board(MK[k], "_ref") for k in ("DRV", "DRV2", "DRV3") if MK.get(k)]
    refs.append(mk_motor_notch(z0 - 1, z0 + T + 1, grow=0.5))
    ears, holes, made = [], [], []
    for j in range(NR):
        if j in MK.get("RIB_SKIP", ()): continue
        a = rot + 2 * pi * (j + 0.5) / NR; u = Vector((math.cos(a), math.sin(a), 0)); v = Vector((-u.y, u.x, 0))
        if not solid(u * ((r0 + r1) / 2) + Vector((0, 0, z0 + 0.5))): continue     # rib foot not there (cut away)
        for sd in (1, -1):
            y0, y1 = sd * (RIB / 2 - 0.5), sd * (RIB / 2 + W)
            e = box_frame("_ear", Vector((0, 0, 0)), u, v, Vector((0, 0, 1)), (r0, r1), sorted((y0, y1)), (z0, z0 + T))
            clash = False
            for rf in refs:
                t_ = new_obj("_t", e.data.copy()); boolean(t_, [new_obj("_r", rf.data.copy())], 'INTERSECT')
                if _vol(t_) > 0.01: clash = True
                m = t_.data; bpy.data.objects.remove(t_); bpy.data.meshes.remove(m)
                if clash: break
            # the ear must lie on air (nothing of the shell already there except the rib itself)
            q = u * ((r0 + r1) / 2) + v * (sd * (RIB / 2 + W * 0.6)) + Vector((0, 0, z0 + 0.5))
            if clash or solid(q):
                m = e.data; bpy.data.objects.remove(e); bpy.data.meshes.remove(m); continue
            c = u * ((r0 + r1) / 2) + v * (sd * (RIB / 2 + W / 2))
            h = rings("_eh", [(R2["EAR_HOLE"] / 2, z0 - 1), (R2["EAR_HOLE"] / 2, z0 + T + 1)], 24)
            h.data.transform(Matrix.Translation(c))
            ears.append(e); holes.append(h); made.append(round(math.degrees(a), 1)); break
    bm.free()
    for rf in refs:
        m = rf.data; bpy.data.objects.remove(rf); bpy.data.meshes.remove(m)
    if ears: boolean(o, ears, 'UNION')
    if holes: boolean(o, holes)
    o["ears_deg"] = made
    return made

# ---- print prep (shell prints standing on its foot, no supports): horizontal holes get 45 deg pointed tops
def mk_tube_slot(Wd):
    """radial stadium-shaped hole through the tube wall; the top is a 45 deg gable instead of the flat top (no bridge)"""
    a = rad(Wd["ANG"]); u = Vector((math.cos(a), math.sin(a), 0)); t = Vector((-u.y, u.x, 0)); z = Vector((0, 0, 1))
    r = Wd["H"] / 2; hw = Wd["W"] / 2 - r; pts = []
    for sx in (-1, 1):
        for j in range(13):                      # lower half + the arcs up to 45 deg
            q = -pi / 2 + (3 * pi / 4) * j / 12
            for x in (22.0, 32.0):
                pts.append(u * x + t * (sx * (hw + r * math.cos(q))) + z * (Wd["ZC"] + r * math.sin(q)))
    k = math.sqrt(0.5); apex = Wd["ZC"] + r * k + hw + r * k
    for x in (22.0, 32.0): pts.append(u * x + z * apex)
    return hull("_tslot", pts)

def mk_rib_hole(ang, r, zc, dia):
    """round hole through a rib, teardrop top (45 deg)"""
    a = rad(ang); u = Vector((math.cos(a), math.sin(a), 0)); t = Vector((-u.y, u.x, 0)); R = dia / 2
    pts = [u * (r + R * math.cos(2 * pi * j / 32)) + Vector((0, 0, zc + R * math.sin(2 * pi * j / 32))) + t * y
           for j in range(32) for y in (-3.0, 3.0)]
    pts += [u * r + Vector((0, 0, zc + R * math.sqrt(2))) + t * y for y in (-3.0, 3.0)]
    return hull("_rhole", pts)

def r2_build():
    """copy ATM_MotorKit -> ATM_MotorKit_R2 (shifted), then replace coupler / pinion / motor / shell / speaker"""
    src = bpy.data.collections["ATM_MotorKit"]
    old = bpy.data.collections.get("ATM_MotorKit_R2")
    if old:
        objs = list(old.all_objects)
        if old.name in bpy.context.scene.collection.children: bpy.context.scene.collection.children.unlink(old)
        bpy.context.view_layer.update(); bpy.data.batch_remove(objs); bpy.data.collections.remove(old)
    kit = bpy.data.collections.new("ATM_MotorKit_R2"); bpy.context.scene.collection.children.link(kit)
    _colls()
    tz = derive(); t1 = TIERS[0]
    P["_DRUM_TOP_FL"] = drum_top(t1) - (t1["H"] + P["STACK_GAP"])
    S = Matrix.Translation(R2["SHIFT"])
    # motor raised by dz (drum gear under the pinion): speaker shelf goes up by the same amount
    zf_old = P["_DRUM_TOP_FL"] + P["KEY_SEAT"] + MK["MOT_SHAFT_L"]
    MK["SHELF_Z"] = R2.get("SHELF_Z0", 51.0) + (r2_z()["zf"] - zf_old) - R2["SHELF_LESS"]
    skip = {"MK_Coupler", "MK_Pinion", "MK_Motor_28BYJ48", "MK_Shell", "MK_Speaker40"}
    M = None
    for o in src.all_objects:
        if o.name == "MK_Shell": M = o.matrix_world.copy()
        if o.name in skip: continue
        c = o.copy(); c.data = o.data.copy(); kit.objects.link(c)
        c.name = o.name.replace("MK_", "MK2_"); c.data.name = c.name
        c.matrix_world = S @ o.matrix_world
        c.hide_set(o.hide_get())
    M = S @ M
    for fn, color, kind, pm in ((r2_drum_gear, "gold", "mk_gear", Matrix()), (r2_loose_gear, "gold", "mk_gear", Matrix()),
                                (r2_idler, "gold", "mk_gear", Matrix.Rotation(pi, 4, 'X')), (mk_pinion, "gold", "mk_gear", Matrix()),
                                (mk_motor, "steel", "mk_ref", Matrix()), (mk_speaker, "steel", "mk_ref", Matrix()),
                                (r2_axle_ref, "gold", "mk_axle", Matrix.Rotation(-pi / 2, 4, 'X')), (r2_shell, "ivory", "mk_shell", Matrix())):
        o = fn(); heal(o)
        for cc in list(o.users_collection): cc.objects.unlink(o)
        kit.objects.link(o); o.matrix_world = M
        o.data.materials.clear(); o.data.materials.append(material(color)); o.color = (*P["COLORS"][color], 1)
        o["part_kind"] = kind; o["print_matrix"] = [x for row in pm for x in row]
        if o.name.startswith("MK_"): o.name = o.name.replace("MK_", "MK2_")
        o.data.name = o.name
    b = bpy.data.collections.get(BLD)
    if b:
        for o in list(b.objects): bpy.data.objects.remove(o)
        bpy.data.collections.remove(b)
    return kit
