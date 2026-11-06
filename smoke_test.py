"""Smoke testas: be tikro pygame (naudojamas stub), bet su tikra numpy garso sinteze."""
import os, sys, random
from types import SimpleNamespace as NS
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import stub_pygame
pg = stub_pygame.build()

from sd import settings
settings.SAVE_FILE = "/tmp/sd_test_save.json"          # testas nerašo į tikrą išsaugojimą
if os.path.exists(settings.SAVE_FILE):
    os.remove(settings.SAVE_FILE)

import shutil, time
from sd import gfx, screens, progress
from sd import audio as audio_mod
from sd import settings as cfg
audio_mod.CACHE_DIR = "/tmp/sd_cache_test"                # muzikos talpykla testui
shutil.rmtree(audio_mod.CACHE_DIR, ignore_errors=True)
from sd.effects import Parallax
from sd.app import App
from sd.entities import EBullet, Asteroid, Enemy, Bullet
from sd.game import SHAPES, SCRIPTED, WAVE_TYPES
from sd.settings import W, H, SAVE

gfx.init()
screen = pg.display.set_mode((W, H))
app = App(screen)
app.audio.build(lambda f, m: None)
app.plx = Parallax()
random.seed(21)

def E(type_, **kw): return NS(type=type_, **kw)

for st in ("menu", "help", "scores", "ach", "hangar"):
    app.state = st
    for _ in range(15):
        app.t += 1; app.update(); app.draw()

frames = 0
def step(g, n, fire=True):
    global frames
    for _ in range(n):
        app.t += 1; frames += 1
        tg = list(g.enemies) or ([g.boss] if g.boss else [])
        dx = 0.0
        if tg:
            tx = min(tg, key=lambda e: abs(e.x - g.px)).x
            dx = max(-1.0, min(1.0, (tx - g.px) / 30))
        g.update(NS(dx=dx, dy=0.0, fire=fire))
        app.state = "play"; app.draw()
        if g.over or g.shop_pending: return

# 1) kiekvienas laivas: ginklo lygiai 1..5, kulkos, pramušimas, raketos
SAVE.ach = [a["id"] for a in progress.ACH if progress.ship_for_achievement(a["id"]) is not None]
for ship in range(4):
    SAVE.ship = ship
    app.start_game(); g = app.game
    assert g.ship == ship
    g.inv = 99999
    for lv in range(1, 6):
        g.weapon = lv
        step(g, 200)
    print("ship", ship, progress.SHIPS[ship]["name"], "score", g.score, "kills", g.kills)
    assert g.kills > 0

# 2) visos formacijos, visi priešų tipai, meteoritai
app.start_game(); g = app.game
g.inv = 99999; g.lives = 9
shapes, kinds, wtypes = set(), set(), set()
for w in range(1, 16):
    if g.shop_pending: g.end_shop()
    if g.bonus is None and g.boss is None:
        if g.wtype == "formation" and g.recent_shapes:
            shapes.add(g.recent_shapes[-1])
        wtypes.add(g.wtype)
        kinds |= {e.kind for e in g.enemies}
    step(g, 500)
    if g.boss:
        g.boss.hp = 1; g.boss.state = "fight"; g.px = g.boss.x; step(g, 200)
print("wave types", sorted(wtypes), "shapes", sorted(shapes), "kinds", sorted(kinds), "wave", g.wave, "gold", g.gold, "ast", len(g.asteroids))

# 2a) atsitiktinės formacijos: visos formos, ribos, nepasikartojimas
app.start_game(); g = app.game; g.inv = 99999
g.wave = 6
sigs = []
for sh in SHAPES:
    shape, sl = g.formation_slots(sh)
    xs = [x for x, _ in sl]; ys = [y for _, y in sl]
    assert 8 <= len(sl) <= 40, (sh, len(sl))
    assert min(xs) >= 40 and max(xs) <= W - 40 and min(ys) >= 60 and max(ys) <= 420, (sh, min(xs), max(xs), min(ys), max(ys))
    sigs.append((sh, round(sum(xs)), round(sum(ys)), len(sl)))
