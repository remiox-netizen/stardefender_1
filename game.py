# -*- coding: utf-8 -*-
"""Pagrindinė žaidimo logika: laivai, bangos, bosai, bonuso etapai, kombo, pavojai, prizai."""
import math
import random

import pygame

from .settings import W, H, OUT, START_LIVES, MAX_LIVES, MAX_BOMBS, BOSS_EVERY, SAVE
from . import gfx, progress
from . import settings as cfg
from .gfx import S, draw_text, text_surf
from .effects import (Flash, Spark, Ring, Puff, Popup, spawn_explosion, spawn_hit,
                      step_list)
from .entities import (Bullet, EBullet, Power, Enemy, Ufo, Boss, Coin, Asteroid)


def clamp(v, a, b):
    return max(a, min(b, v))


# Parduotuvė: (raktas, pavadinimas, aprašymas, kainos pagal lygį arba None)
SHOP = [
    ("rate", "Šaudymo greitis", "Ginklas šauna greičiau", [30, 50, 80]),
    ("cool", "Aušinimas", "Maksimalus ginklas kaista lėčiau", [30, 50, 70]),
    ("speed", "Laivo greitis", "Laivas juda greičiau", [25, 40, 60]),
    ("magnet", "Monetų magnetas", "Traukia monetas ir prizus iš toliau", [20, 35, 50]),
    ("life", "Papildoma gyvybė", "+1 gyvybė", None),
    ("bomb", "Bomba", "+1 bomba (maks. %d)" % MAX_BOMBS, None),
    ("shield", "Skydas", "Skydas 10 sekundžių", None),
]

SHAPES = ["grid", "sine", "zigzag", "vee", "diamond", "columns", "checker", "scatter",
          "wedge", "rings", "chevrons", "arch"]

# Bangų tipai: formacija arba scenarijus (priešai skrenda trajektorijomis)
WAVE_TYPES = {"formation": 2.0, "drop": 2.2, "lanes": 1.6, "ring": 1.6, "orbit": 1.2, "stream": 2.0}
WAVE_MIN = {"formation": 1, "drop": 2, "lanes": 2, "stream": 2, "ring": 3, "orbit": 4}
WAVE_TAGS = {"formation": "Priešų formacija", "drop": "Atakos iš viršaus!",
             "lanes": "Žemyn slenkančios eilės", "ring": "Apsupimas!",
             "orbit": "Orbitos - sunaikink šerdį!", "stream": "Srautai"}
SCRIPTED = ("drop", "lanes", "ring", "orbit", "stream")

# Bonuso etapas: (kadras, trajektorija, fazė)
BONUS_SCHEDULE = [(40, "wave", 0.0), (260, "loop", 0.0), (480, "cross", 1.0),
                  (700, "cross", -1.0), (920, "wave", 3.14159)]


