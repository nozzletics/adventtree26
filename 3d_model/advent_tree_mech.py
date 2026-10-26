# nozzletics — Modular Christmas Tree Advent Calendar  MECH variant (from v42): cam drum + 6x3 magnets in a Ø50 tube.
# Universal cell: hook slot (hook centre) AND a 6x3 magnet pocket + rod push point (drum centre). Only the centre differs.
# Builds into its own collections (AdventTreeMech / ATM_*), objects prefixed "M_", placed at ORIGIN - the hook model is untouched.
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
    "HUB_R": 25.0, "HUB_CLR": 0.4, "BORE_R": 5.0,   # MECH: hub = Ø50 tube around the cam drum
    # ---- MECH: tube, drum, rods, magnets
    "TUBE_RI": 19.8, "TUBE_SPIG_R": 22.0,            # tube bore; tube-to-tube bayonet spigot radius (hollow, bore stays clear)
    "ROD_Z0": 25.0, "ROD_DZ": 8.0,                   # rod height in a tier for cell index i: ROD_Z0 + i*ROD_DZ (clear of bearing ring / hook slot)
    # drum bearing ring at the foot of every tube (drum goes in from the top): flat bore band, 45 deg underside
    "BRG_CLR": 0.25, "BRG_TOP": 17.5,                # radial clearance to the drum; top of the bearing band (the 45 deg cone starts at the socket top)
    "ROD_D": 1.75, "ROD_HOLE_R": 0.95,               # filament rod, its hole in the tube
    # LATCH mechanism (replaces the push rods): a lever through the tube wall pivots on a filament pin glued in the
    # wall; its tooth hangs into a window in the box's hub wall, its tail rests over a flange on the drum. Pulling
    # the box lifts the tooth (45 deg face) -> only possible where the flange has its notch (the box's day).
    "LATCH": True,
    "LT_T": 3.0, "LT_H": 4.0, "LT_PIV": 22.4,        # lever thickness (tangential), bar height, pivot radius (= pin axis)
    "LT_TAIL": 17.0, "LT_TIP_W": 1.6, "LT_TIP_L": 1.8,   # tail tip radius; narrow tip (on the print-bed side) width, length
    "LT_TOOTH_X": 27.4, "LT_TOOTH_D": 3.5,           # tooth starts here (0.4 behind the hub wall), hangs this deep (45 deg both faces -> 2*D long)
    "LT_TOOTH_W": 7.0,                               # tooth only is this wide (tangential), growing from the bed face (-Y) upwards
    "LT_END_R": 0.0,                                  # radius rounding the top of the lever's outer end (0 = square)
    "LT_RAMP": True, "LT_RAMP_DEG": 45.0,                                # wedge in the step from the bar (3) to the wide tooth body (7): no square step to catch
    "LT_HOLE_R": 1.05, "LT_PIN_R": 1.05,             # pivot hole in the lever (free) / pin hole in the tube (glued)
    "LT_SCREW_D": 1.5, "LT_SCREW_L": 6.5,           # pilot hole in the lever's outer end for a small steel screw (weight + magnet pull)
    "LT_CLR": 0.3, "LT_MAX": 22.0,                   # slot clearance; max lever swing (deg, tooth up)
    "LT_GAP": 0.3,                                   # tail -> flange top at rest (locked lift of the tooth stays small)
    "LT_WIN_CLR": 0.4,                               # window in the box hub wall: clearance around the bar
    "LT_WIN_Z": (-2.8, 6.364), "LT_WIN_Y": (-2.4, 6.4),   # FIXED box window (rel. latch axis) - boxes already printed with it
    "BAYO_MARK": True, "BAYO_MARK_DEG": -90.0, "BAYO_MARK_D": 0.6,
    # anti-turn screw at every tier joint (after the bayonet is locked): countersunk 2 x 10 wood screw at 45 deg through
    # the upper tray (between its boxes 6/1, 12/7, 18/13) into the wall of the tube below; top floor: in front of the dial dot
    "TIER_SCREW": True, "SCR_D": 1.3, "SCR_L": 10.0, "SCR_HEAD_D": 4.2, "SCR_HEAD_K": 1.45,
    "SCR_J": 24.5, "SCR_TIP_R": 21.2,               # screw axis radius at the joint plane; radius of the screw tip (tube bore 19.8)
    "SCR_PAD_R": 3.4, "SCR_TOP_PAD": False,         # top floor: False = plain SCR_D hole only (no pad, no countersink)
    "CAP_ARROW": True, "CAP_ARROW_D": 0.7,          # debossed arrow on the cap above box 1 (shows how to put the cap on)   # assembly arrows: tube top + tray underside, aligned when the bayonet is locked
    "MAG_DZ_FIX": 9.9,                               # FIXED latch axis -> magnet centre (boxes already printed)
    "DRUM_SEAT": True, "DRUM_SEAT_CLR": 0.3,        # tube seat under the lowest flange (all tubes but the base)
    "FL_R": 19.3, "FL_T": 1.2, "NOTCH_D": 2.0, "NOTCH_WIN": 2.0,   # drum flange radius / thickness; notch depth; flat-bottom play +- deg
    "NOTCH_RAMP": 45.0,                              # notch sides slope (deg): turning the drum pushes a stuck tail back up
    # DETENT: the key clicks into each of the 25 positions. Two in-plane leaf springs in the top floor's boss (printed
    # flat = bending along the layers) press V-nubs into 25 vertical V-grooves on the T1 drum.
    "DETENT": True,
    "DET_RI": 17.0, "DET_T": 1.2, "DET_SPAN": 60.0, "DET_GAP": 1.0,   # leaf inner radius, thickness, arc length (deg), room behind it
    "DET_POST": 6.0, "DET_PSI": 0.0,                 # post (fixed end) arc (deg); nub angle of leaf 1 (leaf 2 = +12 steps)
    "DET_D": 0.8, "DET_Z": (2.0, 17.0),              # groove depth (45 deg flanks); nub height range (top-floor local z)
    "MAG_D": 6.0, "MAG_T": 3.0, "MAG_CLR": 0.1,      # 6x3 disc magnets: pocket radius = D/2 + CLR
    "WASHER": False, "WASHER_D": 9.0, "WASHER_T": 0.8, "WASHER_CLR": 0.1,   # alternative in the tube: glue in an M4 washer (DIN 125: 9 x 0.8) instead of
                                                     # the magnet (weaker pull); its recess shares the top edge with the magnet pocket
    "PULL_TAB": True, "TAB_INSET": 0.0, "TAB_W": 36.8, "TAB_T": 3.0, "TAB_DROP": 8.0, "TAB_DIMPLE": 1.4,
    # pull tab at the centre of the face (split between A and B), hanging from the widest edge (top of the bottom
    # chamfer), outer side flush with that edge; faceted dimple in its inner side (towards the trunk) for the fingertip
    "FINGER": False, "FINGER_D": 4.5, "FINGER_W": 5.0, "FINGER_IN": 4.0,
    # faceted finger pocket in the bottom chamfer at the +a side edge of each box (half B): pyramid, apex FINGER_D
    # deep behind the chamfer and FINGER_IN in from the side face, base half-size FINGER_W; a pad inside backs it
    "MAG_WEB": 0.6,                                  # plastic between the rod hole and the magnet pocket below it
    "MAG_SET": 0.1,                                  # box magnet: plain 6x3 pocket, magnet 0.1 below the hub-wall face
    "MAG_SET_MAX": 0.1,                              # (no adjustment: pocket = magnet + 0.1)
    "MAG_SKIN": 1.2, "BOSS_TOP": 2.0,                # boss behind / around the box magnet; boss reaches this far above the rod
    "TRAY_PLAY": 3.0,                                # MECH tray this much smaller than the cell recess: lets a box pop out
    "DRUM_R": 16.5, "DRUM_RI": 13.5,                 # drum core / bore
    "CAM_RISE": 2.5, "CAM_H": 4.0, "CAM_CH": 2.5,    # lobe: lift, flat height at the rod, 45 deg chamfer below (prints standing)
    # profile (key angle x relative to the day mark): rod free at the stop after the previous day, smooth rise
    # (gentle where the magnet pulls hardest) to the peak, short hold, sharp drop at the mark, stop STOP_DEG after it
    "STEP_DEG": 360.0 / 25, "STOP_DEG": 4.0,         # 25 stops (start dot + 24 days); a day's drop is STOP_DEG before its stop/mark:
                                                 # rod (r 0.875 = 3.1 deg) clear of the lobe at the stop
    "CAM_HOLD": 0.5, "CAM_MARGIN": 0.75,             # peak hold before the drop (deg); safety margin at both stops (deg)
    "ROD_TIP_R": 0.875, "ROD_TIP_W": 1.0,            # domed rod tip (round the filament end): it meets the low ramp start ~1 deg off-axis
    # drum coupling: a narrowed collar on top of each segment plugs into the bore of the one above;
    # 4 teeth on the collar (one wider = one way only) sit in slots at the foot of that bore
    "CPL_L": 8.0, "CPL_RI": 11.5, "CPL_CLR": 0.2,    # collar length, collar bore, fit clearance per side
    "CPL_TOOTH_R": 14.6, "CPL_TOOTH_W": (4.5, 3.0, 3.0, 3.0), "CPL_TOOTH_DEG": (0.0, 90.0, 180.0, 270.0),
    # drive: tapered spline stud on the top drum (one tooth missing = one way only), the knob wedges onto it
    "SPL_N": 16, "SPL_RT": 13.0, "SPL_RR": 11.5, "SPL_L": 10.0, "SPL_TAPER": 0.97, "SPL_HOLE": 5.5,   # teeth, tip / root radius at the base, length, top scale
    "KEY_CLR": 0.15, "KEY_SEAT": 0.6,                 # hole = stud cone (printed holes come out a bit small -> it wedges); seat height
    "KEY_R": 16.5, "KEY_H": 10.0,                     # knob hub (around the stud)
    "KEY_FIN_W": 10.0, "KEY_FIN_H": 14.0, "KEY_FIN_BACK": 24.0, "KEY_ARROW": 36.0,  # finger fin: width, height, tail, pointer tip radius
    "TOP_BOSS_H": 17.5,                              # MECH top floor: ring boss height (tube socket + top drum bearing)
    "DIAL_TICK": (29.0, 34.0), "DIAL_NUM_R": 41.0, "DIAL_DEPTH": 0.4, "DIAL_RELIEF": 0.6,
    "KEY_PHI": 0.0,                                  # key angle shown in the assembly: 0 = start (dot); day n stop = n * STEP_DEG
    "ORIGIN": (950.0, 0.0, 0.0), "PREFIX": "M_",
    "GAP": 0.4,                        # gap between neighbouring cells
    "WALL": 1.6, "FLOOR": 1.6, "ROOF": 1.6,   # = 4 lines of 0.4 mm
    "HUB_TAB": True, "HUB_TAB_M": 2.5,   # hub-wall strip with the hook slot goes to half B (margin each side of the slot)
    "LIP_ROOT_L": 2.4, "LIP_ROOT_N": 6,   # chamfered root of the lip inside half B (length, steps)
    "LIP_W": 1.2, "LIP_H": 3.0,        # lip on half B: wall thickness, how far it plugs into half A
    "LIP_CLR": 0.05,                   # lip clearance to half A's inner wall (per side) - very tight press fit
    "TRAY_T": 4.0, "TRAY_SET": 12.0, "TRAY_MAXR": 130.0,
    "TRAY_FRAC": 0.9375,               # tray radius as a fraction of the old full-size tray (MECH: wider support for the boxes)
    "TRAY_EDGE_M": 2.2,                # cap: recess + ledge must stay inside the box bottom at its side edges (EDGE_K*(R-CB) - this)
    "TRAY_CLR": 0.4,                   # radial clearance of the tray in the cell recess
    "STACK_GAP": 1.0,                  # MECH: air gap cell top -> cells above (boxes slide out radially, no lift; > side GAP)
    "HOOK_SLOT": False,                # MECH: trunk-hook slot in the hub wall not cut (latch boxes don't use it)
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
    "BASE_MERGE": True,                # MECH: base and the bottom tier's carrier are one part (no bayonet between them)
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
    "STAMP_DEPTH": 0.6, "BRAND_Y": -58.0,     # logo moved forward, clear of the cable groove
    "CABLE": True, "CABLE_GROOVE_W": 10.0, "CABLE_GROOVE_D": 5.0,  # garland channel: base bore + groove to the back edge, top-floor bore
    "COLORS": {"gold": (0.80, 0.60, 0.18), "green": (0.105, 0.235, 0.165), "ivory": (0.90, 0.85, 0.74),
               "terra": (0.55, 0.20, 0.15), "steel": (0.22, 0.24, 0.27), "brass": (0.85, 0.72, 0.30),
               "drum": (0.62, 0.64, 0.66)},
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
                          tray_r=min(P["TRAY_FRAC"] * min(R - P["TRAY_SET"], P["TRAY_MAXR"]),
                                     P["EDGE_K"] * (R - P["CB"]) - P["TRAY_EDGE_M"],    # inside the box bottom
                                     (P["BED"][0] - 6) / 2 + P["TRAY_PLAY"]),          # carrier fits the bed
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
    boolean(o, [pk] + ([slot] if P["HOOK_SLOT"] else []))
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
        if "boss_z" in t:   # MECH: the magnet boss goes to half B as well (whole pocket in one part)
            z0, z1 = t["boss_z"]; xb = t["boss_x"] + 0.5
            tb2 = new_obj("_tab2", body.data.copy())
            boolean(tb2, [box("_tb2", r0, xb, -S, 0.3, z0 - 0.5, z1 + 0.5)], 'INTERSECT')
            boolean(Bh, [tb2], 'UNION')
            boolean(A, [box("_tn2", r0, xb + c, -S - c, 0.01, z0 - 0.5 - c, z1 + 0.5 + c)])
        if P.get("HUB_LIP", True):
            # lip along the free edge of the hub strip: a curved plate on B that laps LIP_H over the inside of A's
            # hub wall (LIP_CLR off it), so the seam at y = -S is covered and the halves line up there too.
            # Half B prints on its +a side wall: the plate grows from the strip towards -y = upwards, no overhang.
            w, L = P["LIP_W"], P["LIP_H"]; ri1 = r_in() + P["WALL"]
            hz, r_end, lift = hook_geom(t)
            zl0 = P["FLOOR"] + P["TRAY_T"] + 0.6; zl1 = t["H"] - P["ROOF"] - 0.6
            plate = cyl(ri1 + c + w, zl0, zl1)
            boolean(plate, [cyl(ri1 + c, zl0 - 1, zl1 + 1)])
            boolean(plate, [box("_lp", 0, 80, -S - L, -S + 0.2, zl0 - 1, zl1 + 1)], 'INTERSECT')
            # root: a 45 deg wedge from the strip's wall out to the plate (on the print-bed side of the plate, +y),
            # so the plate grows out of the wall gradually instead of starting as a 1.35 mm flat overhang
            y0 = -S + 0.05; ro, rw = ri1 + c + w, ri1 - 0.4
            xo = math.sqrt(ro * ro - y0 * y0); xi = math.sqrt(rw * rw - y0 * y0)
            yf = y0 + 0.35                                   # full width up to here (the plate ends inside it)
            y1 = yf + (xo - xi) + 0.2; x1 = math.sqrt(rw * rw - y1 * y1)
            root = hull("_lr", [Vector((x, y, z)) for z in (zl0, zl1) for x, y in ((xi, y0), (xo, y0), (xo, yf), (x1, y1))])
            boolean(plate, [root], 'UNION')
            boolean(Bh, [plate], 'UNION')
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

