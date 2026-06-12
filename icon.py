"""Generiert icon.ico fuer Studforge (kein Pip-Paket noetig)."""
import math, struct, zlib, os

# ── Pixel-Art "S" (5 Zeilen x 7 Spalten) ─────────────────────────
S_ART = [
    [0,1,1,1,1,1,0],
    [1,0,0,0,0,0,0],
    [0,1,1,1,1,1,0],
    [0,0,0,0,0,0,1],
    [0,1,1,1,1,1,0],
]

def make_pixels(size):
    cx = cy = (size - 1) / 2.0
    R = size * 0.44  # Radius Sechseck

    # Spitzes Sechseck (pointy-top, 30° versetzt)
    verts = [
        (cx + R * math.cos(math.radians(30 + 60 * k)),
         cy + R * math.sin(math.radians(30 + 60 * k)))
        for k in range(6)
    ]

    def in_hex(px, py):
        inside = False
        j = 5
        for i in range(6):
            xi, yi = verts[i]; xj, yj = verts[j]
            if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        return inside

    # S-Buchstabe zentriert
    rows_s, cols_s = len(S_ART), len(S_ART[0])
    cell  = size * 0.085
    s_w   = cols_s * cell
    s_h   = rows_s * cell
    s_x0  = cx - s_w / 2
    s_y0  = cy - s_h / 2

    def in_s(px, py):
        c = int((px - s_x0) / cell)
        r = int((py - s_y0) / cell)
        return 0 <= r < rows_s and 0 <= c < cols_s and S_ART[r][c] == 1

    ORANGE = (249, 115, 22)
    WHITE  = (255, 255, 255)
    N = 3  # 3x3 Supersampling fuer glaette Kanten

    result = []
    for y in range(size):
        row = []
        for x in range(size):
            hex_n = s_n = 0
            for sy in range(N):
                for sx in range(N):
                    spx = x + (sx + 0.5) / N
                    spy = y + (sy + 0.5) / N
                    if in_hex(spx, spy):
                        hex_n += 1
                        if in_s(spx, spy):
                            s_n += 1
            total = N * N
            alpha = int(255 * hex_n / total)
            if alpha == 0:
                row.append((0, 0, 0, 0))
            else:
                sf  = s_n / max(hex_n, 1)
                r   = int(ORANGE[0] * (1 - sf) + WHITE[0] * sf)
                g   = int(ORANGE[1] * (1 - sf) + WHITE[1] * sf)
                b   = int(ORANGE[2] * (1 - sf) + WHITE[2] * sf)
                row.append((r, g, b, alpha))
        result.append(row)
    return result


def to_png(size, pixels):
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)

    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    raw  = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b, a in row:
            raw.extend((r, g, b, a))
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 9)) +
            chunk(b'IEND', b''))


def build_ico():
    sizes = [16, 24, 32, 48, 64, 256]
    pngs  = [(s, to_png(s, make_pixels(s))) for s in sizes]
    n     = len(pngs)
    offset = 6 + n * 16
    entries = b''; body = b''
    for s, png in pngs:
        entries += struct.pack('<BBBBHHII',
            s if s < 256 else 0, s if s < 256 else 0,
            0, 0, 1, 32, len(png), offset)
        offset += len(png); body += png
    return struct.pack('<HHH', 0, 1, n) + entries + body


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
    print('Generiere Icon ...')
    data = build_ico()
    with open(out, 'wb') as f:
        f.write(data)
    print(f'Gespeichert: {out}')
