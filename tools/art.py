"""Draws the README's art from code, in the colours of the portfolio's landing page:

  assets/banner.svg  the name, the role, a low poly icosahedron, a pixel Pikachu and the cast of shapes
                     whose eyes blink and look around
  assets/stack.svg   the stack as tags

GitHub shows an SVG as an image, which cannot load fonts: the text is turned into paths with fontTools.
Fonts: Unbounded and JetBrains Mono from Google Fonts (OFL). The Pikachu is the FireRed front sprite the
portfolio uses, drawn one rect per pixel run.

Run: python tools/art.py <folder with Unbounded.ttf and JetBrainsMono.ttf> <path to the sprite PNG>
"""
import itertools
import math
import struct
import sys
import zlib
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

INK, INK2, PAPER, ORANGE, PURPLE, GREEN = '#0e0c12', '#1a1621', '#f4eee3', '#ff6a1f', '#6a3bf0', '#2bd67b'
OUT = Path(__file__).resolve().parent.parent / 'assets'


class Face:
    """A font at one weight: text as SVG path data."""

    def __init__(self, path, wght):
        font = instancer.instantiateVariableFont(TTFont(path), {'wght': wght})
        self.glyphs = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.upm = font['head'].unitsPerEm
        self.hmtx = font['hmtx']

    def width(self, s, size, tracking=0.0):
        return sum(self.hmtx[self.cmap[ord(c)]][0] * size / self.upm + tracking * size for c in s)

    def path(self, s, x, y, size, tracking=0.0):
        """Path data for s with its baseline starting at (x, y)."""
        k = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f'{v:.1f}'.rstrip('0').rstrip('.'))
        for c in s:
            name = self.cmap[ord(c)]
            self.glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, x, y)))
            x += self.hmtx[name][0] * k + tracking * size
        return pen.getCommands()


def read_rgba(path):
    """Pixels of an 8-bit RGBA PNG (the sprite), as rows of (r, g, b, a)."""
    data = Path(path).read_bytes()
    pos, idat = 8, b''
    while pos < len(data):
        n, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', body[:10])
            assert depth == 8 and ctype == 6, 'expects 8-bit RGBA'
        elif kind == b'IDAT':
            idat += body
    raw, stride, rows, prev = zlib.decompress(idat), w * 4, [], bytearray(w * 4)
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - 4] if i >= 4 else 0
            b, c = prev[i], prev[i - 4] if i >= 4 else 0
            p = a + b - c
            pred = [0, a, b, (a + b) // 2, a if abs(p - a) <= abs(p - b) and abs(p - a) <= abs(p - c) else b if abs(p - b) <= abs(p - c) else c][f]
            line[i] = (line[i] + pred) & 255
        rows.append([tuple(line[i:i + 4]) for i in range(0, stride, 4)])
        prev = line
    return rows


def pixels(rows, x, y, k):
    """The sprite as rects of k units, one per horizontal run of one colour."""
    out = []
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            if row[i][3] < 128:
                i += 1
                continue
            n = 1
            while i + n < len(row) and row[i + n] == row[i]:
                n += 1
            r, g, b, _ = row[i]
            out.append(f'<rect x="{x + i * k}" y="{y + j * k}" width="{n * k}" height="{k}" fill="#{r:02x}{g:02x}{b:02x}"/>')
            i += n
    return ''.join(out)


def icosahedron(cx, cy, size, rx=0.45, ry=0.6):
    """A flat-shaded low poly icosahedron, faces in the palette with ink edges, seen from the front."""
    phi = (1 + 5 ** 0.5) / 2
    verts = [(0, s1, s2 * phi) for s1 in (-1, 1) for s2 in (-1, 1)] + [(s1, s2 * phi, 0) for s1 in (-1, 1) for s2 in (-1, 1)] + [(s1 * phi, 0, s2) for s1 in (-1, 1) for s2 in (-1, 1)]
    d2 = lambda a, b: sum((p - q) ** 2 for p, q in zip(a, b))
    faces = [f for f in itertools.combinations(range(12), 3) if all(abs(d2(verts[a], verts[b]) - 4) < 1e-6 for a, b in itertools.combinations(f, 2))]

    def turn(v):
        x, y, z = v
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        return x, y, z

    tv = [turn(v) for v in verts]
    light = (0.4, -0.6, 0.7)
    out = []
    colors = [ORANGE, PURPLE, GREEN, PAPER]
    for n, f in sorted(enumerate(faces), key=lambda e: sum(tv[i][2] for i in e[1])):
        a, b, c = (tv[i] for i in f)
        u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        nx, ny, nz = u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]
        cz = sum(p[2] for p in (a, b, c))
        if (nx * a[0] + ny * a[1] + nz * a[2]) < 0:   # outward normal
            nx, ny, nz = -nx, -ny, -nz
        if nz <= 0:
            continue
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        shade = 0.6 + 0.4 * max(0, (nx * light[0] + ny * light[1] + nz * light[2]) / ln / math.sqrt(sum(l * l for l in light)))
        base = colors[n % 4]
        rgb = [int(int(base[i:i + 2], 16) * shade) for i in (1, 3, 5)]
        pts = ' '.join(f'{cx + p[0] * size:.1f},{cy + p[1] * size:.1f}' for p in (a, b, c))
        out.append(f'<polygon points="{pts}" fill="#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>')
    return ''.join(out)


