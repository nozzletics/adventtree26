# figure definitions for the assembly manual (exec'd inside Blender after man_render.py into the same dict)
import bpy, math
from mathutils import Vector, Matrix
O = bpy.data.objects

def Rz(deg):
    return Matrix.Translation(ORI) @ Matrix.Rotation(math.radians(deg), 4, 'Z') @ Matrix.Translation(-ORI)
def T(x=0, y=0, z=0): return Matrix.Translation((x, y, z))
def rdir(deg): return Vector((math.cos(math.radians(deg)), math.sin(math.radians(deg)), 0))
def wcenter(name):
    o = O[name]; vs = [o.matrix_world @ v.co for v in o.data.vertices]
    return sum(vs, Vector()) / len(vs)
def ang_of(p): q = Vector(p) - ORI; return math.degrees(math.atan2(q.y, q.x))
def angdiff(a, b): return abs((a - b + 180) % 360 - 180)
def part(name, deg, rmin=0, rmax=999):
    """loose parts of a hardware object (pins / magnets) near the cell at angle deg and within a radius band"""
    def keep(c):
        q = c - ORI; r = q.xy.length
        return angdiff(math.degrees(math.atan2(q.y, q.x)), deg) < 20 and rmin <= r <= rmax
    return split_mesh(name, keep)
def cell_deg(i): return -90.0 + 60.0 * i          # FRONT_DEG, anticlockwise from above
TIER = {4: dict(z0=8, first=19), 3: dict(z0=89, first=13), 2: dict(z0=170, first=7), 1: dict(z0=251, first=1)}
def tier_core(sc, k, drum=True, latches=True, mags="tube", boxes=False, M=None, pins=True):
    """carrier (or base for T4) + drum + hardware of tier k"""
    out = []
    out.append(add(sc, "M_Base" if k == 4 else f"M_T{k}_Carrier", M))
    if drum: out.append(add(sc, f"M_T{k}_Drum", M))
    first = TIER[k]["first"]
    if latches:
        for n in range(first, first + 6): out.append(add(sc, f"M_T{k}_Latch_{n:02d}", M))
    if pins and latches: out.append(add(sc, f"M_T{k}_Pins", M))
    if mags == "tube":
        out.append(add(sc, f"M_T{k}_Magnets", M, mesh=split_mesh(f"M_T{k}_Magnets", lambda c: (c - ORI).xy.length < 25.2)))
    elif mags == "all": out.append(add(sc, f"M_T{k}_Magnets", M))
    if boxes:
        for n in range(first, first + 6):
            for h in "AB": out.append(add(sc, f"M_T{k}_C{n:02d}_{h}", M))
    return out