# ------------------------------------------------------------------ MECH: rods / magnets
def rod_z(i): return P["ROD_Z0"] + i * P["ROD_DZ"]                      # rod axis height (tier-local)
def pocket_r(): return P["MAG_D"] / 2 + P["MAG_CLR"]
def mag_dz():
    if P["LATCH"]:   # magnet below the latch: under the tooth (+0.6) with its boss skin
        if P.get("MAG_DZ_FIX"): return P["MAG_DZ_FIX"]
        return P["LT_H"] / 2 + P["LT_TOOTH_D"] + 0.6 + pocket_r() + P["MAG_SKIN"]
    return P["ROD_HOLE_R"] + P["MAG_WEB"] + pocket_r()          # rod axis -> magnet centre (magnet below the rod)

# ------------------------------------------------------------------ MECH: latch lever
def prism_xz(name, poly, y0, y1):
    """polygon in the XZ plane (any shape, CCW or CW) extruded along Y"""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in poly]; b = [bm.verts.new((x, y1, z)) for x, z in poly]
    n = len(poly)
    bm.faces.new(a); bm.faces.new(b[::-1])
    for j in range(n): bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me)

def prism_xy(name, poly, z0, z1):
    bm = bmesh.new()
    a = [bm.verts.new((x, y, z0)) for x, y in poly]; b = [bm.verts.new((x, y, z1)) for x, y in poly]
    n = len(poly)
    bm.faces.new(a); bm.faces.new(b[::-1])
    for j in range(n): bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me)

def sector(name, r0, r1, a0, a1, z0, z1, step=1.5):
    """annular sector r0..r1, angles a0..a1 (deg), z0..z1"""
    n = max(2, int(math.ceil((a1 - a0) / step)))
    angs = [rad(a0 + (a1 - a0) * j / n) for j in range(n + 1)]
    poly = [(r1 * math.cos(a), r1 * math.sin(a)) for a in angs] + [(r0 * math.cos(a), r0 * math.sin(a)) for a in reversed(angs)]
    return prism_xy(name, poly, z0, z1)

