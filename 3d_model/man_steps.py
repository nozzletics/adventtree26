# per-figure render functions; each returns {label: world point}
import bpy, math, json
from mathutils import Vector, Matrix
V = Vector
def placec(sc, name, pos, mesh=None, R=None):
    o = add(sc, name, mesh=mesh)
    vs = [o.matrix_world @ v.co for v in o.data.vertices]; c = sum(vs, V()) / len(vs)
    o.matrix_world = Matrix.Translation(pos) @ (R or Matrix()) @ Matrix.Translation(-c) @ o.matrix_world
    return o
def asm_names(): return [o.name for o in bpy.data.collections["ATM_Assembly"].all_objects if o and o.type == 'MESH']
def z(v): return V((0, 0, v))

def f01(sc):
    for n in asm_names(): add(sc, n)
    cam(sc, ORI + z(240), -75, 12, 760); return {}
def f02(sc):
    for n in [o.name for o in bpy.data.collections["ATM_Exploded"].all_objects if o.type == 'MESH']: add(sc, n)
    cam(sc, V((1290, 0, 500)), -75, 12, 1450); return {}
def f03(sc):
    L = V((2600, 0, 0)); mat("PLA_screw", (0.55, 0.56, 0.6))
    placec(sc, "M_T4_Latch_19", L)
    placec(sc, "M_T4_Pins", L + V((32, 0, 0)), mesh=part("M_T4_Pins", -90))
    placec(sc, "M_T4_Magnets", L + V((55, 0, 0)), mesh=part("M_T4_Magnets", -90, 0, 25.2))
    prim(sc, "cyl", (1.0, 6.0), Matrix.Translation(L + V((72, 0, 0))), "PLA_screw")
    prim(sc, "cyl", (1.9, 1.2), Matrix.Translation(L + V((72, 0, 3.6))), "PLA_screw")
    prim(sc, "cyl", (0.875, 9.5), Matrix.Translation(L + V((88, 0, 0))) @ Matrix.Rotation(math.radians(90), 4, 'Y'), "PLA_brass")
    cam(sc, L + V((44, 0, 0)), -90, 35, 120)
    return {"latch": L, "pin": L + V((32, 0, 0)), "magnet": L + V((55, 0, 0)), "screw": L + V((72, 0, 3)), "starpin": L + V((88, 0, 0))}
def f04(sc):
    add(sc, "M_Base"); cam(sc, ORI + z(40), -62, 30, 300)
    return {"tray": ORI + rdir(-125) * 95 + z(12), "tube": ORI + rdir(-40) * 25 + z(60),
            "slot": ORI + rdir(-90) * 25 + z(33), "pocket": ORI + rdir(-90) * 25 + z(23.1),
            "arrow": ORI + rdir(-90) * 25 + z(85), "spigot": ORI + rdir(-60) * 22 + z(94)}
def f05(sc):
    add(sc, "M_Base"); cam(sc, ORI, -90, -70, 300)
    return {"groove": ORI + V((0, 60, 0)), "hole": ORI}
def f06(sc):
    add(sc, "M_Base")
    for i in range(6):
        d = cell_deg(i); add(sc, "M_T4_Magnets", T(*(rdir(d) * 14)), mesh=part("M_T4_Magnets", d, 0, 25.2))
    cam(sc, ORI + V((0, -20, 40)), -68, 18, 170)
    return {"mag": ORI + rdir(-90) * 39 + z(23.1), "pocket": ORI + rdir(-90) * 25 + z(23.1)}

def run(names):
    out = {}
    for n in names:
        sc = scene(); pts = globals()[n](sc)
        out[n] = render(sc, n + ".png", pts)
    old = {}
    try: old = json.load(open(OUT + "\\labels.json"))
    except Exception: pass
    old.update(out); json.dump(old, open(OUT + "\\labels.json", "w"))
    return out
