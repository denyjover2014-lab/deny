"""Generate index.html: protected bike intersection plan.

All plan geometry is in metres. Origin = centre of the junction,
x = east, y = south (SVG convention), north is up.
Right-hand traffic (Philippines).

Run:  python3 build_plan.py   -> writes index.html next to this file.
"""
import math
import pathlib

HERE = pathlib.Path(__file__).parent

# ---------------------------------------------------------------- geometry
# Main road (N-S)
MED = 1.25            # half median width (2.5 m median)
SB_EDGE = -11.0       # outer edge of SB traffic lanes (3 x 3.25 m)
SB_SEP = -12.5        # separator -11.0 .. -12.5 (1.5 m)
W_KERB = -15.0        # existing west kerb; bike lane -12.5 .. -15.0 (2.5 m)
W_PROP = -22.0        # west property line (7 m sidewalk, verify)
NB_EDGE = 15.0        # NB carriageway kept as is (3 x 3.5 + 3.25 curb lane)
PARK_E = 27.0         # east median park 15 .. 27
SVC_E = 34.0          # east service road 27 .. 34
# Cross street (E-W)
XS_LANE = 3.7         # one 3.7 m lane each way
XS_SEP = 4.2          # separator 3.7 .. 4.2
XS_KERB = 6.0         # bike lane 4.2 .. 6.0 (1.8 m)
XS_PROP = 13.0        # property line (7 m corner sidewalk, verify)
# Protected-intersection ring (bike crossings), set back 5 m
SET = 5.0
RW_V = 2.5                                  # west/east ring width
RW_H = 2.0                                  # north/south ring width
RX_W = SB_EDGE - SET - RW_V / 2             # -17.25 centre of west ring
RX_E = NB_EDGE + SET + RW_V / 2             #  21.25 centre of east ring
RY = XS_LANE + SET + RW_H / 2               #   9.70 centre of N/S ring
# Pedestrian crossings (4 m) outside the ring
PED_Y0, PED_Y1 = RY + RW_H / 2 + 1.0, RY + RW_H / 2 + 5.0     # 11.7 .. 15.7
PED_XW0, PED_XW1 = RX_W - RW_V / 2 - 1.0, RX_W - RW_V / 2 - 5.0  # -19.5 .. -23.5
PED_XE0, PED_XE1 = RX_E + RW_V / 2 + 1.0, RX_E + RW_V / 2 + 4.0  # 23.5 .. 26.5

C = dict(
    ground="#dedbd3", block="#ecebe6", blockline="#c9c6bd", asphalt="#50555b",
    concrete="#c3bfb6", island="#b3aea3", islandline="#8d887d", park="#9fbf83",
    parkpath="#d8d2c2", green="#2c9a52", white="#ffffff", yellow="#f2c230",
    ink="#1d2522", tree="#6f9a5a", jeep="#c8452f", pole="#1d2522",
)


def cubic(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def s_bend(a, b, axis):
    """Smooth S-bend from a to b; tangent along `axis` ('x' or 'y') at both ends."""
    if axis == "y":
        my = (a[1] + b[1]) / 2
        return cubic(a, (a[0], my), (b[0], my), b)
    mx = (a[0] + b[0]) / 2
    return cubic(a, (mx, a[1]), (mx, b[1]), b)


def densify(pts, step=0.5):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / step))
        for i in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out


def join(*segs):
    return densify(_join(*segs))


def _join(*segs):
    out = []
    for s in segs:
        for p in s:
            if not out or (abs(out[-1][0] - p[0]) > 1e-9 or abs(out[-1][1] - p[1]) > 1e-9):
                out.append(p)
    return out


def offset(pts, d):
    """Offset polyline by d (positive = left of travel direction in SVG coords)."""
    res = []
    n = len(pts)
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = dy / L, -dx / L
        res.append((pts[i][0] + nx * d, pts[i][1] + ny * d))
    return res


def band(pts, w):
    left = offset(pts, w / 2)
    right = offset(pts, -w / 2)
    return left + right[::-1]


def poly(pts, fill, stroke=None, sw=0.15, extra=""):
    d = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<polygon points="{d}" fill="{fill}"{s} {extra}/>'


def pline(pts, stroke, sw, extra=""):
    d = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    return f'<polyline points="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def rect(x0, y0, x1, y1, fill, extra=""):
    x, y = min(x0, x1), min(y0, y1)
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{abs(x1 - x0):.2f}" height="{abs(y1 - y0):.2f}" fill="{fill}" {extra}/>'


def line(x0, y0, x1, y1, stroke, sw, extra=""):
    return f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def text(x, y, s, size=1.3, fill=C["ink"], anchor="middle", extra=""):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-family="Barlow Condensed, Arial Narrow, sans-serif" font-weight="600" {extra}>{s}</text>')


# ---------------------------------------------------------------- bike paths
EXT = 60  # extend beyond drawing


def sb_path():
    x_up = (SB_SEP + W_KERB) / 2   # -13.75
    return join([(x_up, -EXT), (x_up, -24)], s_bend((x_up, -24), (RX_W, -14), "y"),
                [(RX_W, -14), (RX_W, 40)], s_bend((RX_W, 40), (x_up, 48), "y"), [(x_up, EXT)])


def wb_west_path():
    yc = -(XS_SEP + XS_KERB) / 2   # -5.1
    return join([(RX_W - RW_V / 2, -RY), (-24, -RY)], s_bend((-24, -RY), (-32, yc), "x"), [(-EXT, yc)])


def eb_west_path():
    yc = (XS_SEP + XS_KERB) / 2
    return join([(-EXT, yc), (-32, yc)], s_bend((-32, yc), (-24, RY), "x"), [(RX_W - RW_V / 2, RY)])


def wb_east_path():
    yc = -(XS_SEP + XS_KERB) / 2
    return join([(EXT, yc), (42, yc)], s_bend((42, yc), (SVC_E, -RY), "x"), [(RX_E + RW_V / 2, -RY)])