def detent_parts():
    """top-floor local: (cutters, solids) for the two click springs"""
    ri, T, gap, span = P["DET_RI"], P["DET_T"], P["DET_GAP"], P["DET_SPAN"]
    hb = P["TOP_BOSS_H"]; R0 = P["DRUM_R"]; z0, z1 = P["DET_Z"]
    cuts, adds = [], []
    for a_n in (P["DET_PSI"], P["DET_PSI"] + 12 * P["STEP_DEG"]):
        a_free = a_n + 6.5; a_att = a_free - span          # nub (+-5 deg at its base) sits just inside the free end
        cuts.append(sector("_dslot", R0 + 0.1, ri + T + gap, a_att + P["DET_POST"], a_free + 2.0, -1, hb + 1))
        adds.append(sector("_dpost", ri - 0.1, ri + T + gap + 0.2, a_att, a_att + P["DET_POST"], 0, hb))
        adds.append(sector("_dleaf", ri, ri + T, a_att, a_free, 0, hb))
        rt_ = R0 - P["DET_D"] + 0.1; rb_ = ri + 0.3
        nub = hull("_dnub", [Vector((x, y, z)) for z in (z0, z1) for x, y in ((rt_, 0), (rb_, -(rb_ - rt_)), (rb_, rb_ - rt_))])
        nub.data.transform(Matrix.Rotation(rad(a_n), 4, 'Z')); adds.append(nub)
    return cuts, adds

def lt_rects():
    """lever outline pieces relative to the pivot height (x = radius): tip, bar, tooth"""
    h, tx, D = P["LT_H"] / 2, P["LT_TOOTH_X"], P["LT_TOOTH_D"]
    x0, x1 = P["LT_TAIL"], P["LT_TAIL"] + P["LT_TIP_L"]
    tip = [(x0, -h), (x1, -h), (x1, h), (x0 + 0.6, h), (x0, h - 0.6)]
    bar = [(x1 - 0.2, -h), (tx + 2 * D, -h), (tx + 2 * D, h), (x1 - 0.2, h)]
    tooth = [(tx, -h + 0.3), (tx, -h), (tx + D, -h - D), (tx + 2 * D, -h), (tx + 2 * D, -h + 0.3)]
    return tip, bar, tooth

def lt_end(): return P["LT_TOOTH_X"] + 2 * P["LT_TOOTH_D"]

def lt_out_x():
    """where the wide outer part starts: its inner top corner stays clear of the tube even at LT_MAX"""
    h, th = P["LT_H"] / 2, rad(P["LT_MAX"])
    return P["LT_PIV"] + (P["HUB_R"] + 0.2 - P["LT_PIV"] + h * math.sin(th)) / math.cos(th)

def lt_out_y(): return -P["LT_T"] / 2, -P["LT_T"] / 2 + max(P["LT_TOOTH_W"], P["LT_T"])

def build_lever(name, z):
    """the lever at rest (tier-local, box direction = +X): prints flat on its -Y face; the narrow tail tip is on
    that side (flush with the bed). Pivot hole along Y at (LT_PIV, z). Outside the tube it widens to LT_W_OUT
    (towards +Y = up in print), tooth included."""
    tip, bar, tooth = lt_rects(); t2 = P["LT_T"] / 2
    y0, y1 = -t2, -t2 + max(P["LT_TOOTH_W"], P["LT_T"])
    h = P["LT_H"] / 2; tx = P["LT_TOOTH_X"]
    E = lt_end(); rr = min(P.get("LT_END_R", 0.0), 2 * h)            # optional rounded top of the outer end
    arc = ([(E - rr + rr * math.cos(rad(90 * j / 8)), h - rr + rr * math.sin(rad(90 * j / 8))) for j in range(9)]
           if rr > 0 else [(E, h)])
    bar = [(bar[0][0], -h), (E, -h)] + arc + [(bar[0][0], h)]
    o = prism_xz(name, [(x, z + q) for x, q in bar], -t2, t2)
    body = [(tx, -h), (E, -h)] + arc + [(tx, h)]                        # the tooth's own body: bar above it as wide as the tooth
    boolean(o, [prism_xz("_lb", [(x, z + q) for x, q in body], y0, y1),
                prism_xz("_lt", [(x, z + q) for x, q in tooth], y0, y1),
                prism_xz("_lp", [(x, z + q) for x, q in tip], -t2, -t2 + P["LT_TIP_W"])], 'UNION')
    if P.get("LT_RAMP") and y1 > t2 + 0.01:
        xa = lt_out_x() + 0.05                                          # starts where the wide part may start (tube clear at LT_MAX)
        xb = xa + (y1 - t2) / math.tan(rad(P.get("LT_RAMP_DEG", 45.0)))   # reaches the full width here (body corner cut)
        pts = [Vector((x, y, z + q)) for x, y in ((xa, t2 - 0.01), (xb, t2 - 0.01), (xb, y1)) for q in (-h, h)]
        boolean(o, [hull("_lramp", pts)], 'UNION')
        zl, zh = z - h - P["LT_TOOTH_D"] - 1, z + h + 1
        cut = [Vector((x, y, q)) for x, y in ((xa, t2), (xb, y1), (xb, y1 + 1), (xa - 0.5, y1 + 1), (xa - 0.5, t2)) for q in (zl, zh)]
        boolean(o, [hull("_lrcut", cut)])
    cuts = [y_cyl("_lh", P["LT_HOLE_R"], -t2 - 1, t2 + 1, P["LT_PIV"], z, 32)]
    if P["LT_SCREW_D"] > 0:
        sc = radial_cyl("_lsc", P["LT_SCREW_D"] / 2, lt_end() - P["LT_SCREW_L"], lt_end() + 1, z, 24)
        sc.data.transform(Matrix.Translation((0, (y0 + y1) / 2, 0))); cuts.append(sc)
    return boolean(o, cuts)

def y_cyl(name, r, y0, y1, x, z, seg=32):
    o = rings(name, [(r, y0), (r, y1)], seg)
    o.data.transform(Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rad(-90), 4, 'X'))   # local +Z -> +Y
    return o

def lt_rot(pts, th):
    xp = P["LT_PIV"]; c, s_ = math.cos(th), math.sin(th)
    return [(xp + (x - xp) * c - q * s_, (x - xp) * s_ + q * c) for x, q in pts]

def lt_sweep(x0, x1, step=0.2):
    """for x bins in [x0, x1]: (min, max) height (rel. pivot) the lever reaches over its swing 0..LT_MAX"""
    pts = []
    for poly in lt_rects()[:2]:
        n = len(poly)
        for j in range(n):
            (ax, az), (bx, bz) = poly[j], poly[(j + 1) % n]
            m = max(2, int(math.hypot(bx - ax, bz - az) / 0.04))
            pts += [(ax + (bx - ax) * u / m, az + (bz - az) * u / m) for u in range(m)]
    allp = []
    for k in range(0, int(P["LT_MAX"] * 2) + 1):
        allp += lt_rot(pts, rad(k * 0.5))
    nb = int(round((x1 - x0) / step)); out = []
    for b in range(nb + 1):
        xb = x0 + b * step
        zs_ = [q for x, q in allp if abs(x - xb) <= step * 0.6]
        out.append((xb, min(zs_), max(zs_)))
    return out

def lt_slot(name, z):
    """slot through the tube wall: the lever's swept envelope + LT_CLR, except the floor on the outer side, which is
    exactly the bar's underside at rest (the heavy outer arm rests on it = rest stop)"""
    h, c = P["LT_H"] / 2, P["LT_CLR"]
    sw = lt_sweep(P["TUBE_RI"] - 0.8, P["HUB_R"] + 0.6)
    top = [(x, hi + c) for x, lo, hi in sw]
    bot = [(x, (-h if lo >= -h - 0.01 else lo - c)) for x, lo, hi in sw]
    poly = top + bot[::-1]
    w = P["LT_T"] / 2 + c
    return prism_xz(name, [(x, z + q) for x, q in poly], -w, w)

def lt_window():
    """window in the box hub wall (rel. latch height): bottom LT_CLR under the bar, top clears the bar lifted to LT_MAX"""
    h, th = P["LT_H"] / 2, rad(P["LT_MAX"]); dx = lt_end() - P["LT_PIV"]
    return -h - P["LT_CLR"], dx * math.sin(th) + h * math.cos(th) + P["LT_CLR"]
def radial_cyl(name, r, x0, x1, z, seg=48):
    """cylinder of radius r along local +X from x0 to x1, axis at height z (y = 0)"""
    o = rings(name, [(r, x0), (r, x1)], seg)
    o.data.transform(Matrix.Translation((0, 0, z)) @ Matrix.Rotation(rad(90), 4, 'Y'))   # local +Z -> +X
    return o

def boss_range(i):
    zm = rod_z(i) - mag_dz(); hw = pocket_r() + P["MAG_SKIN"]
    if P["LATCH"]: return zm - hw, zm + hw
    return zm - hw, rod_z(i) + P["BOSS_TOP"]

