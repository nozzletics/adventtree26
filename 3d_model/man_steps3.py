import bpy, math
from mathutils import Vector, Matrix
V = Vector
def bc(name):
    o = bpy.data.objects[name]; vs = [o.matrix_world @ v.co for v in o.data.vertices]
    lo = V([min(v[i] for v in vs) for i in range(3)]); hi = V([max(v[i] for v in vs) for i in range(3)])
    return (lo + hi) / 2, lo, hi
def boxmag(k, n, M=None):
    d = cell_deg(n - TIER[k]["first"])
    return add(sc_cur[0], f"M_T{k}_Magnets", M, mesh=part(f"M_T{k}_Magnets", d, 25.2, 99))
sc_cur = [None]
def core_stack(sc, upto=1, M=None):
    for k in range(4, upto - 1, -1): tier_core(sc, k, M=M)
def f11(sc):
    sc_cur[0] = sc
    add(sc, "M_T4_C19_A", T(-16, 0, 0)); add(sc, "M_T4_C19_B", T(16, 0, 0))
    boxmag(4, 19, T(16, 14, 0))
    cam(sc, ORI + V((0, -80, 45)), 140, 22, 210)
    return {"A": ORI + V((-40, -95, 60)), "B": ORI + V((40, -95, 60)), "mag": ORI + V((16, -27 + 14, 23.1)),
            "pocket": ORI + V((16, -27.5, 23.1)), "lip": ORI + V((16, -70, 84)), "window": ORI + V((16, -26, 33))}
def f13(sc):
    tier_core(sc, 4)
    tier_core(sc, 3, drum=False, latches=False, mags=None, M=T(0, 0, 30) @ Rz(40))
    cam(sc, ORI + V((0, -30, 100)), -90, -18, 120)
    return {"arrow_low": ORI + rdir(-90) * 25 + z(84), "arrow_up": ORI + rdir(-50) * 29 + z(119),
            "lug": ORI + rdir(90) * 24 + z(96), "spigot": ORI + rdir(-90) * 22 + z(95)}
def f14(sc):
    tier_core(sc, 4); tier_core(sc, 3, drum=False, latches=False, mags=None)
    cam(sc, ORI + V((0, -30, 88)), -90, -18, 90)
    return {"arrow_low": ORI + rdir(-90) * 25 + z(84), "arrow_up": ORI + rdir(-90) * 29 + z(89)}
def f15(sc):
    add(sc, "M_T4_Drum"); add(sc, "M_T3_Drum", T(0, 0, 45))
    cam(sc, ORI + z(120), -60, -12, 150)
    return {"collar": ORI + rdir(-60) * 13.3 + z(93), "wide": ORI + rdir(-90) * 14.6 + z(94),
            "slot": ORI + rdir(-90) * 14 + z(89 + 45 + 2), "drum3": ORI + rdir(-60) * 16.5 + z(150)}
def f16(sc):
    core_stack(sc, 1)
    cam(sc, ORI + z(190), -65, 18, 520)
    return {"t4": ORI + rdir(-130) * 110 + z(10), "t3": ORI + rdir(-130) * 95 + z(91), "t2": ORI + rdir(-130) * 80 + z(172),
            "t1": ORI + rdir(-130) * 64 + z(253)}
def f17(sc):
    tier_core(sc, 1)
    add(sc, "M_TopFloor", T(0, 0, 30) @ Rz(40))
    cam(sc, ORI + V((0, -30, 340)), -90, -15, 140)
    return {"arrow_low": ORI + rdir(-90) * 25 + z(327), "arrow_up": ORI + rdir(-50) * 29 + z(362),
            "springs": ORI + rdir(0) * 18 + z(345), "floor": ORI + rdir(-120) * 60 + z(363)}
def f17b(sc):
    tier_core(sc, 1); add(sc, "M_TopFloor")
    cam(sc, ORI + z(345), -90, 55, 150)
    return {"dial": ORI + rdir(-90) * 40 + z(334.6), "stud": ORI + z(356), "rim": ORI + rdir(-140) * 50 + z(340),
            "springs": ORI + rdir(10) * 19 + z(345)}
