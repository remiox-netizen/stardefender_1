# -*- coding: utf-8 -*-
"""Žaidimo objektai: kulkos, monetos, priešai, UFO, bosai, prizai."""
import math
import random

import pygame

from .settings import W, H, OUT
from . import gfx
from .gfx import S
from .effects import Spark, Flash, Ring


def bonus_path(pat, u, p0):
    """Bonuso etapo priešų skrydžio trajektorijos (u - kadrai nuo pradžios)."""
    if pat == "wave":
        return W / 2 + 260 * math.sin(u * 0.03 + p0), -40 + u * 2.3
    if pat == "loop":
        return (W / 2 + 200 * math.sin(u * 0.022 + p0) + 70 * math.cos(u * 0.09),
                -40 + u * 1.6 + 70 * math.sin(u * 0.09))
    x = (-40 + u * 3.2) if p0 > 0 else (W + 40 - u * 3.2)      # "cross"
    return x, 130 + 80 * math.sin(u * 0.05)


def tri(x):
    """Trikampė banga (-1..1)."""
    return (2 / math.pi) * math.asin(math.sin(x))


def stream_path(pat, u, p):
    """Priešų srautų trajektorijos (u - kadrai nuo pradžios, p - parametrai)."""
    if pat == "drop":                                   # leidimasis žemyn su banguote
        return p["x0"] + p["A"] * math.sin(u * p["w"] + p["ph"]), -40 + u * p["vy"]
    if pat == "diag":                                   # įstrižas skrydis nuo kampo
        return p["x0"] + p["dx"] * u, -40 + u * p["vy"]
    if pat == "zig":                                    # zigzagas
        return p["x0"] + p["A"] * tri(u * p["w"]), -40 + u * p["vy"]
    if pat == "sweep":                                  # horizontalus praskridimas
        x = (-40 + u * p["vx"]) if p["dir"] > 0 else (W + 40 - u * p["vx"])
        return x, p["y0"] + 40 * math.sin(u * 0.06)
    if pat in ("spiral", "ring"):
        def f(uu):
            rr = 1.0 + max(0.0, 30 - uu) / 30.0 * p["k"]            # įskrenda iš už ekrano
            if pat == "spiral":
                a = p["a0"] + p["dir"] * uu * 0.045
                r = max(50.0, 270 - uu * 0.95) * rr
                return p["cx"] + math.cos(a) * r, p["cy"] + math.sin(a) * r * 0.7
            a = p["a0"] + p["dir"] * uu * 0.028
            return p["cx"] + math.cos(a) * p["rx"] * rr, p["cy"] + math.sin(a) * p["ry"] * rr
        ue = 232 if pat == "spiral" else p["ue"]
        if u <= ue:
            return f(u)
        x, y = f(ue)                                    # po orbitos - išskrenda žemyn
        return x, y + (u - ue) * 3.4
    return -100.0, -100.0