def eb_east_path():
    yc = (XS_SEP + XS_KERB) / 2
    return join([(RX_E + RW_V / 2, RY), (SVC_E, RY)], s_bend((SVC_E, RY), (42, yc), "x"), [(EXT, yc)])


def nb_path():
    return [(RX_E, EXT), (RX_E, -EXT)]


# ---------------------------------------------------------------- glyphs
def bike_glyph(x, y, rot, s=1.0):
    """Side-view bicycle pictogram, readable by a rider travelling in direction rot (0 = north)."""
    g = (f'<g transform="translate({x:.2f},{y:.2f}) rotate({rot}) scale({s})" fill="none" '
         f'stroke="#fff" stroke-width="0.16" stroke-linecap="round" stroke-linejoin="round">'
         '<circle cx="-0.72" cy="0.35" r="0.42"/><circle cx="0.72" cy="0.35" r="0.42"/>'
         '<path d="M-0.72 0.35 L-0.2 -0.35 L0.45 -0.35 L0.72 0.35 M-0.2 -0.35 L0.05 0.35 L0.45 -0.35 '
         'M-0.3 -0.55 L-0.05 -0.55 M0.45 -0.35 L0.4 -0.62 L0.62 -0.62"/>'
         '<circle cx="0.05" cy="-1.05" r="0.2" fill="#fff" stroke="none"/></g>')
    return g


def chevron(x, y, rot, s=1.0):
    return (f'<g transform="translate({x:.2f},{y:.2f}) rotate({rot}) scale({s})">'
            '<path d="M-0.55 0.35 L0 -0.25 L0.55 0.35" fill="none" stroke="#fff" stroke-width="0.2"/></g>')


def arrow(x, y, rot, kind="T"):
    head = '<path d="M-0.75 -1.1 L0.75 -1.1 L0 -2.6 Z" fill="#fff"/>'
    if kind == "T":
        body = '<path d="M0 2.4 V-1.2" stroke="#fff" stroke-width="0.32" fill="none"/>' + head
    elif kind == "L":
        body = ('<path d="M0.5 2.4 V0 Q0.5 -1.0 -0.6 -1.0" stroke="#fff" stroke-width="0.32" fill="none"/>'
                '<path d="M-0.6 -1.75 L-0.6 -0.25 L-2.0 -1.0 Z" fill="#fff"/>')
    elif kind == "R":
        body = ('<path d="M-0.5 2.4 V0 Q-0.5 -1.0 0.6 -1.0" stroke="#fff" stroke-width="0.32" fill="none"/>'
                '<path d="M0.6 -1.75 L0.6 -0.25 L2.0 -1.0 Z" fill="#fff"/>')
    elif kind == "TR":
        body = ('<path d="M-0.4 2.4 V-1.2 M-0.4 0.6 Q-0.4 -0.3 0.7 -0.3" stroke="#fff" stroke-width="0.32" fill="none"/>'
                '<path d="M-1.15 -1.1 L0.35 -1.1 L-0.4 -2.6 Z M0.7 -1.05 L0.7 0.45 L2.0 -0.3 Z" fill="#fff"/>')
    else:  # all ways
        body = ('<path d="M0 2.4 V-1.2 M0 0.6 Q0 -0.3 1.1 -0.3 M0 0.6 Q0 -0.3 -1.1 -0.3" stroke="#fff" stroke-width="0.3" fill="none"/>'
                '<path d="M-0.75 -1.1 L0.75 -1.1 L0 -2.6 Z M1.1 -1.05 L1.1 0.45 L2.3 -0.3 Z M-1.1 -1.05 L-1.1 0.45 L-2.3 -0.3 Z" fill="#fff"/>')
    return f'<g transform="translate({x:.2f},{y:.2f}) rotate({rot})">{body}</g>'


def shark_teeth(x0, y0, x1, y1, point_rot):
    """Row of give-way triangles between two points; triangles point toward approaching riders."""
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.6))
    out = []
    for i in range(n):
        t = (i + 0.5) / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        out.append(f'<path transform="translate({x:.2f},{y:.2f}) rotate({point_rot})" d="M-0.22 -0.3 L0.22 -0.3 L0 0.35 Z" fill="#fff"/>')
    return "".join(out)


def callout(x, y, n):
    return (f'<g class="co"><circle cx="{x:.2f}" cy="{y:.2f}" r="1.25" fill="#fff" stroke="{C["ink"]}" stroke-width="0.22"/>'
            + text(x, y + 0.5, str(n), size=1.45) + "</g>")


def tree(x, y, r=1.4):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{C["tree"]}" opacity="0.85"/>'


def jeepney(x, y, rot, label=True):
    g = (f'<g transform="translate({x:.2f},{y:.2f}) rotate({rot})">'
         f'<rect x="-1.05" y="-3.6" width="2.1" height="7.2" rx="0.35" fill="{C["jeep"]}" stroke="#7c2618" stroke-width="0.12"/>'
         '<rect x="-0.85" y="-3.3" width="1.7" height="1.1" rx="0.2" fill="#f4e3c4"/></g>')
    return g


def pole(x, y):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.42" fill="{C["pole"]}" stroke="#fff" stroke-width="0.12"/>'


def zebra_ns(x0, x1, y0, y1):
    """Zebra across a N-S road: bars run N-S, repeat along x."""
    out = []
    x = min(x0, x1) + 0.25
    while x + 0.5 <= max(x0, x1):
        out.append(rect(x, y0, x + 0.5, y1, C["white"]))
        x += 1.0
    return "".join(out)


def zebra_ew(y0, y1, x0, x1):
    out = []
    y = min(y0, y1) + 0.25
    while y + 0.5 <= max(y0, y1):
        out.append(rect(x0, y, x1, y + 0.5, C["white"]))
        y += 1.0
    return "".join(out)