def cell_boss(t, i, o):
    """boss on the inside of the hub wall with a 6x3 magnet pocket open towards the tube; the rod pushes the
    wall just above the magnet. +y side sloped 45 deg (half B prints on its +a side wall, so +y faces down)."""
    ri = r_in(); hw = pocket_r() + P["MAG_SKIN"]
    x_in, x_out = ri - 0.6, ri + P["MAG_T"] + P["MAG_SET_MAX"] + P["MAG_SKIN"]
    z0, z1 = boss_range(i); zm = rod_z(i) - mag_dz()
    pts = [Vector((x, y, z)) for z in (z0, z1) for x, y in
           ((x_in, -hw), (x_out, -hw), (x_out, hw), (x_in, hw + (x_out - x_in)))]
    bs = hull("_boss", pts)
    boolean(bs, [cyl(ri + 0.3, -1, t["H"] + 5)])          # boss starts inside the hub wall (no coplanar faces)
    boolean(o, [bs], 'UNION')
    pk = radial_cyl("_mpk", pocket_r(), ri - 1.0, ri + P["MAG_T"] + P["MAG_SET_MAX"], zm)
    cuts = [pk]
    if P["LATCH"]:   # window for the latch tooth
        w0, w1 = P["LT_WIN_Z"]; y0, y1 = P["LT_WIN_Y"]
        cuts.append(box("_lwin", ri - 1.5, ri + P["WALL"] + 0.3, y0, y1, rod_z(i) + w0, rod_z(i) + w1))
    boolean(o, cuts)
    t["boss_z"] = (z0, z1); t["boss_x"] = x_out

def cell_finger(t, o):
    """faceted finger pocket in the bottom chamfer, right at the +a side edge (the valley to the next box).
    Pyramid: apex FINGER_D deep behind the chamfer, FINGER_IN in from the side face; its base lies just outside
    the chamfer and runs past the side face, so the pocket is open to the front-below and to the seam.
    Half B prints lying on that side face: the facet facing the bed rises at ~50 deg. A pad inside backs it."""
    a, g, k = t["a"], t.get("gap", P["GAP"]) / 2, P["EDGE_K"]
    u = Vector((math.cos(a), math.sin(a), 0)); n = Vector((-math.sin(a), math.cos(a), 0))
    D, W, wi = P["FINGER_D"], P["FINGER_W"], P["FINGER_IN"]
    zc = P["CBH"] * 0.5
    C = u * (k * rho(t, zc)) + n * (-g) + Z * zc                      # on the side edge, mid chamfer
    out = (u * math.cos(rad(45)) - Z * math.sin(rad(45))).normalized()  # outward normal of the bottom chamfer
    tan = (u * math.sin(rad(45)) + Z * math.cos(rad(45))).normalized()  # up the chamfer
    Cc = C - n * wi
    apex = Cc - out * D
    # along n the facet away from the bed faces it: its base reaches out W_far >= depth, so it rises at > 45 deg
    wf = (D + 1.5) * 1.15
    base = [Cc + out * 1.5 + n * i + tan * j * W for i in (-wf, W) for j in (-1, 1)]
    pyr = hull("_fpy", [apex] + base)
    # pad behind it (clipped 0.6 inside the outer skin)
    def pt(s_, z, d): return u * s_ + Z * z + n * (-g - d)
    sR = k * t["R"]
    pad = hull("_fpad", [pt(s_, z, d) for s_ in (sR - 22, sR + 3) for z in (0.4, zc + W + 8) for d in (0.3, wi + W + 2.5)])
    shell = hull("_fsh", levels(t, [(0, rho(t, 0), 0.6), (P["CBH"], t["R"], 0.6), (t["zl"], t["Rm"], 0.6)]))
    boolean(pad, [shell], 'INTERSECT')
    boolean(pad, [cyl(r_in() + P["WALL"] + 0.3, -1, t["H"] + 5)])
    boolean(o, [pad], 'UNION')
    boolean(o, [pyr])

def tab_width(R):
    """tab width scales with the tier: TAB_W at the top tier's radius (TAB_W_REF = T1 ridge radius)"""
    return P["TAB_W"] * R / P["R"][0]

def make_tab(t, R, slope, zb, w):
    """tab hanging from the widest edge (z = CBH, ridge radius R): continues the face downwards with the face's
    lean (radius grows by `slope` per mm down), follows the face profile, TAB_T thick, ends sloped 45 deg.
    Returns (tab solid, dimple cutter) in the tier/segment frame (+X = face centre)."""
    T = P["TAB_T"]; zt = P["CBH"] + 0.4; ins = P.get("TAB_INSET", 0.0)
    rz = lambda z: R + (P["CBH"] - z) * slope
    # outer face flush with the box face (no step); above the chamfer edge it tucks 0.3 inside the wall
    outer = hull("_to", levels(t, [(zb, rz(zb), ins), (P["CBH"], rz(P["CBH"]), ins), (zt, rz(zt), ins + 0.3)], inner_x=0.0))
    inner = hull("_ti", levels(t, [(zb - 1, rz(zb - 1), ins + T), (zt + 1, rz(zt + 1), ins + T)], inner_x=0.0))
    boolean(outer, [inner])
    wb = max(w - (zt - zb), 2.0)
    clip = hull("_tc", [Vector((x, y, z)) for x in (R - T - 10, rz(zb) + 5) for y, z in
                        ((-w - 0.5, zt + 0.5), (w + 0.5, zt + 0.5), (-wb, zb - 0.1), (wb, zb - 0.1))])
    boolean(outer, [clip], 'INTERSECT')
    # dimple in the inner side, in the free part below where the bottom chamfer meets it
    tau = math.atan(slope); nrm = Vector((math.cos(tau), 0, math.sin(tau))); up = Vector((-math.sin(tau), 0, math.cos(tau)))
    zmeet = (P["CB"] + slope * P["CBH"] - ins - T) / (P["CB"] / P["CBH"] + slope)
    zc = (zb + zmeet) / 2; d = P["TAB_DIMPLE"]; hw = min(6.0 * w / 18.4, w - 3.0); hz = min(1.6, (zmeet - zb) / 2 - 0.9)
    pc = Vector((rz(zc) - ins - T, 0, zc))
    dim = hull("_dim", [pc + nrm * d + Vector((0, y, 0)) for y in (-hw + 1.6, hw - 1.6)] +
               [pc - nrm * 0.8 + Vector((0, y, 0)) + up * s_ for y in (-hw - 0.8, hw + 0.8) for s_ in (-hz - 0.8, hz + 0.8)])
    return outer, dim

def cell_tab(t, o):
    """pull tab at the face centre, hanging from the top of the bottom chamfer with the face's lean (TILT); a
    finger slot opens between it and the chamfer, dimple in its inner side. Halves print on their side walls:
    the 45 deg ends let the tab grow out of the box. Far clear of the tier below."""
    tab, dim = make_tab(t, t["R"], math.tan(rad(P["TILT"])), P["CBH"] - P["TAB_DROP"], tab_width(t["R"]) / 2)
    # keep it out of the box interior (the wall leans outwards above the chamfer): cut with the cavity grown 0.3 mm
    wb_, wm_, _ = wall_offsets()
    cav = hull("_tcv", levels(t, [(P["FLOOR"] - 0.3, rho(t, P["FLOOR"] - 0.3), wb_ - 0.3),
                                   (P["CBH"] + 0.6, rho(t, P["CBH"] + 0.6), wm_ - 0.3),
                                   (t["zl"] - 0.6, rho(t, t["zl"] - 0.6), wm_ - 0.3)]))
    boolean(tab, [cav])
    boolean(o, [tab], 'UNION')
    boolean(o, [dim])

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
    cell_boss(t, num - t["first"], o)
    if P["FINGER"]: cell_finger(t, o)
    if P["PULL_TAB"]: cell_tab(t, o)
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

def bearing_bore(z_top, z_band_top):
    """cutters for a tube bore with a drum bearing ring. From the top of the bayonet socket (bore TUBE_SPIG_R + 0.3
    at SPIG_H + 0.6) one 45 deg cone narrows straight to the bearing bore DRUM_R + BRG_CLR - no flat ceiling, prints
    without support - then a flat band up to z_band_top, TUBE_RI again above it (None: bearing bore all the way up)"""
    rb, ri = P["DRUM_R"] + P["BRG_CLR"], P["TUBE_RI"]
    rs, z0 = P["TUBE_SPIG_R"] + 0.3, P["SPIG_H"] + 0.6
    cuts = [rings("_bb", [(rb, -1), (rb, z_top)], 128),
            rings("_bc", [(rs, -1), (rs, z0), (rb - 0.01, z0 + (rs - rb) + 0.01)], 128)]
    if z_band_top is not None:
        zs = drum_seat_z() if (P["LATCH"] and P.get("DRUM_SEAT")) else None
        if zs is not None and zs > z_band_top:   # 45 deg seat under the lowest flange's cone: the drum can't drop
            cuts.append(rings("_bu", [(rb, zs), (ri, zs + (ri - rb)), (ri, z_top)], 128))
        else:
            cuts.append(rings("_bu", [(ri, z_band_top), (ri, z_top)], 128))
    return cuts

def screw_seam():
    """seam between the last and the first box of a tier (6/1, 12/7, 18/13)"""
    return theta(TIERS[0], 0) - pi / 6

def screw_axis(z0):
    """tip point and unit direction (towards the head) of the 45 deg screw in the r/z plane at angle 0; joint plane z0"""
    rt = P["SCR_TIP_R"]; zt = z0 - (P["SCR_J"] - rt)
    return Vector((rt, 0, zt)), Vector((math.sqrt(0.5), 0, math.sqrt(0.5)))