print("shapes ok:", len(SHAPES))
g.recent_shapes = []; seen_sig = set(); dup = 0
for _ in range(60):
    shape, sl = g.formation_slots()
    sig = (shape, len(sl), round(sum(x for x, _ in sl)), round(sum(y for _, y in sl)))
    dup += sig in seen_sig; seen_sig.add(sig)
print("random compositions: unique", len(seen_sig), "of 60")
assert len(seen_sig) >= 45
for _ in range(300):
    g.last_wtype = random.choice(list(WAVE_TYPES)); g.wave = random.randint(2, 15); g.nwave = 5; g.nonform_streak = 0
    t = g.pick_wave_type(); assert t != g.last_wtype
    g.nonform_streak = 2; assert g.pick_wave_type() == "formation"

# 2a-2) kiekvienas scenarijaus tipas: sukuriamas, praeinamas, orbita byra
for wt in SCRIPTED:
    for wave in (3, 7, 12):
        app.start_game(); g = app.game; g.inv = 99999; g.lives = 9; g.wave = wave; g.nwave = 4
        g.enemies = []; g.adapt = 0.9 if wave > 10 else 0.0
        if wt == "ring" and wave < 3 or (wt == "orbit" and wave < 4): continue
        g.build_scripted(wt)
        n0 = len(g.enemies); assert n0 > 4, (wt, n0)
        g.wtype = wt; g.wt_t = 0
        spawned_dive = False
        for f in range(4000):
            step(g, 1)
            if wt == "orbit" and any(e.mode == "core" for e in g.enemies) and f == 400:
                core = [e for e in g.enemies if e.mode == "core"][0]; core.hp = 1
            if any(e.mode == "dive" and e.counts_escape for e in g.enemies): spawned_dive = True
            if not g.enemies or g.shop_pending: break
        left = len(g.enemies)
        print("  wave type", wt, "wave", wave, "enemies", n0, "left", left, "frames", f, "escaped", g.escaped,
              "kills", g.kills, "orbit-break" if spawned_dive else "")
        assert not g.enemies or g.shop_pending, (wt, left)
        if wt == "orbit" and wave == 7: assert spawned_dive

# 2a-3) bomba nebeveikia priešų, kurie dar nepasirodė
app.start_game(); g = app.game; g.inv = 99999; g.wave = 6; g.enemies = []
g.build_scripted("stream"); n0 = len(g.enemies); g.bombs = 1; g.use_bomb()
assert len(g.enemies) == n0, (n0, len(g.enemies))

# 2b) parduotuvė (7 prekės + tęsti)
g.shop_pending = False; g.enemies = []; g.boss = None; g.gold = 2000
g.begin_shop(); app.state = "shop"
for i in range(8):
    app.shop_sel = i; app.t += 1; app.draw()
for i in range(7):
    for _ in range(4): g.buy(i)
print("shop:", g.up, "lives", g.lives, "bombs", g.bombs)
assert g.up["cool"] == 3 and g.gold < 2000
g.gold = 0; assert g.buy(0) is False
app.shop_sel = 7; app.handle(E(pg.KEYDOWN, key=pg.K_RETURN)); assert app.state == "play", app.state

# 3) bonuso etapas
g.shop_pending = False; g.boss = None; g.bonus = None; g.enemies = []; g.asteroids = []
g.wave = 3; g.pending_bonus = True; g.clear_timer = 0
g.next_wave()
assert g.bonus is not None
g.inv = 99999
for _ in range(2500):
    step(g, 1)
    if g.bonus is None: break
print("bonus finished:", g.bonus is None, "wave", g.wave, "perfect:", g.run["bonus_perfect"])
assert g.bonus is None

# 4) vos nepataikė + meteoritas + pasiekimai
g.inv = 0; g.shield = 0; g.lives = 5; g.enemies = []
b = EBullet(g.px + 30, g.py, 0, 0.1); g.ebullets.append(b)
g.update(NS(dx=0, dy=0, fire=False))
print("grazes", g.run["grazes"], "toasts", len(g.toasts))
assert g.run["grazes"] >= 1
g.asteroids.append(Asteroid(g.px, g.py, 0, 0, 0)); g.hit_asteroid(g.asteroids[-1], 5, g.px, g.py)
for _ in range(15):
    g.graze_n += 1; g.on_graze(g.px, g.py)
