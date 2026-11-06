# -*- coding: utf-8 -*-
"""Vaizdo efektai: sprogimai, kibirkštys, dūmai, šukės, bangos, parallax fonas."""
import math
import random

import pygame

from . import settings as cfg
from .settings import W, H, OUT
from . import gfx

DEFAULT_PAL = [(255, 150, 50), (255, 230, 80), (255, 255, 255)]
MAX_FX = 700


def step_list(lst):
    """Atnaujina efektų sąrašą ir pašalina pasibaigusius."""
    lst[:] = [f for f in lst if f.update()]


class Flash:
    """Šviesos blyksnis (additive)."""

    def __init__(self, x, y, radius, color, life=6):
        self.x, self.y, self.radius, self.color = x, y, radius, color
        self.life = self.max = life

    def update(self):
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        k = self.life / self.max
        r = max(8, int(self.radius * (0.4 + 0.6 * k)) // 4 * 4)
        gfx.add_glow(surf, self.x, self.y, r, self.color)


class Spark:
    def __init__(self, x, y, vx, vy, life, color, size, grav=0.0, drag=0.96):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.size, self.grav, self.drag = color, size, grav, drag

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= self.drag
        self.vy = self.vy * self.drag + self.grav
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        r = self.size * self.life / self.max
        if r >= 1:
            p = (int(self.x), int(self.y))
            pygame.draw.circle(surf, OUT, p, int(r) + 2)
            pygame.draw.circle(surf, self.color, p, int(r))


class Puff:
    """Cartoon dūmų debesėlis."""

    def __init__(self, x, y, r, life, vx, vy, c0, c1):
        self.x, self.y, self.r = x, y, r
        self.life = self.max = life
        self.vx, self.vy, self.c0, self.c1 = vx, vy, c0, c1

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        k = 1 - self.life / self.max
        rad = int(self.r * (0.5 + 1.1 * math.sin(min(1.0, k) * math.pi)))
        if rad < 2:
            return
        p = (int(self.x), int(self.y))
        col = gfx.lerp_col(self.c0, self.c1, k * 1.5)
        pygame.draw.circle(surf, OUT, p, rad + 2)
        pygame.draw.circle(surf, col, p, rad)
        pygame.draw.circle(surf, (255, 255, 255), (p[0] - rad // 3, p[1] - rad // 3), max(1, rad // 4))


class Debris:
    """Besisukančios šukės."""

    def __init__(self, x, y, vx, vy, color, size, life):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.color, self.size = color, size
        self.life = self.max = life
        self.ang = random.uniform(0, 6.283)
        self.spin = random.uniform(-0.4, 0.4)
        self.n = random.choice([3, 4])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.18
        self.vx *= 0.99
        self.ang += self.spin
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        sz = self.size * min(1.0, self.life / 14)
        if sz < 1.5:
            return
        pts = [(self.x + math.cos(self.ang + i * 6.283 / self.n) * sz,
                self.y + math.sin(self.ang + i * 6.283 / self.n) * sz) for i in range(self.n)]
        pygame.draw.polygon(surf, self.color, pts)
        pygame.draw.polygon(surf, OUT, pts, 2)


class Ring:
    """Sprogimo smūgio banga."""

    def __init__(self, x, y, size=1.0, color=(255, 255, 255), life=24):
        self.x, self.y, self.size, self.color = x, y, size, color
        self.life = self.max = life

    def update(self):
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        k = 1 - self.life / self.max
        r = int((10 + 60 * k) * self.size)
        w = max(1, int(6 * (1 - k) * min(self.size, 1.5)) + 1)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r, w)


class Burst:
    """Spygliuota cartoon sprogimo žvaigždė."""

    def __init__(self, x, y, size, pal):
        self.x, self.y, self.size, self.pal = x, y, size, pal
        self.t = 0

    def update(self):
        self.t += 1
        return self.t < 14

    def draw(self, surf):
        t = self.t
        k = t / 14
        r = (18 + 40 * k) * self.size
        n = 12
        pts = []
        for i in range(n * 2):
            a = i * math.pi / n + t * 0.1
            rr = r if i % 2 == 0 else r * 0.55
            pts.append((self.x + math.cos(a) * rr, self.y + math.sin(a) * rr))
        pygame.draw.polygon(surf, self.pal[1] if t < 9 else self.pal[0], pts)
        pygame.draw.polygon(surf, OUT, pts, 3)
        core = max(1, int(r * 0.5 * (1 - k * 0.5)))
        pygame.draw.circle(surf, self.pal[2], (int(self.x), int(self.y)), core)


class Popup:
    """Pakilantis tekstas (taškai, pranešimai)."""

    def __init__(self, x, y, text, color=(255, 255, 255), size=22, life=48):
        self.x, self.y, self.text, self.color, self.size = x, y, text, color, size
        self.life = self.max = life

    def update(self):
        self.y -= 0.8
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        img = gfx.text_surf(self.text, self.size, self.color, 2)
        age = self.max - self.life
        if age < 8:
            img = pygame.transform.rotozoom(img, 0, 1.6 - 0.6 * age / 8)
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


def spawn_explosion(fx, x, y, size=1.0, pal=None):
    """Daugiasluoksnis cartoon sprogimas."""
    if len(fx) > MAX_FX:
        size *= 0.6
    pal = pal or DEFAULT_PAL
    f = 0.5 if cfg.LOW_FX else 1.0
    fx.append(Flash(x, y, int(70 * size), (255, 200, 90), 8))
    fx.append(Burst(x, y, size, pal))
    fx.append(Ring(x, y, size, pal[2]))
    for _ in range(int((int(9 * size) + 4) * f)):
        a = random.uniform(0, 6.283)
        sp = random.uniform(1.5, 6.5) * size ** 0.5
        fx.append(Debris(x, y, math.cos(a) * sp, math.sin(a) * sp - 1.5,
                         random.choice(pal[:2]), random.uniform(4, 8) * size ** 0.5,
                         random.randint(26, 44)))
    for _ in range(int((int(10 * size) + 6) * f)):
        a = random.uniform(0, 6.283)
        sp = random.uniform(2, 8) * size ** 0.5
        fx.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(14, 26),
                        random.choice(pal), random.uniform(3, 6) * size ** 0.5, 0.05))
    for _ in range(int(3 * size) + 2):
        a = random.uniform(0, 6.283)
        sp = random.uniform(0.5, 2.2)
        fx.append(Puff(x, y, random.uniform(10, 16) * size ** 0.6, random.randint(26, 40),
                       math.cos(a) * sp, math.sin(a) * sp - 0.4, pal[1], (150, 140, 170)))


