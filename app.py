# -*- coding: utf-8 -*-
"""Programos ciklas: būsenos, klaviatūra / pelė / valdiklis, piešimas."""
import math
import random
import sys
from types import SimpleNamespace

import pygame

from . import settings as cfg
from .settings import W, H, FPS, SAVE, MOBILE, TOUCH
from . import gfx, screens, progress
from .effects import Parallax, step_list
from .audio import Audio
from .game import Game

JOY_TYPES = tuple(getattr(pygame, n) for n in ("JOYAXISMOTION", "JOYHATMOTION", "JOYBUTTONDOWN")
                  if hasattr(pygame, n))


FINGER_TYPES = tuple(getattr(pygame, n) for n in ("FINGERDOWN", "FINGERMOTION", "FINGERUP")
                     if hasattr(pygame, n))


def clamp(v, a, b):
    return max(a, min(b, v))


class App:
    def __init__(self, screen):
        self.screen = screen
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.audio = Audio()
        self.plx = None
        self.state = "menu"
        self.sel = 0
        self.t = 0
        self.fade = 255
        self.game = None
        self.new_rec = False
        self.rank = None
        self.demo = []
        self.shop_sel = 0
        self.hangar_sel = 0
        self.name = ""
        self.cur = 0
        self.scores_back = "menu"
        self.joys = []
        self.axis_dir = {}
        self.touch_ui = TOUCH            # ekraniniai mygtukai (telefonas / planšetė)
        self.fingers = {}                # aktyvūs pirštai žaidimo metu
        self.hint_t = 0
        self.mouse_pos = (-1, -1)

    # ------------------------------------------------------------------
    def quit(self):
        pygame.quit()
        sys.exit()

    def current_ship(self):
        return SAVE.ship if SAVE.ship < len(progress.SHIPS) and progress.ship_unlocked(SAVE, SAVE.ship) else 0

    def cycle_ship(self, d):
        n = len(progress.SHIPS)
        i = self.current_ship()
        for _ in range(n):
            i = (i + d) % n
            if progress.ship_unlocked(SAVE, i):
                break
        SAVE.ship = i
        SAVE.write()
        self.audio.sfx("select")

    def init_joysticks(self):
        self.joys = []
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                j = pygame.joystick.Joystick(i)
                j.init()
                self.joys.append(j)
        except Exception:
            pass

    def load(self):
        bg = gfx.make_background(0)

        def cb(frac, msg):
            self.screen.blit(bg, (0, 0))
            gfx.draw_text(self.screen, "STAR DEFENDER", 64, (255, 225, 80), (W // 2, H // 2 - 60), "center", 5)
            gfx.draw_text(self.screen, msg, 24, (255, 255, 255), (W // 2, H // 2 + 20), "center", 3)
            pygame.draw.rect(self.screen, gfx.OUT, (W // 2 - 200, H // 2 + 60, 400, 26), border_radius=12)
            pygame.draw.rect(self.screen, (110, 225, 255),
                             (W // 2 - 196, H // 2 + 64, int(392 * frac), 18), border_radius=9)
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.quit()

        cb(0.0, "Kraunama...")
        self.audio.build(cb)
        self.plx = Parallax()
        self.init_joysticks()
        self.audio.apply_volume()
        self.audio.music("menu")

    # ------------------------------------------------------------------
    #  Būsenos
    # ------------------------------------------------------------------
    def set_state(self, s):
        self.state = s
        self.fade = 255

    def start_game(self):
        self.audio.set_duck(False)
        self.fingers.clear()
        self.hint_t = 0
        self.game = Game(self.audio, self.plx, self.current_ship())
        self.new_rec = False
        self.rank = None
        self.set_state("play")

    def to_menu(self):
        self.audio.set_duck(False)
        self.plx.set_theme(0)
        self.audio.music("menu")
        self.set_state("menu")

    def save_hi_on_exit(self):
        if self.game:
            self.game.commit()
            if self.game.score > SAVE.hi:
                SAVE.hi = self.game.score
                SAVE.write()

    def finish_game(self):
        g = self.game
        g.commit()
        self.new_rec = g.score > SAVE.hi
        self.rank = None
        self.audio.sfx("gameover")
        self.audio.music("menu")
        if SAVE.qualifies(g.score):
            self.name = ""
            self.cur = 0
            self.set_state("entername")
        else:
            self.set_state("gameover")

    def finish_name(self):
        name = self.name.strip() or "ŽAIDĖJAS"
        self.rank = SAVE.add_score(name, self.game.score, self.game.wave)
        self.audio.sfx("power")
        self.set_state("gameover")

    def end_shop(self):
        self.game.end_shop()
        self.set_state("play")

    def adjust(self, which, delta):
        if which == 5:
            self.audio.set_music_vol(round(self.audio.music_vol + delta, 2))
        else:
            self.audio.set_sfx_vol(round(self.audio.sfx_vol + delta, 2))
        self.audio.sfx("select")

    def activate(self, i, delta=0.1):
        self.audio.sfx("select")
        if i == 0:
            self.start_game()
        elif i == 1:
            self.hangar_sel = self.current_ship()
            self.set_state("hangar")
        elif i == 2:
            self.set_state("ach")
        elif i == 3:
            self.scores_back = "menu"
            self.set_state("scores")
        elif i == 4:
            self.set_state("help")
        elif i in (5, 6):
            self.adjust(i, delta)
        elif i == 7:
            if self.touch_ui:
                self.toggle_quality()
            else:
                pygame.display.toggle_fullscreen()
        elif i == 8:
            self.quit()

    def toggle_quality(self):
        """Žema / aukšta efektų kokybė (žema - greičiau silpnuose telefonuose)."""
        cfg.LOW_FX = not cfg.LOW_FX
        gfx._glow.clear()

    def pause_game(self):
        self.audio.set_duck(True)
        self.fingers.clear()
        self.state = "pause"

    def resume_game(self):
        self.audio.set_duck(False)
        self.fingers.clear()
        self.state = "play"

    # ------------------------------------------------------------------
    #  Lietimas
    # ------------------------------------------------------------------
    def to_logical(self, x, y):
        """Piršto koordinatės (0..1 lango) -> žaidimo koordinatės (su juostomis šonuose)."""
        try:
            ww, wh = pygame.display.get_window_size()
        except Exception:
            ww, wh = W, H
        sc = min(ww / W, wh / H)
        ox, oy = (ww - W * sc) / 2, (wh - H * sc) / 2
        return (x * ww - ox) / sc, (y * wh - oy) / sc

    def pointer(self, kind, fid, x, y):
        """Pirštas žaidimo metu: laivas seka pirštą, mygtukai - bomba ir pauzė."""
        g = self.game
        if kind == "down":
            if screens.BOMB_BTN.collidepoint((x, y)):
                self.fingers[fid] = {"role": "bomb"}
                g.use_bomb()
            elif screens.PAUSE_BTN.collidepoint((x, y)):
                self.pause_game()
            else:
                self.fingers[fid] = {"role": "move", "x": x, "y": y, "x0": x, "y0": y,
                                     "px0": g.px, "py0": g.py}
        elif kind == "move":
            f = self.fingers.get(fid)
            if f is not None and f["role"] == "move":
                f["x"], f["y"] = x, y
        else:
            self.fingers.pop(fid, None)

    def handle_finger(self, ev):
        self.touch_ui = True
        x, y = self.to_logical(ev.x, ev.y)
        fid = getattr(ev, "finger_id", 0)
        kind = {pygame.FINGERDOWN: "down", pygame.FINGERMOTION: "move"}.get(ev.type, "up")
        if self.state == "play":
            self.pointer(kind, fid, x, y)
            return
        if kind == "up":                                   # meniu: pirštas = pelė
            return
        pos = (int(x), int(y))
        self.handle(SimpleNamespace(type=pygame.MOUSEMOTION, pos=pos, buttons=(0, 0, 0), touch=False))
        if kind == "down":
            self.handle(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, pos=pos, button=1, touch=False))

    def handle_mouse_pointer(self, ev):
        """Pelė imituoja pirštą (--touch režimas kompiuteryje)."""
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.pointer("down", -1, *ev.pos)
        elif ev.type == pygame.MOUSEMOTION and ev.buttons[0]:
            self.pointer("move", -1, *ev.pos)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.pointer("up", -1, *ev.pos)

    # ------------------------------------------------------------------
    #  Valdiklis
    # ------------------------------------------------------------------
    def read_input(self):
        keys = pygame.key.get_pressed()
        dx = float((keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a]))
        dy = float((keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w]))
        fire = bool(keys[pygame.K_SPACE])
        for j in self.joys:
            try:
                ax, ay = j.get_axis(0), j.get_axis(1)
                if abs(ax) > 0.25:
                    dx += ax
                if abs(ay) > 0.25:
                    dy += ay
                if j.get_numhats() > 0:
                    hx, hy = j.get_hat(0)
                    dx += hx
                    dy -= hy
                if j.get_numbuttons() > 0 and j.get_button(0):
                    fire = True
            except Exception:
                pass
        g = self.game
        for f in self.fingers.values():                    # lietimas: laivas seka pirštą, šauna kol laikai
            if f["role"] == "move":
                tx = f["px0"] + (f["x"] - f["x0"]) * 1.2
                ty = f["py0"] + (f["y"] - f["y0"]) * 1.2
                dx += clamp((tx - g.px) / 20.0, -1.0, 1.0)
                dy += clamp((ty - g.py) / 20.0, -1.0, 1.0)
                fire = True
        return SimpleNamespace(dx=clamp(dx, -1.0, 1.0), dy=clamp(dy, -1.0, 1.0), fire=fire)

    def joy_key(self, ev):
        """Valdiklio įvykį paverčia klaviatūros klavišu (meniu naršymui)."""
        st, t = self.state, ev.type
        if t == pygame.JOYHATMOTION:
            x, y = ev.value
            if y > 0:
                return pygame.K_UP
            if y < 0:
                return pygame.K_DOWN
            if x < 0:
                return pygame.K_LEFT
            if x > 0:
                return pygame.K_RIGHT
            return None
        if t == pygame.JOYAXISMOTION:
            if ev.axis not in (0, 1):
                return None
            k = (getattr(ev, "instance_id", getattr(ev, "joy", 0)), ev.axis)
            d = 1 if ev.value > 0.6 else (-1 if ev.value < -0.6 else 0)
            old = self.axis_dir.get(k, 0)
            self.axis_dir[k] = d
            if d == 0 or d == old:
                return None
            if ev.axis == 0:
                return pygame.K_RIGHT if d > 0 else pygame.K_LEFT
            return pygame.K_DOWN if d > 0 else pygame.K_UP
        b = ev.button                                  # JOYBUTTONDOWN
        if st == "play":
            if b in (1, 2, 3):
                return pygame.K_b
            if b in (6, 7):
                return pygame.K_p
            return None
        if st == "entername":
            if b == 0:
                return pygame.K_TAB
            if b == 1:
                return pygame.K_BACKSPACE
            if b in (6, 7):
                return pygame.K_RETURN
            return None
        if st == "pause":
            if b in (0, 1, 7):
                return pygame.K_RETURN
            if b == 6:
                return pygame.K_q
            return None
        if b in (0, 7):
            return pygame.K_RETURN
        if b == 1:
            return pygame.K_ESCAPE
        if b == 3:
            return pygame.K_TAB
        return None

    # ------------------------------------------------------------------
    #  Įvykiai
    # ------------------------------------------------------------------
    def handle(self, ev):
        if ev.type == pygame.QUIT:
            if self.state in ("play", "pause", "shop"):
                self.save_hi_on_exit()
            self.quit()
        for n in ("JOYDEVICEADDED", "JOYDEVICEREMOVED"):
            if hasattr(pygame, n) and ev.type == getattr(pygame, n):
                self.init_joysticks()
                return
        if ev.type in JOY_TYPES:
            k = self.joy_key(ev)
            if k is None:
                return
            ev = SimpleNamespace(type=pygame.KEYDOWN, key=k, unicode="")
        for n in ("APP_WILLENTERBACKGROUND", "APP_DIDENTERBACKGROUND"):   # Android: programa į foną
            if hasattr(pygame, n) and ev.type == getattr(pygame, n):
                if self.state == "play":
                    self.pause_game()
                return
        if ev.type in FINGER_TYPES:
            self.handle_finger(ev)
            return
        if (ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP)
                and getattr(ev, "touch", False)):
            return                                          # lietimo imituojama pelė - jau apdorota
        if ev.type == pygame.KEYDOWN and ev.key == getattr(pygame, "K_AC_BACK", None):
            ev = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="")   # Android "atgal"
        if ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self.mouse_pos = ev.pos

        st = self.state
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            elif ev.key == pygame.K_m and st not in ("gameover", "entername"):
                self.audio.toggle_mute()

        if st == "menu":
            self.handle_menu(ev)
        elif st == "help":
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                if not (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_m, pygame.K_F11)):
                    self.audio.sfx("select")
                    self.set_state("menu")
        elif st == "hangar":
            self.handle_hangar(ev)
        elif st == "ach":
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                if not (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_m, pygame.K_F11)):
                    self.audio.sfx("select")
                    self.set_state("menu")
        elif st == "scores":
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                if not (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_m, pygame.K_F11)):
                    self.audio.sfx("select")
                    self.set_state(self.scores_back)
        elif st == "play":
            if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP) and self.touch_ui:
                self.handle_mouse_pointer(ev)
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.pause_game()
                elif ev.key in (pygame.K_b, pygame.K_x, pygame.K_LCTRL):
                    self.game.use_bomb()
        elif st == "pause":
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN):
                    self.resume_game()
                elif ev.key == pygame.K_q:
                    self.save_hi_on_exit()
                    self.to_menu()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if screens.PAUSE_MENU.collidepoint(ev.pos):
                    self.save_hi_on_exit()
                    self.to_menu()
                elif screens.PAUSE_RESUME.collidepoint(ev.pos):
                    self.resume_game()
        elif st == "shop":
            self.handle_shop(ev)
        elif st == "entername":
            self.handle_name(ev)
        elif st == "gameover":
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.start_game()
                elif ev.key == pygame.K_ESCAPE:
                    self.to_menu()
                elif ev.key == pygame.K_TAB:
                    self.scores_back = "gameover"
                    self.set_state("scores")
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, r in enumerate(screens.GO_BTNS):
                    if r.collidepoint(ev.pos):
                        if i == 0:
                            self.start_game()
                        elif i == 1:
                            self.scores_back = "gameover"
                            self.set_state("scores")
                        else:
                            self.to_menu()

    def handle_menu(self, ev):
        n = screens.MENU_COUNT
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % n
                self.audio.sfx("move")
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % n
                self.audio.sfx("move")
            elif ev.key in (pygame.K_LEFT, pygame.K_a) and self.sel in (5, 6):
                self.adjust(self.sel, -0.1)
            elif ev.key in (pygame.K_RIGHT, pygame.K_d) and self.sel in (5, 6):
                self.adjust(self.sel, 0.1)
            elif ev.key in (pygame.K_LEFT, pygame.K_a) and self.sel == 1:
                self.cycle_ship(-1)
            elif ev.key in (pygame.K_RIGHT, pygame.K_d) and self.sel == 1:
                self.cycle_ship(1)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.activate(self.sel)
        elif ev.type == pygame.MOUSEMOTION:
            for i, r in enumerate(screens.MENU_RECTS):
                if r.collidepoint(ev.pos) and self.sel != i:
                    self.sel = i
                    self.audio.sfx("move")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, r in enumerate(screens.MENU_RECTS):
                if r.collidepoint(ev.pos):
                    self.sel = i
                    self.activate(i, -0.1 if ev.pos[0] < r.centerx else 0.1)

    def handle_hangar(self, ev):
        n = len(progress.SHIPS)
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_LEFT, pygame.K_a):
                self.hangar_sel = (self.hangar_sel - 1) % n
                self.audio.sfx("move")
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.hangar_sel = (self.hangar_sel + 1) % n
                self.audio.sfx("move")
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.pick_ship(self.hangar_sel)
            elif ev.key == pygame.K_ESCAPE:
                self.set_state("menu")
        elif ev.type == pygame.MOUSEMOTION:
            for i, r in enumerate(screens.HANGAR_RECTS):
                if r.collidepoint(ev.pos) and self.hangar_sel != i:
                    self.hangar_sel = i
                    self.audio.sfx("move")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if screens.HANGAR_BACK.collidepoint(ev.pos):
                self.audio.sfx("select")
                self.set_state("menu")
                return
            for i, r in enumerate(screens.HANGAR_RECTS):
                if r.collidepoint(ev.pos):
                    self.hangar_sel = i
                    self.pick_ship(i)

    def pick_ship(self, i):
        if progress.ship_unlocked(SAVE, i):
            SAVE.ship = i
            SAVE.write()
            self.audio.sfx("power")
        else:
            self.audio.sfx("denied")

    def shop_action(self, i):
        if i == screens.SHOP_COUNT - 1:
            self.end_shop()
        else:
            self.game.buy(i)

    def handle_shop(self, ev):
        n = screens.SHOP_COUNT
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.shop_sel = (self.shop_sel - 1) % n
                self.audio.sfx("move")
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.shop_sel = (self.shop_sel + 1) % n
                self.audio.sfx("move")
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.shop_action(self.shop_sel)
            elif ev.key == pygame.K_ESCAPE:
                self.end_shop()
        elif ev.type == pygame.MOUSEMOTION:
            for i, r in enumerate(screens.SHOP_RECTS):
                if r.collidepoint(ev.pos) and self.shop_sel != i:
                    self.shop_sel = i
                    self.audio.sfx("move")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, r in enumerate(screens.SHOP_RECTS):
                if r.collidepoint(ev.pos):
                    self.shop_sel = i
                    self.shop_action(i)

    def name_click(self, pos):
        for ch, rc in screens.NAME_CELLS:
            if rc.collidepoint(pos):
                if len(self.name) < 10:
                    self.name += ch
                    self.audio.sfx("select")
                return
        if screens.NAME_DEL.collidepoint(pos):
            self.name = self.name[:-1]
            self.audio.sfx("move")
        elif screens.NAME_OK.collidepoint(pos):
            self.finish_name()

    def handle_name(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.name_click(ev.pos)
            return
        if ev.type != pygame.KEYDOWN:
            return
        k = ev.key
        alpha = screens.ALPHABET
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.finish_name()
        elif k == pygame.K_BACKSPACE:
            self.name = self.name[:-1]
            self.audio.sfx("move")
        elif k == pygame.K_TAB:                       # valdiklio "A" - pridėti pasirinktą raidę
            if len(self.name) < 10:
                self.name += alpha[self.cur]
                self.audio.sfx("select")
        elif k == pygame.K_UP:
            self.cur = (self.cur - 1) % len(alpha)
            self.audio.sfx("move")
        elif k == pygame.K_DOWN:
            self.cur = (self.cur + 1) % len(alpha)
            self.audio.sfx("move")
        else:
            ch = getattr(ev, "unicode", "") or ""
            if ch and len(self.name) < 10 and (ch.isalnum() or ch in " -_"):
                self.name += ch.upper()
                self.audio.sfx("select")

    # ------------------------------------------------------------------
    #  Atnaujinimas ir piešimas
    # ------------------------------------------------------------------
    def update(self):
        if self.state != "pause":
            self.plx.update()
        if self.fade > 0:
            self.fade = max(0, self.fade - 14)
        st = self.state
        if st == "menu":
            if self.t % 22 == 0:
                self.demo.append([W // 2 + math.sin(self.t * 0.02) * 220, 625.0])
            for b in self.demo:
                b[1] -= 10
            self.demo = [b for b in self.demo if b[1] > -30]
        elif st == "play":
            self.hint_t += 1
            self.game.update(self.read_input())
            if self.game.over:
                self.finish_game()
            elif self.game.shop_pending:
                self.shop_sel = 0
                self.audio.music("menu")
                self.set_state("shop")
        elif st in ("shop", "gameover", "entername"):
            step_list(self.game.fx)
            step_list(self.game.pops)

    def draw(self):
        c = self.canvas
        st = self.state
        if st == "menu":
            screens.draw_menu(c, self)
        elif st == "help":
            screens.draw_help(c, self)
        elif st == "hangar":
            screens.draw_hangar(c, self)
        elif st == "ach":
            screens.draw_ach(c, self)
        elif st == "scores":
            hl = self.rank if self.scores_back == "gameover" else None
            screens.draw_scores(c, self, hl)
        else:
            self.plx.draw(c)
            self.game.draw(c)
            if st == "pause":
                screens.draw_pause(c, self)
            elif st == "shop":
                screens.draw_shop(c, self)
            elif st == "entername":
                screens.draw_entername(c, self)
            elif st == "gameover":
                screens.draw_gameover(c, self)
        if st == "play" and self.touch_ui:
            screens.draw_touch(c, self)
        if not cfg.LOW_FX:
            c.blit(gfx.S.vignette, (0, 0))
        if self.fade > 0:
            ov = pygame.Surface((W, H))
            ov.set_alpha(self.fade)
            c.blit(ov, (0, 0))
        if st == "play" and self.game.shake > 0:
            self.screen.fill((0, 0, 0))
            s = min(6, 1 + self.game.shake // 4)
            self.screen.blit(c, (random.randint(-s, s), random.randint(-s, s)))
        else:
            self.screen.blit(c, (0, 0))
        pygame.display.flip()

    def loop(self):
        while True:
            self.clock.tick(FPS)
            self.t += 1
            for ev in pygame.event.get():
                self.handle(ev)
            self.update()
            self.draw()


def run():
    if MOBILE:
        pygame.mixer.pre_init(22050, -16, 2, 1024)        # mažesnė apkrova telefonui
    else:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.display.set_caption("Star Defender")
    flags = pygame.SCALED | (pygame.FULLSCREEN if MOBILE else 0)
    try:
        screen = pygame.display.set_mode((W, H), flags)
    except Exception:
        screen = pygame.display.set_mode((W, H))
    gfx.init()
    app = App(screen)
    app.load()
    app.loop()