def feet_h(y, x0, x1):
    return line(x0, y, x1, y, C["white"], 0.45, 'stroke-dasharray="0.45 0.45"')


def feet_v(x, y0, y1):
    return line(x, y0, x, y1, C["white"], 0.45, 'stroke-dasharray="0.45 0.45"')


def rounded_island(x0, x1, y0, y1, cx, cy, r, n=10):
    """Rectangle polygon with the corner at (cx, cy) replaced by a quarter arc of radius r."""
    xs = sorted([x0, x1]); ys = sorted([y0, y1])
    corners = [(xs[0], ys[0]), (xs[1], ys[0]), (xs[1], ys[1]), (xs[0], ys[1])]
    pts = []
    for i, (px, py) in enumerate(corners):
        if abs(px - cx) > 1e-6 or abs(py - cy) > 1e-6:
            pts.append((px, py))
            continue
        sx = 1 if px == xs[0] else -1
        sy = 1 if py == ys[0] else -1
        ox, oy = px + sx * r, py + sy * r
        on_vert = (px, py + sy * r)      # point on the vertical edge
        on_horz = (px + sx * r, py)      # point on the horizontal edge
        prev = corners[i - 1]
        a, b = (on_vert, on_horz) if abs(prev[0] - px) < 1e-6 else (on_horz, on_vert)
        a0 = math.atan2(a[1] - oy, a[0] - ox)
        a1 = math.atan2(b[1] - oy, b[0] - ox)
        d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n + 1):
            t = a0 + d * k / n
            pts.append((ox + r * math.cos(t), oy + r * math.sin(t)))
    return pts


