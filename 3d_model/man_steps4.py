import bpy, math
from mathutils import Vector, Matrix
V = Vector
def f15(sc):
    add(sc, "M_T4_Drum")
    cam(sc, ORI + z(90), -70, 35, 70)
    return {"collar": ORI + rdir(-20) * 13.4 + z(95), "wide": ORI + rdir(-90) * 14.6 + z(96)}
def f15b(sc):
    add(sc, "M_T3_Drum")
    cam(sc, ORI + z(95), -70, -40, 70)
    return {"slot": ORI + rdir(-90) * 14.0 + z(89.5), "bore": ORI + rdir(-20) * 13 + z(89)}
def f18(sc):
    tier_core(sc, 1); add(sc, "M_TopFloor"); add(sc, "M_Key", T(0, 0, 28))
    cam(sc, ORI + z(365), -90, 30, 120)
    return {"key": ORI + rdir(-90) * 26 + z(386), "stud": ORI + rdir(-90) * 13 + z(355), "gap": ORI + rdir(-90) * 12.3 + z(360),
            "dot": ORI + rdir(-90) * 38 + z(334.6)}
def f20(sc):
    c, lo, hi = bc("M_Star_Front")
    add(sc, "M_TopTier")
    add(sc, "M_Star_Front", T(0, -14, 30)); add(sc, "M_Star_Back", T(0, 14, 30))
    prim(sc, "cyl", (0.875, 9.5), Matrix.Translation(V((c.x, 0, c.z + 30))) @ Matrix.Rotation(math.radians(90), 4, 'X'), "PLA_brass")
    cam(sc, V((c.x, 0, c.z + 5)), 25, 8, 130)
    return {"front": V((c.x, -14, c.z + 38)), "back": V((c.x, 14, c.z + 38)), "pin": V((c.x, 0, c.z + 30)),
            "stem": V((c.x, -14, lo.z + 30 + 4)), "socket": V((c.x, 0, lo.z - 2))}