def spawn_hit(fx, x, y, pal=None, n=5):
    """Mažas pataikymo efektas."""
    pal = pal or DEFAULT_PAL
    fx.append(Flash(x, y, 20, (255, 230, 150), 3))
    for _ in range(n):
        a = random.uniform(0, 6.283)
        sp = random.uniform(1.5, 4.5)
        fx.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(8, 14),
                        random.choice(pal), random.uniform(2.5, 4)))


# ----------------------------------------------------------------------------
#  Parallax fonas
# ----------------------------------------------------------------------------
class Parallax:
    def __init__(self):
        self.t = 0
        self.stars = [[random.uniform(0, W), random.uniform(0, H),
                       random.choice([0.35, 0.7, 1.2, 2.0]), random.random() * 6.28]
                      for _ in range(115)]
        self.comets = []
        self.theme = -1
        self.bg = None
        self.neb = []
        self.neb_y = [0.0, 0.0]
        self.planets = []
        self.set_theme(0)

    def set_theme(self, i):
        i %= len(gfx.THEMES)
        if i == self.theme:
            return
        self.theme = i
        self.bg = gfx.make_background(i)
        self.neb = [gfx.make_nebula(i, 1), gfx.make_nebula(i, 2)]
        n = len(gfx.S.planets)
        self.planets = []
        for k in range(2):
            img = gfx.S.planets[(i * 2 + k) % n]
            self.planets.append([random.uniform(120, W - 120), -100 - k * 380,
                                 0.22 + 0.12 * k, img])

    def update(self):
        self.t += 1
        self.neb_y[0] = (self.neb_y[0] + 0.25) % H
        self.neb_y[1] = (self.neb_y[1] + 0.55) % H
        for p in self.planets:
            p[1] += p[2]
            if p[1] > H + 180:
                p[1] = -200
                p[0] = random.uniform(100, W - 100)
        for s in self.stars:
            s[1] += s[2]
            if s[1] > H + 4:
                s[1] = -4
                s[0] = random.uniform(0, W)
        if random.random() < 0.004 and len(self.comets) < 2:
            self.comets.append([random.uniform(150, W), -20, -random.uniform(4, 6),
                                random.uniform(5, 8)])
        for c in self.comets[:]:
            c[0] += c[2]
            c[1] += c[3]
            if c[1] > H + 40 or c[0] < -40:
                self.comets.remove(c)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        if not cfg.LOW_FX:                          # permatomi ūkų sluoksniai - sunkūs silpniems įrenginiams
            for i, n in enumerate(self.neb):
                y = int(self.neb_y[i])
                surf.blit(n, (0, y))
                surf.blit(n, (0, y - H))
        for x, y, _, img in self.planets:
            surf.blit(img, img.get_rect(center=(int(x), int(y))))
        for x, y, sp, ph in self.stars:
            c = int(170 + 80 * math.sin(self.t * 0.05 + ph))
            col = (c, c, 255)
            if sp < 0.5:
                surf.set_at((int(x) % W, int(y) % H), col)
            elif sp < 1.0:
                pygame.draw.circle(surf, col, (int(x), int(y)), 1)
            else:
                pygame.draw.circle(surf, col, (int(x), int(y)), 2)
                if sp > 1.5:
                    pygame.draw.line(surf, col, (x - 4, y), (x + 4, y), 1)
                    pygame.draw.line(surf, col, (x, y - 4), (x, y + 4), 1)
        for cx, cy, vx, vy in self.comets:
            for i in range(9):
                k = i / 9
                pygame.draw.circle(surf, (255, int(255 - 120 * k), int(210 - 110 * k)),
                                   (int(cx - vx * i * 1.6), int(cy - vy * i * 1.6)),
                                   max(1, int(5 * (1 - k))))