def f18(sc):
    tier_core(sc, 1); add(sc, "M_TopFloor"); add(sc, "M_Key", T(0, 0, 30))
    cam(sc, ORI + z(360), -90, 50, 110)
    return {"key": ORI + rdir(-90) * 20 + z(392), "stud": ORI + z(357), "gap": ORI + rdir(-90) * 12 + z(357),
            "dot": ORI + rdir(-90) * 38 + z(334.6)}
def f19(sc):
    tier_core(sc, 1); add(sc, "M_TopFloor"); add(sc, "M_Key")
    add(sc, "M_TopTier", T(0, 0, 70) @ Rz(-40))
    cam(sc, ORI + z(390), -70, 12, 300)
    return {"cap": ORI + rdir(-70) * 40 + z(470), "rim": ORI + rdir(-70) * 50 + z(338), "key": ORI + rdir(-90) * 15 + z(362)}
def f20(sc):
    c, lo, hi = bc("M_Star_Front")
    cap = add(sc, "M_TopTier")
    add(sc, "M_Star_Front", T(0, -14, 25)); add(sc, "M_Star_Back", T(0, 14, 25))
    prim(sc, "cyl", (0.875, 9.5), Matrix.Translation(V((c.x, 0, c.z + 25 + 0.0))) @ Matrix.Rotation(math.radians(90), 4, 'X'), "PLA_brass")
    cam(sc, V((c.x, 0, c.z + 5)), -40, 10, 120)
    return {"front": V((c.x - 25, -14, c.z + 40)), "back": V((c.x + 25, 14, c.z + 40)), "pin": V((c.x, 0, c.z + 25)),
            "stem": V((c.x, -14, lo.z + 25 + 5)), "socket": V((c.x, 0, lo.z + 8))}
def full(sc, day=0, out_box=None, pull=40):
    """whole tree, drums + key turned to `day`; box out_box pulled out by `pull` mm"""
    step = -360.0 / 25 * day
    for n in asm_names():
        if "_Drum" in n or n == "M_Key": add(sc, n, Rz(step)); continue
        if out_box and (f"_C{out_box:02d}_" in n):
            k = int(n[3]); d = cell_deg(out_box - TIER[k]["first"])
            add(sc, n, T(*(rdir(d) * pull))); continue
        if n.endswith("_Magnets"):
            k = int(n[3])
            def keep(c, k=k):
                q = c - ORI; r = q.xy.length; a = math.degrees(math.atan2(q.y, q.x))
                return not (out_box and r > 25.2 and TIER[k]["first"] <= out_box < TIER[k]["first"] + 6
                            and angdiff(a, cell_deg(out_box - TIER[k]["first"])) < 20)
            add(sc, n, mesh=split_mesh(n, keep))
            if out_box and TIER[k]["first"] <= out_box < TIER[k]["first"] + 6:
                d = cell_deg(out_box - TIER[k]["first"])
                add(sc, n, T(*(rdir(d) * pull)), mesh=part(n, d, 25.2, 99))
            continue
        add(sc, n)
def f12(sc):
    full(sc, 1, 1, 45)
    cam(sc, ORI + z(270), -70, 22, 300)
    return {"box": ORI + rdir(-90) * 125 + z(300), "tube": ORI + rdir(-90) * 26 + z(290)}
def f21(sc):
    for n in asm_names():
        if n in ("M_TopTier", "M_Star_Front", "M_Star_Back"): continue
        if "_Drum" in n or n == "M_Key": add(sc, n, Rz(-360.0 / 25 * 7)); continue
        add(sc, n)
    cam(sc, ORI + z(340), -90, 89.5, 160)
    return {"pointer": ORI + rdir(-90 + 360.0 / 25 * -7) * 30 + z(345), "dot": ORI + rdir(-90) * 38 + z(335)}