class Game:
    def __init__(self, audio, plx, ship=0):
        self.a = audio
        self.plx = plx
        self.ship = ship if progress.ship_unlocked(SAVE, ship) else 0
        self.sdef = progress.SHIPS[self.ship]
        self.run = progress.new_run()
        self.committed = False
        self.new_ach = []
        self.toasts = []
        self.score = 0
        self.shown = 0.0
        self.lives = START_LIVES
        self.wave = 0
        self.nwave = 0
        self.bombs = 1
        self.gold = 0
        self.up = {"rate": 0, "cool": 0, "speed": 0, "magnet": 0, "life": 0}
        self.adapt = 0.0                 # prisitaikantis sunkumas (-0.6 .. 1.6)
        self.wave_t0 = 0
        self.wave_hits = 0
        self.heat = 0.0                  # maksimalaus ginklo temperatūra (0..100)
        self.overheated = False
        self.wtype = "formation"         # dabartinės bangos tipas
        self.last_wtype = ""
        self.nonform_streak = 0
        self.recent_shapes = []
        self.wt_t = 0
        self.wave_span = 0
        self.escaped = 0
        self.wcount9 = 0
        self.banner_tag = ""
        self.shop_pending = False
        self.pending_bonus = False
        self.bonus = None
        self.coins = []
        self.coin_cd = 0
        self.asteroids = []
        self.haz_timer = 700
        self.shower_left = 0
        self.shower_timer = 0
        self.graze_cd = 0
        self.graze_n = 0
        self.boss_hit_taken = False
        self.px, self.py = W / 2, H - 80.0
        self.pvx = 0.0
        self.weapon = 1
        self.cool = 0
        self.shield = 0
        self.inv = 0
        self.bullets, self.ebullets, self.enemies = [], [], []
        self.ufos, self.powers = [], []
        self.boss = None
        self.fx, self.pops = [], []
        self.shake = 0
        self.flash = 0
        self.flash_col = (255, 255, 255)
        self.hitstop = 0
        self.banner = 0
        self.banner_text = ""
        self.banner_sub = ""
        self.banner_kind = "normal"
        self.dead = False
        self.dead_timer = 0
        self.over = False
        self.t = 0
        self.clear_timer = 0
        self.combo = 0
        self.combo_t = 0
        self.max_combo = 0
        self.kills = 0
        self.ufo_timer = random.randint(700, 1100)
        self.ox = self.oy = 0.0
        self.dir = 1
        self.total = 1
        self.shoot_timer = 100
        self.dive_timer = 300
        self.hit_cd = 0
        self._flash_surf = pygame.Surface((W, H))
        self._panel = pygame.Surface((W, 48), pygame.SRCALPHA)
        self._panel.fill((10, 5, 40, 175))
        pygame.draw.line(self._panel, (120, 100, 220), (0, 46), (W, 46), 2)
        self.next_wave()

    @property
    def magnet_r(self):
        return 130 + 50 * self.up["magnet"]

    # ------------------------------------------------------------------
    #  Sunkumas
    # ------------------------------------------------------------------
    def hp_bonus(self):
        """Papildomos priešų gyvybės: auga su banga ir su žaidėjo galia."""
        b = 0
        if self.wave >= 8:
            b += 1
        if self.wave >= 14:
            b += 1
        if self.wave >= 20:
            b += 1
        if self.adapt >= 1.2:
            b += 2
        elif self.adapt >= 0.6:
            b += 1
        return b

    def threat_level(self):
        thr = 0.3 * self.wave + 2.0 * self.adapt
        return int(clamp(int(thr / 1.2) + 1, 1, 5))

    def adapt_difficulty(self):
        """Po bangos: greitai ir be nuostolių išvalei - sunkumas kyla; daug smūgių - kiek nukrenta."""
        dur = self.t - self.wave_t0 - self.wave_span
        target = 1500 + 50 * min(self.wave, 20)
        hits = self.wave_hits
        old = self.adapt
        if hits == 0 and dur < 0.55 * target:
            self.adapt += 0.25
        elif hits == 0 and dur < 0.8 * target:
            self.adapt += 0.12
        elif hits <= 1 and dur < 0.6 * target:
            self.adapt += 0.08
        if hits >= 2:
            self.adapt -= 0.075 * min(hits, 6)
        self.adapt = clamp(self.adapt, -0.6, 1.6)
        d = self.adapt - old
        if d >= 0.1:
            self.pops.append(Popup(W / 2, 150, "PRIEŠAI STIPRĖJA!", (255, 110, 110), 28, 90))
        elif d <= -0.1:
            self.pops.append(Popup(W / 2, 150, "Sunkumas sumažėjo", (150, 255, 170), 24, 80))

    # ------------------------------------------------------------------
    #  Pasiekimai
    # ------------------------------------------------------------------
    def check_ach(self):
        for a in progress.check(SAVE, self.run):
            si = progress.ship_for_achievement(a["id"])
            sub = ("Atrakintas laivas: %s" % progress.SHIPS[si]["name"]) if si is not None else a["desc"]
            self.toasts.append(["PASIEKIMAS: %s" % a["name"], sub, 190])
            self.new_ach.append(a["name"])
            self.a.sfx("ach")

    def commit(self):
        """Išsaugo žaidimo statistiką (kviečiama vieną kartą)."""
        if not self.committed:
            self.committed = True
            progress.commit_run(SAVE, self.run)
            self.check_ach()

    # ------------------------------------------------------------------
    #  Bangos ir formacijos
    # ------------------------------------------------------------------
    def formation_slots(self, shape=None):
        """Atsitiktinė formacijos kompozicija: forma, dydis, tarpai ir properšos kiekvieną kartą kitokie."""
        w = self.wave
        if shape is None:
            pool = [x for x in SHAPES if x not in self.recent_shapes[-3:]]
            shape = random.choice(pool)
        self.recent_shapes.append(shape)
        extra = 1 if self.adapt >= 0.5 else 0
        slots = []
        if shape in ("grid", "sine", "zigzag"):
            cols = random.choice([6, 7, 8, 9])
            spx = min(76, (W - 150) // (cols - 1))
            cap = 5 + (1 if (w >= 10 or self.adapt >= 0.8) else 0)
            rows = min(3 + w // 2 + extra, cap)
            if cols <= 6:
                rows = min(rows + 1, cap + 1)
            spy = 56 if rows <= 5 else 50
            x0 = (W - (cols - 1) * spx) / 2
            amp, fr, ph = random.uniform(14, 34), random.uniform(0.6, 1.2), random.uniform(0, 6.28)
            for r in range(rows):
                for c in range(cols):
                    bx, by = x0 + c * spx, 100 + r * spy
                    if shape == "sine":
                        by += amp * math.sin(c * fr + ph)
                    if shape == "zigzag" and r % 2 == 1:
                        if c == cols - 1:
                            continue
                        bx += spx / 2
                    slots.append((bx, by))
        elif shape == "vee":
            n = random.choice([3, 4, 5])
            layers = min(4, 2 + (1 if w >= 8 else 0) + (1 if w >= 14 else 0) + (1 if self.adapt >= 0.8 else 0))
            step = random.randint(26, 36)
            sp = min(70, (W - 150) // (2 * n))
            invert = random.random() < 0.3
            for layer in range(layers):
                for i in range(-n, n + 1):
                    depth = abs(i) if invert else (n - abs(i))
                    slots.append((W / 2 + i * sp, 96 + layer * 54 + depth * step))
        elif shape == "diamond":
            m = random.choice([3, 4, 4])
            counts = list(range(1, 2 * m, 2)) + list(range(2 * m - 3, 0, -2))
            sp, rs = random.randint(60, 68), random.randint(42, 48)
            for r, n in enumerate(counts):
                for j in range(n):
                    slots.append((W / 2 + (j - (n - 1) / 2) * sp, 96 + r * rs))
        elif shape == "columns":
            nc = random.choice([4, 5, 6])
            sp = min(130, (W - 160) // (nc - 1))
            rows = 5 + (1 if w >= 10 else 0)
            step = 50 if rows <= 5 else 45
            for c in range(nc):
                for r in range(rows):
                    slots.append((W / 2 + (c - (nc - 1) / 2) * sp, 96 + r * step))
        elif shape == "checker":
            cols, rows = random.choice([8, 9]), random.choice([5, 6])
            sp = min(70, (W - 150) // (cols - 1))
            x0 = (W - (cols - 1) * sp) / 2
            for r in range(rows):
                for c in range(cols):
                    if (r + c) % 2 == 0:
                        slots.append((x0 + c * sp, 100 + r * 48))
        elif shape == "scatter":
            n = min(30, 18 + w // 2 + (3 if self.adapt >= 0.5 else 0))
            tries = 0
            while len(slots) < n and tries < 600:
                tries += 1
                x, y = random.uniform(70, W - 70), random.uniform(96, 300)
                if all((x - a) ** 2 + (y - b) ** 2 >= 62 ** 2 for a, b in slots):
                    slots.append((x, y))
        elif shape == "wedge":
            counts = [9, 7, 5, 3, 1]
            if random.random() < 0.5:
                counts.reverse()
            for r, n in enumerate(counts):
                for j in range(n):
                    slots.append((W / 2 + (j - (n - 1) / 2) * 66, 96 + r * 50))
        elif shape == "rings":
            ph = random.uniform(0, 6.28)
            slots.append((W / 2, 200.0))
            for n, rx, ry in ((7, 95, 62), (13, 190, 118)):
                for k in range(n):
                    a = k * 6.283 / n + ph
                    slots.append((W / 2 + math.cos(a) * rx, 200 + math.sin(a) * ry))
        elif shape == "chevrons":
            k = 3 + (1 if w >= 8 else 0)
            for layer in range(k):
                for i in range(-3, 4):
                    slots.append((W / 2 + i * 72, 96 + layer * 58 + (3 - abs(i)) * 22))
        else:                                       # arch
            for n, R in ((11, 270), (7, 190)):
                for k in range(n):
                    a = math.pi + k * math.pi / (n - 1)
                    slots.append((W / 2 + math.cos(a) * R, 330 + math.sin(a) * R * 0.9))
        slots = [(min(W - 50, max(50, x)), y) for x, y in slots]
        if shape != "scatter" and len(slots) > 14:  # atsitiktinės properšos
            for _ in range(int(len(slots) * random.uniform(0, 0.15))):
                slots.pop(random.randrange(len(slots)))
        if len(slots) > 40:
            random.shuffle(slots)
            slots = slots[:40]
        return shape, slots

    def build_formation(self):
        shape, slots = self.formation_slots()
        ys = [y for _, y in slots]
        lo, hi = min(ys), max(ys)
        span = max(1.0, hi - lo)
        w = self.wave
        avail = []
        if w >= 3:
            avail.append(3)                         # kamikadzės
        if w >= 4:
            avail.append(5)                         # skylantys
        if w >= 5:
            avail.append(6)                         # skydininkai
        if w >= 6:
            avail += [4, 7]                         # šarvuoti, regeneratoriai
        if w >= 7:
            avail.append(8)                         # šokliukai
        if w >= 8:
            avail.append(9)                         # gydytojai
        caps = {9: 2 + (1 if w >= 15 else 0)}
        counts = {}
        prob = min(0.34, 0.05 * w + 0.05 * max(self.adapt, 0.0))
        hpb = self.hp_bonus()
        for bx, by in slots:
            rank = (by - lo) / span
            kind = 2 if rank < 0.2 else (1 if rank < 0.55 else 0)
            if rank > 0.1 and avail and random.random() < prob:
                k = random.choice(avail)
                if counts.get(k, 0) < caps.get(k, 99):
                    kind = k
                    counts[k] = counts.get(k, 0) + 1
            delay = int(rank * 50) + int(abs(bx - W / 2) / 20)
            self.enemies.append(Enemy(int(bx), int(by), kind, bx, by, delay, hpb))
        self.total = len(self.enemies)

    # ------------------------------------------------------------------
    #  Bangų tipai: scenarijai (priešai skrenda trajektorijomis)
    # ------------------------------------------------------------------
    def pick_wave_type(self):
        if self.nwave <= 1:
            return "formation"
        if self.nonform_streak >= 2:
            return "formation"
        types = [t for t in WAVE_TYPES if WAVE_MIN[t] <= self.wave and t != self.last_wtype]
        if not types:
            return "formation"
        return random.choices(types, [WAVE_TYPES[t] for t in types])[0]

    def avail_kinds(self):
        w, a = self.wave, []
        if w >= 4:
            a.append(5)
        if w >= 5:
            a.append(6)
        if w >= 6:
            a += [4, 7]
        if w >= 7:
            a.append(8)
        if w >= 8:
            a.append(9)
        return a

    def random_kind(self):
        r = random.random()
        k = 0 if r < 0.5 else (1 if r < 0.82 else 2)
        av = self.avail_kinds()
        if av and random.random() < min(0.34, 0.05 * self.wave + 0.05 * max(self.adapt, 0.0)):
            c = random.choice(av)
            cap9 = 2 + (1 if self.wave >= 15 else 0)
            if c != 9 or self.wcount9 < cap9:
                k = c
                if c == 9:
                    self.wcount9 += 1
        return k

    def fire_rate(self, base):
        """Dalis scenarijaus priešų šaudo (retkarčiais)."""
        if random.random() < min(0.6, 0.2 + 0.03 * self.wave):
            return max(60, int(base / (1.0 + 0.3 * max(self.adapt, 0.0))))
        return 0

    def build_scripted(self, wt):
        hpb = self.hp_bonus()
        fn = {"drop": self.script_drop, "lanes": self.script_lanes, "ring": self.script_ring,
              "orbit": self.script_orbit, "stream": self.script_stream}[wt]
        en = fn(hpb)
        self.enemies.extend(en)
        self.wave_span = max([e.bdelay for e in en] + [60])
        self.total = max(1, len(en))

    def script_drop(self, hpb):
        """Grupės pasirodo iš viršaus ir leidžiasi žemyn savo trajektorijomis."""
        w, ad = self.wave, max(self.adapt, 0.0)
        out, t = [], 30
        for _ in range(min(12, int(5 + w * 0.35 + ad * 2.5))):
            cnt = random.randint(4, 6) + (1 if ad >= 0.8 else 0)
            kind = self.random_kind()
            mixed = random.random() < 0.25
            shape = random.choice(["line", "vee", "pair"])
            pat = random.choice(["drop", "diag", "zig"])
            vy = min(3.4, random.uniform(2.0, 2.8) + 0.04 * w + 0.3 * ad)
            offmax = 20 * cnt if shape == "vee" else 30
            if pat == "diag":
                side = random.choice([-1, 1])
                pp = dict(x0=-40.0 if side > 0 else W + 40.0, dx=side * random.uniform(1.4, 2.4), vy=vy * 0.9)
            else:
                A = random.uniform(30, 110) if pat == "drop" else random.uniform(120, 200)
                lo, hi = A + offmax - 10, W + 10 - A - offmax
                x0 = random.uniform(lo, hi) if lo < hi else W / 2
                if pat == "drop":
                    pp = dict(x0=x0, A=A, w=random.uniform(0.03, 0.06), ph=random.uniform(0, 6.28), vy=vy)
                else:
                    pp = dict(x0=x0, A=A, w=random.uniform(0.04, 0.055), vy=vy)
            fe = self.fire_rate(150)
            for i in range(cnt):
                k = self.random_kind() if mixed else kind
                if shape == "line":
                    delay, off = t + i * 11, (0.0, 0.0)
                elif shape == "vee":
                    j = i - (cnt - 1) / 2
                    delay, off = t, (j * 38, -abs(j) * 30)
                else:
                    delay, off = t + (i // 2) * 13, ((-22.0 if i % 2 == 0 else 22.0), 0.0)
                out.append(Enemy.pathed(k, pat, pp, delay, hpb, off, fe))
            t += random.randint(85, 125)
        return out

    def script_lanes(self, hpb):
        """Eilės priešų slenka žemyn juostomis su properšomis - pasirink, kur lįsti."""
        w, ad = self.wave, max(self.adapt, 0.0)
        lanes = random.choice([5, 6, 7])
        rows = random.randint(6, 8) + (1 if ad >= 0.8 else 0)
        xs = [90 + i * (620 / (lanes - 1)) for i in range(lanes)]
        gap = max(46, int(random.uniform(60, 80) / (1 + 0.15 * ad)))
        vy = min(2.6, 1.3 + 0.07 * w + 0.3 * ad)
        drift = random.choice([0, 0, 16, 26])
        ph = random.uniform(0, 6.28)
        out, t = [], 40
        for _ in range(rows):
            holes = random.sample(range(lanes), random.randint(1, max(1, lanes // 2)))
            for li, x in enumerate(xs):
                if li in holes:
                    continue
                fe = self.fire_rate(160) if random.random() < 0.3 else 0
                pp = dict(x0=x, A=drift, w=0.03, ph=ph, vy=vy)
                out.append(Enemy.pathed(self.random_kind(), "drop", pp, t + random.randint(0, 6), hpb,
                                        (0.0, 0.0), fe))
            t += gap
        return out

    def script_ring(self, hpb):
        """Apsupimas: priešai įskrenda iš šonų, apsuka ekraną ir išskrenda žemyn."""
        w, ad = self.wave, max(self.adapt, 0.0)
        streams = 2 + (1 if (w >= 6 or ad >= 0.8) else 0)
        n = random.randint(7, 9) + (1 if ad >= 0.8 else 0)
        cx, cy = W / 2, random.uniform(260, 300)
        rx, ry = random.uniform(280, 320), random.uniform(150, 185)
        ue = 30 + int(224 * random.uniform(1.0, 1.5))
        out, t0 = [], 20
        for s in range(streams):
            sc = 1.0 if s < 2 else 0.62
            rxe = rx * sc
            pp = dict(cx=cx, cy=cy, rx=rxe, ry=ry * sc, a0=math.pi if s % 2 == 0 else 0.0,
                      dir=random.choice([-1, 1]), ue=ue, k=max(0.7, (cx + 90) / rxe - 1))
            kind, fe = self.random_kind(), self.fire_rate(140)
            for i in range(n):
                out.append(Enemy.pathed(kind, "ring", pp, t0 + i * 9, hpb, (0.0, 0.0), fe))
            t0 += random.randint(60, 90)
        return out

    def script_orbit(self, hpb):
        """Didelė šerdis, aplink kurią sukasi priešų žiedai - sunaikink šerdį."""
        w, ad = self.wave, max(self.adapt, 0.0)
        core = Enemy.make_core(hpb)
        out = [core]
        rings = [(8, 110, 1)]
        if w >= 7 or ad >= 0.8:
            rings.append((12, 165, -1))
        core.ring_radii = [r for _, r, _ in rings]
        for n, rad, d in rings:
            for i in range(n):
                out.append(Enemy.orbiter(self.random_kind(), core, i * 6.283 / n, rad, d * 0.022, hpb))
        return out

    def script_stream(self, hpb):
        """Srautai: zigzagai, spiralės, praskridimai ir įstrižos linijos."""
        w, ad = self.wave, max(self.adapt, 0.0)
        out, t, last = [], 30, ""
        for _ in range(random.randint(4, 6) + (1 if ad >= 0.8 else 0)):
            pat = random.choice([p for p in ("zig", "spiral", "sweep", "diag", "drop") if p != last])
            last = pat
            cnt = random.randint(6, 9)
            vy = min(3.4, random.uniform(2.0, 2.8) + 0.04 * w + 0.3 * ad)
            if pat == "zig":
                A = random.uniform(120, 200)
                pp = dict(x0=random.uniform(A - 10, W + 10 - A), A=A, w=random.uniform(0.04, 0.055), vy=vy)
            elif pat == "spiral":
                pp = dict(cx=random.uniform(250, 550), cy=random.uniform(200, 280),
                          a0=random.choice([math.pi, 0.0, -math.pi / 2]) + random.uniform(-0.3, 0.3),
                          dir=random.choice([-1, 1]), k=1.5)
            elif pat == "sweep":
                pp = dict(vx=random.uniform(3.0, 3.8), dir=random.choice([-1, 1]), y0=random.uniform(130, 300))
            elif pat == "diag":
                side = random.choice([-1, 1])
                pp = dict(x0=-40.0 if side > 0 else W + 40.0, dx=side * random.uniform(1.4, 2.4), vy=vy * 0.9)
            else:
                A = random.uniform(30, 110)
                pp = dict(x0=random.uniform(A + 20, W - A - 20), A=A, w=random.uniform(0.03, 0.06),
                          ph=random.uniform(0, 6.28), vy=vy)
            kind, fe = self.random_kind(), self.fire_rate(150)
            for i in range(cnt):
                out.append(Enemy.pathed(kind, pat, pp, t + i * 9, hpb, (0.0, 0.0), fe))
            t += random.randint(130, 190)
        return out

    def next_wave(self):
        if self.pending_bonus:
            self.pending_bonus = False
            self.start_bonus()
            return
        self.wave += 1
        self.wave_t0 = self.t
        self.wave_hits = 0
        self.wave_span = 0
        self.escaped = 0
        self.wcount9 = 0
        self.wt_t = 0
        self.banner_tag = ""
        self.run["best_wave"] = max(self.run["best_wave"], self.wave)
        theme = (self.wave - 1) // 3
        self.plx.set_theme(theme)
        self.ebullets = []
        self.enemies = []
        self.boss = None
        self.asteroids = []
        self.ox = self.oy = 0.0
        self.dir = 1
        self.shoot_timer = 100
        self.dive_timer = 300
        self.haz_timer = random.randint(500, 900)
        self.shower_left = 0
        self.banner_sub = ""
        if (self.wave - 1) % 3 == 0:
            names = gfx.SECTOR_NAMES
            self.banner_sub = "SEKTORIUS %d: %s" % (theme + 1, names[theme % len(names)])
        if self.wave % BOSS_EVERY == 0:
            self.wtype = "boss"
            self.boss = Boss(self.wave // BOSS_EVERY, 1.0 + 0.3 * max(0.0, self.adapt))
            self.boss_hit_taken = False
            self.total = 1
            self.banner_text = "BOSAS!"
            self.banner_kind = "boss"
            self.banner_sub = self.boss.name
            self.a.sfx("boss_warn")
            self.a.music("boss")
        else:
            self.nwave += 1
            wt = self.pick_wave_type()
            self.nonform_streak = self.nonform_streak + 1 if wt != "formation" else 0
            self.wtype = self.last_wtype = wt
            if wt == "formation":
                self.build_formation()
            else:
                self.build_scripted(wt)
            self.banner_tag = WAVE_TAGS[wt]
            self.banner_text = "BANGA %d" % self.wave
            self.banner_kind = "normal"
            self.a.sfx("wave")
            self.a.music("game1" if self.wave % 2 == 1 else "game2")
            if self.wave % 4 == 2:
                self.shower_left = 8
                self.shower_timer = 120
                self.pops.append(Popup(W / 2, 200, "METEORITŲ LIETUS!", (255, 190, 110), 30, 100))
                self.a.sfx("warn")
        self.banner = 120

    # --- bonuso etapas -------------------------------------------------
    def start_bonus(self):
        self.wtype = "bonus"
        self.bonus = {"t": 0, "total": 0, "killed": 0, "groups": 0}
        self.ebullets = []
        self.enemies = []
        self.ufos = []
        self.boss = None
        self.asteroids = []
        self.banner_text = "BONUSO ETAPAS!"
        self.banner_kind = "bonus"
        self.banner_sub = "Sušaudyk kuo daugiau - papildomos monetos!"
        self.banner = 120
        self.a.sfx("wave")
        self.a.music("bonus")

    def update_bonus(self):
        b = self.bonus
        b["t"] += 1
        if b["groups"] < len(BONUS_SCHEDULE):
            tt, pat, p0 = BONUS_SCHEDULE[b["groups"]]
            if b["t"] >= tt:
                for i in range(8):
                    self.enemies.append(Enemy.bonus(pat, i, 1 if i % 4 == 3 else 0, p0))
                b["total"] += 8
                b["groups"] += 1
        elif not self.enemies:
            self.finish_bonus()

    def finish_bonus(self):
        b = self.bonus
        self.bonus = None
        txt = "BONUSAS: %d/%d" % (b["killed"], b["total"])
        if b["killed"] >= b["total"] > 0:
            self.score += 1000
            self.run["bonus_perfect"] += 1
            txt += "   IDEALU! +1000"
        self.pops.append(Popup(W / 2, H / 2, txt, (110, 255, 200), 30, 110))
        self.a.sfx("power")
        self.next_wave()

    # ------------------------------------------------------------------
    #  Žaidėjas ir ginklai
    # ------------------------------------------------------------------
    def player_rect(self):
        return pygame.Rect(int(self.px) - 16, int(self.py) - 30, 32, 56)

    def drone_pos(self, sx):
        return (self.px + sx * 50 + math.sin(self.t * 0.1) * 3,
                self.py + 8 + math.cos(self.t * 0.08 + sx) * 4)

    def fire(self):
        lv = self.weapon
        x, y = self.px, self.py - 34
        ship = self.ship
        if ship == 1:                                # Šturmas - vėduoklė, trumpas nuotolis
            pats = {1: [(0, 0), (-8, -0.22), (8, 0.22)],
                    2: [(0, 0), (-10, -0.18), (10, 0.18), (-16, -0.36), (16, 0.36)],
                    4: [(0, 0), (-8, -0.14), (8, 0.14), (-14, -0.28), (14, 0.28), (-20, -0.42), (20, 0.42)]}
            shots = pats[1 if lv == 1 else (2 if lv <= 3 else 4)]
            for dx, ang in shots:
                self.bullets.append(Bullet(x + dx, y, math.sin(ang) * 10, -math.cos(ang) * 10, lv, life=42))
            base = [26, 24, 20, 20, 18][lv - 1]
        elif ship == 2:                              # Spindulys - pramušantys šūviai
            streams = {1: [0], 2: [-8, 8], 3: [-8, 8], 4: [0, -12, 12], 5: [0, -12, 12]}[lv]
            pierce = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}[lv]
            for dx in streams:
                self.bullets.append(Bullet(x + dx, y, 0, -14, lv, pierce=pierce))
            base = [14, 13, 12, 10, 9][lv - 1]
        elif ship == 3:                              # Raketa - nukreipiamos raketos
            seeds = {1: [(0, 0)], 2: [(-10, -0.1), (10, 0.1)],
                     3: [(0, 0), (-12, -0.3), (12, 0.3)], 4: [(0, 0), (-12, -0.3), (12, 0.3)],
                     5: [(-8, -0.12), (8, 0.12), (-18, -0.4), (18, 0.4)]}[lv]
            for dx, ang in seeds:
                self.bullets.append(Bullet(x + dx, y, math.sin(ang) * 8.5, -math.cos(ang) * 8.5, lv,
                                           homing=True))
            base = [30, 28, 26, 22, 20][lv - 1]
        else:                                        # Sakalas - klasika
            if lv == 1:
                shots = [(0, 0)]
            elif lv == 2:
                shots = [(-10, 0), (10, 0)]
            elif lv in (3, 4):
                shots = [(0, 0), (-12, -0.18), (12, 0.18)]
            else:
                shots = [(0, 0), (-14, -0.16), (14, 0.16), (-22, -0.34), (22, 0.34)]
            for dx, ang in shots:
                self.bullets.append(Bullet(x + dx, y, math.sin(ang) * 11, -math.cos(ang) * 11, lv))
            base = [24, 20, 18, 12, 12][lv - 1]
        if lv >= 5:                                  # pagalbiniai dronai
            for sx in (-1, 1):
                dx, dy = self.drone_pos(sx)
                self.bullets.append(Bullet(dx, dy - 12, 0, -11, 2))
        self.fx.append(Flash(x, y, 26, (255, 240, 150), 4))
        self.cool = max(4, int(base * self.sdef["cool"] * (1 - 0.12 * self.up["rate"])))
        self.a.sfx("shoot%d" % lv)
        if lv >= 5:                                  # maksimalus ginklas kaista
            self.heat += self.cool * 0.55 * (1 - 0.15 * self.up["cool"])
            if self.heat >= 100:
                self.heat = 100.0
                self.overheated = True
                self.shake = max(self.shake, 8)
                self.pops.append(Popup(self.px, self.py - 60, "PERKAITA!", (255, 110, 80), 26, 60))
                self.a.sfx("overheat")

    def update_heat(self, inp):
        if self.weapon < 5:
            self.heat = max(0.0, self.heat - 0.6)
            self.overheated = False
            return
        if self.overheated:
            self.heat = max(0.0, self.heat - 0.55)
            if self.t % 6 == 0:
                self.fx.append(Puff(self.px + random.uniform(-10, 10), self.py - 20, 8, 30,
                                    random.uniform(-0.3, 0.3), -1.2, (210, 210, 220), (110, 110, 140)))
            if self.heat <= 30:
                self.overheated = False
                self.pops.append(Popup(self.px, self.py - 60, "Atvėso", (150, 230, 255), 20, 40))
                self.a.sfx("cool")
        elif not inp.fire:
            self.heat = max(0.0, self.heat - 0.35)

    def hurt(self):
        if self.dead or self.inv > 0:
            return
        self.wave_hits += 1
        self.combo = 0
        self.combo_t = 0
        if self.shield > 0:
            self.shield = 0
            self.inv = 60
            self.shake = 8
            spawn_explosion(self.fx, self.px, self.py - 10, 0.6,
                            [(120, 190, 255), (220, 240, 255), (255, 255, 255)])
            self.a.sfx("hurt")
            return
        self.lives -= 1
        if self.boss is not None:
            self.boss_hit_taken = True
        self.shake = 18
        self.flash = 150
        self.flash_col = (255, 60, 60)
        if self.lives <= 0:
            self.dead = True
            self.dead_timer = 100
            spawn_explosion(self.fx, self.px, self.py, 2.2)
            self.a.sfx("boom_l")
        else:
            self.inv = 130
            self.weapon = max(1, self.weapon - 1)
            spawn_explosion(self.fx, self.px, self.py, 1.0)
            self.a.sfx("hurt")

    def use_bomb(self):
        if self.bombs <= 0 or self.dead:
            return
        self.bombs -= 1
        self.flash = 255
        self.flash_col = (255, 255, 255)
        self.shake = 22
        self.hitstop = 4
        self.fx.append(Ring(self.px, self.py, 6.0, (255, 240, 150), 30))
        self.fx.append(Flash(self.px, self.py, 160, (255, 220, 120), 12))
        self.a.sfx("bomb")
        for b in self.ebullets:
            spawn_hit(self.fx, b.x, b.y, None, 3)
        self.ebullets = []
        for e in self.enemies[:]:
            if e.y < 0 or e.x < 0 or e.x > W:
                continue
            self.hit_enemy(e, 3, e.x, e.y)
        for u in self.ufos[:]:
            self.hit_ufo(u, 3, u.x, u.y)
        for a in self.asteroids[:]:
            self.hit_asteroid(a, 3, a.x, a.y)
        if self.boss and self.boss.state == "fight":
            self.hit_boss(12, self.boss.x, self.boss.y)

    # ------------------------------------------------------------------
    #  Taškai, kombo, prizai
    # ------------------------------------------------------------------
    def mult(self):
        return min(5, 1 + self.combo // 5)

    def add_score(self, pts, x, y, color=(255, 240, 120)):
        old = self.mult()
        self.combo += 1
        self.combo_t = 150
        self.max_combo = max(self.max_combo, self.combo)
        self.run["best_combo"] = max(self.run["best_combo"], self.combo)
        m = self.mult()
        gain = pts * m
        self.score += gain
        txt = "+%d" % gain if m == 1 else "+%d  x%d" % (gain, m)
        self.pops.append(Popup(x, y - 10, txt, color))
        if m > old:
            self.a.sfx("combo")
            self.pops.append(Popup(W / 2, 120, "KOMBO x%d!" % m, (255, 200, 80), 34, 60))

    def drop_power(self, x, y, force=False, chance=0.15):
        if not force and random.random() >= chance:
            return
        r = random.random() * 100
        kind = "W" if r < 55 else "S" if r < 72 else "B" if r < 88 else "H"
        self.powers.append(Power(x, y, kind))

    def spawn_coins(self, x, y, n):
        for _ in range(n):
            self.coins.append(Coin(x + random.uniform(-10, 10), y + random.uniform(-8, 8)))

    def collect(self, p):
        col = gfx.POWER_COLS[p.kind]
        pal = [col, (255, 255, 255), (255, 255, 255)]
        spawn_hit(self.fx, p.x, p.y, pal, 9)
        self.fx.append(Ring(p.x, p.y, 0.7, col, 18))
        if p.kind == "W":
            self.a.sfx("power")
            if self.weapon < 5:
                self.weapon += 1
                self.pops.append(Popup(p.x, p.y - 20, "GINKLAS %d!" % self.weapon, (255, 200, 80), 24))
            else:
                self.score += 200
                self.pops.append(Popup(p.x, p.y - 20, "+200", (255, 200, 80)))
        elif p.kind == "S":
            self.a.sfx("shield")
            self.shield = 600
            self.pops.append(Popup(p.x, p.y - 20, "SKYDAS!", (130, 200, 255), 24))
        elif p.kind == "H":
            self.a.sfx("life")
            if self.lives < MAX_LIVES:
                self.lives += 1
                self.pops.append(Popup(p.x, p.y - 20, "+1 GYVYBĖ", (255, 130, 170), 24))
            else:
                self.score += 200
                self.pops.append(Popup(p.x, p.y - 20, "+200", (255, 130, 170)))
        else:
            self.a.sfx("power")
            if self.bombs < MAX_BOMBS:
                self.bombs += 1
                self.pops.append(Popup(p.x, p.y - 20, "BOMBA +1", (210, 160, 255), 24))
            else:
                self.score += 300
                self.pops.append(Popup(p.x, p.y - 20, "+300", (210, 160, 255)))

    def on_graze(self, x, y):
        """Vos nepataikė: kulka praskrido visai šalia - bonusas ir kombo pratęsimas."""
        self.graze_n += 1
        self.run["grazes"] += 1
        self.score += 10
        if self.combo > 0:
            self.combo_t = max(self.combo_t, 120)
        self.fx.append(Flash(self.px, self.py, 30, (150, 220, 255), 4))
        if self.graze_cd <= 0:
            self.graze_cd = 25
            self.pops.append(Popup(self.px, self.py - 46, "VOS NEPATAIKĖ! +10", (150, 230, 255), 18, 40))
            self.a.sfx("graze")
        if self.graze_n % 10 == 0:
            self.spawn_coins(self.px, self.py - 20, 3)
            self.pops.append(Popup(self.px, self.py - 70, "ŠALTAKRAUJIS! +3 monetos", (255, 215, 90), 20, 60))

    # ------------------------------------------------------------------
    #  Žala priešams
    # ------------------------------------------------------------------
    def hit_enemy(self, e, dmg, x, y):
        e.hp -= dmg
        e.flash = 6
        e.since_hit = 0
        if e.hp <= 0:
            self.kill_enemy(e)
        else:
            spawn_hit(self.fx, x, y, e.pal)
            self.a.sfx("hit")

    def kill_enemy(self, e):
        if e in self.enemies:
            self.enemies.remove(e)
        sc = e.scale
        spawn_explosion(self.fx, e.x, e.y, (1.0 + 0.2 * min(e.kind, 2)) * sc ** 0.8, e.pal)
        self.a.sfx("boom_l" if sc > 1 else ("boom_m" if e.kind in (2, 4) else "boom_s"))
        self.kills += 1
        self.run["kills"] += 1
        self.shake = max(self.shake, 3 + min(e.kind, 2) * 2)
        self.add_score(Enemy.PTS[e.kind] * (int(round(sc)) if sc > 1 else 1), e.x, e.y)
        self.spawn_coins(e.x, e.y, Enemy.COINS[e.kind] * (3 if sc > 1 else 1))
        if e.mode == "core":
            self.shake = max(self.shake, 16)
            self.pops.append(Popup(e.x, e.y + 40, "ORBITA SUGRIUVO!", (255, 220, 120), 28, 80))
        self.drop_power(e.x, e.y, chance=0.13 + 0.05 * min(e.kind, 2))
        if self.bonus is not None and e.mode == "bonus":
            self.bonus["killed"] += 1
            self.spawn_coins(e.x, e.y, 2)
        if e.kind == 5:                             # skylantis suskyla į du
            for sx in (-1, 1):
                m = Enemy.minion(e.x + sx * 20, e.y)
                m.amp = sx * random.uniform(40, 90)
                self.enemies.append(m)

    def hit_ufo(self, u, dmg, x, y):
        u.hp -= dmg
        u.flash = 6
        if u.hp <= 0:
            if u in self.ufos:
                self.ufos.remove(u)
            spawn_explosion(self.fx, u.x, u.y, 1.4, Ufo.PAL)
            self.a.sfx("boom_m")
            self.kills += 1
            self.run["kills"] += 1
            self.add_score(150, u.x, u.y, (150, 240, 255))
            self.drop_power(u.x, u.y, force=True)
            self.spawn_coins(u.x, u.y, 8)
        else:
            spawn_hit(self.fx, x, y, Ufo.PAL)
            self.a.sfx("hit")

    def hit_asteroid(self, a, dmg, x, y):
        a.hp -= dmg
        if a.hp > 0:
            spawn_hit(self.fx, x, y, Asteroid.PAL)
            self.a.sfx("hit")
            return
        if a in self.asteroids:
            self.asteroids.remove(a)
        spawn_explosion(self.fx, a.x, a.y, 1.2 if a.size == 0 else 0.7, Asteroid.PAL)
        self.a.sfx("boom_s")
        self.add_score(15 if a.size == 0 else 10, a.x, a.y, (240, 210, 170))
        if a.size == 0:
            self.spawn_coins(a.x, a.y, 1)
            for sx in (-1, 1):
                self.asteroids.append(Asteroid(a.x + sx * 10, a.y, sx * random.uniform(0.8, 1.8) + a.vx * 0.5,
                                               a.vy, 1))

    def hit_boss(self, dmg, x, y):
        b = self.boss
        if b is None or b.state != "fight":
            return
        b.hp -= dmg
        b.flash = 3
        if self.hit_cd <= 0:
            self.a.sfx("hit")
            self.hit_cd = 3
        spawn_hit(self.fx, x, y, b.pal, 3)
        if b.hp <= 0:
            b.hp = 0
            b.state = "dying"
            b.dying = 0
            b.clear_attacks()
            self.ebullets = []
            self.shake = 30
            self.a.sfx("boom_l")

    def boss_death_fx(self, b):
        x = b.x + random.uniform(-90, 90)
        y = b.y + 30 + random.uniform(-50, 60)
        spawn_explosion(self.fx, x, y, random.uniform(0.9, 1.6), b.pal)
        self.shake = max(self.shake, 8)
        if b.dying % 8 == 0:
            self.a.sfx("boom_m")

    def boss_finish(self, b):
        spawn_explosion(self.fx, b.x, b.y + 30, 3.5, b.pal)
        self.fx.append(Flash(b.x, b.y + 30, 220, (255, 230, 160), 16))
        self.flash = 255
        self.flash_col = (255, 255, 255)
        self.hitstop = 8
        self.shake = 30
        bonus = 1000 * b.level
        self.score += bonus
        self.pops.append(Popup(b.x, b.y, "BOSAS NUGALĖTAS! +%d" % bonus, (255, 240, 120), 30, 90))
        if not self.boss_hit_taken:
            self.run["boss_nohit"] += 1
            self.pops.append(Popup(b.x, b.y + 40, "NEPALIESTA! +500", (150, 255, 170), 26, 90))
            self.score += 500
        self.run["bosses"] += 1
        for dx in (-60, 0, 60):
            self.drop_power(b.x + dx, b.y + 40, force=True)
        self.spawn_coins(b.x, b.y + 40, 40)
        self.kills += 1
        self.run["kills"] += 1
        self.boss = None
        self.a.sfx("boom_l")

    def spawn_minions(self, x, y, n):
        for i in range(n):
            self.enemies.append(Enemy.minion(x + (i - (n - 1) / 2) * 50, y))
        self.pops.append(Popup(W / 2, 150, "Pakalikai!", (255, 150, 150), 26, 50))

    def spawn_asteroid(self):
        size = 0 if random.random() < 0.7 else 1
        vy = random.uniform(2.0, 3.2) if size == 0 else random.uniform(2.8, 4.0)
        self.asteroids.append(Asteroid(random.uniform(60, W - 60), -40.0,
                                       random.uniform(-1.2, 1.2), vy, size))

    def nearest_target(self, x, y):
        """Artimiausias taikinys raketoms (aukščiau už raketą)."""
        best, bd = None, 500.0 ** 2
        cands = list(self.enemies) + list(self.ufos) + list(self.asteroids)
        if self.boss is not None and self.boss.state == "fight":
            cands.append(self.boss)
        for o in cands:
            if o.y < 40 or o.y > y + 10:
                continue
            d = (o.x - x) ** 2 + (o.y - y) ** 2
            if d < bd:
                best, bd = o, d
        return best

    # ------------------------------------------------------------------
    #  Parduotuvė
    # ------------------------------------------------------------------
    def shop_item(self, i):
        key, name, desc, prices = SHOP[i]
        if prices is not None:
            lv = self.up[key]
            maxed = lv >= len(prices)
            price = None if maxed else prices[lv]
            info = "%d/%d" % (lv, len(prices))
        elif key == "life":
            maxed = self.lives >= MAX_LIVES
            price = None if maxed else 60 + 20 * self.up["life"]
            info = "Turi: %d" % self.lives
        elif key == "bomb":
            maxed = self.bombs >= MAX_BOMBS
            price = None if maxed else 40
            info = "Turi: %d/%d" % (self.bombs, MAX_BOMBS)
        else:
            maxed = False
            price = 35
            info = ""
        return {"key": key, "name": name, "desc": desc, "price": price,
                "maxed": maxed, "info": info}

    def buy(self, i):
        it = self.shop_item(i)
        if it["maxed"] or self.gold < it["price"]:
            self.a.sfx("denied")
            return False
        self.gold -= it["price"]
        key = it["key"]
        if key in ("rate", "cool", "speed", "magnet"):
            self.up[key] += 1
        elif key == "life":
            self.lives += 1
            self.up["life"] += 1
        elif key == "bomb":
            self.bombs += 1
        else:
            self.shield = 600
        self.a.sfx("power")
        return True

    def end_shop(self):
        self.shop_pending = False
        self.next_wave()

    def begin_shop(self):
        """Surenka likusias monetas ir paruošia parduotuvę."""
        for c in self.coins:
            self.gold += c.v
            self.run["coins"] += c.v
        self.coins = []
        self.asteroids = []
        self.ebullets = []
        self.shop_pending = True
        self.check_ach()

    # ------------------------------------------------------------------
    #  Atnaujinimas
    # ------------------------------------------------------------------
    def update(self, inp):
        if self.hitstop > 0:
            self.hitstop -= 1
            return
        self.t += 1
        self.shown += (self.score - self.shown) * 0.15
        if abs(self.score - self.shown) < 1:
            self.shown = float(self.score)
        if self.flash > 0:
            self.flash = max(0, self.flash - 14)
        if self.shake > 0:
            self.shake -= 1
        if self.banner > 0:
            self.banner -= 1
        if self.hit_cd > 0:
            self.hit_cd -= 1
        if self.graze_cd > 0:
            self.graze_cd -= 1
        if self.combo_t > 0:
            self.combo_t -= 1
            if self.combo_t == 0:
                self.combo = 0
        if self.toasts:
            self.toasts[0][2] -= 1
            if self.toasts[0][2] <= 0:
                self.toasts.pop(0)
        if self.t % 20 == 0:
            self.check_ach()

        self.update_player(inp)
        self.update_enemies()
        self.update_projectiles()
        self.collisions()

        for p in self.powers:
            p.update(self)
        self.powers = [p for p in self.powers if p.y < H + 30]
        for c in self.coins:
            c.update(self)
        self.coins = [c for c in self.coins if c.y < H + 30]
        if self.coin_cd > 0:
            self.coin_cd -= 1
        step_list(self.fx)
        step_list(self.pops)

        if (not self.enemies and self.boss is None and not self.dead and not self.shop_pending
                and self.bonus is None):
            self.clear_timer += 1
            if self.clear_timer > 60:
                self.clear_timer = 0
                bonus = 100 * self.wave
                self.score += bonus
                self.pops.append(Popup(W / 2, H / 2 + 40, "BANGOS BONUSAS +%d" % bonus,
                                       (150, 255, 170), 28, 70))
                if self.wtype in SCRIPTED and self.escaped == 0:
                    clean = 50 * self.wave
                    self.score += clean
                    self.pops.append(Popup(W / 2, H / 2 + 80, "NIEKAS NEPABĖGO! +%d" % clean,
                                           (255, 235, 120), 26, 80))
                self.adapt_difficulty()
                if self.wave % 5 == 3:
                    self.pending_bonus = True
                self.begin_shop()

    def update_player(self, inp):
        if self.dead:
            self.dead_timer -= 1
            if self.dead_timer <= 0:
                self.over = True
            return
        dx, dy = inp.dx, inp.dy
        spd = (6.5 + 0.8 * self.up["speed"]) * self.sdef["speed"]
        self.pvx += (dx * spd - self.pvx) * 0.3
        self.px = clamp(self.px + self.pvx, 36, W - 36)
        self.py = clamp(self.py + dy * 5, H - 170, H - 50)
        self.cool = max(0, self.cool - 1)
        self.update_heat(inp)
        if inp.fire and self.cool == 0 and not self.overheated:
            self.fire()
        if self.shield > 0:
            self.shield -= 1
        if self.inv > 0:
            self.inv -= 1
        if self.t % (4 if cfg.LOW_FX else 2) == 0:   # variklių kibirkštys
            for ex in (-10, 10):
                self.fx.append(Spark(self.px + ex, self.py + 30, random.uniform(-0.4, 0.4),
                                     random.uniform(2.5, 4), 12, (255, 170, 60), 5))

    def update_enemies(self):
        form = [e for e in self.enemies if not e.free]
        ready = bool(form) and all(e.mode != "enter" for e in form)
        if ready:
            self.move_formation(form)
        if self.wtype in SCRIPTED:
            self.wt_t += 1
        for e in self.enemies:
            e.update(self)
        self.enemies = [e for e in self.enemies if not e.gone]
        active = ready or (self.wtype in SCRIPTED and self.wt_t > 90 and bool(self.enemies))
        if ready and not self.dead:
            for e in form:
                if e.mode == "form" and e.y + 24 >= self.py - 40:
                    self.hurt()
                    self.oy = 0.0
                    break
            self.enemy_ai([e for e in self.enemies if not e.free])

        for u in self.ufos:
            u.update(self)
        self.ufos = [u for u in self.ufos if not u.gone]
        if self.boss is not None:
            self.boss.update(self)

        if self.wave >= 2 and self.boss is None and active and not self.dead and self.bonus is None:
            self.ufo_timer -= 1
            if self.ufo_timer <= 0 and not self.ufos:
                self.ufos.append(Ufo())
                self.a.sfx("ufo")
                self.ufo_timer = random.randint(1100, 1700)

        if self.bonus is not None:
            self.update_bonus()
        self.update_hazards(active)

    def update_hazards(self, ready):
        active = ready or (self.boss is not None and self.boss.state == "fight")
        if active and not self.dead and self.bonus is None:
            if self.shower_left > 0:
                self.shower_timer -= 1
                if self.shower_timer <= 0:
                    self.spawn_asteroid()
                    self.shower_left -= 1
                    self.shower_timer = 40
            if self.wave >= 3:
                self.haz_timer -= 1
                if self.haz_timer <= 0:
                    self.spawn_asteroid()
                    self.haz_timer = random.randint(600, 1100)
        for a in self.asteroids:
            a.update(self)
        self.asteroids = [a for a in self.asteroids if a.alive()]

    def move_formation(self, form):
        n = len(form)
        sp = min(4.5, (0.9 + 0.12 * self.wave) * (1 + 1.2 * (1 - n / max(1, self.total))))
        self.ox += self.dir * sp
        minx = min(e.bx for e in form) + self.ox - 28
        maxx = max(e.bx for e in form) + self.ox + 28
        if maxx > W - 10:
            self.ox -= maxx - (W - 10)
            self.dir = -1
            self.oy += 20
        elif minx < 10:
            self.ox += 10 - minx
            self.dir = 1
            self.oy += 20

    def start_dive(self, e):
        e.mode = "dive"
        e.sx, e.sy, e.t, e.shot = e.x, e.y, 0, False
        e.amp = random.choice([-1, 1]) * random.uniform(80, 160)

    def enemy_ai(self, form):
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            lowest = {}
            for e in form:
                if e.mode == "form" and (e.col not in lowest or e.row > lowest[e.col].row):
                    lowest[e.col] = e
            shooters = list(lowest.values())
            if shooters:
                for _ in range(1 + (self.wave >= 4) + (self.adapt >= 1.0)):
                    e = random.choice(shooters)
                    vy = min(3.2 + self.wave * 0.25 + 0.5 * max(self.adapt, 0.0), 7.0)
                    if e.kind == 4:                 # šarvuotas šaudo dvigubai
                        self.ebullets.append(EBullet(e.x - 8, e.y + 18, -0.6, vy))
                        self.ebullets.append(EBullet(e.x + 8, e.y + 18, 0.6, vy))
                    else:
                        self.ebullets.append(EBullet(e.x, e.y + 18, 0, vy))
            f = 1.0 / (1.0 + 0.3 * self.adapt)
            self.shoot_timer = max(12, int(random.randint(max(18, 70 - self.wave * 5),
                                                          max(40, 110 - self.wave * 6)) * f))
        for e in form:                              # kamikadzės pačios puola
            if e.kind == 3 and e.mode == "form" and random.random() < 0.0025:
                self.start_dive(e)
        self.dive_timer -= 1
        if self.dive_timer <= 0:
            cands = [e for e in form if e.mode == "form"]
            if cands:
                self.start_dive(random.choice(cands))
            self.dive_timer = max(60, int(random.randint(max(90, 260 - self.wave * 20),
                                                         max(150, 380 - self.wave * 20))
                                          / (1.0 + 0.3 * self.adapt)))

    def update_projectiles(self):
        for b in self.bullets:
            b.update(self)
        self.bullets = [b for b in self.bullets if b.alive()]
        for b in self.ebullets:
            b.update()
        self.ebullets = [b for b in self.ebullets if b.alive()]

    def all_targets(self):
        t = [(e, "e") for e in self.enemies]
        t += [(u, "u") for u in self.ufos]
        t += [(a, "a") for a in self.asteroids]
        if self.boss is not None and self.boss.state == "fight":
            t.append((self.boss, "b"))
        return t

    def collisions(self):
        # žaidėjo kulkos prieš visus taikinius (su pramušimu)
        targets = self.all_targets()
        for b in self.bullets[:]:
            br = pygame.Rect(int(b.x) - 5, int(b.y) - 12, 10, 24)
            for obj, kind in targets:
                if id(obj) in b.hit_ids or obj.hp <= 0:
                    continue
                if kind == "e" and obj.kind == 6 and b.vy < 0 and br.colliderect(obj.shield_rect()):
                    spawn_hit(self.fx, b.x, b.y, [(190, 200, 230), (255, 255, 255), (255, 255, 255)], 4)
                    self.a.sfx("clang")
                    if b in self.bullets:
                        self.bullets.remove(b)
                    break
                if not br.colliderect(obj.rect()):
                    continue
                b.hit_ids.add(id(obj))
                if kind == "e":
                    self.hit_enemy(obj, b.dmg, b.x, b.y)
                elif kind == "u":
                    self.hit_ufo(obj, b.dmg, b.x, b.y)
                elif kind == "a":
                    self.hit_asteroid(obj, b.dmg, b.x, b.y)
                else:
                    self.hit_boss(b.dmg, b.x, b.y)
                b.pierce -= 1
                if b.pierce < 0:
                    if b in self.bullets:
                        self.bullets.remove(b)
                    break

        if self.dead:
            return
        pr = self.player_rect()
        for b in self.ebullets[:]:
            if pr.colliderect(pygame.Rect(int(b.x) - 7, int(b.y) - 7, 14, 14)):
                self.ebullets.remove(b)
                self.hurt()
        for b in self.ebullets:                      # "vos nepataikė"
            if not b.grazed and abs(b.x - self.px) < 40 and abs(b.y - self.py) < 30:
                b.grazed = True
                self.on_graze(b.x, b.y)
        for e in self.enemies[:]:
            if e.mode in ("dive", "ret", "stream", "orbit") and pr.colliderect(e.rect()):
                self.kill_enemy(e)
                self.hurt()
            elif e.mode == "core" and pr.colliderect(e.rect()):
                self.hurt()
        for a in self.asteroids[:]:
            if pr.colliderect(a.rect()):
                self.asteroids.remove(a)
                spawn_explosion(self.fx, a.x, a.y, 1.0, Asteroid.PAL)
                self.a.sfx("boom_s")
                self.hurt()
        bs = self.boss
        if bs is not None and bs.state == "fight":
            brc = bs.beam_rect()
            if brc is not None and pr.colliderect(brc):
                self.hurt()
            if bs.dash is not None and pr.colliderect(bs.rect()):
                self.hurt()
        for p in self.powers[:]:
            if pr.inflate(10, 10).colliderect(p.rect()):
                self.powers.remove(p)
                self.collect(p)
        for c in self.coins[:]:
            if pr.inflate(10, 10).colliderect(c.rect()):
                self.coins.remove(c)
                self.gold += c.v
                self.run["coins"] += c.v
                if self.coin_cd <= 0:
                    self.a.sfx("coin")
                    self.coin_cd = 3

    # ------------------------------------------------------------------
    #  Piešimas
    # ------------------------------------------------------------------
    def draw(self, surf):
        if self.boss is not None:
            self.boss.draw(surf, self)
        for e in self.enemies:
            e.draw(surf, self)
        for u in self.ufos:
            u.draw(surf, self)
        for a in self.asteroids:
            a.draw(surf)
        for p in self.powers:
            p.draw(surf)
        for c in self.coins:
            c.draw(surf)
        for b in self.bullets:
            b.draw(surf)
        for b in self.ebullets:
            b.draw(surf, self.t)
        if not self.dead:
            if self.weapon >= 5:
                for sx in (-1, 1):
                    dx, dy = self.drone_pos(sx)
                    gfx.add_glow(surf, dx, dy, 22, (30, 120, 150))
                    surf.blit(S.drone, S.drone.get_rect(center=(int(dx), int(dy))))
            blink = self.inv > 0 and self.shield <= 0 and (self.t // 4) % 2 == 0
            gfx.draw_ship(surf, int(self.px), int(self.py), self.t, -self.pvx * 1.6, blink, self.ship)
            if self.overheated:
                gfx.add_glow(surf, self.px, self.py, 44 + int(6 * math.sin(self.t * 0.4)), (190, 50, 20))
            if self.shield > 0 and (self.shield > 120 or (self.t // 5) % 2 == 0):
                r = 48 + int(2 * math.sin(self.t * 0.2))
                g = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
                c = r + 4
                pygame.draw.circle(g, (90, 180, 255, 70), (c, c), r)
                pygame.draw.circle(g, (200, 235, 255, 230), (c, c), r, 4)
                pygame.draw.circle(g, (255, 255, 255, 200), (c - r // 3, c - r // 3), 5)
                surf.blit(g, g.get_rect(center=(int(self.px), int(self.py))))
        for f in self.fx:
            f.draw(surf)
        for p in self.pops:
            p.draw(surf)
        self.draw_hud(surf)
        self.draw_banner(surf)
        self.draw_toast(surf)
        if self.flash > 0:
            self._flash_surf.fill(self.flash_col)
            self._flash_surf.set_alpha(int(min(255, self.flash) * 0.75))
            surf.blit(self._flash_surf, (0, 0))

    def draw_banner(self, surf):
        if self.banner <= 0:
            return
        age = 120 - self.banner
        k = min(1.0, age / 18)
        sc = 1 + (1 - k) ** 2 * 1.5
        col = (255, 235, 110)
        if self.banner_kind == "boss":
            col = (255, 90, 90) if (self.t // 6) % 2 == 0 else (255, 200, 90)
        elif self.banner_kind == "bonus":
            col = (110, 255, 220)
        size = 76 if len(self.banner_text) < 12 else 58
        img = pygame.transform.rotozoom(text_surf(self.banner_text, size, col, 5), 0, sc)
        surf.blit(img, img.get_rect(center=(W // 2, H // 2 - 40)))
        y = H // 2 + 20
        if self.banner_sub:
            draw_text(surf, self.banner_sub, 26, (255, 255, 255), (W // 2, y), "center", 3)
            y += 34
        elif self.banner_kind == "boss":
            draw_text(surf, "Pasiruošk!", 30, (255, 255, 255), (W // 2, y), "center", 3)
        if self.banner_tag:
            draw_text(surf, self.banner_tag, 24, (255, 215, 120), (W // 2, y), "center", 3)

    def draw_toast(self, surf):
        if not self.toasts:
            return
        title, sub, t = self.toasts[0]
        k = min(1.0, (190 - t) / 12, t / 12)
        y = int(112 - (1 - k) * 50)
        r = pygame.Rect(W // 2 - 240, y - 28, 480, 58)
        pygame.draw.rect(surf, OUT, r.move(0, 4), border_radius=16)
        pygame.draw.rect(surf, (35, 70, 140), r, border_radius=16)
        pygame.draw.rect(surf, (255, 215, 90), r, 4, border_radius=16)
        gfx.poly(surf, (255, 230, 90), gfx.star_pts(r.x + 34, r.centery, 16, 7), 2)
        draw_text(surf, title, 20, (255, 230, 120), (r.x + 64, r.centery - 10), "midleft", 3)
        draw_text(surf, sub, 15, (255, 255, 255), (r.x + 64, r.centery + 13), "midleft", 2)

    def draw_hud(self, surf):
        surf.blit(self._panel, (0, 0))
        gfx.poly(surf, (255, 230, 90), gfx.star_pts(24, 25, 11, 5), 2)
        draw_text(surf, "%07d" % int(self.shown), 28, (255, 235, 110), (44, 25), "midleft", 3)
        if self.bonus is not None:
            draw_text(surf, "BONUSAS", 26, (110, 255, 220), (W // 2 + 20, 25), "center", 3)
            draw_text(surf, "Sunaikinta %d / %d" % (self.bonus["killed"], max(self.bonus["total"], 40)),
                      20, (110, 255, 220), (W // 2, 70), "center", 3)
        elif self.boss is not None:
            draw_text(surf, "BOSAS", 26, (255, 110, 110), (W // 2 + 20, 25), "center", 3)
        else:
            draw_text(surf, "Banga %d" % self.wave, 26, (150, 255, 170), (W // 2 + 20, 25), "center", 3)
        surf.blit(S.coin[0], S.coin[0].get_rect(center=(214, 25)))
        draw_text(surf, "%d" % self.gold, 22, (255, 215, 90), (228, 25), "midleft", 3)
        sp = min(30, int(230 / max(1, self.lives)))
        icon = S.life[self.ship]
        for i in range(self.lives):
            surf.blit(icon, (W - 12 - (i + 1) * sp - (30 - sp), 9))
        if self.combo >= 3:
            m = self.mult()
            col = [(255, 255, 255), (255, 255, 255), (255, 235, 110), (255, 190, 80),
                   (255, 130, 80), (255, 90, 140)][m]
            draw_text(surf, "KOMBO x%d  (%d)" % (m, self.combo), 22, col, (14, 70), "midleft", 3)
            pygame.draw.rect(surf, OUT, (12, 86, 124, 10), border_radius=4)
            pygame.draw.rect(surf, col, (14, 88, int(120 * self.combo_t / 150), 6), border_radius=3)
        b = self.boss
        if b is not None and b.state != "enter":
            bx, by, bw = W // 2 - 230, 60, 460
            pygame.draw.rect(surf, OUT, (bx - 4, by - 4, bw + 8, 22), border_radius=8)
            pygame.draw.rect(surf, (90, 30, 50), (bx, by, bw, 14), border_radius=6)
            draw_text(surf, b.name, 16, (255, 200, 200), (W // 2, by + 28), "center", 2)
            fw = int(bw * max(0, b.hp) / b.maxhp)
            if fw > 0:
                pygame.draw.rect(surf, (255, 90, 90), (bx, by, fw, 14), border_radius=6)
                pygame.draw.rect(surf, (255, 170, 150), (bx + 4, by + 2, max(0, fw - 8), 4), border_radius=2)
        # apačia: ginklas, bombos, skydas
        draw_text(surf, "Ginklas", 18, (255, 255, 255), (14, H - 22), "midleft", 2)
        for i in range(5):
            r = pygame.Rect(100 + i * 24, H - 31, 20, 18)
            pygame.draw.rect(surf, gfx.BULLET_COLS[i] if i < self.weapon else (60, 55, 90), r, border_radius=5)
            pygame.draw.rect(surf, OUT, r, 3, border_radius=5)
        for i in range(self.bombs):
            surf.blit(S.bomb_icon, (W - 14 - (i + 1) * 30, H - 38))
        draw_text(surf, "B", 16, (210, 160, 255), (W - 14 - MAX_BOMBS * 30 - 8, H - 24), "midright", 2)
        if self.weapon >= 5 or self.heat > 1:        # ginklo temperatūra
            bx, by, bw = 234, H - 30, 100
            pygame.draw.rect(surf, OUT, (bx - 3, by - 3, bw + 6, 16), border_radius=6)
            pygame.draw.rect(surf, (60, 55, 90), (bx, by, bw, 10), border_radius=4)
            k = max(0.0, min(1.0, self.heat / 100.0))
            col = gfx.lerp_col((90, 230, 120), (255, 70, 50), k)
            if self.overheated and (self.t // 5) % 2 == 0:
                col = (255, 255, 255)
            if k > 0:
                pygame.draw.rect(surf, col, (bx, by, max(4, int(bw * k)), 10), border_radius=4)
            draw_text(surf, "PERKAITA!" if self.overheated else "Temp.", 14,
                      (255, 120, 100) if self.overheated else (255, 255, 255),
                      (bx + bw + 10, by + 5), "midleft", 2)
        lvl = self.threat_level()                    # grėsmės lygis
        draw_text(surf, "Grėsmė", 14, (255, 255, 255), (440, H - 22), "midleft", 2)
        for i in range(5):
            c = gfx.lerp_col((255, 230, 90), (255, 70, 60), i / 4) if i < lvl else (60, 55, 90)
            pygame.draw.rect(surf, c, (500 + i * 14, H - 30, 10, 14), border_radius=3)
            pygame.draw.rect(surf, OUT, (500 + i * 14, H - 30, 10, 14), 2, border_radius=3)
        if self.shield > 0:
            draw_text(surf, "Skydas %ds" % (self.shield // 60 + 1), 18, (150, 210, 255),
                      (W // 2, H - 52), "center", 2)