# ---------------------------------------------------------------- the plan
def build_plan(view="-48 -48 96 96", detail=False, idp="p"):
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" role="img" class="plan-svg' + (' detail' if detail else '') + '">')
    o.append('<defs>'
             f'<pattern id="{idp}hatch" width="0.6" height="0.6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             f'<rect width="0.6" height="0.6" fill="{C["island"]}"/><line x1="0" y1="0" x2="0" y2="0.6" stroke="#8d887d" stroke-width="0.18"/></pattern>'
             '</defs>')
    o.append(rect(-60, -60, 60, 60, C["ground"]))
    # property blocks
    for (x0, y0, x1, y1, lab) in [
        (-60, -60, W_PROP, -XS_PROP, "SERVICE STATION / COMMERCIAL"),
        (-60, XS_PROP, W_PROP, 60, "CORNER PLAZA / COMMERCIAL"),
        (SVC_E + 4, -60, 60, -XS_PROP, "COMMERCIAL"),
        (SVC_E + 4, XS_PROP, 60, 60, "COMMERCIAL"),
    ]:
        o.append(rect(x0, y0, x1, y1, C["block"], f'stroke="{C["blockline"]}" stroke-width="0.2"'))
        cx = (max(x0, -47) + min(x1, 47)) / 2
        cy = (max(y0, -47) + min(y1, 47)) / 2
        if not detail:
            o.append(text(cx, cy, lab, size=1.3, fill="#8a877e"))
    # asphalt
    o.append(rect(W_KERB, -60, NB_EDGE, 60, C["asphalt"]))
    o.append(rect(-60, -XS_KERB, 60, XS_KERB, C["asphalt"]))
    o.append(rect(PARK_E, -60, SVC_E, 60, C["asphalt"]))
    # east median park (north + south), with footpath and trees
    for sgn in (-1, 1):
        y_in, y_out = sgn * (RY + RW_H / 2), sgn * 60
        o.append(rect(NB_EDGE, sgn * XS_KERB, PARK_E, y_out, C["park"]))
        o.append(rect(PED_XE0, sgn * XS_KERB, PED_XE1, y_out, C["parkpath"]))
        for yy in range(16, 60, 7):
            o.append(tree(NB_EDGE + 2.4, sgn * yy, 1.5))
        # paved landing for the main-road pedestrian crossing
        o.append(rect(NB_EDGE, sgn * PED_Y0, RX_E, sgn * PED_Y1, C["concrete"]))
    # main median: planted beyond the crossings, refuge through them
    for sgn in (-1, 1):
        o.append(rect(-MED, sgn * 17.5, MED, sgn * 60, C["park"]))
        o.append(rect(-MED, sgn * 7.7, MED, sgn * 17.5, C["concrete"], f'rx="0.9" stroke="{C["islandline"]}" stroke-width="0.12"'))
        for yy in range(22, 60, 8):
            o.append(tree(0, sgn * yy, 1.0))

    # --- corner islands and separator wedges (raised concrete)
    sb = sb_path()
    a, b = offset(sb, RW_V / 2), offset(sb, -RW_V / 2)
    sb_in = a if sum(p[0] for p in a) > sum(p[0] for p in b) else b   # east edge of the SB lane
    # clip the upstream separator portion into the wedge polygons
    north_wedge = [(SB_EDGE, -60), (SB_SEP, -60)] + [p for p in sb_in if -60 < p[1] <= -(RY + RW_H / 2)] + [(SB_EDGE, -(RY + RW_H / 2))]
    south_wedge = [(SB_EDGE, RY + RW_H / 2)] + [p for p in sb_in if RY + RW_H / 2 <= p[1] < 60] + [(SB_SEP, 60), (SB_EDGE, 60)]
    o.append(poly(north_wedge, C["island"], C["islandline"]))
    o.append(poly(south_wedge, C["island"], C["islandline"]))

    def side_wedge(path, w, y_road, keep):
        """Wedge between a bent cross-street bike lane and the traffic lane edge."""
        a = offset(path, w / 2)
        b = offset(path, -w / 2)
        # the edge closer to the road (smaller |y|)
        edge = a if sum(abs(p[1]) for p in a) < sum(abs(p[1]) for p in b) else b
        edge = [p for p in edge if keep(p[0])]
        return [(edge[0][0], y_road)] + edge + [(edge[-1][0], y_road)]

    o.append(poly(side_wedge(wb_west_path(), 1.8, -XS_LANE, lambda x: x <= RX_W - RW_V / 2 + 1e-6), C["island"], C["islandline"]))
    o.append(poly(side_wedge(eb_west_path(), 1.8, XS_LANE, lambda x: x <= RX_W - RW_V / 2 + 1e-6), C["island"], C["islandline"]))
    o.append(poly(side_wedge(wb_east_path(), 1.8, -XS_LANE, lambda x: x >= RX_E + RW_V / 2 - 1e-6), C["island"], C["islandline"]))
    o.append(poly(side_wedge(eb_east_path(), 1.8, XS_LANE, lambda x: x >= RX_E + RW_V / 2 - 1e-6), C["island"], C["islandline"]))
    # the service road stays open across the east wedges
    for sgn in (-1, 1):
        o.append(rect(PARK_E, sgn * XS_LANE, SVC_E, sgn * (RY - RW_H / 2), C["asphalt"]))
        o.append(rect(PARK_E, sgn * (RY + RW_H / 2), SVC_E, sgn * 14, C["asphalt"]))

    # four corner protection islands (5 m x 5 m, rounded 3.5 m toward traffic)
    ri = 4.2
    islands = [
        (SB_EDGE - SET, SB_EDGE, -XS_LANE - SET, -XS_LANE, SB_EDGE, -XS_LANE),
        (SB_EDGE - SET, SB_EDGE, XS_LANE, XS_LANE + SET, SB_EDGE, XS_LANE),
        (NB_EDGE, NB_EDGE + SET, -XS_LANE - SET, -XS_LANE, NB_EDGE, -XS_LANE),
        (NB_EDGE, NB_EDGE + SET, XS_LANE, XS_LANE + SET, NB_EDGE, XS_LANE),
    ]
    for (x0, x1, y0, y1, cx, cy) in islands:
        # hatched crescent = 75 mm mountable apron for jeepneys / trucks; solid core = 150 mm kerb
        o.append(poly(rounded_island(x0, x1, y0, y1, cx, cy, 1.8), f"url(#{idp}hatch)", C["islandline"], 0.12))
        o.append(poly(rounded_island(x0, x1, y0, y1, cx, cy, ri), C["island"], C["islandline"], 0.2))

    # jeepney boarding island (south-west, far side for southbound)
    o.append(rect(SB_EDGE, 22, SB_EDGE - 3.0, 37, C["concrete"], f'stroke="{C["islandline"]}" stroke-width="0.15"'))
    o.append(rect(SB_EDGE - 2.6, 26, SB_EDGE - 1.2, 33, "#7d8a86"))  # shelter

    # --- lane markings
    for x in (-4.5, -7.75):
        o.append(line(x, -60, x, -17.2, C["white"], 0.15, 'stroke-dasharray="3 5"'))
        o.append(line(x, 7.7, x, 60, C["white"], 0.15, 'stroke-dasharray="3 5"'))
    for x in (4.75, 8.25, 11.75):
        o.append(line(x, -60, x, -7.7, C["white"], 0.15, 'stroke-dasharray="3 5"'))
        o.append(line(x, 17.2, x, 60, C["white"], 0.15, 'stroke-dasharray="3 5"'))
    # solid edge lines along separators
    o.append(line(SB_EDGE + 0.1, -60, SB_EDGE + 0.1, -17.2, C["white"], 0.15))
    o.append(line(SB_EDGE + 0.1, 7.7, SB_EDGE + 0.1, 60, C["white"], 0.15))
    # cross street centre line (double yellow)
    for dy in (-0.12, 0.12):
        o.append(line(-60, dy, PED_XW1 - 1.0, dy, C["yellow"], 0.12))
        o.append(line(SVC_E + 0.5, dy, 60, dy, C["yellow"], 0.12))
    # stop lines (vehicles), 1 m behind the pedestrian crossing
    o.append(line(-MED, -PED_Y1 - 1.0, SB_EDGE, -PED_Y1 - 1.0, C["white"], 0.4))
    o.append(line(MED, PED_Y1 + 1.0, NB_EDGE, PED_Y1 + 1.0, C["white"], 0.4))
    o.append(line(PED_XW1 - 1.0, 0.2, PED_XW1 - 1.0, XS_LANE, C["white"], 0.4))
    o.append(line(PARK_E + 0.6, -0.2, PARK_E + 0.6, -XS_LANE, C["white"], 0.4))
    # turn arrows
    for (x, k) in ((-2.875, "L"), (-6.125, "T"), (-9.375, "T")):
        o.append(arrow(x, -24, 180, k))
    for (x, k) in ((3.0, "L"), (6.5, "T"), (10.0, "T"), (13.4, "R")):
        o.append(arrow(x, 24, 0, k))
    o.append(arrow(-32, 1.85, 90, "A"))
    o.append(arrow(44, -1.85, -90, "A"))

    # --- separators upstream on the cross street (0.5 m rubber kerb + posts)
    for sgn in (-1, 1):
        o.append(rect(-60, sgn * XS_LANE, -32, sgn * XS_SEP, C["concrete"]))
        o.append(rect(42, sgn * XS_LANE, 60, sgn * XS_SEP, C["concrete"]))
        for x in range(-58, -32, 3):
            o.append(f'<circle cx="{x}" cy="{sgn * (XS_LANE + XS_SEP) / 2:.2f}" r="0.14" fill="#f5f5f5"/>')
        for x in range(43, 60, 3):
            o.append(f'<circle cx="{x}" cy="{sgn * (XS_LANE + XS_SEP) / 2:.2f}" r="0.14" fill="#f5f5f5"/>')

    # --- pedestrian crossings (outside the bike ring)
    for sgn in (-1, 1):
        y0, y1 = sgn * PED_Y0, sgn * PED_Y1
        o.append(zebra_ns(RX_W - RW_V / 2, NB_EDGE, y0, y1))
        o.append(zebra_ns(RX_E - RW_V / 2, RX_E + RW_V / 2, y0, y1))
    o.append(zebra_ew(-(RY + RW_H / 2 + 0.9), RY + RW_H / 2 + 0.9, PED_XW1, PED_XW0))
    o.append(zebra_ew(-(RY + RW_H / 2 + 0.9), RY + RW_H / 2 + 0.9, PED_XE0, PED_XE1))
    # zebra across the NB cycle track at the far-side jeepney stop
    o.append(zebra_ns(RX_E - RW_V / 2, RX_E + RW_V / 2, -31.5, -28.5))
    o.append(rect(NB_EDGE, -31.5, RX_E - RW_V / 2, -28.5, C["concrete"]))

    # --- bike lanes (green)
    g = C["green"]
    o.append(poly(band(sb_path(), RW_V), g))
    for pth in (wb_west_path(), eb_west_path(), wb_east_path(), eb_east_path()):
        o.append(poly(band(pth, 1.8), g))
    o.append(poly(band(nb_path(), RW_V), g))
    # ring (north / south crossings)
    for sgn in (-1, 1):
        o.append(rect(RX_W - RW_V / 2, sgn * (RY - RW_H / 2), RX_E + RW_V / 2, sgn * (RY + RW_H / 2), g))
    # re-draw ped zebra over the bike lanes where they cross (pedestrian priority)
    for sgn in (-1, 1):
        y0, y1 = sgn * PED_Y0, sgn * PED_Y1
        o.append(zebra_ns(RX_W - RW_V / 2, RX_W + RW_V / 2, y0, y1))
    o.append(zebra_ew(-(RY + RW_H / 2 + 0.9), -(RY - RW_H / 2 - 0.9), PED_XW1, PED_XW0))
    o.append(zebra_ew(RY - RW_H / 2 - 0.9, RY + RW_H / 2 + 0.9, PED_XW1, PED_XW0))
    o.append(zebra_ew(-(RY + RW_H / 2 + 0.9), -(RY - RW_H / 2 - 0.9), PED_XE0, PED_XE1))
    o.append(zebra_ew(RY - RW_H / 2 - 0.9, RY + RW_H / 2 + 0.9, PED_XE0, PED_XE1))
    o.append(zebra_ns(RX_E - RW_V / 2, RX_E + RW_V / 2, -31.5, -28.5))

    # elephant's-feet edges where the ring crosses traffic lanes
    for sgn in (-1, 1):
        for yy in (sgn * (RY - RW_H / 2), sgn * (RY + RW_H / 2)):
            o.append(feet_h(yy, SB_EDGE, -MED))
            o.append(feet_h(yy, MED, NB_EDGE))
        o.append(feet_h(sgn * (RY - RW_H / 2) , PARK_E, SVC_E))
        o.append(feet_h(sgn * (RY + RW_H / 2), PARK_E, SVC_E))
    for xx in (RX_W - RW_V / 2, RX_W + RW_V / 2, RX_E - RW_V / 2, RX_E + RW_V / 2):
        o.append(feet_v(xx, -XS_LANE, XS_LANE))

    # bike stop lines at the ring corners
    o.append(line(RX_W - RW_V / 2, -XS_LANE - 0.5, RX_W + RW_V / 2, -XS_LANE - 0.5, C["white"], 0.3))
    o.append(line(RX_E - RW_V / 2, XS_LANE + 0.5, RX_E + RW_V / 2, XS_LANE + 0.5, C["white"], 0.3))
    o.append(line(SB_EDGE - 0.5, RY - RW_H / 2, SB_EDGE - 0.5, RY + RW_H / 2, C["white"], 0.3))
    o.append(line(NB_EDGE + 0.5, -RY - RW_H / 2, NB_EDGE + 0.5, -RY + RW_H / 2, C["white"], 0.3))

    # give-way (shark teeth): riders yield to pedestrians before every zebra
    o.append(shark_teeth(RX_W - RW_V / 2, -PED_Y1 - 0.8, RX_W + RW_V / 2, -PED_Y1 - 0.8, 180))
    o.append(shark_teeth(RX_W - RW_V / 2, PED_Y0 - 0.8, RX_W + RW_V / 2, PED_Y0 - 0.8, 180))
    o.append(shark_teeth(RX_E - RW_V / 2, PED_Y1 + 0.8, RX_E + RW_V / 2, PED_Y1 + 0.8, 0))
    o.append(shark_teeth(RX_E - RW_V / 2, -PED_Y0 + 0.8, RX_E + RW_V / 2, -PED_Y0 + 0.8, 0))
    o.append(shark_teeth(PED_XW1 - 0.8, RY - 0.9, PED_XW1 - 0.8, RY + 0.9, 90))
    o.append(shark_teeth(PED_XE1 + 0.8, -RY - 0.9, PED_XE1 + 0.8, -RY + 0.9, -90))

    # bike pictograms + chevrons (direction of travel)
    for y in (-40, -30):
        o.append(bike_glyph(-13.75, y, 180)); o.append(chevron(-13.75, y + 3, 180))
    for y in (22, 45):
        o.append(bike_glyph(RX_W, y, 180)); o.append(chevron(RX_W, y + 3, 180))
    for y in (40, 30, -22, -40):
        o.append(bike_glyph(RX_E, y, 0)); o.append(chevron(RX_E, y - 3, 0))
    o.append(bike_glyph(-44, 5.1, 90, 0.85)); o.append(chevron(-40, 5.1, 90))
    o.append(bike_glyph(-44, -5.1, -90, 0.85)); o.append(chevron(-48 + 1, -5.1, -90))
    o.append(bike_glyph(47, -5.1, -90, 0.85)); o.append(chevron(44, -5.1, -90))
    o.append(bike_glyph(47, 5.1, 90, 0.85))
    for x in (-6, 6):
        o.append(chevron(x, RY, 90, 0.9)); o.append(chevron(x, -RY, -90, 0.9))
    o.append(chevron(RX_W, 0, 180, 0.9)); o.append(chevron(RX_E, 0, 0, 0.9))

    # trees on sidewalks
    for yy in (-44, -36, -28, 28, 44):
        o.append(tree(-20.3, yy, 1.3))
    for xx in (-44, -36):
        o.append(tree(xx, -11.5, 1.2)); o.append(tree(xx, 11.5, 1.2))

    # signal poles (vehicle + bike heads) on islands / refuges
    for (x, y) in ((-12.2, -7.6), (-12.2, 7.6), (16.2, -7.6), (16.2, 7.6), (0, -16.8), (0, 16.8),
                   (-25.0, -8.0), (-25.0, 8.0), (27.8, -12.5), (27.8, 12.5)):
        o.append(pole(x, y))

    # jeepneys at the far-side stops
    o.append(jeepney(-9.4, 30, 180))
    o.append(jeepney(13.4, -30, 0))

    if not detail:
        # callouts
        for (x, y, n) in ((-13.5, -6.2, 1), (6.0, -12.7, 2), (-13.75, -35, 3), (RX_E, -36, 4), (-40, 5.1, 5),
                          (-6.5, PED_Y0 + 2.0, 6), (0, 12.5, 7), (-13.3, 24, 8), (13.4, -24.5, 9),
                          (RX_E + 2.6, RY + 2.6, 10), (17.6, 6.2, 11), (30.5, RY, 12), (-19.2, -18.5, 13)):
            o.append(callout(x, y, n))
        # street names
        o.append(text(-8, -45, "MAIN ROAD · SOUTHBOUND", 1.3, "#e9ecef", extra='letter-spacing="0.15"'))
        o.append(text(8.5, 45.8, "MAIN ROAD · NORTHBOUND", 1.3, "#e9ecef", extra='letter-spacing="0.15"'))
        o.append(text(-40, -1.2, "CROSS STREET (W)", 1.2, "#e9ecef"))
        o.append(text(48, 2.9, "CROSS STREET (E)", 1.2, "#e9ecef", anchor="end"))
        o.append(text(30.5, -36, "SERVICE RD", 1.2, "#e9ecef", extra=f'transform="rotate(-90 30.5 -36)"'))
        o.append(text(25.2, 40, "PARK PATH", 1.0, "#6b6353", extra=f'transform="rotate(-90 25.2 40)"'))
        # north arrow + scale bar
        o.append('<g transform="translate(-43,-41)"><circle r="3" fill="#fff" stroke="#1d2522" stroke-width="0.2"/>'
                 '<path d="M0 -2.4 L1.1 1.6 L0 0.8 L-1.1 1.6 Z" fill="#1d2522"/>'
                 + text(0, -3.5, "N", 1.6) + '</g>')
        o.append('<g transform="translate(-47,44)">'
                 '<rect x="0" y="0" width="20" height="2.8" fill="#fff" opacity="0.9"/>'
                 '<rect x="1" y="0.6" width="5" height="0.6" fill="#1d2522"/><rect x="6" y="0.6" width="5" height="0.6" fill="#fff" stroke="#1d2522" stroke-width="0.1"/>'
                 '<rect x="11" y="0.6" width="5" height="0.6" fill="#1d2522"/>'
                 + text(1, 2.5, "0", 0.9) + text(6, 2.5, "5", 0.9) + text(11, 2.5, "10", 0.9) + text(16, 2.5, "15 m", 0.9)
                 + '</g>')
    else:
        o.append(detail_dims())
    o.append('</svg>')
    return "\n".join(o)


