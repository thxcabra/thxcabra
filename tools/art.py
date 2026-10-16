"""Draws the README's art from code, in the look of the portfolio's landing page:

  assets/banner.svg  the name and the role on a purple field, and João's own pixel art goat waving over a
                     flat orange shape, with a light film grain
  assets/stack.svg   the stack as cartoon tags

GitHub shows an SVG as an image, which cannot load fonts: the text is turned into paths with fontTools.
Fonts: Dela Gothic One and VT323 from Google Fonts (OFL). The goat is João's 90x90 pixel art, drawn one
rect per run of pixels.

Run: python tools/art.py <folder with DelaGothicOne.ttf and VT323.ttf> <path to the goat PNG>
"""
import struct
import sys
import zlib
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

INK, INK2, PAPER, ORANGE, PURPLE, GREEN = '#0e0c12', '#1a1621', '#f4eee3', '#ff6a1f', '#6a3bf0', '#2bd67b'
OUT = Path(__file__).resolve().parent.parent / 'assets'


class Face:
    """A font as SVG path data."""

    def __init__(self, path):
        font = TTFont(path)
        self.glyphs = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.upm = font['head'].unitsPerEm
        self.hmtx = font['hmtx']

    def width(self, s, size):
        return sum(self.hmtx[self.cmap[ord(c)]][0] for c in s) * size / self.upm

    def path(self, s, x, y, size):
        """Path data for s with its baseline starting at (x, y)."""
        k = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f'{v:.1f}'.rstrip('0').rstrip('.'))
        for c in s:
            name = self.cmap[ord(c)]
            self.glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, x, y)))
            x += self.hmtx[name][0] * k
        return pen.getCommands()


def read_rgba(path):
    """Pixels of an 8-bit RGBA PNG, as rows of (r, g, b, a)."""
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


def crop(rows):
    ys = [y for y, row in enumerate(rows) if any(p[3] for p in row)]
    xs = [x for x in range(len(rows[0])) if any(row[x][3] for row in rows)]
    return [row[min(xs):max(xs) + 1] for row in rows[min(ys):max(ys) + 1]]


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


GRAIN = f'''<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="5"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .07 0"/></filter>'''


def banner(display, vt, goat):
    w, h, k = 1200, 340, 4
    gw, gh = len(goat[0]) * k, len(goat) * k
    gx, gy = 1030 - gw // 2, h - gh - 18
    hello = display.path('OPA, EU SOU O', 62, 96, 34)
    name = display.path('JOÃO CABRAL.', 58, 196, 80)
    role = vt.path('Software Engineer · AI & Data Automation · Game Dev', 64, 262, 30)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="João Cabral, software engineer, AI and data automation, game dev, with his pixel art goat waving">
<defs>{GRAIN}<clipPath id="card"><rect width="{w}" height="{h}" rx="24"/></clipPath></defs>
<g clip-path="url(#card)">
<rect width="{w}" height="{h}" fill="{PURPLE}"/>
<path d="M{gx - 40} {h - 30} C {gx - 70} {h - 190}, {gx + 60} {h - 300}, {gx + 170} {h - 270} S {gx + 250} {h - 90}, {gx + 200} {h - 20} Z" fill="{ORANGE}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
<path d="{hello}" fill="{PAPER}"/>
<path d="{name}" fill="{INK}" transform="translate(5 5)"/>
<path d="{name}" fill="{PAPER}" stroke="{INK}" stroke-width="7" stroke-linejoin="round" paint-order="stroke"/>
<path d="{role}" fill="{PAPER}"/>
<g shape-rendering="crispEdges">{pixels(goat, gx, gy, k)}</g>
<rect width="{w}" height="{h}" filter="url(#grain)"/>
</g>
<rect x="2.5" y="2.5" width="{w - 5}" height="{h - 5}" rx="22" fill="none" stroke="{INK}" stroke-width="5"/>
</svg>
'''


STACK = [
    ('languages', ['PYTHON', 'TYPESCRIPT', 'JAVASCRIPT', 'C#', 'GIT']),
    ('web & data', ['REACT', 'NEXT.JS', 'FASTAPI', 'SUPABASE', 'GOOGLE CLOUD', 'BIGQUERY', 'DOCKER']),
    ('games & design', ['UNITY', 'GAMEMAKER', 'BLENDER', 'BLOCKBENCH', 'ASEPRITE', 'PHOTOSHOP', 'FIGMA']),
    ('ai & automation', ['LLMS', 'GEMINI', 'ANTHROPIC', 'DATA PIPELINES']),
]
CHIP = [(ORANGE, INK), (PURPLE, PAPER), (GREEN, INK), (PAPER, INK)]


def stack(vt):
    w, size, pad, row_h = 1200, 26, 12, 62
    out, y = [], 46
    for r, (label, items) in enumerate(STACK):
        out.append(f'<path d="{vt.path(label, 44, y + 7, 26)}" fill="{GREEN}"/>')
        x = 260
        for i, item in enumerate(items):
            tw = vt.width(item, size)
            bg, fg = CHIP[(r + i) % 4]
            rot = (-1.5, 1, -0.5, 1.5, -1)[(r + i) % 5]
            out.append(f'<g transform="rotate({rot} {x + tw / 2 + pad:.1f} {y})"><rect x="{x}" y="{y - 18}" width="{tw + 2 * pad:.1f}" height="34" rx="6" fill="{bg}" stroke="{INK}" stroke-width="3"/>'
                       f'<path d="{vt.path(item, x + pad, y + 7, size)}" fill="{fg}"/></g>')
            x += tw + 2 * pad + 12
        y += row_h
    h = y - row_h + 50
    label = '; '.join(f'{name}: {", ".join(items)}' for name, items in STACK).replace('&', 'and')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Stack: {label}">
<rect x="2.5" y="2.5" width="{w - 5}" height="{h - 5}" rx="20" fill="{INK2}" stroke="{INK}" stroke-width="5"/>
{''.join(out)}
</svg>
'''


if __name__ == '__main__':
    fonts, goat = Path(sys.argv[1]), crop(read_rgba(sys.argv[2]))
    display, vt = Face(fonts / 'DelaGothicOne.ttf'), Face(fonts / 'VT323.ttf')
    OUT.mkdir(exist_ok=True)
    (OUT / 'banner.svg').write_text(banner(display, vt, goat), encoding='utf-8')
    (OUT / 'stack.svg').write_text(stack(vt), encoding='utf-8')
    print('banner.svg and stack.svg written')