# The cast, as on the landing page (site/cast.js): 200-unit bodies with their eyes.
BODIES = {
    'circle': f'<circle cx="100" cy="100" r="88" fill="{ORANGE}"/>',
    'star': f'<path d="M100 10 L124 72 L190 76 L138 116 L156 182 L100 144 L44 182 L62 116 L10 76 L76 72 Z" fill="{GREEN}" filter="url(#grain)" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>',
    'blob': '<path d="M104 12 C150 10 190 46 188 98 C186 150 150 190 98 188 C46 186 10 152 14 100 C18 52 58 14 104 12 Z" fill="url(#gloss)"/>',
    'squiggle': f'<path d="M18 128 C34 52 76 44 90 104 S 140 176 162 98 S 192 44 184 70" fill="none" stroke="{PAPER}" stroke-width="9" stroke-linecap="round"/>',
}
EYES = {'circle': [(74, 92), (126, 92)], 'star': [(84, 104), (116, 104)], 'blob': [(78, 88), (128, 92)], 'squiggle': [(70, 52), (100, 50)]}
R = {'circle': 15, 'star': 11, 'blob': 17, 'squiggle': 11}


def char(kind, x, y, size, rot=0, delay=0.0):
    r = R[kind]
    eyes = ''.join(f'<g transform="translate({ex} {ey})"><g class="eye" style="animation-delay:{delay:.2f}s"><ellipse rx="{r}" ry="{r * 1.15:.1f}" fill="{PAPER}" stroke="{INK}" stroke-width="3"/><circle class="pupil" r="{r * 0.5:.1f}" fill="{INK}"/></g></g>' for ex, ey in EYES[kind])
    return f'<g transform="translate({x} {y}) rotate({rot} {size / 2} {size / 2}) scale({size / 200})">{BODIES[kind]}{eyes}</g>'


DEFS = f'''<defs>
  <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.3" fill="{PAPER}" fill-opacity=".1"/></pattern>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .5 0"/><feComposite in2="SourceGraphic" operator="in" result="g"/><feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="g"/></feMerge></filter>
  <radialGradient id="gloss" cx=".34" cy=".3" r=".8"><stop offset="0" stop-color="#c3b0ff"/><stop offset=".42" stop-color="{PURPLE}"/><stop offset="1" stop-color="#26105f"/></radialGradient>
</defs>
<style>
  .eye {{ transform-box: fill-box; transform-origin: center; animation: blink 5.2s infinite; }}
  .pupil {{ animation: look 7s ease-in-out infinite; }}
  @keyframes blink {{ 0%, 92%, 100% {{ transform: scaleY(1); }} 95% {{ transform: scaleY(.08); }} }}
  @keyframes look {{ 0%, 18% {{ transform: translate(0, 0); }} 26%, 44% {{ transform: translate(-6px, -3px); }} 52%, 70% {{ transform: translate(6px, 2px); }} 78%, 94% {{ transform: translate(2px, 5px); }} 100% {{ transform: translate(0, 0); }} }}
  @media (prefers-reduced-motion: reduce) {{ .eye, .pupil {{ animation: none; }} }}
</style>'''