def dim_h(x0, x1, y, label, above=True):
    t = -0.5 if above else 1.3
    return (f'<g class="dim">{line(x0, y, x1, y, "#111", 0.08)}'
            f'{line(x0, y - 0.5, x0, y + 0.5, "#111", 0.08)}{line(x1, y - 0.5, x1, y + 0.5, "#111", 0.08)}'
            f'<rect x="{(x0 + x1) / 2 - len(label) * 0.27 - 0.2:.2f}" y="{y + t - 0.95:.2f}" width="{len(label) * 0.54 + 0.4:.2f}" height="1.2" fill="#fff" opacity="0.9"/>'
            f'{text((x0 + x1) / 2, y + t, label, 0.95, "#111")}</g>')


def dim_v(x, y0, y1, label):
    return (f'<g class="dim">{line(x, y0, x, y1, "#111", 0.08)}'
            f'{line(x - 0.5, y0, x + 0.5, y0, "#111", 0.08)}{line(x - 0.5, y1, x + 0.5, y1, "#111", 0.08)}'
            f'<rect x="{x - len(label) * 0.27 - 0.2:.2f}" y="{(y0 + y1) / 2 - 0.62:.2f}" width="{len(label) * 0.54 + 0.4:.2f}" height="1.2" fill="#fff" opacity="0.9"/>'
            f'{text(x, (y0 + y1) / 2 + 0.36, label, 0.95, "#111")}</g>')