def screw_cut(ang, z0, head=True):
    """cutters: pilot hole SCR_D (0.3 past the tip), countersink + head clearance along the axis (head sunk below the surface)"""
    tip, w = screw_axis(z0); L, k = P["SCR_L"], P["SCR_HEAD_K"]; rh = P["SCR_HEAD_D"] / 2; rp = P["SCR_D"] / 2
    M = Matrix.Rotation(ang, 4, 'Z') @ Matrix.Translation(tip) @ Matrix.Rotation(rad(45), 4, 'Y')
    if not head:
        pil = rings("_scp", [(rp, -0.3), (rp, L + 8)], 24); pil.data.transform(M); return [pil]
    pil = rings("_scp", [(rp, -0.3), (rp, L - k + 0.05)], 24)
    hd = rings("_sch", [(rp, L - k), (rh, L), (rh, L + 8)], 32)
    for o in (pil, hd): o.data.transform(M)
    return [pil, hd]

def screw_pad(ang, z0, z_floor):
    """solid pad whose face (perpendicular to the screw) carries the head: for thin plates (top floor)"""
    tip, w = screw_axis(z0); E = tip + w * P["SCR_L"]
    p = Vector((w.z, 0, -w.x)); t_ = Y; R = P["SCR_PAD_R"]
    ring = [E + (p * math.cos(a) + t_ * math.sin(a)) * R for a in [2 * pi * i / 24 for i in range(24)]]
    o = hull("_spad", ring + [Vector((q.x, q.y, z_floor)) for q in ring])
    o.data.transform(Matrix.Rotation(ang, 4, 'Z'))
    return o

def cap_arrow(td, rho_d, Hd):
    """debossed arrow on the cap face above box 1 (segment 0), pointing down; cutter = arrow prism outside the inset skin"""
    zs = P["TOP_SPLIT"]; R, tip = td["R"], P["TOP_TIP_R"]; sl = (R - tip) / (Hd - P["CBH"])
    up = Vector((-sl, 0, 1)).normalized(); n = Vector((1, 0, sl)).normalized()
    z_t = P["CBH"] + 4.0; c = Vector((rho_d(z_t), 0, z_t))
    def pr(name, pts2):
        return hull(name, [c + Y * u + up * v + n * e for u, v in pts2 for e in (-6.0, 3.0)])
    head = pr("_ah", [(0, 0), (-2.8, 4.0), (2.8, 4.0)])
    stem = pr("_as", [(-0.9, 3.8), (0.9, 3.8), (-0.9, 12.0), (0.9, 12.0)])
    boolean(head, [stem], 'UNION')
    d = P["CAP_ARROW_D"]
    inner = hull("_ain", levels(td, [(zs - 1, rho_d(max(zs - 1, 0)), d), (P["CBH"], R, d), (Hd, tip, d)], inner_x=0.0))
    boolean(head, [inner])
    head.data.transform(Matrix.Rotation(theta(td, 0), 4, 'Z'))
    return head

def drum_seat_z():
    """height (tier-local) where the seat cone meets the bearing bore: parallel to the underside cone of the lowest
    drum flange, DRUM_SEAT_CLR (normal) below it"""
    R0, Rf, rb = P["DRUM_R"], P["FL_R"], P["DRUM_R"] + P["BRG_CLR"]
    zfb = rod_z(0) - P["LT_H"] / 2 - P["LT_GAP"] - P["FL_T"]          # flange band bottom = top of its 45 deg cone
    z_at_rb = zfb - (Rf - rb)                                           # flange cone height at the bearing radius
    return z_at_rb - P["DRUM_SEAT_CLR"] * math.sqrt(2)

def mark_top(z_top):
    """arrow on the tube wall just under the shoulder, pointing up (debossed)"""
    R, d, a = P["HUB_R"], P["BAYO_MARK_D"], rad(P["BAYO_MARK_DEG"])
    stem = box("_mks", R - d, R + 1, -0.6, 0.6, z_top - 8.0, z_top - 3.0)
    head = hull("_mkh", [Vector((x, y, z)) for x in (R - d, R + 1) for y, z in ((-1.8, z_top - 3.4), (1.8, z_top - 3.4), (0, z_top - 1.0))])
    for o in (stem, head): o.data.transform(Matrix.Rotation(a, 4, 'Z'))
    return [stem, head]

def mark_bottom():
    """arrow on the underside (z = 0) next to the socket, pointing at the axis (debossed; prints on the bed)"""
    d, a = P["BAYO_MARK_D"], rad(P["BAYO_MARK_DEG"]); r0 = P["TUBE_SPIG_R"] + 2.0
    stem = box("_mbs", r0 + 2.4, r0 + 9.0, -0.6, 0.6, -1, d)
    head = hull("_mbh", [Vector((x, y, z)) for z in (-1, d) for x, y in ((r0 + 2.8, -1.8), (r0 + 2.8, 1.8), (r0, 0))])
    for o in (stem, head): o.data.transform(Matrix.Rotation(a, 4, 'Z'))
    return [stem, head]

def build_carrier(t, merged=False):
    """MECH carrier: tray (TRAY_PLAY smaller than the cell recess, so a box can pop out) + Ø50 tube up to the
    next tier, tube bayonet spigot on top / socket below, per cell: rod hole and 6x3 magnet pocket (open outwards)"""
    T, top = P["TRAY_T"], t["H"] + P["STACK_GAP"]
    tr = t["tray_r"] - P["TRAY_PLAY"]; rs = P["TUBE_SPIG_R"]
    o = rings(f"T{t['k']+1}_Carrier", [(tr, 0), (tr, T - 0.8), (tr - 0.8, T)], 128)
    boolean(o, [rings("_tube", [(P["HUB_R"], T - 0.5), (P["HUB_R"], top)], 128)] + spigot(top, r=rs), 'UNION')
    if merged:   # grows straight out of the base: no socket, the bearing band starts at the floor
        rb = P["DRUM_R"] + P["BRG_CLR"]
        cut = [rings("_bb", [(rb, -1), (rb, top + P["SPIG_H"] + 1)], 128),
               rings("_bu", [(P["TUBE_RI"], P["BRG_TOP"]), (P["TUBE_RI"], top + P["SPIG_H"] + 1)], 128)]
    else:
        cut = socket(0, r=rs) + bearing_bore(top + P["SPIG_H"] + 1, P["BRG_TOP"])
        if P["BAYO_MARK"]: cut += mark_bottom()
    if P["BAYO_MARK"]: cut += mark_top(top)
    if P.get("TIER_SCREW"):
        # screw from the part above (tier k-1 tray, or the top floor for T1) into this tube's top
        cut += screw_cut(rad(P["FRONT_DEG"]) if t["k"] == 0 else screw_seam(), top)
        if not merged:   # this tray is screwed into the tube below (head in the tray, between boxes)
            cut += screw_cut(screw_seam(), 0.0)
    for i in range(t["n"]):
        R_ = Matrix.Rotation(theta(t, i), 4, 'Z')
        if P["LATCH"]:
            sl = lt_slot("_ls", rod_z(i))
            boolean(sl, [y_cyl("_lpin", P["LT_PIN_R"], -13, 13, P["LT_PIV"], rod_z(i), 24)], 'UNION')
            h = sl
        else:
            h = radial_cyl("_rh", P["ROD_HOLE_R"], P["TUBE_RI"] - 1, P["HUB_R"] + 1, rod_z(i), 16)
        pk = radial_cyl("_tp", pocket_r(), P["HUB_R"] - P["MAG_T"] - 0.1, P["HUB_R"] + 1, rod_z(i) - mag_dz())
        wr = P["WASHER_D"] / 2 + P["WASHER_CLR"]          # washer recess: same top edge as the magnet pocket, centre lower
        extra = [radial_cyl("_tw", wr, P["HUB_R"] - P["WASHER_T"] - 0.2, P["HUB_R"] + 1,
                            rod_z(i) - mag_dz() - (wr - pocket_r()), 64)] if P["WASHER"] else []
        for c_ in [h, pk] + extra: c_.data.transform(R_)
        cut += [h, pk] + extra
    return boolean(o, cut)

def cam_x0():
    """ramp start (key-angle offset before the mark): just clear of the rod at the previous stop"""
    return -P["STEP_DEG"] + P["STOP_DEG"] + P["ROD_TIP_W"] + P["CAM_MARGIN"]

def cam_lift(x):
    """rod lift at key-angle offset x from the day mark (drop at x = 0)"""
    x0, xh, rise = cam_x0(), -P["CAM_HOLD"], P["CAM_RISE"]
    if x < x0 or x > 0: return 0.0
    if x >= xh: return rise
    u = (x - x0) / (xh - x0); return rise * (0.5 * u + 0.5 * u * u)   # slope 0.5x avg at the start, 1.5x at the top