class Bullet:
    """Žaidėjo kulka (gali pramušti taikinius, sekti taikinį, turėti riboto nuotolio)."""

    def __init__(self, x, y, vx, vy, lv, dmg=1, pierce=0, homing=False, life=None):
        self.x, self.y, self.vx, self.vy, self.lv, self.dmg = x, y, vx, vy, lv, dmg
        self.pierce, self.homing, self.life = pierce, homing, life
        self.hit_ids = set()
        self.age = 0

    def update(self, g=None):
        if self.homing and g is not None:
            tgt = g.nearest_target(self.x, self.y)
            if tgt is not None:
                want = math.atan2(tgt.x - self.x, -(tgt.y - self.y))
                cur = math.atan2(self.vx, -self.vy)
                d = (want - cur + math.pi) % (2 * math.pi) - math.pi
                cur += max(-0.12, min(0.12, d))
                sp = math.hypot(self.vx, self.vy)
                self.vx = math.sin(cur) * sp
                self.vy = -math.cos(cur) * sp
        self.x += self.vx
        self.y += self.vy
        self.age += 1

    def alive(self):
        return (-40 < self.y < H + 40 and -40 < self.x < W + 40
                and (self.life is None or self.age < self.life))

    def draw(self, surf):
        gfx.add_glow(surf, self.x, self.y, 20, gfx.GLOW_COLS[self.lv - 1])
        img = S.bullet[self.lv - 1]
        if abs(self.vx) > 0.05:
            img = pygame.transform.rotate(img, -math.degrees(math.atan2(self.vx, -self.vy)))
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class EBullet:
    """Priešo kulka."""

    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.grazed = False

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def alive(self):
        return -30 < self.y < H + 30 and -30 < self.x < W + 30

    def draw(self, surf, t):
        gfx.add_glow(surf, self.x, self.y, 18, (150, 20, 60))
        r = 1.0 + 0.12 * math.sin(t * 0.4)
        img = pygame.transform.rotozoom(S.ebullet, 0, r)
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class Asteroid:
    """Asteroidas - pavojus: griūva žemyn, didelis skyla į du mažus."""
    PAL = [(190, 160, 130), (240, 215, 180), (255, 255, 255)]

    def __init__(self, x, y, vx, vy, size=0):
        self.x, self.y, self.vx, self.vy, self.size = x, y, vx, vy, size
        self.r = [26, 14][size]
        self.hp = [3, 1][size]
        self.ang = random.uniform(0, 360)
        self.spin = random.uniform(-3, 3)

    def update(self, g):
        self.x += self.vx
        self.y += self.vy
        self.ang += self.spin

    def alive(self):
        return self.y < H + 60 and -80 < self.x < W + 80

    def rect(self):
        rr = int(self.r * 0.85)
        return pygame.Rect(int(self.x) - rr, int(self.y) - rr, rr * 2, rr * 2)

    def draw(self, surf):
        img = pygame.transform.rotate(S.asteroid[self.size], self.ang)
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class Coin:
    """Moneta - perkama parduotuvėje."""

    def __init__(self, x, y, v=1):
        self.x, self.y, self.v = x, y, v
        self.vx = random.uniform(-2.0, 2.0)
        self.vy = random.uniform(-3.8, -1.2)
        self.t = random.randint(0, 20)

    def update(self, g):
        self.t += 1
        dx, dy = g.px - self.x, g.py - self.y
        d = math.hypot(dx, dy) or 1.0
        if not g.dead and d < g.magnet_r:
            self.x += dx / d * 6.0
            self.y += dy / d * 6.0
        else:
            self.x += self.vx
            self.y += self.vy
            self.vx *= 0.97
            self.vy = min(self.vy + 0.12, 2.6)

    def rect(self):
        return pygame.Rect(int(self.x) - 12, int(self.y) - 12, 24, 24)

    def draw(self, surf):
        gfx.add_glow(surf, self.x, self.y, 14, (150, 110, 20))
        img = S.coin[(self.t // 5) % 4]
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class Power:
    """Prizas: W ginklas, S skydas, H gyvybė, B bomba."""

    def __init__(self, x, y, kind):
        self.x, self.y, self.kind, self.t = x, y, kind, 0

    def update(self, g):
        self.t += 1
        dx, dy = g.px - self.x, g.py - self.y
        d = math.hypot(dx, dy) or 1.0
        if not g.dead and d < g.magnet_r:             # magnetas
            self.x += dx / d * 4.5
            self.y += dy / d * 4.5
        else:
            self.y += 2.2

    def rect(self):
        return pygame.Rect(int(self.x) - 20, int(self.y) - 20, 40, 40)

    def draw(self, surf):
        yy = self.y + math.sin(self.t * 0.15) * 4
        gfx.add_glow(surf, self.x, yy, int(34 + 4 * math.sin(self.t * 0.2)),
                     gfx.POWER_COLS[self.kind])
        img = S.power[self.kind]
        surf.blit(img, img.get_rect(center=(int(self.x), int(yy))))
        a = self.t * 0.08
        pygame.draw.circle(surf, (255, 255, 255),
                           (int(self.x + math.cos(a) * 26), int(yy + math.sin(a) * 26)), 2)


class Enemy:
    """Priešų rūšys: 0 blobas, 1 kiklopas, 2 piktuolis, 3 kamikadzė, 4 šarvuotas,
    5 skylantis, 6 skydininkas (slankiojantis skydas), 7 regeneratorius (gyja),
    8 šokliukas (teleportuojasi nuo šūvių), 9 gydytojas (gydo kitus)."""
    HP = [1, 2, 3, 1, 4, 2, 3, 4, 2, 3]
    PTS = [10, 20, 30, 25, 40, 30, 40, 40, 35, 50]
    COINS = [1, 2, 3, 2, 4, 2, 3, 3, 3, 4]
    PAL = [
        [(110, 240, 130), (220, 255, 200), (255, 255, 255)],
        [(190, 120, 255), (240, 200, 255), (255, 255, 255)],
        [(255, 140, 60), (255, 230, 80), (255, 255, 255)],
        [(255, 100, 140), (255, 200, 220), (255, 255, 255)],
        [(170, 185, 215), (230, 240, 255), (255, 255, 255)],
        [(90, 230, 210), (200, 255, 245), (255, 255, 255)],
        [(110, 170, 255), (210, 230, 255), (255, 255, 255)],
        [(120, 225, 130), (200, 255, 200), (255, 255, 255)],
        [(170, 155, 255), (225, 215, 255), (255, 255, 255)],
        [(245, 245, 255), (255, 150, 160), (255, 255, 255)],
    ]

    def __init__(self, col, row, kind, bx, by, delay=0, hpb=0):
        self.col, self.row, self.kind = col, row, kind
        self.hp = self.maxhp = self.HP[kind] + hpb
        self.since_hit = 0          # kadrai nuo paskutinio pataikymo (regeneratoriui)
        self.sh_off = 0.0           # skydininko skydo poslinkis
        self.tp_off = 0.0           # šokliuko teleportacijos poslinkis
        self.tp_cd = 0
        self.heal_t = random.randint(0, 60)
        self.link = None            # gydytojo "gydymo spindulys" [x1, y1, x2, y2, kadrai]
        self.bx, self.by = bx, by
        self.mode = "enter"
        self.delay = delay
        self.et = 0
        self.side = random.choice([-1, 1])
        self.sx0 = bx + self.side * random.randint(120, 260)
        self.x, self.y = float(self.sx0), -60.0
        self.flash = 0
        self.t = 0
        self.phase = random.random() * 6.28
        self.sx = self.sy = self.amp = 0.0
        self.shot = False
        self.free = False       # laisvas priešas (pakalikas) nepriklauso formacijai
        self.gone = False
        self.pat, self.p0, self.bdelay = "", 0.0, 0
        self.pp = {}                # srauto trajektorijos parametrai
        self.off = (0.0, 0.0)       # poslinkis grupėje
        self.fire_every, self.fire_phase = 0, 0
        self.min_u = 10             # kiek kadrų negali "pabėgti"
        self.counts_escape = False  # ar pabėgimas skaičiuojamas
        self.core = None            # orbitos šerdis
        self.ang, self.rad, self.spd = 0.0, 0.0, 0.0
        self.scale = 1.0
        self.ring_radii = []

    @classmethod
    def pathed(cls, kind, pat, pp, delay=0, hpb=0, off=(0.0, 0.0), fire_every=0):
        """Priešas, skrendantis trajektorija (srautai, grupės, eilės, apsupimas)."""
        e = cls(random.randint(0, 9), 0, kind, 0, 0, 0, hpb)
        e.mode = "stream"
        e.free = True
        e.counts_escape = True
        e.pat, e.pp, e.bdelay, e.off = pat, pp, delay, off
        e.fire_every = fire_every
        e.fire_phase = random.randint(30, 90)
        e.min_u = 40 if pat in ("spiral", "ring") else 10
        e.x, e.y = -100.0, -100.0
        return e

    @classmethod
    def make_core(cls, hpb=0):
        """Orbitos šerdis - didelis priešas, aplink kurį sukasi žiedai."""
        e = cls(0, 0, 4, 0, 0, 0, 0)
        e.hp = e.maxhp = 14 + 3 * hpb
        e.mode = "core"
        e.free = True
        e.scale = 1.8
        e.x, e.y = W / 2, -260.0
        return e

    @classmethod
    def orbiter(cls, kind, core, ang, rad, spd, hpb=0):
        e = cls(random.randint(0, 9), 0, kind, 0, 0, 0, hpb)
        e.mode = "orbit"
        e.free = True
        e.counts_escape = True
        e.core, e.ang, e.rad, e.spd = core, ang, rad, spd
        e.x = core.x + math.cos(ang) * rad
        e.y = core.y + math.sin(ang) * rad * 0.85
        return e

    @classmethod
    def bonus(cls, pat, idx, kind, p0=0.0):
        """Bonuso etapo priešas - skrenda trajektorija, nešaudo ir nežeidžia."""
        e = cls(idx, 0, kind, 0, 0)
        e.mode = "bonus"
        e.free = True
        e.pat, e.p0, e.bdelay = pat, p0, idx * 9
        e.x, e.y = -100.0, -100.0
        return e

    @classmethod
    def minion(cls, x, y):
        e = cls(random.randint(0, 7), 0, 0, x, y)
        e.mode = "dive"
        e.free = True
        e.x, e.y = x, y
        e.sx, e.sy = x, y
        e.amp = random.choice([-1, 1]) * random.uniform(60, 140)
        return e

    @property
    def pal(self):
        return self.PAL[self.kind]

    def rect(self):
        sc = self.scale
        return pygame.Rect(int(self.x - 22 * sc), int(self.y - 18 * sc), int(44 * sc), int(36 * sc))

    def shield_rect(self):
        return pygame.Rect(int(self.x + self.sh_off) - 15, int(self.y) + 17, 30, 9)

    def teleport(self, g):
        d = random.choice([-1, 1])
        if not (50 < self.x + d * 110 < W - 50):
            d = -d
        g.fx.append(Flash(self.x, self.y, 40, (190, 170, 255), 6))
        g.fx.append(Ring(self.x, self.y, 0.5, (210, 200, 255), 14))
        self.tp_off += d * 110
        self.x += d * 110
        self.tp_cd = 150
        g.fx.append(Flash(self.x, self.y, 40, (190, 170, 255), 6))
        g.fx.append(Ring(self.x, self.y, 0.5, (210, 200, 255), 14))
        g.a.sfx("tp")

    def special(self, g):
        """Ypatingi rūšių gebėjimai (kviečiama kiekvieną kadrą)."""
        k = self.kind
        if k == 6:
            self.sh_off = 14 * math.sin(g.t * 0.06 + self.phase)
        elif k == 7:
            self.since_hit += 1
            if self.since_hit > 90 and self.hp < self.maxhp and g.t % 45 == 0:
                self.hp += 1
                for _ in range(5):
                    g.fx.append(Spark(self.x + random.uniform(-14, 14), self.y + random.uniform(-10, 10),
                                      0, -1.2, 18, (130, 255, 150), 4))
        elif k == 8:
            if self.tp_cd > 0:
                self.tp_cd -= 1
            self.tp_off *= 0.992
            if self.tp_cd <= 0 and self.mode in ("form", "stream"):
                for b in g.bullets:
                    if b.vy < 0 and 0 < b.y - self.y < 170 and abs(b.x - self.x) < 30:
                        self.teleport(g)
                        break
        elif k == 9:
            self.heal_t += 1
            if self.link is not None:
                self.link[4] -= 1
                if self.link[4] <= 0:
                    self.link = None
            if self.heal_t >= 120 and self.mode in ("form", "stream", "orbit"):
                tgt, worst = None, 0.0
                for o in g.enemies:
                    if o is self or o.hp >= o.maxhp or o.mode == "enter":
                        continue
                    if (o.x - self.x) ** 2 + (o.y - self.y) ** 2 > 190 ** 2:
                        continue
                    lost = o.maxhp - o.hp
                    if lost > worst:
                        tgt, worst = o, lost
                if tgt is not None:
                    self.heal_t = 0
                    tgt.hp += 1
                    self.link = [self.x, self.y, tgt.x, tgt.y, 14]
                    for _ in range(6):
                        g.fx.append(Spark(tgt.x + random.uniform(-14, 14), tgt.y + random.uniform(-10, 10),
                                          0, -1.0, 18, (255, 150, 170), 4))
                    g.a.sfx("heal")

    def update(self, g):
        self.special(g)
        slotx = self.bx + g.ox
        sloty = self.by + g.oy + math.sin(g.t * 0.05 + self.phase) * 3
        if self.mode == "enter":
            if self.delay > 0:
                self.delay -= 1
                self.x, self.y = float(self.sx0), -60.0
            else:
                self.et += 1
                p = min(1.0, self.et / 70.0)
                e = 1 - (1 - p) ** 3
                self.x = self.sx0 + (slotx - self.sx0) * e + math.sin(p * math.pi) * self.side * 110
                self.y = -60 + (sloty + 60) * e
                if p >= 1.0:
                    self.mode = "form"
        elif self.mode == "form":
            self.x = max(30.0, min(W - 30.0, slotx + self.tp_off))
            self.y = sloty
        elif self.mode == "dive":
            self.t += 1
            if self.kind == 3 and not self.free:          # kamikadzė seka žaidėją
                self.y += 5.4
                k = 1.0 if self.t > 10 else 0.3
                self.x += max(-2.4, min(2.4, g.px - self.x)) * k
            else:
                self.x = self.sx + math.sin(self.t * 0.07) * self.amp
                self.y = self.sy + self.t * 3.6
                if self.t == 30 and not self.shot:
                    self.shot = True
                    g.ebullets.append(EBullet(self.x, self.y + 16, 0, 5.0))
            if self.y > H + 40:
                if self.free:
                    self.gone = True
                    if self.counts_escape:
                        g.escaped += 1
                else:
                    self.mode = "ret"
                    self.x, self.y = slotx, -50.0
        elif self.mode == "stream":
            self.t += 1
            u = self.t - self.bdelay
            if u < 0:
                self.x, self.y = -100.0, -100.0
            else:
                px, py = stream_path(self.pat, u, self.pp)
                self.x = px + self.off[0] + self.tp_off
                self.y = py + self.off[1]
                if (self.fire_every and u > 20 and 20 < self.y < H - 220
                        and (u - self.fire_phase) % self.fire_every == 0):
                    g.ebullets.append(EBullet(self.x, self.y + 16, 0, 4.2 + 0.5 * max(g.adapt, 0.0)))
                if u > self.min_u and (self.y > H + 60 or self.x < -110 or self.x > W + 110):
                    self.gone = True
                    if self.counts_escape:
                        g.escaped += 1
        elif self.mode == "orbit":
            c = self.core
            if c is None or c.hp <= 0 or c not in g.enemies or g.wt_t > 2400:   # šerdis žuvo / laikas baigėsi - žiedas byra
                self.mode = "dive"
                self.sx, self.sy, self.t, self.shot = self.x, self.y, 0, False
                self.amp = random.choice([-1, 1]) * random.uniform(60, 120)
            else:
                self.ang += self.spd
                self.x = c.x + math.cos(self.ang) * self.rad
                self.y = c.y + math.sin(self.ang) * self.rad * 0.85
        elif self.mode == "core" and g.wt_t > 3000:                  # per ilgai - šerdis pasitraukia
            self.y -= 4.0
            if self.y < -300:
                self.gone = True
                g.escaped += 1
        elif self.mode == "core":
            self.t += 1
            p = min(1.0, self.t / 90.0)
            e = 1 - (1 - p) ** 3
            self.x = W / 2 + math.sin(self.t * 0.012) * 190
            self.y = -260 + (190 + 260) * e + math.sin(self.t * 0.02) * 10 * p
            if self.t > 100 and self.t % 100 == 0 and not g.dead:
                base = math.atan2(g.py - self.y, g.px - self.x)
                spread = (-0.25, 0.0, 0.25) if g.adapt >= 0.6 else (0.0,)
                for a in spread:
                    g.ebullets.append(EBullet(self.x, self.y + 30, math.cos(base + a) * 4.6,
                                              math.sin(base + a) * 4.6))
        elif self.mode == "bonus":
            self.t += 1
            u = self.t - self.bdelay
            if u < 0:
                self.x, self.y = -100.0, -100.0
            else:
                self.x, self.y = bonus_path(self.pat, u, self.p0)
                if u > 10 and (self.y > H + 50 or self.x < -80 or self.x > W + 80):
                    self.gone = True
        else:  # ret
            self.x += (slotx - self.x) * 0.1
            self.y += 4.5
            if self.y >= sloty:
                self.mode = "form"
        if self.flash > 0:
            self.flash -= 1

    def draw(self, surf, g):
        frame = (g.t // 20 + self.col) % 2
        img = (S.enemy_flash if self.flash > 0 else S.enemy)[self.kind][frame]
        sc = self.scale
        eyes = gfx.EYES[self.kind]
        if self.mode == "core":
            for rr in self.ring_radii:
                pygame.draw.ellipse(surf, (95, 75, 160), pygame.Rect(int(self.x - rr), int(self.y - rr * 0.85),
                                                                    int(rr * 2), int(rr * 1.7)), 1)
            gfx.add_glow(surf, self.x, self.y, 70, (70, 30, 90))
        if sc != 1.0:
            img = pygame.transform.rotozoom(img, 0, sc)
            eyes = [(ex * sc, ey * sc, max(1, int(pr * sc)), mo * sc) for ex, ey, pr, mo in eyes]
        r = img.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(img, r)
        gfx.draw_pupils(surf, r.topleft, eyes, self.x, self.y, g.px, g.py)
        if self.kind == 6:                                  # slankiojantis skydas
            sr = self.shield_rect()
            pygame.draw.rect(surf, (200, 210, 235), sr, border_radius=4)
            pygame.draw.rect(surf, (245, 250, 255), (sr.x + 3, sr.y + 1, sr.w - 6, 3), border_radius=2)
            pygame.draw.rect(surf, OUT, sr, 3, border_radius=4)
        elif self.kind == 9:
            gfx.add_glow(surf, self.x, self.y, 26, (30, 90, 50))
            if self.link is not None:
                a = self.link
                pygame.draw.line(surf, (255, 150, 170), (a[0], a[1]), (a[2], a[3]), 4)
                pygame.draw.line(surf, (255, 255, 255), (a[0], a[1]), (a[2], a[3]), 1)
        if self.kind > 0 and self.hp < self.maxhp:
            w = int(34 * sc)
            bx, by = int(self.x) - w // 2, int(self.y - 32 * sc)
            pygame.draw.rect(surf, OUT, (bx - 2, by - 2, w + 4, 8), border_radius=3)
            pygame.draw.rect(surf, (255, 90, 90), (bx, by, w, 4))
            pygame.draw.rect(surf, (110, 240, 120), (bx, by, int(w * self.hp / self.maxhp), 4))


class Ufo:
    """Bonusinis skraidantis šaudyklė - nušovus iškrenta prizas ir monetos."""
    PAL = [(120, 230, 255), (255, 255, 200), (255, 255, 255)]

    def __init__(self):
        self.dir = random.choice([-1, 1])
        self.x = -40.0 if self.dir == 1 else W + 40.0
        self.y = 80.0
        self.hp = self.maxhp = 3
        self.t = 0
        self.flash = 0
        self.gone = False

    def rect(self):
        return pygame.Rect(int(self.x) - 32, int(self.y) - 16, 64, 32)

    def update(self, g):
        self.t += 1
        self.x += self.dir * 2.6
        self.y = 80 + math.sin(self.t * 0.06) * 12
        if self.flash > 0:
            self.flash -= 1
        if self.x < -70 or self.x > W + 70:
            self.gone = True

    def draw(self, surf, g):
        gfx.add_glow(surf, self.x, self.y + 16, 30, (40, 160, 220))
        img = (S.ufo_flash if self.flash > 0 else S.ufo)[(self.t // 10) % 2]
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class Boss:
    """Trys skirtingi bosai (rūšis keičiasi ciklu):
    0 Motinlaivis - nutaikyti šūviai, spinduliai, lietus;
    1 Kosmoso akis - lazerio spindulys, spiralė, vėduoklė;
    2 Megarobotas - žiedų salvės, meteorų lietus, smūgis žemyn."""

    def __init__(self, level, hp_scale=1.0):
        self.level = level
        self.kind = (level - 1) % 3
        self.name = gfx.BOSS_NAMES[self.kind]
        self.pal = gfx.BOSS_PALS[self.kind]
        self.maxhp = int((40 + 22 * level) * hp_scale)
        self.hp = self.maxhp
        self.x, self.y = W / 2, -130.0
        self.t = 0
        self.mt = 0                 # judėjimo laikas (stoja smūgio metu)
        self.state = "enter"
        self.flash = 0
        self.atk = 80
        self.pat = 0
        self.dying = 0
        self.sched = []             # atidėti veiksmai [kadrai, vardas, argumentas]
        self.beam = None            # lazerio spindulys {"x", "t"}
        self.dash = None            # None / "down" / "up"
        self.dash_x = W / 2
        self.marks = [[0.66, False], [0.33, False]]

    @property
    def rage(self):
        return 1.0 + (1.0 - self.hp / self.maxhp) * 0.9

    def rect(self):
        return pygame.Rect(int(self.x) - 95, int(self.y) - 55, 190, 110)

    def beam_rect(self):
        if self.beam is not None and self.beam["t"] >= 45:
            return pygame.Rect(int(self.beam["x"]) - 22, 50, 44, H - 50)
        return None

    def base_pos(self):
        r = self.rage
        return (W / 2 + math.sin(self.mt * 0.012 * r) * (W / 2 - 150),
                110 + math.sin(self.mt * 0.03) * 14)

    def clear_attacks(self):
        self.sched = []
        self.beam = None
        self.dash = None

    def update(self, g):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        if self.state == "enter":
            self.y += 2.0
            if self.y >= 110:
                self.y = 110.0
                self.state = "fight"
            return
        if self.state == "dying":
            self.dying += 1
            self.x += math.sin(self.t * 0.9) * 2.0
            if self.dying % 4 == 0:
                g.boss_death_fx(self)
            if self.dying >= 100:
                g.boss_finish(self)
            return

        self.run_sched(g)
        bx, by = self.base_pos()
        if self.dash is None:
            self.mt += 1
            self.x, self.y = bx, by
            self.atk -= 1
            if self.atk <= 0 and not g.dead:
                self.attack(g)
                self.atk = int(random.randint(55, 85) / self.rage)
        elif self.dash == "down":
            self.y += 9
            self.x += (self.dash_x - self.x) * 0.08
            if self.y >= H - 250:
                self.dash = "up"
        else:
            self.y -= 6
            self.x += (bx - self.x) * 0.08
            if self.y <= by + 2:
                self.dash = None
        if self.beam is not None:
            self.beam["t"] += 1
            if self.beam["t"] >= 80:
                self.beam = None

        frac = self.hp / self.maxhp
        for m in self.marks:
            if not m[1] and frac < m[0]:
                m[1] = True
                g.spawn_minions(self.x, self.y + 40, 4)

    # --- atidėti veiksmai --------------------------------------------------
    def run_sched(self, g):
        keep = []
        for item in self.sched:
            item[0] -= 1
            if item[0] <= 0:
                getattr(self, "do_" + item[1])(g, item[2])
            else:
                keep.append(item)
        self.sched = keep

    def do_ring(self, g, off):
        n = 10
        for i in range(n):
            ang = off + i * 6.283 / n
            g.ebullets.append(EBullet(self.x, self.y + 30, math.cos(ang) * 3.2, math.sin(ang) * 3.2))

    def do_meteor(self, g, _):
        g.ebullets.append(EBullet(random.uniform(40, W - 40), 54, 0, random.uniform(4.2, 6.0)))

    # --- atakos -------------------------------------------------------------
    def attack(self, g):
        p = self.pat % 3
        self.pat += 1
        if self.kind == 0:
            self.attack_mothership(g, p)
        elif self.kind == 1:
            self.attack_eye(g, p)
        else:
            self.attack_robot(g, p)

    def attack_mothership(self, g, p):
        if p == 0:                                  # nutaikytas šūvis
            base = math.atan2(g.py - self.y, g.px - self.x)
            for a in (-0.28, 0.0, 0.28):
                ang = base + a
                g.ebullets.append(EBullet(self.x, self.y + 50,
                                          math.cos(ang) * 5.2, math.sin(ang) * 5.2))
        elif p == 1:                                # spinduliai į visas puses
            n = 14
            off = random.random() * 6.283
            for i in range(n):
                ang = off + i * 6.283 / n
                g.ebullets.append(EBullet(self.x, self.y + 20,
                                          math.cos(ang) * 3.4, math.sin(ang) * 3.4))
        else:                                       # kulkų lietus iš kanonų
            for dx in (-80, -40, 0, 40, 80):
                g.ebullets.append(EBullet(self.x + dx, self.y + 55, 0, 4.6))

    def attack_eye(self, g, p):
        if p == 0 and self.beam is None:            # lazerio spindulys su įspėjimu
            self.beam = {"x": max(60, min(W - 60, g.px)), "t": 0}
            g.a.sfx("warn")
        elif p <= 1:                                # spiralė
            off = random.random() * 6.283
            for i in range(18):
                ang = off + i * 0.38
                sp = 2.2 + i * 0.12
                g.ebullets.append(EBullet(self.x, self.y + 30,
                                          math.cos(ang) * sp, math.sin(ang) * sp))
        else:                                       # vėduoklė į žaidėją
            base = math.atan2(g.py - self.y, g.px - self.x)
            for k in range(-2, 3):
                ang = base + k * 0.2
                g.ebullets.append(EBullet(self.x, self.y + 40,
                                          math.cos(ang) * 4.8, math.sin(ang) * 4.8))

    def attack_robot(self, g, p):
        if p == 0:                                  # žiedų salvės
            for i in range(4):
                self.sched.append([i * 14 + 1, "ring", i * 0.28])
        elif p == 1:                                # meteorų lietus
            for i in range(10):
                self.sched.append([i * 8 + 1, "meteor", 0])
        else:                                       # smūgis žemyn
            self.dash = "down"
            self.dash_x = max(100, min(W - 100, g.px))
            g.a.sfx("warn")

    # --- piešimas -----------------------------------------------------------
    def draw(self, surf, g):
        if self.beam is not None:
            bx = int(self.beam["x"])
            t = self.beam["t"]
            if t < 45:
                if (t // 4) % 2 == 0:
                    pygame.draw.rect(surf, (255, 60, 60), (bx - 3, 50, 6, H - 50))
                gfx.draw_text(surf, "!", 34, (255, 230, 90), (bx, 72), "center", 3)
            else:
                pygame.draw.rect(surf, (255, 120, 60), (bx - 22, 50, 44, H - 50))
                pygame.draw.rect(surf, (255, 240, 150), (bx - 14, 50, 28, H - 50))
                pygame.draw.rect(surf, (255, 255, 255), (bx - 6, 50, 12, H - 50))
        gfx.add_glow(surf, self.x, self.y, 130, tuple(c // 3 for c in self.pal[0]))
        img = (S.boss_flash if self.flash > 0 else S.boss)[self.kind][(self.t // 15) % 2]
        r = img.get_rect(center=(int(self.x), int(self.y + 30)))
        surf.blit(img, r)
        gfx.draw_pupils(surf, r.topleft, gfx.BOSS_EYES[self.kind], self.x, self.y, g.px, g.py)