def detail_dims():
    o = []
    # widths across the south arm (looking along the SB lane)
    o.append(dim_h(W_PROP, RX_W - RW_V / 2, 20.6, "3.5"))
    o.append(dim_h(RX_W - RW_V / 2, RX_W + RW_V / 2, 20.6, "2.5"))
    o.append(dim_h(RX_W + RW_V / 2, SB_EDGE, 20.6, "5.0"))
    o.append(dim_h(SB_EDGE, -7.75, 20.6, "3.25"))
    o.append(dim_h(-7.75, -4.5, 20.6, "3.25"))
    o.append(dim_h(-4.5, -MED, 20.6, "3.25"))
    # upstream (north arm) SB lane
    o.append(dim_h(W_KERB, SB_SEP, -2.0, "2.5"))
    o.append(dim_h(SB_SEP, SB_EDGE, -3.4, "1.5"))
    # set-back on the cross street side
    o.append(dim_v(-26.5, XS_LANE, RY - RW_H / 2, "5.0"))
    o.append(dim_v(-8.5, 0, XS_LANE, "3.7"))
    o.append(dim_v(-14.0, RY - RW_H / 2, RY + RW_H / 2, "2.0"))
    o.append(dim_v(-3.0, PED_Y0, PED_Y1, "4.0"))
    o.append(dim_v(-29.5, RY + RW_H / 2, 12.5, "1.0"))
    # boarding island
    o.append(dim_h(SB_EDGE - 3.0, SB_EDGE, 38.6, "3.0", above=False))
    o.append(dim_v(-6.0, 22, 37, "15.0"))
    # labels
    lab = [
        (-13.6, 6.0, "CORNER ISLAND"), (-13.6, 7.1, "R4.2 + APRON"),
        (-22.5, 7.9, "QUEUE"),
        (-13.6, 29.5, "JEEPNEY"), (-13.6, 30.7, "PLATFORM"),
        (-30.5, 8.5, "EB BIKE"),
    ]
    for (x, y, s) in lab:
        o.append(text(x, y, s, 0.85, "#1d2522"))
    o.append('<g transform="translate(-2.5,34)"><circle r="1.8" fill="#fff" stroke="#1d2522" stroke-width="0.15"/>'
             '<path d="M0 -1.4 L0.7 1.0 L0 0.5 L-0.7 1.0 Z" fill="#1d2522"/>' + text(0, -2.2, "N", 1.0) + '</g>')
    return "".join(o)


