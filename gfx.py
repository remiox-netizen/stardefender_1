# -*- coding: utf-8 -*-
"""Grafika: šriftai, cartoon sprite'ai (piešiami kodu), švytėjimai, fonai."""
import math
import random

import pygame

from . import settings as cfg
from .settings import W, H, OUT

# ----------------------------------------------------------------------------
#  Tekstas su kontūru
# ----------------------------------------------------------------------------
_fonts = {}
_tcache = {}


def get_font(size):
    f = _fonts.get(size)
    if f is None:
        try:
            f = pygame.font.SysFont(
                "comicsansms,comic sans ms,verdana,dejavusans,arial", size, bold=True)
        except Exception:                          # pvz. Android be sisteminių šriftų
            f = pygame.font.Font(None, int(size * 1.25))
            f.set_bold(True)
        _fonts[size] = f
    return f


def text_surf(text, size, color, outline=3):
    key = (text, size, color, outline)
    s = _tcache.get(key)
    if s is None:
        f = get_font(size)
        base = f.render(text, True, color)
        if outline:
            o = f.render(text, True, OUT)
            s = pygame.Surface((base.get_width() + outline * 2,
                                base.get_height() + outline * 2), pygame.SRCALPHA)
            for dx in range(-outline, outline + 1):
                for dy in range(-outline, outline + 1):
                    if dx * dx + dy * dy <= outline * outline + 1:
                        s.blit(o, (dx + outline, dy + outline))
            s.blit(base, (outline, outline))
        else:
            s = base
        if len(_tcache) > 600:
            _tcache.clear()
        _tcache[key] = s
    return s


def draw_text(surf, text, size, color, pos, anchor="center", outline=3):
    s = text_surf(text, size, color, outline)
    r = s.get_rect()
    setattr(r, anchor, (int(pos[0]), int(pos[1])))
    surf.blit(s, r)
    return r


def lerp_col(a, b, k):
    k = max(0.0, min(1.0, k))
    return (int(a[0] + (b[0] - a[0]) * k), int(a[1] + (b[1] - a[1]) * k),
            int(a[2] + (b[2] - a[2]) * k))


# ----------------------------------------------------------------------------
#  Piešimo pagalbinės funkcijos
# ----------------------------------------------------------------------------
def poly(s, color, pts, w=3):
    pygame.draw.polygon(s, color, pts)
    pygame.draw.polygon(s, OUT, pts, w)


def ell(s, color, rect, w=3):
    pygame.draw.ellipse(s, color, rect)
    pygame.draw.ellipse(s, OUT, rect, w)


def circ(s, color, c, r, w=3):
    pygame.draw.circle(s, color, c, r)
    pygame.draw.circle(s, OUT, c, r, w)