def _add_lobe(bm, alpha, zf):
    """cam lobe in drum coordinates (alpha = drum angle of the day mark): smooth ramp from cam_x0() to the peak,
    hold, sharp drop at alpha; flat band zf..zf+CAM_H; 45 deg chamfer CAM_CH high underneath (prints standing)"""
    R0, rise = P["DRUM_R"], P["CAM_RISE"]
    x0 = cam_x0(); nth = int(round(-x0 / 0.25))
    xs = [x0 * (1 - j / nth) for j in range(nth + 1)]
    zb = zf - P["CAM_CH"]; levels_ = [zb + P["CAM_CH"] * j / 10 for j in range(11)] + [zf + P["CAM_H"]]
    rings_ = []
    for z in levels_:
        ring = []
        for x in xs:
            r = R0 + min(cam_lift(min(x, -1e-6)), max(z - zb, 0.0) * rise / P["CAM_CH"]); ar = rad(alpha + x)
            ring.append(bm.verts.new((r * math.cos(ar), r * math.sin(ar), z)))
        for x in reversed(xs):
            ar = rad(alpha + x); ring.append(bm.verts.new(((R0 - 0.5) * math.cos(ar), (R0 - 0.5) * math.sin(ar), z)))
        rings_.append(ring)
    n = len(rings_[0]); bm.faces.new(rings_[0][::-1]); bm.faces.new(rings_[-1])
    for a_, b_ in zip(rings_[:-1], rings_[1:]):
        for j in range(n): bm.faces.new((a_[j], a_[(j + 1) % n], b_[(j + 1) % n], b_[j]))
    bmesh.ops.remove_doubles(bm, verts=[v for r in rings_ for v in r], dist=1e-4)

def _house(name, w, h, x0, x1, z0):
    """prism along X: flat sides up to z0 + h, then a 45 deg gable (peak z0 + h + w/2)"""
    pts = []
    for x in (x0, x1):
        pts += [Vector((x, y, z)) for y in (-w / 2, w / 2) for z in (z0, z0 + h)] + [Vector((x, 0, z0 + h + w / 2))]
    return hull(name, pts)

def drum_top(t):
    top = t["H"] + P["STACK_GAP"]
    return top + P["TOP_BOSS_H"] + 2.0 if t["k"] == 0 else top

def build_drum(t):
    """drum segment of one tier (tier-local z, drum frame = key at 0 deg): lobes for the tier's days.
    Coupling: collar with 4 teeth on top (plugs into the bore of the segment above), 4 slots at the foot of
    the bore (45 deg roofs); inside the segment the bore narrows to the collar bore on a 45 deg cone. Prints standing."""
    k, nt = t["k"], len(P["H"]); zt = drum_top(t); R0, RI = P["DRUM_R"], P["DRUM_RI"]
    o = rings(f"T{k+1}_Drum", [(R0, 0), (R0, zt)], 96)
    if k == 0:
        hr = P["SPL_HOLE"]   # 45 deg roof down to the garland hole, which runs on up through the spline stud
        bore = rings("_db", [(RI, -1), (RI, zt - 2 - (RI - hr)), (hr, zt - 2)], 96)
    else:
        ci = P["CPL_RI"]; zc = zt - 0.3 - (RI - ci)
        bore = rings("_db", [(RI, -1), (RI, zc)], 96)
        cone = rings("_dc", [(RI, zc - 0.01), (ci, zc + (RI - ci))], 96)       # 45 deg step down to the collar bore
    cuts = [bore] + ([] if k == 0 else [cone, rings("_dcb", [(P["CPL_RI"], zc), (P["CPL_RI"], zt + 1)], 96)])
    c, L = P["CPL_CLR"], P["CPL_L"]
    if k < nt - 1:   # slots for the teeth of the collar below
        for a, w in zip(P["CPL_TOOTH_DEG"], P["CPL_TOOTH_W"]):
            sl = _house("_slot", w + 2 * c, L + c + 1.0, RI - 1.0, P["CPL_TOOTH_R"] + c, -1.0)
            sl.data.transform(Matrix.Rotation(rad(a), 4, 'Z')); cuts.append(sl)
    boolean(o, cuts)
    notches = []
    if P["LATCH"]:
        add = []
        Rf = P["FL_R"]; t2 = P["LT_T"] / 2
        yc = -t2 + P["LT_TIP_W"] / 2                                    # tail tip centre (tangential offset)
        rm = P["LT_TAIL"] + P["LT_TIP_L"] / 2
        off = math.degrees(math.atan2(yc, rm))
        hh = math.degrees(math.atan2(P["LT_TIP_W"] / 2, P["LT_TAIL"])) + P["NOTCH_WIN"]   # flat bottom half-width
        run = math.degrees(1.0 / (rm * math.tan(rad(P["NOTCH_RAMP"]))))            # ramp: deg per mm of depth
        for i in range(t["n"]):
            n = t["first"] + i
            zft = rod_z(i) - P["LT_H"] / 2 - P["LT_GAP"]; zfb = zft - P["FL_T"]
            fl = rings("_fl", [(R0 - 0.3, zfb - (Rf - R0) - 0.3), (Rf, zfb), (Rf, zft), (R0 - 0.3, zft)], 96)
            boolean(fl, [cyl(R0 - 0.6, zfb - 10, zft + 1, 96)])
            add.append(fl)
            al = math.degrees(theta(t, i)) + P["STEP_DEG"] * n + off   # aligned with the tail when the key is on day n
            zb_, zt_ = zft - P["NOTCH_D"], zft + 0.5
            ht = hh + run * (zt_ - zb_)
            ri_ = R0 / math.cos(rad(ht)) + 0.05
            pts = [Vector((r * math.cos(rad(al + d)), r * math.sin(rad(al + d)), z)) for r in (ri_, Rf + 1.5)
                   for d, z in ((-hh, zb_), (hh, zb_), (-ht, zt_), (ht, zt_))]
            notches.append(hull("_notch", pts))
    else:
        bm = bmesh.new()
        for i in range(t["n"]):
            n = t["first"] + i
            _add_lobe(bm, math.degrees(theta(t, i)) + P["STEP_DEG"] * n - P["STOP_DEG"], rod_z(i) - P["CAM_H"] / 2)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("_lobes"); bm.to_mesh(me); bm.free()
        add = [new_obj("_lobes", me)]
    if k > 0:
        ro = RI - c; ci = P["CPL_RI"]
        col = rings("_col", [(ro, zt - 0.5), (ro, zt + L - 0.6), (ro - 0.6, zt + L)], 96)
        boolean(col, [rings("_cb", [(ci, zt - 1), (ci, zt + L + 1)], 96)])
        add.append(col)
        for a, w in zip(P["CPL_TOOTH_DEG"], P["CPL_TOOTH_W"]):
            tb = hull("_tooth", [Vector((x, y, z)) for y in (-w / 2, w / 2) for x, z in
                                 ((ro - 0.4, zt - 0.5), (P["CPL_TOOTH_R"], zt - 0.5), (P["CPL_TOOTH_R"], zt + L - 1.5),
                                  (ro - 0.4, zt + L - 0.5))])
            tb.data.transform(Matrix.Rotation(rad(a), 4, 'Z')); add.append(tb)
    else:
        P["_SPL_Z"] = zt
        add.append(spline_stud("_stud", zt - 0.5, zt + P["SPL_L"], 0.0, P["FRONT_DEG"]))   # missing tooth under the pointer
        notches.append(rings("_gh", [(P["SPL_HOLE"], zt - 3), (P["SPL_HOLE"], zt + P["SPL_L"] + 1)], 64))   # garland hole
    boolean(o, add, 'UNION')
    if k == 0 and P["DETENT"]:   # 25 V-grooves for the click springs (vertical: prints standing)
        z0g = t["H"] + P["STACK_GAP"] + P["DET_Z"][0] - 1.0; rt_ = R0 - P["DET_D"]; ro_ = R0 + 1.0
        for j in range(25):
            gr = hull("_grv", [Vector((x, y, z)) for z in (z0g, zt + 1) for x, y in
                               ((rt_, 0), (ro_, -(ro_ - rt_)), (ro_, ro_ - rt_))])
            gr.data.transform(Matrix.Rotation(rad(P["DET_PSI"] + j * P["STEP_DEG"]), 4, 'Z'))
            notches.append(gr)
    if notches: boolean(o, notches)
    return o

def spline_profile(grow):
    """closed 2D outline of the spline: SPL_N teeth, tooth 0 (pointing at the arrow, +X) left out"""
    n, rt, rr = P["SPL_N"], P["SPL_RT"] + grow, P["SPL_RR"] + grow
    p = 2 * pi / n; pts = []
    for j in range(n):
        a = j * p
        if j == 0:
            pts += [(rr, a - 0.45 * p), (rr, a), (rr, a + 0.45 * p)]
        else:
            pts += [(rr, a - 0.45 * p), (rt, a - 0.18 * p), (rt, a + 0.18 * p), (rr, a + 0.45 * p)]
    return [(r * math.cos(a), r * math.sin(a)) for r, a in pts]