g.run["kills"] = 500; g.run["coins"] = 999; g.run["best_wave"] = 12; g.run["best_combo"] = 25
g.check_ach(); step(g, 5)
app.state = "play"; app.draw()
print("achievements:", len(SAVE.ach), "new:", g.new_ach[:3])

# 5) žūtis -> vardas -> lentelė -> kitos būsenos
g.score = 4242; g.inv = 0
for _ in range(15):
    g.inv = 0; g.hurt(); step(g, 3, False)
for _ in range(200):
    g.update(NS(dx=0, dy=0, fire=False))
    if g.over: break
app.state = "play"; app.finish_game()
assert app.state == "entername", app.state
app.draw()
for ch in "Ona":
    app.handle(E(pg.KEYDOWN, key=1, unicode=ch))
app.handle(E(pg.KEYDOWN, key=pg.K_RETURN)); app.draw()
print("rank", app.rank, "stats games", SAVE.stats.get("games"), "kills", SAVE.stats.get("kills"))
app.handle(E(pg.KEYDOWN, key=pg.K_TAB)); app.draw()
app.handle(E(pg.KEYDOWN, key=pg.K_x)); app.handle(E(pg.KEYDOWN, key=pg.K_ESCAPE))
assert app.state == "menu"

# 5b) nauji priešai, perkaitimas, prisitaikantis sunkumas
app.start_game(); g = app.game; g.inv = 99999; g.enemies = []; g.boss = None
# skydininko skydas blokuoja šūvį iš apačios, bet ne iš šono
e = Enemy(400, 300, 6, 400.0, 300.0); e.mode = "form"; e.x, e.y = 400.0, 300.0; e.sh_off = 0.0
g.enemies = [e]; hp0 = e.hp
g.bullets = [Bullet(400, 330, 0, -10, 1)]; g.collisions()
assert e.hp == hp0 and not g.bullets, (e.hp, g.bullets)
g.bullets = [Bullet(425, 305, 0, -10, 1)]; g.collisions()
assert e.hp == hp0 - 1, e.hp
# regeneratorius gyja
r = Enemy(300, 300, 7, 300.0, 300.0); r.mode = "form"; r.hp = 1; r.maxhp = 4; r.since_hit = 100
g.enemies = [r]; g.t = 45; r.special(g); assert r.hp == 2
# šokliukas teleportuojasi nuo šūvio
b8 = Enemy(400, 300, 8, 400.0, 300.0); b8.mode = "form"; b8.x, b8.y = 400.0, 300.0
g.enemies = [b8]; g.bullets = [Bullet(400, 400, 0, -10, 1)]; b8.special(g)
assert b8.tp_cd == 150 and abs(b8.tp_off) > 50, (b8.tp_cd, b8.tp_off)
# gydytojas gydo sąjungininką
h = Enemy(300, 300, 9, 300.0, 300.0); h.mode = "form"; h.heal_t = 130; h.x, h.y = 300.0, 300.0
al = Enemy(340, 300, 4, 340.0, 300.0); al.mode = "form"; al.hp = 1; al.x, al.y = 340.0, 300.0
g.enemies = [h, al]; g.bullets = []; h.special(g); assert al.hp == 2 and h.link is not None
# perkaitimas
g.enemies = [Enemy(400, 60, 0, 400.0, 60.0)]; g.weapon = 5; g.ship = 0; g.sdef = progress.SHIPS[0]
g.bullets = []; over_seen = False
for _ in range(400):
    g.dive_timer = g.shoot_timer = 10 ** 9
    g.update(NS(dx=0.0, dy=0.0, fire=True)); g.enemies = g.enemies or [Enemy(400, 60, 0, 400.0, 60.0)]
    g.enemies[0].hp = 99
    if g.overheated: over_seen = True
    app.state = "play"; app.draw()
assert over_seen, "neperkaito"
for _i in range(200):
    g.dive_timer = g.shoot_timer = 10 ** 9           # testo priešas nepuola ir nešaudo
    g.update(NS(dx=0.0, dy=0.0, fire=False))
    g.enemies = g.enemies or [Enemy(400, 60, 0, 400.0, 60.0)]
    g.enemies[0].hp = 99