def star_pts(cx, cy, r1, r2, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        a = rot + i * math.pi / n
        r = r1 if i % 2 == 0 else r2
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


# ----------------------------------------------------------------------------
#  Švytėjimas (additive glow)
# ----------------------------------------------------------------------------
_glow = {}


def glow(radius, color):
    key = (radius, color)
    g = _glow.get(key)
    if g is None:
        if len(_glow) > 400:
            _glow.clear()
        g = pygame.Surface((radius * 2, radius * 2))
        g.fill((0, 0, 0))
        for i in range(radius, 0, -1):
            k = (1 - i / radius) ** 2
            c = (int(color[0] * k), int(color[1] * k), int(color[2] * k))
            pygame.draw.circle(g, c, (radius, radius), i)
        _glow[key] = g
    return g


def add_glow(surf, x, y, radius, color):
    radius = max(4, int(radius))
    if cfg.LOW_FX and radius < 40:                 # silpnuose įrenginiuose - tik dideli švytėjimai
        return
    g = glow(radius, color)
    surf.blit(g, (int(x) - radius, int(y) - radius), special_flags=pygame.BLEND_RGB_ADD)


# ----------------------------------------------------------------------------
#  Fonai (temos)
# ----------------------------------------------------------------------------
THEMES = [
    ((16, 8, 52), (52, 20, 106), [(120, 60, 200, 40), (40, 120, 220, 34), (220, 70, 160, 30)]),
    ((6, 22, 56), (10, 66, 112), [(40, 160, 230, 40), (60, 220, 200, 30), (120, 90, 230, 34)]),
    ((44, 10, 44), (116, 26, 72), [(230, 70, 120, 40), (255, 150, 80, 30), (160, 60, 220, 34)]),
    ((8, 38, 36), (22, 96, 84), [(60, 220, 150, 36), (60, 160, 230, 34), (200, 230, 90, 28)]),
]


def make_background(i):
    top, bot, _ = THEMES[i % len(THEMES)]
    bg = pygame.Surface((W, H))
    for y in range(H):
        k = y / H
        c = (int(top[0] + (bot[0] - top[0]) * k), int(top[1] + (bot[1] - top[1]) * k),
             int(top[2] + (bot[2] - top[2]) * k))
        pygame.draw.line(bg, c, (0, y), (W, y))
    return bg.convert()


def make_nebula(i, seed):
    rnd = random.Random(i * 10 + seed)
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    cols = THEMES[i % len(THEMES)][2]
    for _ in range(6):
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(100, 220)
        col = rnd.choice(cols)
        for dy in (-H, 0, H):
            for k in range(5):          # išorė silpnesnė, centras ryškesnis
                rr = max(2, int(r * (1 - k * 0.2)))
                a = int(col[3] * (k + 1) / 5)
                pygame.draw.circle(s, (col[0], col[1], col[2], a), (x, y + dy), rr)
    return s.convert_alpha()


def make_planet(r, body, light, dark, ring=None):
    w = int(r * 4.2) + 16 if ring else r * 2 + 10
    h = r * 2 + 10
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    rr = None
    if ring:
        rr = pygame.Rect(cx - int(r * 2.1), cy - int(r * 0.5), int(r * 4.2), int(r * 1.0))
        pygame.draw.ellipse(s, ring, rr, 6)
    pygame.draw.circle(s, body, (cx, cy), r)
    pygame.draw.circle(s, light, (cx - r // 3, cy - r // 3), max(2, r // 3))
    pygame.draw.circle(s, dark, (cx + r // 3, cy + r // 3), max(2, r // 5))
    pygame.draw.circle(s, dark, (cx + r // 6, cy - r // 2), max(2, r // 8))
    pygame.draw.circle(s, OUT, (cx, cy), r, 4)
    if ring:
        pygame.draw.arc(s, ring, rr, math.pi, 2 * math.pi, 6)
    return s


SECTOR_NAMES = ["Violetinis ūkas", "Ledo planeta", "Raudonoji zona", "Smaragdo ūkas"]

PLANET_SPECS = [
    (70, (255, 170, 90), (255, 215, 140), (230, 120, 70), (190, 120, 255)),
    (44, (110, 200, 255), (190, 238, 255), (70, 140, 220), None),
    (88, (150, 230, 140), (215, 255, 195), (90, 180, 100), (255, 230, 120)),
    (32, (255, 120, 160), (255, 185, 205), (210, 70, 120), None),
]


def make_vignette():
    v = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(60):
        a = int(120 * (1 - i / 60) ** 2.2)
        pygame.draw.rect(v, (0, 0, 15, a), (i, i, W - 2 * i, H - 2 * i), 1)
    return v


# ----------------------------------------------------------------------------
#  Sprite'ai
# ----------------------------------------------------------------------------
SHIP_PAL = [
    ((110, 205, 255), (255, 95, 95), (255, 225, 110)),      # Sakalas
    ((140, 230, 120), (255, 210, 80), (255, 255, 255)),     # Šturmas
    ((190, 140, 255), (90, 220, 255), (255, 140, 220)),     # Spindulys
    ((255, 170, 90), (240, 240, 250), (120, 230, 255)),     # Raketa
]


def make_player(v=0):
    body, wing, canopy = SHIP_PAL[v]
    s = pygame.Surface((70, 76), pygame.SRCALPHA)
    cx = 35
    poly(s, wing, [(cx - 10, 34), (2, 60), (4, 72), (cx - 8, 62)])
    poly(s, wing, [(cx + 10, 34), (68, 60), (66, 72), (cx + 8, 62)])
    if v == 1:                                      # platūs sparnų galai
        poly(s, body, [(2, 60), (0, 50), (10, 54)], 2)
        poly(s, body, [(68, 60), (70, 50), (60, 54)], 2)
    for dx in (-10, 10):
        pygame.draw.rect(s, (150, 150, 175), (cx + dx - 5, 56, 10, 12), border_radius=3)
        pygame.draw.rect(s, OUT, (cx + dx - 5, 56, 10, 12), 3, border_radius=3)
    if v == 3:                                      # raketų konteineriai
        for dx in (-22, 22):
            ell(s, (255, 90, 90), (cx + dx - 4, 40, 8, 20), 2)
    if v == 2:                                      # siauresnis korpusas
        poly(s, body, [(cx, 2), (cx + 11, 30), (cx + 12, 62), (cx, 56), (cx - 12, 62), (cx - 11, 30)])
    else:
        poly(s, body, [(cx, 2), (cx + 13, 30), (cx + 15, 62),
                       (cx, 56), (cx - 15, 62), (cx - 13, 30)])
    poly(s, (255, 255, 255), [(cx, 8), (cx + 5, 20), (cx - 5, 20)], 2)
    ell(s, canopy, (cx - 8, 26, 16, 22))
    pygame.draw.ellipse(s, (255, 255, 255), (cx - 5, 29, 6, 9))
    pygame.draw.line(s, OUT, (cx - 9, 52), (cx - 9, 60), 3)
    pygame.draw.line(s, OUT, (cx + 9, 52), (cx + 9, 60), 3)
    return s


def make_asteroid(r):
    size = r * 2 + 8
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    rnd = random.Random(r)
    pts = []
    n = 10
    for i in range(n):
        a = i * 2 * math.pi / n
        rr = r * rnd.uniform(0.78, 1.0)
        pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
    pygame.draw.polygon(s, (150, 125, 105), pts)
    pygame.draw.polygon(s, (185, 160, 135), [(c + (x - c) * 0.6 - 3, c + (y - c) * 0.6 - 3) for x, y in pts])
    pygame.draw.polygon(s, OUT, pts, 4)
    for dx, dy, cr in ((-0.3, -0.25, 0.22), (0.3, 0.1, 0.17), (-0.05, 0.4, 0.14)):
        pygame.draw.circle(s, (110, 90, 75), (int(c + dx * r), int(c + dy * r)), max(2, int(cr * r)))
        pygame.draw.circle(s, OUT, (int(c + dx * r), int(c + dy * r)), max(2, int(cr * r)), 2)
    return s


def make_drone():
    s = pygame.Surface((28, 28), pygame.SRCALPHA)
    circ(s, (120, 230, 255), (14, 14), 11, 3)
    pygame.draw.circle(s, (255, 255, 255), (14, 14), 6)
    pygame.draw.circle(s, OUT, (15, 15), 3)
    poly(s, (255, 170, 60), [(14, 0), (9, 6), (19, 6)], 2)
    return s


# Akių padėtys (x, y, vyzdžio spindulys, maks. pasislinkimas) sprite'o koordinatėmis
EYES = {
    0: [(20, 23, 3, 3), (36, 23, 3, 3)],
    1: [(28, 24, 5, 4)],
    2: [(18, 26, 3, 2), (38, 26, 3, 2)],
    3: [(22, 22, 2, 2), (34, 22, 2, 2)],
    4: [(22, 28, 2, 2), (34, 28, 2, 2)],
    5: [(18, 26, 3, 3), (38, 26, 3, 3)],
    6: [(20, 20, 3, 3), (36, 20, 3, 3)],
    7: [(20, 20, 3, 3), (36, 20, 3, 3)],
    8: [(20, 20, 3, 3), (36, 20, 3, 3)],
    9: [(19, 28, 3, 3), (37, 28, 3, 3)],
}
BOSS_EYES = {
    0: [(102, 40, 6, 5), (138, 40, 6, 5)],
    1: [(120, 92, 17, 15)],
    2: [(106, 36, 4, 4), (134, 36, 4, 4)],
}
BOSS_NAMES = ["MOTINLAIVIS", "KOSMOSO AKIS", "MEGAROBOTAS"]
BOSS_PALS = [
    [(190, 120, 255), (255, 220, 120), (255, 255, 255)],
    [(255, 150, 190), (255, 240, 150), (255, 255, 255)],
    [(150, 170, 200), (255, 200, 80), (255, 255, 255)],
]


def enemy_sprite(kind, frame):
    """Priešai be vyzdžių - vyzdžius piešiame dinamiškai (seka žaidėją)."""
    s = pygame.Surface((56, 50), pygame.SRCALPHA)
    wob = 3 if frame else 0
    if kind == 0:                                   # žalias "blobas"
        for sx in (-1, 1):
            x2 = 28 + sx * 17
            pygame.draw.line(s, OUT, (28 + sx * 9, 12), (x2, 5 + wob), 4)
            circ(s, (255, 230, 90), (x2, 5 + wob), 4, 2)
        for x in (15, 41):
            ell(s, (80, 200, 100), (x - 7, 36 + wob // 2, 14, 10), 3)
        ell(s, (110, 230, 120), (4, 9, 48, 33))
        for x in (20, 36):
            circ(s, (255, 255, 255), (x, 23), 7, 2)
        pygame.draw.arc(s, OUT, (20, 28, 16, 10), math.pi, 2 * math.pi, 2)
        pygame.draw.ellipse(s, (190, 255, 200), (11, 13, 14, 6))
    elif kind == 1:                                 # violetinis kiklopas
        poly(s, (255, 230, 120), [(14, 14), (10, 2), (22, 10)], 2)
        poly(s, (255, 230, 120), [(42, 14), (46, 2), (34, 10)], 2)
        a = 4 if frame else -2
        ell(s, (160, 90, 230), (0, 22 + a, 14, 12), 2)
        ell(s, (160, 90, 230), (42, 22 - a, 14, 12), 2)
        ell(s, (190, 130, 255), (6, 10, 44, 32))
        circ(s, (255, 255, 255), (28, 24), 10, 2)
        pygame.draw.rect(s, (255, 255, 255), (19, 35, 18, 5), border_radius=2)
        pygame.draw.rect(s, OUT, (19, 35, 18, 5), 2, border_radius=2)
    elif kind == 2:                                 # raudonas piktuolis
        for x in (14, 28, 42):
            poly(s, (255, 220, 80), [(x - 6, 12), (x, 0), (x + 6, 12)], 2)
        ell(s, (220, 100, 50), (10, 40 + wob // 2, 12, 9), 2)
        ell(s, (220, 100, 50), (34, 40 + wob // 2, 12, 9), 2)
        pygame.draw.rect(s, (255, 140, 70), (4, 9, 48, 34), border_radius=14)
        pygame.draw.rect(s, OUT, (4, 9, 48, 34), 3, border_radius=14)
        for x in (18, 38):
            ell(s, (255, 255, 255), (x - 7, 19, 14, 12), 2)
        pygame.draw.line(s, OUT, (10, 13), (24, 19), 4)
        pygame.draw.line(s, OUT, (46, 13), (32, 19), 4)
        poly(s, (255, 255, 255), [(20, 35), (25, 35), (22, 42)], 2)
        poly(s, (255, 255, 255), [(31, 35), (36, 35), (33, 42)], 2)
    elif kind == 3:                                 # kamikadzė (šikšnosparnis)
        a = 3 if frame else -2
        poly(s, (190, 50, 100), [(2, 12 + a), (20, 22), (18, 38)], 3)
        poly(s, (190, 50, 100), [(54, 12 + a), (36, 22), (38, 38)], 3)
        poly(s, (255, 230, 120), [(16, 12), (14, 0), (23, 9)], 2)
        poly(s, (255, 230, 120), [(40, 12), (42, 0), (33, 9)], 2)
        ell(s, (255, 100, 140), (14, 8, 28, 34))
        for x in (22, 34):
            circ(s, (255, 255, 255), (x, 22), 5, 2)
        poly(s, (255, 255, 255), [(24, 34), (28, 34), (26, 41)], 2)
        poly(s, (255, 255, 255), [(29, 34), (33, 34), (31, 41)], 2)
    elif kind == 4:                                 # šarvuotas
        pygame.draw.line(s, OUT, (28, 9), (28, 2), 3)
        circ(s, (255, 90, 90), (28, 3), 3, 2)
        ell(s, (110, 120, 150), (10, 41 + wob // 2, 12, 8), 2)
        ell(s, (110, 120, 150), (34, 41 + wob // 2, 12, 8), 2)
        pygame.draw.rect(s, (150, 160, 185), (4, 8, 48, 36), border_radius=10)
        pygame.draw.rect(s, (110, 120, 150), (4, 8, 48, 10), border_radius=8)
        pygame.draw.rect(s, OUT, (4, 8, 48, 36), 3, border_radius=10)
        pygame.draw.rect(s, (30, 30, 60), (12, 21, 32, 14), border_radius=6)
        pygame.draw.rect(s, OUT, (12, 21, 32, 14), 2, border_radius=6)
        for x in (22, 34):
            circ(s, (255, 255, 255), (x, 28), 4, 1)
        for rx, ry in ((9, 13), (47, 13), (9, 39), (47, 39)):
            pygame.draw.circle(s, (230, 230, 240), (rx, ry), 2)
    elif kind == 5:                                 # skylantis (dvi dalys)
        a = 2 if frame else 0
        ell(s, (90, 220, 210), (2, 11 + a, 32, 31), 3)
        ell(s, (90, 220, 210), (22, 11 - a, 32, 31), 3)
        pygame.draw.ellipse(s, (170, 250, 240), (8, 16 + a, 12, 6))
        pygame.draw.ellipse(s, (170, 250, 240), (36, 16 - a, 12, 6))
        for x in (18, 38):
            circ(s, (255, 255, 255), (x, 27), 6, 2)
        pygame.draw.arc(s, OUT, (20, 33, 16, 8), math.pi, 2 * math.pi, 2)
    elif kind == 6:                                 # skydininkas (skydas piešiamas atskirai)
        poly(s, (255, 230, 120), [(28, 7), (24, 0), (32, 0)], 2)
        ell(s, (60, 120, 210), (10, 39 + wob // 2, 12, 8), 2)
        ell(s, (60, 120, 210), (34, 39 + wob // 2, 12, 8), 2)
        ell(s, (80, 150, 240), (6, 6, 44, 36))
        for x in (20, 36):
            circ(s, (255, 255, 255), (x, 20), 7, 2)
        pygame.draw.arc(s, OUT, (22, 27, 12, 8), math.pi, 2 * math.pi, 2)
        pygame.draw.ellipse(s, (170, 205, 255), (12, 10, 12, 5))
    elif kind == 7:                                 # regeneratorius (gleivė su kryžiumi)
        ell(s, (120, 225, 130), (12, 36, 8, 10 + wob), 2)
        ell(s, (120, 225, 130), (36, 36, 8, 10 + wob), 2)
        ell(s, (120, 225, 130), (6, 6, 44, 36))
        for x in (20, 36):
            circ(s, (255, 255, 255), (x, 19), 6, 2)
        pygame.draw.rect(s, (255, 255, 255), (25, 28, 6, 13))
        pygame.draw.rect(s, (255, 255, 255), (21, 32, 14, 6))
        pygame.draw.rect(s, (60, 170, 80), (25, 28, 6, 13), 1)
        pygame.draw.rect(s, (60, 170, 80), (21, 32, 14, 6), 1)
        pygame.draw.ellipse(s, (190, 255, 195), (11, 10, 11, 5))
    elif kind == 8:                                 # šokliukas (vaiduoklis, teleportuojasi)
        for i in range(3):
            ell(s, (165, 150, 255), (8 + i * 13, 30 + (wob if i == 1 else 0), 14, 14), 2)
        ell(s, (165, 150, 255), (8, 6, 40, 36))
        for x in (20, 36):
            circ(s, (255, 255, 255), (x, 20), 7, 2)
        pygame.draw.ellipse(s, (215, 205, 255), (13, 10, 12, 5))
        gfx_star = star_pts(5, 12 + wob, 5, 2, 4)
        poly(s, (255, 240, 120), gfx_star, 1)
        poly(s, (255, 240, 120), star_pts(51, 16 - wob, 5, 2, 4), 1)
    else:                                           # gydytojas (gydo kitus)
        pygame.draw.ellipse(s, (255, 230, 90), (14, 0, 28, 9), 3)
        ell(s, (150, 150, 175), (10, 40 + wob // 2, 12, 8), 2)
        ell(s, (150, 150, 175), (34, 40 + wob // 2, 12, 8), 2)
        ell(s, (245, 245, 255), (6, 8, 44, 36))
        pygame.draw.rect(s, (230, 60, 70), (25, 11, 6, 14))
        pygame.draw.rect(s, (230, 60, 70), (21, 15, 14, 6))
        for x in (19, 37):
            circ(s, (255, 255, 255), (x, 28), 6, 2)
        pygame.draw.arc(s, OUT, (22, 34, 12, 6), math.pi, 2 * math.pi, 2)
    return s


def make_ufo(frame):
    s = pygame.Surface((70, 44), pygame.SRCALPHA)
    ell(s, (150, 230, 255), (18, 2, 34, 24), 3)
    ell(s, (190, 190, 215), (2, 14, 66, 24), 3)
    cols = [(255, 230, 90), (255, 120, 150), (120, 255, 160)]
    for i in range(5):
        circ(s, cols[(i + frame) % 3], (12 + i * 11, 27), 3, 2)
    pygame.draw.ellipse(s, (255, 255, 255), (26, 6, 8, 6))
    return s


def _boss0(frame):
    s = pygame.Surface((240, 170), pygame.SRCALPHA)
    poly(s, (110, 60, 190), [(8, 80), (58, 46), (66, 118), (18, 126)], 4)
    poly(s, (110, 60, 190), [(232, 80), (182, 46), (174, 118), (222, 126)], 4)
    for x in (30, 192):                                          # kanonai
        pygame.draw.rect(s, (150, 150, 175), (x, 118, 18, 38), border_radius=5)
        pygame.draw.rect(s, OUT, (x, 118, 18, 38), 4, border_radius=5)
        pygame.draw.rect(s, (255, 120, 80), (x + 3, 150, 12, 6))
    ell(s, (165, 105, 240), (20, 52, 200, 104), 4)
    ell(s, (205, 155, 255), (60, 100, 120, 48), 3)
    ell(s, (140, 235, 255), (68, 4, 104, 72), 4)                 # kupolas
    for x in (102, 138):
        circ(s, (255, 255, 255), (x, 40), 12, 3)
    pygame.draw.line(s, OUT, (86, 22), (112, 32), 5)
    pygame.draw.line(s, OUT, (154, 22), (128, 32), 5)
    pygame.draw.rect(s, (90, 20, 60), (92, 88, 56, 26), border_radius=10)     # burna
    for i in range(5):
        x = 96 + i * 11
        poly(s, (255, 255, 255), [(x, 88), (x + 9, 88), (x + 4, 98)], 2)
    pygame.draw.rect(s, OUT, (92, 88, 56, 26), 4, border_radius=10)
    cols = [(255, 230, 90), (255, 110, 140), (120, 255, 160)]
    for i in range(5):
        circ(s, cols[(i + frame) % 3], (60 + i * 30, 134), 6, 3)
    return s


def _boss1(frame):
    """Kosmoso akis."""
    s = pygame.Surface((240, 170), pygame.SRCALPHA)
    for i in range(5):
        off = 6 if (i + frame) % 2 else 0
        ell(s, (255, 150, 190), (26 + i * 40, 120 + off, 28, 44), 3)
    for k in range(9):
        a = math.radians(-170 + k * 20)
        cx, cy = 120 + math.cos(a) * 66, 92 + math.sin(a) * 66
        tip = (120 + math.cos(a) * 94, 92 + math.sin(a) * 94)
        pa = a + math.pi / 2
        poly(s, (255, 220, 80), [(cx + math.cos(pa) * 10, cy + math.sin(pa) * 10), tip,
                                 (cx - math.cos(pa) * 10, cy - math.sin(pa) * 10)], 3)
    circ(s, (255, 240, 245), (120, 92), 68, 4)
    for a in (0.3, 1.2, 2.2, 3.0, 4.0, 5.2):
        pygame.draw.line(s, (230, 70, 90),
                         (120 + math.cos(a) * 64, 92 + math.sin(a) * 64),
                         (120 + math.cos(a) * 44, 92 + math.sin(a) * 44), 3)
    circ(s, (60, 190, 255), (120, 92), 38, 4)
    pygame.draw.circle(s, (30, 120, 200), (120, 92), 28)
    pygame.draw.line(s, OUT, (62, 40), (108, 58), 6)
    pygame.draw.line(s, OUT, (178, 40), (132, 58), 6)
    return s


def _boss2(frame):
    """Megarobotas."""
    s = pygame.Surface((240, 170), pygame.SRCALPHA)
    for x in (90, 150):
        poly(s, (255, 140, 40), [(x - 10, 140), (x + 10, 140), (x, 166 - (5 if frame else 0))], 3)
    for x in (6, 198):
        pygame.draw.rect(s, (100, 120, 150), (x, 92, 36, 52), border_radius=10)
        pygame.draw.rect(s, OUT, (x, 92, 36, 52), 4, border_radius=10)
        circ(s, (255, 200, 80), (x + 18, 148), 16, 4)
    pygame.draw.rect(s, (120, 140, 170), (45, 56, 150, 86), border_radius=18)
    pygame.draw.rect(s, OUT, (45, 56, 150, 86), 4, border_radius=18)
    pygame.draw.rect(s, (40, 45, 80), (82, 78, 76, 42), border_radius=8)
    pygame.draw.rect(s, OUT, (82, 78, 76, 42), 3, border_radius=8)
    cols = [(255, 90, 90), (255, 230, 90), (120, 255, 160)]
    for i in range(3):
        circ(s, cols[(i + frame) % 3], (100 + i * 20, 99), 6, 3)
    for x in (40, 200):
        circ(s, (255, 200, 80), (x, 78), 22, 4)
    pygame.draw.rect(s, (150, 170, 200), (78, 4, 84, 58), border_radius=14)
    pygame.draw.rect(s, OUT, (78, 4, 84, 58), 4, border_radius=14)
    pygame.draw.rect(s, (40, 40, 70), (88, 22, 64, 28), border_radius=10)
    pygame.draw.rect(s, OUT, (88, 22, 64, 28), 3, border_radius=10)
    for x in (106, 134):
        circ(s, (255, 255, 255), (x, 36), 9, 2)
    circ(s, (255, 80, 80), (92, 11), 4, 2)
    return s


def make_boss(kind, frame):
    return (_boss0, _boss1, _boss2)[kind](frame)


def make_coin(frame):
    s = pygame.Surface((22, 22), pygame.SRCALPHA)
    w = [18, 12, 6, 12][frame]
    r = pygame.Rect(11 - w // 2, 2, w, 18)
    pygame.draw.ellipse(s, (255, 205, 50), r)
    pygame.draw.ellipse(s, OUT, r, 3 if w >= 12 else 2)
    if w >= 12:
        pygame.draw.ellipse(s, (255, 240, 150), (r.x + 4, 6, w - 8, 10))
    return s


def make_power(kind):
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    col = {"W": (255, 170, 40), "S": (80, 170, 255), "H": (255, 95, 140),
           "B": (170, 100, 235)}[kind]
    pygame.draw.circle(s, col, (20, 20), 18)
    pygame.draw.circle(s, OUT, (20, 20), 18, 3)
    if kind == "W":
        poly(s, (255, 245, 110), star_pts(20, 21, 12, 5.5), 2)
    elif kind == "S":
        poly(s, (255, 255, 255), [(12, 11), (28, 11), (28, 22), (20, 31), (12, 22)], 2)
        pygame.draw.line(s, col, (20, 14), (20, 26), 3)
    elif kind == "H":
        pygame.draw.circle(s, (255, 255, 255), (15, 17), 5)
        pygame.draw.circle(s, (255, 255, 255), (25, 17), 5)
        pygame.draw.polygon(s, (255, 255, 255), [(10, 19), (30, 19), (20, 30)])
    else:
        poly(s, (255, 240, 100), [(23, 6), (12, 22), (19, 22), (16, 34), (29, 17), (22, 17)], 2)
    return s


BULLET_COLS = [(90, 230, 255), (120, 255, 150), (255, 235, 90),
               (255, 160, 60), (255, 100, 200)]
GLOW_COLS = [(30, 150, 200), (50, 190, 100), (200, 170, 30), (210, 110, 30), (210, 50, 140)]
POWER_COLS = {"W": (255, 170, 40), "S": (80, 170, 255), "H": (255, 95, 140), "B": (190, 120, 255)}


def make_bullet(lv):
    s = pygame.Surface((14, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(s, BULLET_COLS[lv - 1], (1, 1, 12, 30))
    pygame.draw.ellipse(s, OUT, (1, 1, 12, 30), 3)
    pygame.draw.ellipse(s, (255, 255, 255), (5, 6, 4, 16))
    return s


def make_ebullet():
    s = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(s, (255, 80, 120), (10, 10), 9)
    pygame.draw.circle(s, OUT, (10, 10), 9, 3)
    pygame.draw.circle(s, (255, 230, 240), (7, 7), 3)
    return s


def flash_version(img):
    f = img.copy()
    f.fill((130, 130, 130, 0), special_flags=pygame.BLEND_RGB_ADD)
    return f


class S:
    """Paruošti sprite'ai (užpildomi funkcijoje init)."""
    pass


def init():
    """Sukuria visus sprite'us. Kviesti po pygame.display.set_mode()."""
    S.player = [make_player(v).convert_alpha() for v in range(len(SHIP_PAL))]
    S.life = [pygame.transform.smoothscale(p, (28, 30)) for p in S.player]
    S.asteroid = [make_asteroid(26).convert_alpha(), make_asteroid(14).convert_alpha()]
    S.drone = make_drone().convert_alpha()
    S.enemy = [[enemy_sprite(k, f).convert_alpha() for f in (0, 1)] for k in range(10)]
    S.enemy_flash = [[flash_version(i) for i in row] for row in S.enemy]
    S.ufo = [make_ufo(f).convert_alpha() for f in (0, 1)]
    S.ufo_flash = [flash_version(i) for i in S.ufo]
    S.boss = [[make_boss(k, f).convert_alpha() for f in (0, 1)] for k in range(3)]
    S.boss_flash = [[flash_version(i) for i in row] for row in S.boss]
    S.coin = [make_coin(f).convert_alpha() for f in range(4)]
    S.power = {k: make_power(k).convert_alpha() for k in "WSHB"}
    S.bomb_icon = pygame.transform.smoothscale(S.power["B"], (26, 26))
    S.bullet = [make_bullet(i).convert_alpha() for i in range(1, 6)]
    S.ebullet = make_ebullet().convert_alpha()
    S.planets = [make_planet(*a).convert_alpha() for a in PLANET_SPECS]
    S.vignette = make_vignette().convert_alpha()


def draw_ship(surf, x, y, t, tilt=0.0, blink=False, ship=0):
    """Erdvėlaivis su animuota liepsna ir švytėjimu. (x, y) - laivo centras."""
    for dx in (-10, 10):
        ln = 15 + 6 * math.sin(t * 0.6 + dx) + 3 * math.sin(t * 1.3)
        base = y + 28
        poly(surf, (255, 140, 40), [(x + dx - 6, base), (x + dx + 6, base), (x + dx, base + ln)], 2)
        pygame.draw.polygon(surf, (255, 240, 120),
                            [(x + dx - 3, base), (x + dx + 3, base), (x + dx, base + ln * 0.6)])
        add_glow(surf, x + dx, base + 6, 18, (160, 80, 20))
    if not blink:
        img = S.player[ship]
        if abs(tilt) > 0.5:
            img = pygame.transform.rotate(img, tilt)
        surf.blit(img, img.get_rect(center=(int(x), int(y))))


def draw_pupils(surf, topleft, eyes, x, y, tx, ty):
    dx, dy = tx - x, ty - y
    d = math.hypot(dx, dy) or 1.0
    dx, dy = dx / d, dy / d
    for ex, ey, pr, mo in eyes:
        px = int(topleft[0] + ex + dx * mo)
        py = int(topleft[1] + ey + dy * mo)
        pygame.draw.circle(surf, OUT, (px, py), pr)
        pygame.draw.circle(surf, (255, 255, 255), (px - pr // 3, py - pr // 3), max(1, pr // 3))