def banner(display, mono, sprite):
    w, h = 1200, 340
    name1 = display.path('JOÃO', 60, 138, 104)
    name2 = display.path('CABRAL', 60, 250, 104)
    role = mono.path('Software Engineer · AI & Data Automation · Game Dev', 64, 300, 19)
    underline = f'<path d="M64 318 C 150 308, 250 324, 360 314 S 520 310, 600 316" fill="none" stroke="{GREEN}" stroke-width="5" stroke-linecap="round"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="João Cabral, software engineer, AI and data automation, game dev">
{DEFS}
<rect width="{w}" height="{h}" rx="28" fill="{INK}"/>
<rect width="{w}" height="{h}" rx="28" fill="url(#dots)"/>
<path d="{name1}" fill="{PAPER}"/>
<path d="{name2}" fill="{INK}" stroke="{ORANGE}" stroke-width="6" stroke-linejoin="round" paint-order="stroke"/>
<path d="{role}" fill="{GREEN}"/>
{underline}
{char('blob', 900, 70, 230, delay=0.0)}
{char('star', 792, 16, 112, rot=-12, delay=1.3)}
{icosahedron(708, 150, 32)}
{char('circle', 800, 196, 118, delay=2.1)}
{char('squiggle', 1060, 210, 110, rot=8, delay=3.4)}
<g transform="rotate(8 1100 80)">{pixels(sprite, 1036, 22, 2)}</g>
</svg>
'''


STACK = [
    ('languages', ['PYTHON', 'TYPESCRIPT', 'JAVASCRIPT', 'C#', 'GIT']),
    ('web & data', ['REACT', 'NEXT.JS', 'FASTAPI', 'SUPABASE', 'GOOGLE CLOUD', 'BIGQUERY', 'DOCKER']),
    ('games & design', ['UNITY', 'FIGMA', 'BLENDER', 'PHOTOSHOP', 'ASEPRITE']),
    ('ai & automation', ['LLMS', 'GEMINI', 'ANTHROPIC', 'DATA PIPELINES']),
]
CHIP = [(ORANGE, INK), (PURPLE, PAPER), (GREEN, INK), (PAPER, INK)]


def stack(mono):
    w, size, pad, row_h = 1200, 15, 14, 64
    out, y = [], 40
    for r, (label, items) in enumerate(STACK):
        out.append(f'<path d="{mono.path(label, 48, y + 6, 15)}" fill="{GREEN}"/>')
        x = 250
        for i, item in enumerate(items):
            tw = mono.width(item, size)
            bg, fg = CHIP[(r + i) % 4]
            rot = (-1.5, 1, -0.5, 1.5, -1)[(r + i) % 5]
            out.append(f'<g transform="rotate({rot} {x + tw / 2 + pad} {y})"><rect x="{x}" y="{y - 19}" width="{tw + 2 * pad:.1f}" height="34" rx="17" fill="{bg}" stroke="{INK}" stroke-width="2.5"/>'
                       f'<path d="{mono.path(item, x + pad, y + 4, size)}" fill="{fg}"/></g>')
            x += tw + 2 * pad + 12
        y += row_h
    h = y - row_h + 48
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Stack: {'; '.join(label + ': ' + ', '.join(items) for label, items in STACK).replace('&', 'and')}">
<rect width="{w}" height="{h}" rx="24" fill="{INK2}"/>
{''.join(out)}
</svg>
'''


if __name__ == '__main__':
    fonts, sprite = Path(sys.argv[1]), read_rgba(sys.argv[2])
    display = Face(fonts / 'Unbounded.ttf', 900)
    mono = Face(fonts / 'JetBrainsMono.ttf', 700)
    OUT.mkdir(exist_ok=True)
    (OUT / 'banner.svg').write_text(banner(display, mono, sprite), encoding='utf-8')
    (OUT / 'stack.svg').write_text(stack(mono), encoding='utf-8')
    print('banner.svg and stack.svg written')
