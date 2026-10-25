# helper for the assembly-manual renders (exec'd inside Blender)
import bpy, bmesh, math, os
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
OUT = bpy.path.abspath("//../manual")
ORI = Vector((950.0, 0.0, 0.0))
RES = (1600, 1200)

def scene():
    sc = bpy.data.scenes.get("_MAN")
    if sc is None:
        sc = bpy.data.scenes.new("_MAN")
    for o in list(sc.collection.objects):
        me = o.data if o.get("_man_own") else None
        bpy.data.objects.remove(o)
        if me is not None and me.users == 0: bpy.data.meshes.remove(me)
    r = sc.render; r.engine = 'BLENDER_WORKBENCH'; r.resolution_x, r.resolution_y = RES; r.resolution_percentage = 100
    r.film_transparent = True; r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_object_outline = True
    sh.object_outline_color = (0.12, 0.12, 0.12); sh.show_cavity = True; sh.cavity_type = 'WORLD'
    sh.show_specular_highlight = True
    try: sc.display.render_aa = '16'
    except Exception: pass
    sc.view_settings.view_transform = 'Standard'
    os.makedirs(OUT, exist_ok=True)
    return sc

def add(sc, name, M=None, mesh=None, mat=None):
    src = bpy.data.objects[name]; o = src.copy(); o.name = "_m_" + name
    if mesh is not None: o.data = mesh; o["_man_own"] = 1
    o["_man"] = 1
    sc.collection.objects.link(o)
    o.matrix_world = (M or Matrix()) @ src.matrix_world
    o.hide_render = False; o.hide_viewport = False
    if mat is not None:
        o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = bpy.data.materials[mat]
    return o

def mat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0); return name

def split_mesh(name, keep):
    """copy of an object's mesh keeping only the loose parts whose world centre passes keep(centre)"""
    src = bpy.data.objects[name]; bm = bmesh.new(); bm.from_mesh(src.data)
    W = src.matrix_world; seen = set(); kill = []
    for v in bm.verts:
        if v in seen: continue
        comp = []; st = [v]; seen.add(v)
        while st:
            x = st.pop(); comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y not in seen: seen.add(y); st.append(y)
        c = sum((W @ x.co for x in comp), Vector()) / len(comp)
        if not keep(c): kill += comp
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    me = bpy.data.meshes.new("_man_" + name); bm.to_mesh(me); bm.free()
    for m in src.data.materials: me.materials.append(m)
    return me

def prim(sc, kind, size, M, matname, name="_m_prim"):
    bm = bmesh.new()
    if kind == "cyl":
        r, h = size; bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(bpy.data.materials[matname])
    o = bpy.data.objects.new(name, me); o["_man"] = 1; o["_man_own"] = 1
    sc.collection.objects.link(o); o.matrix_world = M
    return o

def cam(sc, target, az, el, scale, persp=0.0):
    c = bpy.data.objects.get("_MAN_CAM")
    if c is None:
        c = bpy.data.objects.new("_MAN_CAM", bpy.data.cameras.new("_MAN_CAM"))
    if c.name not in sc.collection.objects: sc.collection.objects.link(c)
    target = Vector(target); a, e = math.radians(az), math.radians(el)
    d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
    c.data.clip_start = 1; c.data.clip_end = 5000
    if persp:
        c.data.type = 'PERSP'; c.data.lens = persp; dist = scale
    else:
        c.data.type = 'ORTHO'; c.data.ortho_scale = scale; dist = 1500
    q = (-d).to_track_quat('-Z', 'Y')
    c.location = target + d * dist
    c.rotation_euler = q.to_euler()
    c.matrix_world = Matrix.Translation(target + d * dist) @ q.to_matrix().to_4x4()
    c["_t"] = list(target); c["_d"] = list(d); c["_s"] = scale
    sc.camera = c
    return c

def render(sc, fn, pts=None):
    sc.render.filepath = os.path.join(OUT, fn)
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return project(sc, pts)

def project(sc, pts):
    c = sc.camera; R = c.matrix_world.to_3x3(); right = R.col[0]; up = R.col[1]
    t = Vector(c["_t"]); s = c["_s"]; out = {}
    for k, p in (pts or {}).items():
        v = Vector(p) - t
        x = v.dot(right) / s + 0.5; y = 0.5 - v.dot(up) / (s * RES[1] / RES[0])
        out[k] = (round(x * RES[0]), round(y * RES[1]))
    return out