assert not g.overheated and g.heat < 30, (g.overheated, g.heat)
print("overheat OK, heat", round(g.heat, 1))
# prisitaikantis sunkumas
g.adapt = 0.0; g.wave = 6
for _ in range(6):
    g.wave_t0 = g.t - 300; g.wave_hits = 0; g.adapt_difficulty()
print("adapt up:", round(g.adapt, 2), "hp bonus", g.hp_bonus(), "threat", g.threat_level())
assert g.adapt >= 1.2 and g.hp_bonus() >= 2
g.wave = 5 - 1; g.enemies = []; g.nwave = 0; g.shop_pending = False; g.next_wave()
print("boss maxhp scaled:", g.boss.maxhp, "vs base", 40 + 22)
assert g.boss.maxhp > 62
g.boss = None; g.wave = 6; g.nwave = 3; g.build_formation()
assert all(e.maxhp >= Enemy.HP[e.kind] + 2 for e in g.enemies)
for _ in range(5):
    g.wave_hits = 4; g.adapt_difficulty()
print("adapt down:", round(g.adapt, 2)); assert g.adapt < 0.5
app.state = "play"; app.draw()

# 6) meniu: hangaras, pasiekimai, laivo parinkimas, valdiklis
app.state = "menu"
app.sel = 1; app.handle(E(pg.KEYDOWN, key=pg.K_RIGHT)); app.handle(E(pg.KEYDOWN, key=pg.K_LEFT))
app.handle(E(pg.KEYDOWN, key=pg.K_RETURN)); assert app.state == "hangar"
for key in (pg.K_RIGHT, pg.K_RIGHT, pg.K_RETURN, pg.K_LEFT, pg.K_RETURN):
    app.handle(E(pg.KEYDOWN, key=key)); app.draw()
app.handle(E(pg.MOUSEMOTION, pos=(500, 300))); app.handle(E(pg.MOUSEBUTTONDOWN, button=1, pos=(500, 300)))
app.handle(E(pg.KEYDOWN, key=pg.K_ESCAPE)); assert app.state == "menu"
app.sel = 2; app.handle(E(pg.KEYDOWN, key=pg.K_RETURN)); assert app.state == "ach"
app.handle(E(pg.KEYDOWN, key=pg.K_a)); assert app.state == "menu"
app.handle(E(pg.MOUSEBUTTONDOWN, button=1, pos=(420, 212 + 5 * 46 + 10)))
app.handle(E(pg.JOYHATMOTION, value=(0, -1), hat=0)); app.handle(E(pg.JOYBUTTONDOWN, button=0))
# užrakinti laivai
SAVE.ach = []; SAVE.ship = 3
assert app.current_ship() == 0
app.start_game(); assert app.game.ship == 0
app.handle(E(pg.JOYBUTTONDOWN, button=7)); app.handle(E(pg.JOYBUTTONDOWN, button=0))
# 7) MOBILUS: lietimo valdymas, mygtukai, žema kokybė, talpykla
t0 = time.time(); a2 = audio_mod.Audio(); a2.build(lambda f, m: None)
print("audio rebuild with cache: %.1fs, tracks: %d" % (time.time() - t0, len(a2.tracks)))
assert len(a2.tracks) >= 5 and time.time() - t0 < 4.0
cfg.LOW_FX = True                                          # kaip telefone
app.touch_ui = True
def norm(lx, ly):
    ww, wh = 1600, 720
    sc = min(ww / W, wh / H); ox, oy = (ww - W * sc) / 2, (wh - H * sc) / 2
    return (ox + lx * sc) / ww, (oy + ly * sc) / wh
def finger(kind, lx, ly, fid=1):
    x, y = norm(lx, ly)
    t = {"down": pg.FINGERDOWN, "move": pg.FINGERMOTION, "up": pg.FINGERUP}[kind]
    app.handle(E(t, x=x, y=y, finger_id=fid))
def run_frames(n):
    for _ in range(n):
        app.t += 1; app.update(); app.draw()

