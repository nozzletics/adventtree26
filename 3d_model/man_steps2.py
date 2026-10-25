import bpy, math
from mathutils import Vector, Matrix
V = Vector
def f03(sc):
    L = V((2600, 0, 0)); mat("PLA_screw", (0.55, 0.56, 0.6))
    placec(sc, "M_T4_Latch_19", L)
    placec(sc, "M_T4_Pins", L + V((28, 0, 0)), mesh=part("M_T4_Pins", -90), R=Matrix.Rotation(math.radians(90), 4, 'Z'))
    placec(sc, "M_T4_Magnets", L + V((40, 0, 0)), mesh=part("M_T4_Magnets", -90, 0, 25.2))
    placec(sc, "M_T4_Magnets", L + V((49, 0, 0)), mesh=part("M_T4_Magnets", -90, 25.2, 99))
    prim(sc, "cyl", (1.0, 6.0), Matrix.Translation(L + V((60, 0, 0))), "PLA_screw")
    prim(sc, "cyl", (1.9, 1.2), Matrix.Translation(L + V((60, 0, 3.6))), "PLA_screw")
    prim(sc, "cyl", (0.875, 9.5), Matrix.Translation(L + V((70, 0, 0))) @ Matrix.Rotation(math.radians(90), 4, 'X'), "PLA_brass")
    cam(sc, L + V((36, 0, 0)), -90, 30, 95)
    return {"latch": L, "pin": L + V((28, 0, 0)), "magnet": L + V((40, 0, 0)), "magnet2": L + V((49, 0, 0)),
            "screw": L + V((60, 0, 3)), "starpin": L + V((70, 0, 0))}
def f04(sc):
    add(sc, "M_Base"); cam(sc, ORI + z(45), -62, 28, 250)
    return {"base": ORI + rdir(-125) * 90 + z(8), "tube": ORI + rdir(-40) * 25 + z(60),
            "slot": ORI + rdir(-90) * 25 + z(33), "pocket": ORI + rdir(-90) * 25 + z(23.1),
            "arrow": ORI + rdir(-90) * 25 + z(85), "spigot": ORI + rdir(-60) * 22 + z(94)}
def f07(sc):
    tier_core(sc, 4, drum=False, latches=False, mags="tube")
    add(sc, "M_T4_Drum", T(0, 0, 120))
    cam(sc, ORI + z(110), -62, 22, 330)
    return {"drum": ORI + rdir(-62) * 16.5 + z(160), "collar": ORI + rdir(-62) * 14 + z(120 + 82),
            "wide": ORI + rdir(-90) * 14.6 + z(120 + 85), "tube": ORI + rdir(-40) * 25 + z(60)}
def latch_frame():
    o = bpy.data.objects["M_T4_Latch_19"]; vs = [o.matrix_world @ v.co for v in o.data.vertices]
    ymin = min(v.y for v in vs); end = [v for v in vs if v.y < ymin + 0.01]
    c = sum(end, V()) / len(end); return ymin, c
def f08(sc):
    tier_core(sc, 4, drum=True, latches=False, mags="tube")
    for n in range(20, 25): add(sc, f"M_T4_Latch_{n:02d}")
    add(sc, "M_T4_Latch_19", T(0, -22, 0))
    add(sc, "M_T4_Pins", T(26, 0, 0), mesh=part("M_T4_Pins", -90))
    for d in (-30, 30, 90, 150, 210):
        add(sc, "M_T4_Pins", mesh=part("M_T4_Pins", d))
    cam(sc, ORI + V((8, -28, 33)), -55, 18, 95)
    return {"slot": ORI + V((0, -25, 33)), "latch": ORI + V((0, -51, 33)), "pin": ORI + V((35, -22.4, 33)),
            "hole": ORI + V((8.7, -22.4, 33)), "tooth": ORI + V((0, -53, 28))}
def f08b(sc):
    tier_core(sc, 4, drum=True, latches=True, mags="tube")
    cam(sc, ORI + V((0, -28, 33)), -55, 18, 95)
    return {"latch": ORI + V((0, -31, 33)), "pin": ORI + V((8.7, -22.4, 33))}
def f09(sc):
    S0 = V((950, 600, 0))
    for n in ("SEC7_Base", "SEC7_T4_Drum", "SEC7_T4_Latch_19", "SEC7_T4_Pins", "SEC7_T4_Magnets", "SEC7_T4_C19_A", "SEC7_T4_C19_B"):
        if n in bpy.data.objects: add(sc, n)
    cam(sc, S0 + V((0, -30, 32)), 180, 0, 75)
    return {"tail": S0 + V((0, -18, 31)), "flange": S0 + V((0, -18.3, 28.4)), "tooth": S0 + V((0, -29, 27.5)),
            "window": S0 + V((0, -26.5, 36)), "pinx": S0 + V((0, -22.4, 33)), "mag": S0 + V((0, -25.5, 23.1)),
            "boxmag": S0 + V((0, -27.5, 23.1)), "drum": S0 + V((0, -10, 40))}
def f10(sc):
    tier_core(sc, 4, drum=True, latches=True, mags="tube")
    ymin, c = latch_frame(); mat("PLA_screw", (0.55, 0.56, 0.6))
    R = Matrix.Rotation(math.radians(-90), 4, 'X')
    prim(sc, "cyl", (1.0, 6.0), Matrix.Translation(V((c.x, ymin - 12, c.z))) @ R, "PLA_screw")
    prim(sc, "cyl", (1.9, 1.2), Matrix.Translation(V((c.x, ymin - 15.6, c.z))) @ R, "PLA_screw")
    cam(sc, V((c.x, ymin - 6, c.z)), -60, 15, 60)
    return {"hole": c, "screw": V((c.x, ymin - 13, c.z))}