def spline_stud(name, z0, z1, grow, rot=0.0):
    """tapered splined prism: full size at the base (SPL_L above the drum top), SPL_TAPER at the far end -> wedge fit.
    The taper is referenced to the drum top so the stud and the knob hole share one cone."""
    bm = bmesh.new(); prof = spline_profile(grow); rings_ = []
    for z in (z0, z1):
        u = (z - P["_SPL_Z"]) / P["SPL_L"]; k = 1.0 + (P["SPL_TAPER"] - 1.0) * u
        rings_.append([bm.verts.new((x * k, y * k, z)) for x, y in prof])
    nn = len(prof)
    bm.faces.new(rings_[0][::-1]); bm.faces.new(rings_[1])
    for a in range(nn): bm.faces.new((rings_[0][a], rings_[0][(a + 1) % nn], rings_[1][(a + 1) % nn], rings_[1][a]))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.transform(Matrix.Rotation(rad(rot), 4, 'Z'))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me)

def build_key():
    """turning knob: hub on the spline stud + a finger fin that ends in the pointer (+X; placed at FRONT_DEG).
    Through hole = the stud cone + KEY_CLR, so the knob wedges tight a little above the drum top. Prints flat side down."""
    h, fh, fw = P["KEY_H"], P["KEY_FIN_H"], P["KEY_FIN_W"] / 2
    o = rings("Key", [(P["KEY_R"], 0), (P["KEY_R"], h - 0.8), (P["KEY_R"] - 0.8, h)], 64)
    tail, tip = -P["KEY_FIN_BACK"], P["KEY_ARROW"]
    fin = hull("_fin", [Vector((x, y, z)) for x, y, z in
                        [(tail, -fw, 0), (tail, fw, 0), (tail + 2, -fw, fh), (tail + 2, fw, fh),     # tail: full height
                         (tip - 12, -fw, 0), (tip - 12, fw, 0), (tip - 14, -fw, fh), (tip - 14, fw, fh),
                         (tip, 0, 0), (tip, 0, 2.0)]])                                        # pointer: low, sharp
    boolean(o, [fin], 'UNION')
    # stud cone in key coordinates: key bottom = KEY_SEAT above the drum top
    P["_SPL_Z"] = -P["KEY_SEAT"]
    return boolean(o, [spline_stud("_hole", -1.0, fh + 1.0, P["KEY_CLR"])], solver='EXACT')

def build_dial(zs):
    """marks on the top floor: start dot + one bar and number per day at its STOP (just after the drop), clockwise from the front.
    Returns (recess cutter, inlay) like the cell numbers"""
    d, rel = P["DIAL_DEPTH"], P["DIAL_RELIEF"]; r0, r1 = P["DIAL_TICK"]
    def marks(z0, z1, grow):
        parts = []
        for n in range(0, 25):                 # 0 = start (dot), 1..24 = days; mark = stop position
            a = rad(P["FRONT_DEG"] - P["STEP_DEG"] * n)
            if n == 0:
                m = rings("_dt", [(1.6 + grow, z0), (1.6 + grow, z1)], 24)
                m.data.transform(Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((P["DIAL_NUM_R"], 0, 0))); parts.append(m)
                continue
            m = box("_tk", r0, r1, -0.7 - grow, 0.7 + grow, z0, z1)
            m.data.transform(Matrix.Rotation(a, 4, 'Z')); parts.append(m)
            v = Vector((math.cos(a), math.sin(a), 0))
            u = Vector((math.sin(a), -math.cos(a), 0))
            parts.append(text_cutter("_dn", str(n), 3.4, 5.2, v * P["DIAL_NUM_R"], u, v, Z, z0, z1))
        o = parts[0]; boolean(o, parts[1:], 'UNION', solver='EXACT'); return o
    inl = marks(zs - d, zs + rel, 0.0)
    cut = new_obj("_dialcut", inl.data.copy())
    return cut, inl

def build_hardware(t):
    """reference only (not printed): filament rods at rest, tube magnets, box magnets"""
    rods, mags, levers = [], [], []
    for i in range(t["n"]):
        R_ = Matrix.Rotation(theta(t, i), 4, 'Z'); zm = rod_z(i) - mag_dz(); md = P["MAG_D"] / 2
        rr, x0 = P["ROD_D"] / 2, P["DRUM_R"]
        if P["LATCH"]:
            m1 = radial_cyl("_m1", md, P["HUB_R"] - P["MAG_T"], P["HUB_R"], zm, 32)
            m2 = radial_cyl("_m2", md, r_in() + P["MAG_SET"], r_in() + P["MAG_SET"] + P["MAG_T"], zm, 32)
            xp = P["LT_PIV"]; yl = math.sqrt((P["HUB_R"] - 0.1) ** 2 - (xp + rr) ** 2)   # pin cut just inside the tube surface
            r = y_cyl("_pin", rr, -yl, yl, xp, rod_z(i), 16)
            lv = build_lever(f"T{t['k']+1}_Latch_{t['first'] + i:02d}", rod_z(i))
            for o in (r, m1, m2, lv): o.data.transform(R_)
            lv["compartment"] = t["first"] + i
            rods.append(r); mags += [m1, m2]; levers.append(lv)
            continue
        r = rings("_rod", [(rr * math.sin(rad(a)), x0 + rr * (1 - math.cos(rad(a)))) for a in (15, 40, 65, 90)] + [(rr, P["HUB_R"])], 12)
        r.data.transform(Matrix.Translation((0, 0, rod_z(i))) @ Matrix.Rotation(rad(90), 4, 'Y'))   # domed tip on the drum
        m1 = radial_cyl("_m1", md, P["HUB_R"] - P["MAG_T"], P["HUB_R"], zm, 32)
        m2 = radial_cyl("_m2", md, r_in() + P["MAG_SET"], r_in() + P["MAG_SET"] + P["MAG_T"], zm, 32)
        for o in (r, m1, m2): o.data.transform(R_)
        rods.append(r); mags += [m1, m2]
    def join(name, objs):
        bm = bmesh.new()
        for o in objs: bm.from_mesh(o.data)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        for o in objs:
            m = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(m)
        return new_obj(name, me)
    if P["LATCH"]:
        return join(f"T{t['k']+1}_Pins", rods), join(f"T{t['k']+1}_Magnets", mags), levers
    return join(f"T{t['k']+1}_Rods", rods), join(f"T{t['k']+1}_Magnets", mags), []

def build_carrier_hook(t):
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
    carn = P.pop("_BASE_CAR", None) if P["BASE_MERGE"] else None
    if not carn:
        boolean(o, spigot(Bh, r=P["TUBE_SPIG_R"]), 'UNION')
        # hollow tube spigot (the drum stands inside it on the base)
        boolean(o, [rings("_tb", [(P["TUBE_RI"], Bh), (P["TUBE_RI"], Bh + P["SPIG_H"] + 1)], 128)])
    # centring pin in the drum bore
    pr = P["DRUM_RI"] - 0.3
    boolean(o, [rings("_pin", [(pr, Bh - 0.5), (pr, Bh + 3.5), (pr - 1.0, Bh + 4.5)], 64)], 'UNION')
    if P["CABLE"]:   # garland: up through the centre, out along a groove on the underside to the back edge
        w, d = P["CABLE_GROOVE_W"] / 2, P["CABLE_GROOVE_D"]
        boolean(o, [rings("_cbore", [(P["BORE_R"], -1), (P["BORE_R"], Bh + P["SPIG_H"] + 1)], 32),
                    box("_cgroove", -w, w, 0.0, R + 5, -1, d)])
    tc = stamp_cutter("_brand", P["BRAND_STAMP"], P["BRAND_W"], Vector((0, P["BRAND_Y"], 0)), -X, Y, -Z, -P["STAMP_DEPTH"], 1.0)
    if tc is None and P["BRAND"]:
        tc = text_cutter("_brand", P["BRAND"], 11, 110, Vector((0, -30, 0)), -X, Y, -Z, -0.6, 1.0)
    if tc: boolean(o, [tc], solver='EXACT')
    if carn:   # bottom carrier as part of the base (tier-local z0 = BASE_H); joined last, after the EXACT stamp cut
        car = bpy.data.objects[carn]; car.data.transform(Matrix.Translation((0, 0, TIERS[-1]["z0"])))
        boolean(o, [car], 'UNION')
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
    # MECH: ring boss carrying the tube socket; the drum passes through its bore up to the key
    rs = P["TUBE_SPIG_R"]; rb = rs + P["LUG_R"] + P["BAYO_CLR"] + 1.6
    boss = rings("_boss", [(rb, zs - 0.5), (rb, P["TOP_BOSS_H"] - 0.8), (rb - 0.8, P["TOP_BOSS_H"])], 128)
    boolean(fl, [boss], 'UNION')
    dc, dinl = build_dial(zs)
    if P.get("TIER_SCREW") and P.get("SCR_TOP_PAD"):
        a_s = rad(P["FRONT_DEG"])
        boolean(fl, [screw_pad(a_s, 0.0, zs - 0.5)], 'UNION')
    boolean(fl, socket(0, r=rs) + bearing_bore(P["TOP_BOSS_H"] + 1, None)
            + (mark_bottom() if P["BAYO_MARK"] else [])
            + (screw_cut(rad(P["FRONT_DEG"]), 0.0, head=P.get("SCR_TOP_PAD", False)) if P.get("TIER_SCREW") else []))   # top bearing for the drum
    if P["DETENT"]:   # before the dial cut (EXACT result may not be clean enough for MANIFOLD)
        dcut, dadd = detent_parts()
        boolean(fl, dcut); boolean(fl, dadd, 'UNION')
    boolean(fl, [dc], solver='EXACT')
    fl["dial_inlay"] = dinl.name
    # ---- cap: z zs..Hd, hollow cone; reversed bayonet grooves in its foot ride on the rim lugs; star socket at the tip
    boolean(o, [box("_cut", -500, 500, -500, 500, -500, zs)])
    z_in = zs + Hr + 0.6
    boolean(o, [hollow(z_in - 0.01)])
    boolean(o, socket(zs, sense=-1, r=Rr, h=Hr) + [star_socket(Hd)])
    if P["PULL_TAB"] and P.get("TOP_TABS", True):
        # decorative tabs on the six dummy segments, same style; they end at the cap's bottom (zs) so the cap still
        # prints standing on its rim: the tabs rise from the bed and lean inwards with the cone (~30 deg)
        slope = (td["R"] - tip) / (Hd - P["CBH"])
        tabs, dims = [], []
        for i in range(6):
            tb, dm = make_tab(td, td["R"], slope, zs, tab_width(td["R"]) / 2)
            for x in (tb, dm): x.data.transform(Matrix.Rotation(theta(td, i), 4, 'Z'))
            tabs.append(tb); bpy.data.objects.remove(dm)        # decorative: no dimple (it would print as a flat ceiling here)
        boolean(o, tabs, 'UNION')
    if P.get("CAP_ARROW"): boolean(o, [cap_arrow(td, rho_d, Hd)])
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