app.state = "menu"
app.start_game(); g = app.game; g.inv = 99999; g.enemies = []; g.boss = None
g.enemies = [Enemy(400, 60, 0, 400.0, 60.0)]; g.dive_timer = g.shoot_timer = 10 ** 9
x0 = g.px
finger("down", 400, 500); finger("move", 600, 500); run_frames(40)
print("touch move:", round(x0), "->", round(g.px), "bullets", len(g.bullets))
assert g.px > x0 + 80 and g.bullets, (g.px, len(g.bullets))
finger("move", 200, 500); run_frames(60); assert g.px < x0
finger("up", 200, 500); n_b = len(g.bullets); run_frames(30)
assert not app.fingers
g.dive_timer = g.shoot_timer = 10 ** 9
b0 = g.bombs; bx, by = screens.BOMB_BTN.center; finger("down", bx, by, 2); assert g.bombs == b0 - 1; finger("up", bx, by, 2)
px_, py_ = screens.PAUSE_BTN.center; finger("down", px_, py_, 3); assert app.state == "pause"; finger("up", px_, py_, 3)
run_frames(3)
# pauzės mygtukai: tęsti ir į meniu (piršto "pelė")
rx, ry = screens.PAUSE_RESUME.center; finger("down", rx, ry, 4); assert app.state == "play", app.state
app.handle(E(pg.KEYDOWN, key=pg.K_AC_BACK)); assert app.state == "pause"
app.handle(E(pg.APP_WILLENTERBACKGROUND)); assert app.state == "pause"
mx, my = screens.PAUSE_MENU.center; finger("down", mx, my, 5); assert app.state == "menu", app.state
# fonas -> pauzė
app.start_game(); app.handle(E(pg.APP_WILLENTERBACKGROUND)); assert app.state == "pause"
app.resume_game(); assert app.state == "play"
# lietimu imituojama pelė ignoruojama (kad nedubliuotųsi)
app.handle(E(pg.MOUSEBUTTONDOWN, button=1, pos=(100, 100), touch=True)); assert app.state == "play"
app.to_menu()
# meniu: kokybės perjungimas piršto lietimu
q0 = cfg.LOW_FX; qx, qy = screens.MENU_RECTS[7].center
finger("down", qx, qy, 6); assert cfg.LOW_FX != q0
finger("down", qx, qy, 6); assert cfg.LOW_FX == q0
# angaras: atgal mygtukas
app.sel = 1; hx, hy = screens.MENU_RECTS[1].center; finger("down", hx, hy, 7); assert app.state == "hangar", app.state
app.draw(); bx_, by_ = screens.HANGAR_BACK.center; finger("down", bx_, by_, 8); assert app.state == "menu"
# žaidimo pabaiga ir vardas liečiant
app.start_game(); g = app.game; g.score = 99999; g.lives = 0; g.dead = True; g.over = True
app.state = "play"; app.update(); app.draw()
assert app.state == "entername", app.state
for ch in "AB":
    rc = [r for c, r in screens.NAME_CELLS if c == ch][0]; finger("down", rc.centerx, rc.centery, 9)
finger("down", *screens.NAME_DEL.center, 9); finger("down", *screens.NAME_OK.center, 9)
assert app.state == "gameover" and SAVE.scores[0]["name"] == "A", (app.state, SAVE.scores[:1])
app.draw()
for i, expect in ((1, "scores"), ):
    finger("down", *screens.GO_BTNS[i].center, 10); assert app.state == expect, app.state
    app.handle(E(pg.MOUSEBUTTONDOWN, button=1, pos=(10, 10)))
assert app.state == "gameover"
finger("down", *screens.GO_BTNS[2].center, 11); assert app.state == "menu"
# visas žaidimas žema kokybe: kelios bangos
app.start_game(); g = app.game; g.inv = 99999; g.lives = 9
for _ in range(1800):
    app.t += 1; tg = list(g.enemies)
    dx = max(-1.0, min(1.0, (min(tg, key=lambda e: abs(e.x - g.px)).x - g.px) / 30)) if tg else 0.0
    g.update(NS(dx=dx, dy=0.0, fire=True)); app.state = "play"; app.draw()
    if g.shop_pending: g.end_shop()
print("low-fx game wave", g.wave, "score", g.score)
cfg.LOW_FX = False
print("SMOKE OK, frames:", frames)