# ---------------------------------------------------------------- sections
SEC_COL = {
    "walk": "#d6d2c8", "bike": C["green"], "sep": "#b3aea3", "lane": C["asphalt"],
    "med": C["park"], "park": C["park"], "path": C["parkpath"], "bus": "#6f767c",
}


def section(parts, title):
    total = sum(w for _, w, _ in parts)
    W = total
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -5 {W + 2:.2f} 11.5" class="sec-svg" role="img" aria-label="{title}">']
    x = 0.0
    for (lab, w, kind) in parts:
        h = {"walk": 0.9, "sep": 0.9, "med": 0.9, "park": 0.9, "path": 0.9}.get(kind, 0.3)
        top = 2.0 - h
        o.append(rect(x, top, x + w, 2.0 + 0.6, SEC_COL[kind], 'stroke="#fff" stroke-width="0.06"'))
        if kind in ("park", "med") and w >= 2:
            o.append(f'<circle cx="{x + w / 2:.2f}" cy="{top - 1.3:.2f}" r="1.2" fill="{C["tree"]}"/>'
                     f'<rect x="{x + w / 2 - 0.08:.2f}" y="{top - 0.4:.2f}" width="0.16" height="0.4" fill="#5b4a36"/>')
        o.append(line(x, 3.2, x, 3.8, "currentColor", 0.05))
        o.append(f'<text x="{x + w / 2:.2f}" y="3.95" font-size="0.62" text-anchor="middle" fill="currentColor" '
                 f'font-family="IBM Plex Mono, monospace">{w:g}</text>')
        o.append(f'<text x="{x + w / 2:.2f}" y="4.95" font-size="0.56" text-anchor="middle" fill="currentColor" '
                 f'font-family="Barlow Condensed, sans-serif" font-weight="600">{lab}</text>')
        x += w
    o.append(line(total, 3.2, total, 3.8, "currentColor", 0.05))
    o.append(line(0, 3.5, total, 3.5, "currentColor", 0.04))
    o.append(f'<text x="{total / 2:.2f}" y="-3.8" font-size="0.7" text-anchor="middle" fill="currentColor" '
             f'font-family="IBM Plex Mono, monospace">{total:.2f} m between property lines</text>')
    o.append('</svg>')
    return "".join(o)


SEC_A = [
    ("SIDEWALK", 7.0, "walk"), ("SB BIKE", 2.5, "bike"), ("SEP", 1.5, "sep"),
    ("SB", 3.25, "lane"), ("SB", 3.25, "lane"), ("SB", 3.25, "lane"), ("MEDIAN", 2.5, "med"),
    ("NB", 3.5, "lane"), ("NB", 3.5, "lane"), ("NB", 3.5, "lane"), ("NB CURB/PUJ", 3.25, "lane"),
    ("PLANTING", 5.0, "park"), ("NB BIKE", 2.5, "bike"), ("", 1.0, "path"), ("PARK PATH", 3.0, "path"),
    ("", 0.5, "park"), ("SERVICE RD", 7.0, "lane"), ("WALK", 4.0, "walk"),
]
SEC_B = [
    ("SIDEWALK (VARIES)", 4.0, "walk"), ("WB BIKE", 1.8, "bike"), ("SEP", 0.5, "sep"), ("WB", 3.7, "lane"),
    ("EB", 3.7, "lane"), ("SEP", 0.5, "sep"), ("EB BIKE", 1.8, "bike"), ("SIDEWALK (VARIES)", 4.0, "walk"),
]
SEC_C = [
    ("SIDEWALK", 3.5, "walk"), ("SB BIKE", 2.5, "bike"), ("PLATFORM", 3.0, "sep"), ("JEEPNEY", 3.25, "bus"),
    ("SB", 3.25, "lane"), ("SB", 3.25, "lane"), ("MEDIAN", 2.5, "med"),
]


