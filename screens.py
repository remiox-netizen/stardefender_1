# -*- coding: utf-8 -*-
"""Ekranai: meniu, rezultatai, parduotuvė, vardo įvedimas, valdymas, pauzė, game over."""
import math

import pygame

from .settings import W, H, OUT, START_LIVES, SAVE
from . import gfx, progress
from . import settings as cfg
from .gfx import S, draw_text

# ----------------------------------------------------------------------------
#  Meniu
# ----------------------------------------------------------------------------
MENU_COUNT = 9
MENU_RECTS = [pygame.Rect(W // 2 - 190, 212 + i * 46, 380, 40) for i in range(MENU_COUNT)]
# meniu indeksai: 0 žaisti, 1 angaras, 2 pasiekimai, 3 rezultatai, 4 valdymas,
#                 5 muzika, 6 efektai, 7 pilnas ekranas, 8 išeiti

MENU_ENEMIES = [(95, 120, 0), (705, 110, 1), (100, 330, 3),
                (705, 340, 5), (70, 540, 4), (735, 550, 2)]


def pct_label(name, v):
    if v <= 0.001:
        return "%s: IŠJUNGTA" % name
    return "%s:  <  %d%%  >" % (name, int(round(v * 100)))


def menu_labels(app):
    return ["Pradėti žaidimą",
            "Angaras:  %s" % progress.SHIPS[app.current_ship()]["name"],
            "Pasiekimai  (%d/%d)" % (len(SAVE.ach), len(progress.ACH)),
            "Rezultatai", "Valdymas",
            pct_label("Muzika", app.audio.music_vol),
            pct_label("Efektai", app.audio.sfx_vol),
            (("Kokybė:  " + ("ŽEMA" if cfg.LOW_FX else "AUKŠTA")) if app.touch_ui else "Pilnas ekranas"),
            "Išeiti"]


def draw_button(surf, rect, label, sel, t, size=22):
    r = rect.copy()
    if sel:
        r.inflate_ip(14 + int(4 * math.sin(t * 0.15)), 4)
        col = (255, 205, 60)
    else:
        col = (80, 165, 255)
    pygame.draw.rect(surf, OUT, r.move(0, 6), border_radius=20)
    pygame.draw.rect(surf, col, r, border_radius=20)
    light = (min(255, col[0] + 55), min(255, col[1] + 55), min(255, col[2] + 55))
    pygame.draw.rect(surf, light, (r.x + 12, r.y + 4, r.w - 24, r.h // 3), border_radius=8)
    pygame.draw.rect(surf, OUT, r, 4, border_radius=20)
    draw_text(surf, label, size, (255, 255, 255), r.center, "center", 3)


def draw_menu(surf, app):
    t = app.t
    app.plx.draw(surf)
    for i, (x, y, k) in enumerate(MENU_ENEMIES):
        yy = y + math.sin(t * 0.04 + i) * 12
        xx = x + math.cos(t * 0.03 + i * 2) * 10
        img = S.enemy[k][(t // 20 + i) % 2]
        img = pygame.transform.rotozoom(img, math.sin(t * 0.05 + i) * 8, 1.15)
        surf.blit(img, img.get_rect(center=(int(xx), int(yy))))
    for bx, by in app.demo:
        gfx.add_glow(surf, bx, by, 20, gfx.GLOW_COLS[0])
        surf.blit(S.bullet[0], S.bullet[0].get_rect(center=(int(bx), int(by))))
    sx = W // 2 + math.sin(t * 0.02) * 220
    gfx.draw_ship(surf, int(sx), 655 + int(math.sin(t * 0.06) * 6), t, math.cos(t * 0.02) * 6,
                  False, app.current_ship())
    bob = math.sin(t * 0.05) * 7
    gfx.add_glow(surf, W // 2, 120, int(150 + 10 * math.sin(t * 0.07)), (50, 35, 110))
    t1 = pygame.transform.rotozoom(gfx.text_surf("STAR", 92, (255, 225, 80), 6), math.sin(t * 0.03) * 2, 1)
    t2 = pygame.transform.rotozoom(gfx.text_surf("DEFENDER", 66, (110, 225, 255), 6), math.sin(t * 0.03 + 1) * 2, 1)
    surf.blit(t1, t1.get_rect(center=(W // 2, 70 + bob)))
    surf.blit(t2, t2.get_rect(center=(W // 2, 150 - bob)))
    for i in range(5):
        a = t * 0.03 + i * 1.256
        px = W // 2 + math.cos(a) * 300
        py = 115 + math.sin(a) * 40
        gfx.poly(surf, (255, 240, 120), gfx.star_pts(px, py, 9 + 2 * math.sin(t * 0.1 + i), 4, 5, a), 2)
    labels = menu_labels(app)
    for i, r in enumerate(MENU_RECTS):
        draw_button(surf, r, labels[i], i == app.sel, t)
    if SAVE.hi > 0:
        draw_text(surf, "Rekordas: %d" % SAVE.hi, 22, (255, 235, 110), (W - 16, H - 18), "midright", 2)
    if not app.audio.synth_ok and app.audio.reason:
        draw_text(surf, app.audio.reason, 16, (255, 160, 160), (14, H - 18), "midleft", 2)


# ----------------------------------------------------------------------------
#  Rezultatų lentelė
# ----------------------------------------------------------------------------
def draw_panel(surf, rect, alpha=225):
    p = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(p, (15, 10, 50, alpha), (0, 0, rect.w, rect.h), border_radius=28)
    pygame.draw.rect(p, (140, 120, 255), (0, 0, rect.w, rect.h), 5, border_radius=28)
    surf.blit(p, rect.topleft)


def draw_scores(surf, app, highlight=None):
    t = app.t
    app.plx.draw(surf)
    draw_panel(surf, pygame.Rect(70, 40, 660, 620))
    draw_text(surf, "REZULTATAI  -  TOP 10", 40, (255, 225, 80), (W // 2, 90), "center", 4)
    draw_text(surf, "Vieta", 18, (160, 160, 220), (115, 140), "midleft", 2)
    draw_text(surf, "Vardas", 18, (160, 160, 220), (190, 140), "midleft", 2)
    draw_text(surf, "Taškai", 18, (160, 160, 220), (545, 140), "midright", 2)
    draw_text(surf, "Banga", 18, (160, 160, 220), (680, 140), "midright", 2)
    if not SAVE.scores:
        draw_text(surf, "Dar nėra rezultatų - būk pirmas!", 24, (255, 255, 255), (W // 2, 360), "center", 3)
    for i, e in enumerate(SAVE.scores):
        y = 180 + i * 42
        col = (255, 255, 255)
        if i == 0:
            col = (255, 225, 80)
        elif i == 1:
            col = (210, 220, 240)
        elif i == 2:
            col = (240, 170, 110)
        if highlight == i:
            col = (110, 255, 200) if (t // 8) % 2 == 0 else (255, 255, 255)
            pygame.draw.rect(surf, (60, 90, 160), (95, y - 17, 610, 34), border_radius=10)
        draw_text(surf, "%d." % (i + 1), 24, col, (115, y), "midleft", 3)
        draw_text(surf, e["name"], 24, col, (190, y), "midleft", 3)
        draw_text(surf, "%d" % e["score"], 24, col, (545, y), "midright", 3)
        draw_text(surf, "%d" % e["wave"], 24, col, (680, y), "midright", 3)
    draw_text(surf, "Spausk bet kurį klavišą", 20, (180, 255, 190),
              (W // 2, 628 + int(math.sin(t * 0.1) * 3)), "center", 2)


# ----------------------------------------------------------------------------
#  Parduotuvė
# ----------------------------------------------------------------------------
SHOP_COUNT = 8          # 7 prekės + "Tęsti"
SHOP_RECTS = [pygame.Rect(100, 138 + i * 55, 600, 48) for i in range(SHOP_COUNT)]


def draw_shop(surf, app):
    g = app.game
    t = app.t
    draw_overlay(surf, 150)
    draw_text(surf, "PARDUOTUVĖ", 54, (255, 225, 80), (W // 2, 62 + math.sin(t * 0.06) * 4), "center", 5)
    surf.blit(S.coin[(t // 5) % 4], S.coin[0].get_rect(center=(W // 2 - 60, 112)))
    draw_text(surf, "%d" % g.gold, 32, (255, 215, 90), (W // 2 - 40, 112), "midleft", 3)
    for i, r in enumerate(SHOP_RECTS):
        sel = i == app.shop_sel
        rr = r.inflate(10, 4) if sel else r
        if i < SHOP_COUNT - 1:
            it = g.shop_item(i)
            can = (not it["maxed"]) and g.gold >= it["price"]
            base = (60, 80, 150) if can or it["maxed"] else (70, 50, 90)
            pygame.draw.rect(surf, OUT, rr.move(0, 4), border_radius=16)
            pygame.draw.rect(surf, (255, 205, 60) if sel else base, rr, border_radius=16)
            pygame.draw.rect(surf, OUT, rr, 4, border_radius=16)
            tc = (40, 30, 70) if sel else (255, 255, 255)
            draw_text(surf, it["name"], 21, (255, 255, 255), (rr.x + 18, rr.y + 16), "midleft", 3)
            draw_text(surf, it["desc"] + ("   [%s]" % it["info"] if it["info"] else ""), 14,
                      (225, 225, 255), (rr.x + 18, rr.y + 36), "midleft", 2)
            if it["maxed"]:
                draw_text(surf, "MAKS.", 22, (150, 255, 170), (rr.right - 18, rr.centery), "midright", 3)
            else:
                pc = (255, 215, 90) if can else (255, 120, 120)
                draw_text(surf, "%d" % it["price"], 24, pc, (rr.right - 50, rr.centery), "midright", 3)
                surf.blit(S.coin[0], S.coin[0].get_rect(center=(rr.right - 32, rr.centery)))
        else:
            col = (255, 205, 60) if sel else (90, 200, 120)
            pygame.draw.rect(surf, OUT, rr.move(0, 4), border_radius=16)
            pygame.draw.rect(surf, col, rr, border_radius=16)
            pygame.draw.rect(surf, OUT, rr, 4, border_radius=16)
            draw_text(surf, "Tęsti į kitą bangą", 26, (255, 255, 255), rr.center, "center", 3)
    draw_text(surf, "Aukštyn / žemyn - rinktis,  Enter - pirkti,  Esc - tęsti", 16, (200, 200, 255),
              (W // 2, H - 22), "center", 2)


# ----------------------------------------------------------------------------
#  Vardo įvedimas
# ----------------------------------------------------------------------------
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


NAME_CELLS = []
for _i, _ch in enumerate(ALPHABET):
    NAME_CELLS.append((_ch, pygame.Rect(80 + (_i % 10) * 64, 290 + (_i // 10) * 58, 60, 52)))
NAME_DEL = pygame.Rect(W // 2 - 210, 535, 180, 48)
NAME_OK = pygame.Rect(W // 2 + 30, 535, 180, 48)


def draw_entername(surf, app):
    g = app.game
    t = app.t
    draw_overlay(surf, 200)
    draw_text(surf, "TOP 10!", 54, (110, 225, 255), (W // 2, 55 + math.sin(t * 0.08) * 4), "center", 5)
    draw_text(surf, "Taškai: %d" % g.score, 30, (255, 235, 110), (W // 2, 112), "center", 4)
    draw_text(surf, "Įvesk savo vardą:", 24, (255, 255, 255), (W // 2, 160), "center", 3)
    box = pygame.Rect(W // 2 - 190, 188, 380, 66)
    pygame.draw.rect(surf, OUT, box.move(0, 5), border_radius=18)
    pygame.draw.rect(surf, (40, 40, 100), box, border_radius=18)
    pygame.draw.rect(surf, (255, 205, 60), box, 4, border_radius=18)
    txt = app.name
    r = draw_text(surf, txt, 38, (255, 255, 255), (box.x + 20, box.centery), "midleft", 3)
    if len(txt) < 10:
        cx = r.right + 4 if txt else box.x + 20
        draw_text(surf, ALPHABET[app.cur], 38, (255, 230, 120) if (t // 20) % 2 == 0 else (150, 150, 200),
                  (cx, box.centery), "midleft", 3)
    mp = getattr(app, "mouse_pos", (-1, -1))
    for ch, rc in NAME_CELLS:
        hot = rc.collidepoint(mp)
        pygame.draw.rect(surf, OUT, rc.move(0, 3), border_radius=10)
        pygame.draw.rect(surf, (255, 205, 60) if hot else (80, 165, 255), rc, border_radius=10)
        pygame.draw.rect(surf, OUT, rc, 3, border_radius=10)
        draw_text(surf, ch, 26, (255, 255, 255), rc.center, "center", 3)
    draw_button(surf, NAME_DEL, "Trinti", NAME_DEL.collidepoint(mp), t, 24)
    draw_button(surf, NAME_OK, "Gerai", NAME_OK.collidepoint(mp), t, 24)
    draw_text(surf, "Klaviatūra: rašyk vardą, Enter - patvirtinti", 17, (200, 200, 255),
              (W // 2, 616), "center", 2)
    draw_text(surf, "Valdiklis: aukštyn / žemyn - raidė, A - pridėti, B - trinti, Start - gerai",
              15, (200, 200, 255), (W // 2, 642), "center", 2)


# ----------------------------------------------------------------------------
#  Valdymas
# ----------------------------------------------------------------------------
def draw_help(surf, app):
    t = app.t
    app.plx.draw(surf)
    draw_panel(surf, pygame.Rect(50, 20, 700, 660))
    draw_text(surf, "VALDYMAS", 40, (255, 225, 80), (W // 2, 58), "center", 4)
    lines = ["Rodyklės arba W A S D  -  valdyti laivą",
             "Tarpas  -  šaudyti (laikant šaudo nuolat)",
             "B (arba X)  -  paleisti bombą",
             "P arba Esc  -  pauzė,   M  -  nutildyti,   F11  -  pilnas ekranas",
             "Valdiklis: lazdelė - judėti, A - šaudyti, B/X - bomba, Start - pauzė"]
    for i, ln in enumerate(lines):
        draw_text(surf, ln, 18, (255, 255, 255), (80, 108 + i * 28), "midleft", 2)
    draw_text(surf, "PRIZAI IR MONETOS", 30, (110, 225, 255), (W // 2, 270), "center", 3)
    info = [("W", "Ginklo patobulinimas (iki 5 lygio, 5-ame atsiranda dronai)"),
            ("S", "Skydas - sugeria vieną smūgį"),
            ("H", "Papildoma gyvybė"),
            ("B", "Bomba - išvalo ekraną ir smarkiai žeidžia priešus")]
    for i, (k, txt) in enumerate(info):
        y = 318 + i * 42
        surf.blit(S.power[k], S.power[k].get_rect(center=(95, y + int(math.sin(t * 0.1 + i) * 3))))
        draw_text(surf, txt, 17, (255, 255, 255), (125, y), "midleft", 2)
    surf.blit(S.coin[(t // 5) % 4], S.coin[0].get_rect(center=(95, 486)))
    draw_text(surf, "Moneta - po kiekvienos bangos perki patobulinimus parduotuvėje", 17,
              (255, 255, 255), (125, 486), "midleft", 2)
    tips = ["Bangos įvairios: formacijos, atakos iš viršaus, srautai, apsupimas, orbitos.",
            "Kombo didina taškų daugiklį (iki x5). Praskriesk arti kulkų - gausi bonusą!",
            "Maksimalus ginklas kaista - šaudyk pertraukomis, kitaip jis išsijungs.",
            "Skydininkų skydas slankioja - pataikyk, kai atsiveria. Pirma šauk gydytojus!",
            "Po 3-ios bangos - BONUSO ETAPAS, kas 5-a - BOSAS. Žaidimas prisitaiko prie tavo galios."]
    for i, ln in enumerate(tips):
        draw_text(surf, ln, 16, (255, 235, 150), (W // 2, 530 + i * 22), "center", 2)
    draw_text(surf, "Spausk bet kurį klavišą", 20, (180, 255, 190),
              (W // 2, 656 + int(math.sin(t * 0.1) * 3)), "center", 2)


# ----------------------------------------------------------------------------
#  Pauzė ir žaidimo pabaiga
# ----------------------------------------------------------------------------
def draw_overlay(surf, alpha=150):
    d = pygame.Surface((W, H), pygame.SRCALPHA)
    d.fill((5, 0, 30, alpha))
    surf.blit(d, (0, 0))


PAUSE_RESUME = pygame.Rect(W // 2 - 150, H // 2 + 10, 300, 52)
PAUSE_MENU = pygame.Rect(W // 2 - 150, H // 2 + 78, 300, 52)


def draw_pause(surf, app):
    draw_overlay(surf)
    draw_text(surf, "PAUZĖ", 84, (255, 225, 80), (W // 2, H // 2 - 70), "center", 6)
    mp = getattr(app, "mouse_pos", (-1, -1))
    draw_button(surf, PAUSE_RESUME, "Tęsti", PAUSE_RESUME.collidepoint(mp), app.t, 26)
    draw_button(surf, PAUSE_MENU, "Į meniu", PAUSE_MENU.collidepoint(mp), app.t, 26)
    draw_text(surf, "P arba Esc - tęsti,   Q - į meniu", 16, (200, 200, 255), (W // 2, H // 2 + 150), "center", 2)


GO_BTNS = [pygame.Rect(W // 2 - 170, 455 + i * 60, 340, 50) for i in range(3)]


def draw_gameover(surf, app):
    g = app.game
    t = app.t
    draw_overlay(surf, 170)
    draw_text(surf, "ŽAIDIMAS BAIGTAS", 58, (255, 110, 110), (W // 2, 160 + math.sin(t * 0.06) * 6), "center", 5)
    draw_text(surf, "Taškai: %d" % g.score, 42, (255, 235, 110), (W // 2, 255), "center", 4)
    draw_text(surf, "Banga: %d    Nušauta: %d    Geriausias kombo: %d" % (g.wave, g.kills, g.max_combo),
              22, (150, 255, 170), (W // 2, 310), "center", 3)
    if app.rank is not None:
        draw_text(surf, "Vieta lentelėje: #%d" % (app.rank + 1), 34, (110, 225, 255),
                  (W // 2, 375 + math.sin(t * 0.15) * 4), "center", 4)
    elif app.new_rec:
        draw_text(surf, "NAUJAS REKORDAS!", 36, (110, 225, 255),
                  (W // 2, 375 + math.sin(t * 0.15) * 4), "center", 4)
    else:
        draw_text(surf, "Rekordas: %d" % SAVE.hi, 26, (200, 200, 255), (W // 2, 375), "center", 3)
    if g.new_ach:
        draw_text(surf, "Nauji pasiekimai: " + ", ".join(g.new_ach[:3]), 20, (255, 230, 120),
                  (W // 2, 420), "center", 3)
    mp = getattr(app, "mouse_pos", (-1, -1))
    for r, label in zip(GO_BTNS, ("Žaisti iš naujo", "Rezultatų lentelė", "Meniu")):
        draw_button(surf, r, label, r.collidepoint(mp), t, 24)
    draw_text(surf, "Enter - iš naujo,  Tab - lentelė,  Esc - meniu", 15, (200, 200, 255),
              (W // 2, 655), "center", 2)


# ----------------------------------------------------------------------------
#  Angaras (laivų pasirinkimas)
# ----------------------------------------------------------------------------
_dark = {}


def dark_ship(i):
    if i not in _dark:
        img = S.player[i].copy()
        img.fill((130, 130, 130, 0), special_flags=pygame.BLEND_RGB_SUB)
        _dark[i] = img
    return _dark[i]


HANGAR_RECTS = [pygame.Rect(42 + i * 182, 120, 170, 470) for i in range(4)]
HANGAR_BACK = pygame.Rect(50, 614, 150, 42)


def draw_hangar(surf, app):
    t = app.t
    app.plx.draw(surf)
    draw_panel(surf, pygame.Rect(20, 30, 760, 640))
    draw_text(surf, "ANGARAS", 42, (255, 225, 80), (W // 2, 72), "center", 4)
    for i, r in enumerate(HANGAR_RECTS):
        sd = progress.SHIPS[i]
        unlocked = progress.ship_unlocked(SAVE, i)
        sel = i == app.hangar_sel
        chosen = i == app.current_ship()
        rr = r.inflate(8, 8) if sel else r
        pygame.draw.rect(surf, (35, 40, 100) if unlocked else (30, 25, 60), rr, border_radius=18)
        pygame.draw.rect(surf, (255, 205, 60) if sel else (110, 100, 200), rr, 5 if sel else 3, border_radius=18)
        cx = r.centerx
        img = S.player[i] if unlocked else dark_ship(i)
        img = pygame.transform.rotozoom(img, math.sin(t * 0.04 + i) * 6, 1.5)
        surf.blit(img, img.get_rect(center=(cx, r.y + 90 + int(math.sin(t * 0.06 + i) * 5))))
        draw_text(surf, sd["name"], 26, (255, 255, 255) if unlocked else (150, 150, 170), (cx, r.y + 185), "center", 3)
        draw_text(surf, sd["tag"], 17, (110, 225, 255) if unlocked else (120, 120, 150), (cx, r.y + 214), "center", 2)
        for k, ln in enumerate(sd["desc"]):
            draw_text(surf, ln, 15, (220, 220, 255) if unlocked else (130, 130, 160),
                      (cx, r.y + 255 + k * 21), "center", 2)
        # greitis / šaudymas
        spd = sd["speed"]
        rate = 1.0 / sd["cool"]
        for k, (lab, val) in enumerate((("Greitis", (spd - 0.8) / 0.5), ("Šaudymas", (rate - 0.8) / 0.5))):
            by = r.y + 335 + k * 26
            draw_text(surf, lab, 14, (200, 200, 230), (r.x + 12, by), "midleft", 2)
            pygame.draw.rect(surf, OUT, (r.x + 80, by - 6, 78, 12), border_radius=5)
            pygame.draw.rect(surf, (110, 225, 255) if unlocked else (90, 90, 120),
                             (r.x + 82, by - 4, int(74 * max(0.1, min(1.0, val))), 8), border_radius=4)
        if unlocked:
            if chosen:
                draw_text(surf, "PASIRINKTAS", 20, (150, 255, 170), (cx, r.y + 420), "center", 3)
            else:
                draw_text(surf, "Enter - rinktis", 17, (255, 255, 255), (cx, r.y + 420), "center", 2)
        else:
            a = progress.ACH_BY_ID[sd["unlock"]]
            cur, tgt = progress.ach_progress(SAVE, a)
            draw_text(surf, "UŽRAKINTA", 18, (255, 150, 150), (cx, r.y + 392), "center", 3)
            draw_text(surf, a["name"] + ":", 14, (255, 215, 120), (cx, r.y + 418), "center", 2)
            draw_text(surf, a["desc"], 13, (230, 230, 255), (cx, r.y + 438), "center", 2)
            draw_text(surf, "(%d / %d)" % (cur, tgt), 14, (230, 230, 255), (cx, r.y + 456), "center", 2)
    mp = getattr(app, "mouse_pos", (-1, -1))
    draw_button(surf, HANGAR_BACK, "Atgal", HANGAR_BACK.collidepoint(mp), t, 22)
    draw_text(surf, "Kairė / dešinė - rinktis,  Enter - patvirtinti,  Esc - atgal", 16, (200, 200, 255),
              (W // 2 + 60, 640), "center", 2)


# ----------------------------------------------------------------------------
#  Pasiekimai
# ----------------------------------------------------------------------------
def draw_ach(surf, app):
    t = app.t
    app.plx.draw(surf)
    draw_panel(surf, pygame.Rect(40, 30, 720, 640))
    draw_text(surf, "PASIEKIMAI  %d / %d" % (len(SAVE.ach), len(progress.ACH)), 38, (255, 225, 80),
              (W // 2, 72), "center", 4)
    for i, a in enumerate(progress.ACH):
        y = 130 + i * 50
        done = a["id"] in SAVE.ach
        pygame.draw.rect(surf, (45, 60, 130) if done else (28, 28, 60), (70, y - 22, 660, 44), border_radius=12)
        col = (255, 230, 90) if done else (90, 90, 120)
        gfx.poly(surf, col, gfx.star_pts(100, y, 15, 7), 2)
        draw_text(surf, a["name"], 21, (255, 255, 255) if done else (160, 160, 190), (130, y - 9), "midleft", 3)
        desc = a["desc"]
        si = progress.ship_for_achievement(a["id"])
        if si is not None:
            desc += "   (atrakina laivą: %s)" % progress.SHIPS[si]["name"]
        draw_text(surf, desc, 14, (220, 220, 255) if done else (140, 140, 170), (130, y + 11), "midleft", 2)
        if done:
            draw_text(surf, "Atlikta", 18, (150, 255, 170), (712, y), "midright", 3)
        else:
            cur, tgt = progress.ach_progress(SAVE, a)
            draw_text(surf, "%d / %d" % (cur, tgt), 18, (200, 200, 230), (712, y), "midright", 2)
    draw_text(surf, "Spausk bet kurį klavišą", 20, (180, 255, 190),
              (W // 2, 645 + int(math.sin(t * 0.1) * 3)), "center", 2)


# ----------------------------------------------------------------------------
#  Lietimo valdymas (telefonams / planšetėms)
# ----------------------------------------------------------------------------
BOMB_BTN = pygame.Rect(W - 125, H - 175, 110, 110)
PAUSE_BTN = pygame.Rect(W - 72, 56, 56, 56)


def draw_touch(surf, app):
    """Ekraniniai mygtukai: bomba ir pauzė, pirmosiomis sekundėmis - pagalbinis tekstas."""
    g = app.game
    c = BOMB_BTN.center
    ready = g.bombs > 0
    pygame.draw.circle(surf, OUT, c, 54)
    pygame.draw.circle(surf, (170, 100, 235) if ready else (70, 60, 100), c, 49)
    pygame.draw.circle(surf, (255, 255, 255) if ready else (120, 110, 150), c, 49, 3)
    icon = S.power["B"]
    surf.blit(icon, icon.get_rect(center=(c[0], c[1] - 8)))
    draw_text(surf, "x%d" % g.bombs, 20, (255, 255, 255), (c[0], c[1] + 28), "center", 3)
    r = PAUSE_BTN
    pygame.draw.rect(surf, OUT, r.inflate(6, 6), border_radius=14)
    pygame.draw.rect(surf, (80, 165, 255), r, border_radius=12)
    pygame.draw.rect(surf, (255, 255, 255), (r.x + 16, r.y + 14, 8, 28), border_radius=3)
    pygame.draw.rect(surf, (255, 255, 255), (r.x + 32, r.y + 14, 8, 28), border_radius=3)
    if app.hint_t < 420:
        draw_text(surf, "Laikyk pirštą ant ekrano - laivas seka ir šaudo", 22, (255, 255, 255),
                  (W // 2, H - 130), "center", 3)
        draw_text(surf, "Pakelk pirštą - šaudymas sustoja (ginklas atvėsta)", 17, (255, 235, 150),
                  (W // 2, H - 100), "center", 2)