ROOT, ASM, EXP, BLD = "AdventTreeMech", "ATM_Assembly", "ATM_Exploded", "_build_m"
def wipe():
    """take the old mech collections out of the scene and rename them *_trash (no deleting here: deleting these
    objects while they are in the depsgraph crashed Blender); purge_trash() removes them in a later call"""
    root = bpy.data.collections.get(ROOT)
    if root:
        for parent in [bpy.context.scene.collection] + list(bpy.data.collections):
            if root.name in parent.children: parent.children.unlink(root)
    for cn in (ROOT, ASM, EXP, BLD):
        c = bpy.data.collections.get(cn)
        if c:
            for o in c.all_objects:
                if not o.name.endswith("_trash"): o.name = o.name + "_trash"
            for ch in [c] + list(c.children_recursive): ch.name = ch.name + "_trash"
            if c.name.startswith(BLD):
                for parent in [bpy.context.scene.collection] + list(bpy.data.collections):
                    if c.name in parent.children: parent.children.unlink(c)

def purge_trash():
    cs = [c for c in bpy.data.collections if c.name.endswith("_trash")]
    objs = {o for c in cs for o in c.all_objects}
    if objs: bpy.data.batch_remove(list(objs))
    if cs: bpy.data.batch_remove(cs)
    orphan = [m for m in bpy.data.meshes if m.users == 0] + [d for d in bpy.data.curves if d.users == 0]
    if orphan: bpy.data.batch_remove(orphan)
    return len(objs)

def heal(o):
    """dissolve boolean slivers (< 0.02 mm) around non-manifold edges, only if that makes the mesh manifold"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bad = [e for e in bm.edges if not e.is_manifold]
    if bad:
        pts = [v.co.copy() for e in bad for v in e.verts]
        near = [e for e in bm.edges if any((e.verts[0].co - p).length < 0.2 for p in pts)]
        bmesh.ops.dissolve_degenerate(bm, edges=near, dist=0.02)
        if not any(not e.is_manifold for e in bm.edges): bm.to_mesh(o.data)
    bm.free()

def place(o, coll, M, color, kind, print_M):
    heal(o)
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o); o.matrix_world = Matrix.Translation(P["ORIGIN"]) @ M
    o.data.materials.clear(); o.data.materials.append(material(color))
    o.color = (*P["COLORS"][color], 1)
    o["part_kind"] = kind
    nm = o.name.split(".")[0]
    if nm.startswith("T") and nm[1].isdigit(): o["tier"] = int(nm[1])
    o["print_matrix"] = [x for row in print_M for x in row]
    o["variant"] = "mech"
    o.name = P["PREFIX"] + nm; o.data.name = o.name

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

def _colls():
    global BUILD
    root = get_coll(ROOT); asm = get_coll(ASM, root); BUILD = get_coll(BLD)
    return root, asm

def key_rot(): return Matrix.Rotation(rad(-P["KEY_PHI"]), 4, 'Z')   # key turns clockwise seen from above

def build_begin():
    wipe()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 0.001
    sc.unit_settings.length_unit = 'MILLIMETERS'
    _colls(); return derive()

def build_tier(k):
    derive(); _, asm = _colls(); t = TIERS[k]
    tc = get_coll(f"ATM_T{k+1}_{t['n']}x", asm)
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
        place(hA, tc, Mw, t["color"], "module", print_A); hA["compartment"] = num; hA["half"] = "A"
        place(hB, tc, Mw, t["color"], "module", print_B); hB["compartment"] = num; hB["half"] = "B"
        for h, q in ((hA, nA), (hB, nB)):
            if q is not None: join_inlay(h, q)
        t.pop("boss_z", None)
    m = base.data; bpy.data.objects.remove(base); bpy.data.meshes.remove(m); bpy.data.meshes.remove(t["lip"])
    M0 = Matrix.Translation((0, 0, t["z0"]))
    if P["BASE_MERGE"] and k == len(P["H"]) - 1:
        car = build_carrier(t, merged=True); P["_BASE_CAR"] = car.name   # joined to the base in build_core
    else:
        place(build_carrier(t), tc, M0, t["color"], "carrier", Matrix())
    place(build_drum(t), tc, M0 @ key_rot(), "drum", "drum", Matrix())
    rods, mags, levers = build_hardware(t)
    place(rods, tc, M0, "brass", "hardware", Matrix()); place(mags, tc, M0, "steel", "hardware", Matrix())
    for lv in levers:   # printed: lying flat on its -Y face
        th = theta(t, (lv["compartment"] - t["first"]))
        Mp = Matrix.Rotation(rad(90), 4, 'X') @ Matrix.Rotation(-th, 4, 'Z')
        place(lv, tc, M0, "gold", "latch", Mp)

def build_core():
    top_z = derive(); _, asm = _colls()
    core = get_coll("ATM_Core", asm)
    place(build_base(), core, Matrix(), "green", "base", Matrix())
    cap, tfl = build_top()
    place(cap, core, Matrix.Translation((0, 0, top_z)), P["TOP_COLOR"], "top", Matrix())
    dinl = bpy.data.objects[tfl["dial_inlay"]]; del tfl["dial_inlay"]
    place(tfl, core, Matrix.Translation((0, 0, top_z)), P["TOP_COLOR"], "topfloor", Matrix())
    join_inlay(tfl, dinl)
    zk = TIERS[0]["z0"] + drum_top(TIERS[0]) + P["KEY_SEAT"]
    place(build_key(), core, Matrix.Translation((0, 0, zk)) @ key_rot() @ Matrix.Rotation(rad(P["FRONT_DEG"]), 4, 'Z'),
          "gold", "key", Matrix())
    sh = build_star_half(); _, _, y_tip, _ = star_geom(); zt_ = top_z + P["TOP_H"] - y_tip
    Mf = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, zt_), (0, 0, 0, 1)))
    Mb = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, zt_), (0, 0, 0, 1)))
    sb = new_obj("Star_Back", sh.data); sh.name = "Star_Front"
    place(sh, core, Mf, "ivory", "star", Matrix()); place(sb, core, Mb, "ivory", "star", Matrix())
    return top_z

def build_exploded():
    derive(); root, asm = _colls()
    old = bpy.data.collections.get(EXP)
    if old:
        bpy.data.batch_remove(list(old.all_objects)); bpy.data.collections.remove(old)
    exp = get_coll(EXP, root); nt = len(P["H"])
    for o in list(asm.all_objects):
        e = o.copy(); exp.objects.link(e); e.name = o.name + "_X"
        k = o.get("tier"); kind = o["part_kind"]; dz = 0
        if k: dz = (nt - k) * 105 + (0 if (P["BASE_MERGE"] and k == nt) else 30)   # merged base carries T4's tube: keep T4 at its height
        elif kind == "top": dz = nt * 105 + 70
        elif kind in ("topfloor", "key"): dz = nt * 105 + 25 + (12 if kind == "key" else 0)
        elif kind == "star": dz = nt * 105 + 110
        if kind == "drum": dz += 20
        out = {"module": 30}.get(kind, 0)
        th = o.matrix_world.to_euler().z
        off = Vector((math.cos(th) * out, math.sin(th) * out, dz)) + Vector((340, 0, 0))
        if o.get("half"): off += Vector((-math.sin(th), math.cos(th), 0)) * (12 if o["half"] == "B" else -12)
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

if globals().get("AT_RUN", False):
    TOP_Z = build_all()