# ---------------------------------------------------------------- photo overlay
def overlay_svg():
    """Concept overlay on the existing drone photo (image pixel coords 2000 x 1125)."""
    G = "#2fb35f"
    o = ['<svg class="ov" viewBox="0 0 2000 1125" preserveAspectRatio="none" aria-hidden="true">']
    o.append('<defs><pattern id="zeb" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(-8)">'
             '<rect width="9" height="18" fill="#fff"/></pattern>'
             '<pattern id="zebh" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(-24)">'
             '<rect width="16" height="8" fill="#fff"/></pattern></defs>')
    op = 'fill-opacity="0.86"'
    # SB protected lane on the north arm (in carriageway), bends out at NW corner
    o.append(f'<path d="M1012,118 L1034,118 L962,300 L905,452 L862,540 L815,566 L780,566 L822,520 L866,440 L925,292 Z" fill="{G}" {op}/>')
    # separator north arm
    o.append('<path d="M1034,118 L1048,118 L978,300 L922,452 L880,540 L862,540 L905,452 L962,300 Z" fill="#cfcac0" fill-opacity="0.95"/>')
    # ring - north segment (WB crossing), inside existing north crosswalk
    o.append(f'<path d="M790,562 L1488,568 L1500,598 L785,592 Z" fill="{G}" {op}/>')
    # ring - west segment (SB crossing of west arm)
    o.append(f'<path d="M772,562 L812,562 L733,770 L692,770 Z" fill="{G}" {op}/>')
    # ring - south segment (EB crossing), inside existing south crosswalk
    o.append(f'<path d="M700,736 L1610,730 L1625,764 L692,770 Z" fill="{G}" {op}/>')
    # ring - east segment (NB crossing of east arm)
    o.append(f'<path d="M1500,570 L1552,570 L1664,792 L1610,792 Z" fill="{G}" {op}/>')
    # NB cycle track in the SE plaza
    o.append(f'<path d="M1610,792 L1664,792 L1790,1000 L1870,1125 L1795,1125 L1726,1000 Z" fill="{G}" {op}/>')
    # NB cycle track in the NE linear park
    o.append(f'<path d="M1500,570 L1552,570 L1462,400 L1400,250 L1368,160 L1352,160 L1380,250 L1440,400 Z" fill="{G}" {op}/>')
    # SB lane on the south arm (bent out behind corner island, then back along kerb)
    o.append(f'<path d="M692,770 L733,770 L744,850 L672,1125 L585,1125 L680,860 Z" fill="{G}" {op}/>')
    o.append('<path d="M744,850 L772,852 L712,1125 L672,1125 Z" fill="#cfcac0" fill-opacity="0.95"/>')
    # west arm lanes (WB north side, EB south side)
    o.append(f'<path d="M785,592 L748,630 L0,640 L0,602 L730,606 L772,562 Z" fill="{G}" {op}/>')
    o.append(f'<path d="M692,770 L700,736 L350,806 L0,896 L0,945 L360,850 Z" fill="{G}" {op}/>')
    # corner islands
    isl = 'fill="#d9d4c9" stroke="#fff" stroke-width="3" fill-opacity="0.95"'
    o.append(f'<path d="M815,596 L890,596 Q872,648 800,652 Z" {isl}/>')
    o.append(f'<path d="M1497,600 L1418,600 Q1440,652 1522,652 Z" {isl}/>')
    o.append(f'<path d="M1600,728 L1570,672 Q1530,676 1508,728 Z" {isl}/>')
    o.append(f'<path d="M742,732 L826,732 Q818,686 764,684 Z" {isl}/>')
    # median refuges extended through the crossings
    o.append(f'<path d="M1086,512 L1114,512 L1120,598 L1090,598 Z" {isl}/>')
    o.append(f'<path d="M1088,728 L1146,728 L1150,868 L1086,868 Z" {isl}/>')
    # new pedestrian crossing on the west arm (outside the ring) and east arm
    o.append('<path d="M752,612 L706,612 L636,786 L682,786 Z" fill="url(#zebh)" fill-opacity="0.9"/>')
    o.append('<path d="M1560,588 L1612,588 L1726,794 L1672,794 Z" fill="url(#zebh)" fill-opacity="0.9"/>')
    # bike pictograms (white)
    def bk(x, y, s, r=0):
        return (f'<g transform="translate({x},{y}) rotate({r}) scale({s})" fill="none" stroke="#fff" stroke-width="2.2">'
                '<circle cx="-9" cy="4" r="6"/><circle cx="9" cy="4" r="6"/><path d="M-9 4 L-3 -5 L6 -5 L9 4 M-3 -5 L0 4 L6 -5"/></g>')
    for (x, y, s) in ((980, 210, 0.9), (908, 400, 1.2), (1200, 580, 1.0), (730, 690, 1.1), (1180, 752, 1.3),
                      (1640, 700, 1.2), (1760, 960, 1.6), (1440, 360, 1.0), (640, 1000, 1.7), (300, 620, 1.2), (300, 836, 1.3)):
        o.append(bk(x, y, s))
    o.append('</svg>')
    return "".join(o)


OV_LABELS = [
    # (left %, top %, number, anchor side)
    (39.0, 57.0, 1), (60.0, 53.0, 2), (47.0, 20.0, 3), (73.5, 29.0, 4), (14.0, 60.0, 5),
    (70.0, 77.0, 6), (55.5, 69.5, 7), (78.0, 62.0, 11), (84.5, 89.0, 4),
]


# ---------------------------------------------------------------- page
def page():
    plan = build_plan()
    detail = build_plan(view="-34 -5 36 47", detail=True, idp="d")
    secA, secB, secC = section(SEC_A, "Section A-A"), section(SEC_B, "Section B-B"), section(SEC_C, "Section C-C")
    ov = overlay_svg()
    ov_marks = "".join(
        f'<span class="ov-n" style="left:{l}%;top:{t}%">{n}</span>' for (l, t, n) in OV_LABELS)
    tpl = (HERE / "template.html").read_text()
    return (tpl.replace("{{PLAN}}", plan).replace("{{DETAIL}}", detail)
            .replace("{{SECA}}", secA).replace("{{SECB}}", secB).replace("{{SECC}}", secC)
            .replace("{{OVERLAY}}", ov).replace("{{OVMARKS}}", ov_marks))


if __name__ == "__main__":
    (HERE / "index.html").write_text(page())
    print("wrote", HERE / "index.html")
