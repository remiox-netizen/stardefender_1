# -*- coding: utf-8 -*-
"""
Garsas: visa muzika ir efektai sintezuojami kodu (numpy), be išorinių failų.

Jei norite SAVO muzikos - įdėkite failus į assets/music/ :
    menu.ogg   - meniu muzika
    game1.ogg  - žaidimo muzika (nelyginės bangos)   [arba tiesiog game.ogg]
    game2.ogg  - žaidimo muzika (lyginės bangos)     [arba tiesiog game.ogg]
    boss.ogg   - boso kovos muzika
Palaikomi formatai: .ogg .mp3 .wav .flac  (rekomenduojamas .ogg)
"""
import hashlib
import math
import os
import random

import pygame

from .settings import MUSIC_DIR, CACHE_DIR, SAVE

try:
    import numpy as np
except Exception:                       # numpy neįdiegtas - sintezė išjungta
    np = None

SR = 44100
AUDIO_VERSION = "1"                 # pakeisk, jei keiti muzikos sintezę (nuvalo talpyklą)
EXT = (".ogg", ".mp3", ".wav", ".flac")
MUSIC_GAIN = 0.6


# ----------------------------------------------------------------------------
#  Sintezės pagrindai
# ----------------------------------------------------------------------------
_rng = None


def rng():
    global _rng
    if _rng is None:
        _rng = np.random.default_rng(12345)
    return _rng


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def tt(n):
    return np.arange(n) / SR


def wave(kind, freq, t):
    ph = 2 * np.pi * freq * t
    if kind == "sine":
        return np.sin(ph)
    if kind == "tri":
        return (2 / np.pi) * np.arcsin(np.sin(ph))
    if kind == "square":
        w = np.zeros_like(t)
        for k in range(1, 14, 2):
            if freq * k < SR / 2:
                w += np.sin(ph * k) / k
        return w * (4 / np.pi) * 0.6
    # saw
    w = np.zeros_like(t)
    for k in range(1, 12):
        if freq * k < SR / 2:
            w += np.sin(ph * k) / k
    return w * (2 / np.pi)


def note(freq, dur, kind="tri", decay=5.0, attack=0.004, amp=1.0, rel=0.01):
    n = int(SR * dur)
    t = tt(n)
    env = np.minimum(1.0, t / attack) * np.exp(-decay * t)
    r = int(SR * rel)
    if 0 < r < n:
        env[-r:] *= np.linspace(1, 0, r)
    return wave(kind, freq, t) * env * amp


def pad_note(freq, dur, amp=1.0):
    n = int(SR * dur)
    t = tt(n)
    w = (np.sin(2 * np.pi * freq * t) + np.sin(2 * np.pi * freq * 1.004 * t)
         + 0.5 * np.sin(2 * np.pi * freq * 0.996 * t + 1.0)
         + 0.25 * np.sin(2 * np.pi * freq * 2 * t)) * 0.4
    att, rel = 0.25, 0.35
    env = np.minimum(1.0, t / att) * np.minimum(1.0, (dur - t) / rel)
    return w * np.clip(env, 0, 1) * amp


def kick(vol=1.0):
    n = int(SR * 0.30)
    t = tt(n)
    f = 42 + 120 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-t * 9) + 0.3 * np.exp(-t * 200) * rng().standard_normal(n)) * vol


def snare(vol=1.0):
    n = int(SR * 0.22)
    t = tt(n)
    nz = np.diff(rng().standard_normal(n), prepend=0)
    return (nz * 0.45 * np.exp(-t * 22) + np.sin(2 * np.pi * 185 * t) * 0.5 * np.exp(-t * 28)) * vol


def hat(open_=False, vol=1.0):
    n = int(SR * (0.22 if open_ else 0.06))
    t = tt(n)
    nz = np.diff(rng().standard_normal(n), prepend=0)
    return nz * np.exp(-t * (18 if open_ else 70)) * 0.35 * vol


def tom(freq, vol=1.0):
    n = int(SR * 0.25)
    t = tt(n)
    f = freq * (1 - 0.4 * t / 0.25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) * vol


def put(buf, sig, start, gain=1.0, pan=0.0):
    """Įrašo signalą į stereo buferį (su apvijimu - sklandžiam ciklui)."""
    n = len(sig)
    N = len(buf)
    l = math.cos((pan + 1) * math.pi / 4) * gain
    r = math.sin((pan + 1) * math.pi / 4) * gain
    start %= N
    end = start + n
    if end <= N:
        buf[start:end, 0] += sig * l
        buf[start:end, 1] += sig * r
    else:
        k = N - start
        buf[start:, 0] += sig[:k] * l
        buf[start:, 1] += sig[:k] * r
        m = min(n - k, N)
        buf[:m, 0] += sig[k:k + m] * l
        buf[:m, 1] += sig[k:k + m] * r


def to_bytes(arr):
    """float masyvas (N,2) -> neapdoroti mikserio baitai (pagal mikserio formatą)."""
    _, fmt, ch = pygame.mixer.get_init()
    arr = np.clip(arr, -1.0, 1.0)
    if ch == 1:
        arr = arr.mean(axis=1)
    if fmt == 32:                                    # float32 mikseris
        data = arr.astype(np.float32)
    elif fmt == 16:                                  # unsigned 16 bit
        data = ((arr + 1.0) * 32767).astype(np.uint16)
    else:                                            # įprastas signed 16 bit
        data = (arr * 32767).astype(np.int16)
    return np.ascontiguousarray(data).tobytes()


def to_sound(arr):
    """float masyvas (N,2) -> pygame.mixer.Sound"""
    return pygame.mixer.Sound(buffer=to_bytes(arr))


def mono_to_stereo(sig):
    return np.stack([sig, sig], axis=1)


# ----------------------------------------------------------------------------
#  Muzikos kūrimas
# ----------------------------------------------------------------------------
TRACKS = {
    "menu":  dict(bpm=92,  prog=[(45, "m"), (41, "M"), (48, "M"), (43, "M")], style="calm", seed=1),
    "game1": dict(bpm=128, prog=[(50, "m"), (46, "M"), (53, "M"), (48, "M")], style="drive", seed=2),
    "game2": dict(bpm=136, prog=[(52, "m"), (48, "M"), (55, "M"), (50, "M")], style="drive2", seed=3),
    "boss":  dict(bpm=150, prog=[(48, "m"), (44, "M"), (46, "M"), (43, "M")], style="boss", seed=4),
    "bonus": dict(bpm=140, prog=[(48, "M"), (43, "M"), (45, "m"), (41, "M")], style="drive2", seed=5),
}

STYLES = {
    "calm": dict(
        kick=[0, 8], snare=[], hat=[4, 12], ohat=[], gains=(0.45, 0.8, 1.0, 0.8),
        arp={s: i for s, i in zip(range(0, 16, 2), [0, 2, 4, 2, 1, 3, 5, 3])},
        bass={0: 0}, bass_len=15, melody=True, mel_vol=0.5, swing=False),
    "drive": dict(
        kick=[0, 4, 8, 12], snare=[4, 12], hat=list(range(0, 16, 2)), ohat=[2, 6, 10, 14],
        gains=(0.85, 0.9, 0.65, 0.8),
        arp={s: i for s, i in zip(range(16), [0, 2, 4, 2, 5, 4, 2, 1, 0, 2, 4, 2, 5, 4, 3, 1])},
        bass={0: 0, 2: 0, 4: 12, 6: 0, 8: 0, 10: 0, 12: 12, 14: 0}, bass_len=2, melody=True,
        mel_vol=0.7),
    "drive2": dict(
        kick=[0, 4, 8, 10, 12], snare=[4, 12, 15], hat=list(range(0, 16, 2)), ohat=[6, 14],
        gains=(0.85, 0.9, 0.6, 0.8),
        arp={s: i for s, i in zip(range(0, 16, 2), [0, 3, 5, 3, 1, 4, 2, 4])},
        bass={s: o for s, o in zip(range(16), [0, 0, 12, 0, 0, 12, 0, 0, 0, 0, 12, 0, 0, 12, 0, 12])},
        bass_len=1, melody=True, mel_vol=0.7),
    "boss": dict(
        kick=[0, 3, 6, 8, 10, 12, 14], snare=[4, 12, 14], hat=list(range(16)), ohat=[2, 10],
        gains=(1.0, 1.0, 0.55, 0.85),
        arp={s: i for s, i in zip(range(16), [0, 4, 2, 5, 0, 4, 2, 5, 1, 4, 3, 5, 1, 4, 3, 5])},
        bass={s: o for s, o in zip(range(16), [0, 0, 0, 12, 0, 0, 0, 12, 0, 0, 0, 12, 0, 0, 12, 0])},
        bass_len=1, melody=True, mel_vol=0.75),
}

MEL_RHYTHMS = [
    [(0, 3), (3, 3), (6, 2), (8, 4), (12, 4)],
    [(0, 2), (2, 2), (4, 4), (8, 2), (10, 2), (12, 4)],
    [(0, 4), (4, 2), (6, 2), (8, 3), (11, 1), (12, 4)],
]


def build_track(spec):
    return to_sound(render_track(spec))


def render_track(spec):
    bpm, prog = spec["bpm"], spec["prog"]
    st = STYLES[spec["style"]]
    beat = 60.0 / bpm
    s16 = beat / 4
    reps = 4
    nbars = len(prog) * reps
    N = int(SR * beat * 4 * nbars)
    names = ("drums", "bass", "pad", "lead")
    bufs = {k: np.zeros((N, 2), dtype=np.float32) for k in names}
    r = random.Random(spec["seed"])
    kicks = []

    def at(step):
        return int(round(step * s16 * SR))

    tonic = prog[0][0] + 24
    ivs = (0, 3, 5, 7, 10) if prog[0][1] == "m" else (0, 2, 4, 7, 9)   # minorinė / mažorinė pentatonika
    scale_notes = [tonic + 12 * o + i for o in (-1, 0) for i in ivs]
    mel_idx = 6

    for bar in range(nbars):
        rep = bar // len(prog)
        root, q = prog[bar % len(prog)]
        ct = [0, 3, 7] if q == "m" else [0, 4, 7]
        tones = [root + 12 + c for c in ct] + [root + 24 + c for c in ct]
        s0 = bar * 16
        d, b, p, ld = bufs["drums"], bufs["bass"], bufs["pad"], bufs["lead"]

        # ritmas
        for s in st["kick"]:
            put(d, kick(1.0), at(s0 + s), 1.0)
            kicks.append(at(s0 + s))
        snare_steps = list(st["snare"]) if rep >= 1 else []
        if spec["style"] == "calm" and rep >= 2:
            snare_steps = [12]
        for s in snare_steps:
            put(d, snare(0.7 if spec["style"] == "calm" else 1.0), at(s0 + s), 0.8)
        if rep == 3 and bar % 4 == 3:                         # užbaigimo "fill"
            for s in (12, 13, 14, 15):
                put(d, snare(0.8), at(s0 + s), 0.7)
        for s in st["hat"]:
            put(d, hat(False, 0.6 if s % 4 else 0.9), at(s0 + s), 0.6, pan=0.25)
        if rep >= 2:
            for s in st["ohat"]:
                put(d, hat(True, 0.8), at(s0 + s), 0.6, pan=-0.25)

        # bosas
        bf = mtof(root - 12)
        if spec["style"] == "calm":
            put(b, note(bf, beat * 4 * 0.95, "sine", decay=0.6, amp=0.9), at(s0), 1.0)
        else:
            for s, o in st["bass"].items():
                f = mtof(root - 12 + o)
                dur = s16 * (st["bass_len"] * 0.9 if st["bass_len"] > 1 else 0.85)
                kind = "saw" if spec["style"] == "boss" else "square"
                sig = note(f, dur, kind, decay=7.0, amp=0.55) + note(f, dur, "sine", decay=7.0, amp=0.6)
                put(b, sig, at(s0 + s), 0.8)

        # pad
        for tn in tones[:3]:
            put(p, pad_note(mtof(tn), beat * 4 * 1.05, 0.5), at(s0), 0.55,
                pan=r.uniform(-0.6, 0.6))

        # arpeggio
        for s, idx in st["arp"].items():
            kind = "tri"
            sig = note(mtof(tones[idx]), s16 * 3, kind, decay=9.0, amp=0.5) \
                + 0.25 * note(mtof(tones[idx] + 12), s16 * 3, "sine", decay=11.0, amp=0.5)
            put(ld, sig, at(s0 + s), 0.55, pan=0.45 if (s // 2) % 2 else -0.45)

        # melodija (nuo 3-ojo pasikartojimo)
        if st["melody"] and rep >= 2:
            for k, (s, dur) in enumerate(r.choice(MEL_RHYTHMS)):
                mel_idx = max(0, min(len(scale_notes) - 1, mel_idx + r.choice([-2, -1, -1, 0, 1, 1, 2])))
                if bar % 4 == 3 and k == len(MEL_RHYTHMS[0]) - 1:
                    mel_idx = 5
                f = mtof(scale_notes[mel_idx])
                sig = 0.6 * note(f, s16 * dur * 1.1, "tri", decay=2.5, amp=0.8) \
                    + 0.4 * note(f, s16 * dur * 1.1, "saw", decay=2.5, amp=0.5)
                put(ld, sig, at(s0 + s), st["mel_vol"], pan=0.1)

    # aido efektas (ping-pong), apvyniotas ratu
    lead = bufs["lead"]
    d1 = int(s16 * 3 * SR)
    echo = np.roll(lead, d1, axis=0)[:, ::-1] * 0.35 + np.roll(lead, d1 * 2, axis=0) * 0.18
    lead = lead + echo

    # "sidechain" pumpavimas nuo bosinio būgno
    duck = np.ones(N, dtype=np.float32)
    seg = int(SR * 0.25)
    curve = 1 - 0.55 * np.exp(-np.arange(seg) / SR * 9)
    for k in kicks:
        end = min(N, k + seg)
        duck[k:end] = np.minimum(duck[k:end], curve[:end - k])
    dg, bg, pg, lg = st["gains"]
    mix = (bufs["drums"] * dg + bufs["bass"] * duck[:, None] * bg
           + bufs["pad"] * duck[:, None] * pg + lead * (0.7 + 0.3 * duck[:, None]) * lg)
    peak = float(np.max(np.abs(mix))) or 1.0
    mix = mix / peak * 0.9
    mix = np.tanh(mix * 1.25) / np.tanh(1.25)
    return mix


# ----------------------------------------------------------------------------
#  Garso efektai
# ----------------------------------------------------------------------------
def laser(f0, f1, dur, kind="square", vol=0.3):
    n = int(SR * dur)
    t = tt(n)
    f = np.linspace(f0, f1, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    w = np.sin(ph)
    if kind == "square":
        w = 0.5 * np.sign(w) + 0.5 * w
    elif kind == "saw":
        w = 2 * ((ph / (2 * np.pi)) % 1.0) - 1
    env = np.minimum(1.0, t / 0.002) * (1 - t / dur) ** 1.5
    return w * env * vol


def boom(dur, low, vol, lp):
    n = int(SR * dur)
    t = tt(n)
    nz = rng().standard_normal(n)
    nz = np.convolve(nz, np.ones(lp) / lp, mode="same") * math.sqrt(lp)
    f = low * np.exp(-t * 3) + 28
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = np.exp(-t * (3.5 / dur)) * (1 - t / dur)
    return (nz * 0.7 + sub * 0.9) * env * vol


def arp_seq(midis, dur=0.07, kind="tri", decay=8.0, vol=0.3):
    return np.concatenate([note(mtof(m), dur, kind, decay=decay, amp=vol) for m in midis])


def siren():
    parts = []
    for _ in range(2):
        parts.append(laser(500, 850, 0.3, "square", 0.25))
        parts.append(laser(850, 500, 0.3, "square", 0.25))
    return np.concatenate(parts)


def warble():
    n = int(SR * 0.4)
    t = tt(n)
    f = 900 + 200 * np.sin(2 * np.pi * 12 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - t / 0.4) * 0.18


def layer(*sigs):
    """Sudeda skirtingo ilgio signalus (trumpesnius papildo tyla) - veikia su bet kokiu diskretizavimu."""
    n = max(len(x) for x in sigs)
    out = np.zeros(n)
    for x in sigs:
        out[:len(x)] += x
    return out


def mono(sig):
    return mono_to_stereo(np.asarray(sig, dtype=float))


def build_sfx():
    sfx = {}
    for lv in range(1, 6):
        sfx["shoot%d" % lv] = to_sound(mono(laser(800 + lv * 130, 280 + lv * 40, 0.11, "square", 0.17)))
    sfx["hit"] = to_sound(mono(laser(800, 400, 0.05, "sine", 0.25)))
    sfx["boom_s"] = [to_sound(mono(boom(0.35, 160, 0.55, 5))), to_sound(mono(boom(0.38, 140, 0.55, 7)))]
    sfx["boom_m"] = [to_sound(mono(boom(0.55, 130, 0.65, 7))), to_sound(mono(boom(0.6, 110, 0.65, 9)))]
    sfx["boom_l"] = to_sound(mono(boom(1.4, 90, 0.9, 11)))
    sfx["power"] = to_sound(mono(arp_seq([72, 76, 79, 84, 88], 0.07)))
    sfx["shield"] = to_sound(mono(laser(300, 1300, 0.3, "sine", 0.3)))
    sfx["bomb"] = to_sound(mono(layer(boom(1.1, 70, 0.9, 14), laser(1600, 60, 0.9, "square", 0.18))))
    sfx["hurt"] = to_sound(mono(laser(500, 70, 0.4, "square", 0.4)))
    sfx["select"] = to_sound(mono(laser(600, 1000, 0.07, "sine", 0.25)))
    sfx["move"] = to_sound(mono(laser(800, 840, 0.03, "sine", 0.15)))
    sfx["wave"] = to_sound(mono(arp_seq([67, 72, 76, 79], 0.09, vol=0.28)))
    sfx["combo"] = to_sound(mono(arp_seq([84, 88, 91], 0.05, vol=0.28)))
    sfx["life"] = to_sound(mono(arp_seq([72, 79, 84, 91, 96], 0.07, vol=0.3)))
    sfx["boss_warn"] = to_sound(mono(siren()))
    sfx["ufo"] = to_sound(mono(warble()))
    sfx["gameover"] = to_sound(mono(arp_seq([67, 64, 60, 55, 48], 0.2, "tri", 3.0, 0.35)))
    sfx["coin"] = to_sound(mono(arp_seq([88, 95], 0.045, "tri", 6.0, 0.22)))
    sfx["denied"] = to_sound(mono(laser(220, 120, 0.14, "square", 0.25)))
    sfx["graze"] = to_sound(mono(laser(1500, 2200, 0.05, "sine", 0.18)))
    sfx["ach"] = to_sound(mono(arp_seq([72, 76, 79, 84, 79, 84, 88], 0.08, "tri", 5.0, 0.3)))
    sfx["clang"] = to_sound(mono(laser(1800, 900, 0.09, "square", 0.22)))
    sfx["overheat"] = to_sound(mono(layer(boom(0.5, 400, 0.5, 3), laser(900, 200, 0.45, "saw", 0.2))))
    sfx["cool"] = to_sound(mono(arp_seq([79, 84], 0.07, "sine", 6.0, 0.25)))
    sfx["tp"] = to_sound(mono(laser(300, 1600, 0.12, "sine", 0.25)))
    sfx["heal"] = to_sound(mono(arp_seq([76, 80, 83], 0.06, "sine", 6.0, 0.22)))
    sfx["warn"] = to_sound(mono(arp_seq([81, 76, 81, 76], 0.07, "square", 4.0, 0.2)))
    return sfx


# ----------------------------------------------------------------------------
#  Valdiklis
# ----------------------------------------------------------------------------
class Audio:
    def __init__(self):
        global SR
        self.mixer_ok = pygame.mixer.get_init() is not None
        self.synth_ok = self.mixer_ok and np is not None
        if self.mixer_ok:
            SR = pygame.mixer.get_init()[0]
        self.sfx_snd = {}
        self.tracks = {}
        self.cur = None
        self.ch = None
        self.muted = False
        self.duck = False
        self.music_vol = SAVE.music
        self.sfx_vol = SAVE.sfx
        self.reason = ""
        if not self.mixer_ok:
            self.reason = "Garso įrenginys nerastas (mixer neįsijungė)"
        elif np is None:
            self.reason = "Garsui reikia numpy:  pip install numpy"
        if self.reason:
            print("[Star Defender] " + self.reason)

    def build(self, cb=None):
        if not self.mixer_ok:
            return
        pygame.mixer.set_num_channels(20)
        pygame.mixer.set_reserved(1)
        self.ch = pygame.mixer.Channel(0)
        if not self.synth_ok:
            return
        try:
            if cb:
                cb(0.05, "Kuriami garso efektai...")
            self.sfx_snd = build_sfx()
            names = list(TRACKS)
            for i, name in enumerate(names):
                if self.find_ext(name) is None:     # išorinė muzika pakeičia sintezuotą
                    if cb:
                        cb(0.2 + 0.8 * i / len(names), "Kuriama muzika: %s..." % name)
                    self.tracks[name] = self.track_sound(name)
            if cb:
                cb(1.0, "Paruošta!")
        except Exception as e:                      # garsas neturi nulaužti žaidimo
            self.synth_ok = False
            self.reason = "Garso kūrimo klaida: %s" % e
            print("[Star Defender] " + self.reason)

    def track_sound(self, name):
        """Sintezuota muzika kešuojama diske - kitą kartą paleidus kraunasi akimirksniu."""
        spec = TRACKS[name]
        info = pygame.mixer.get_init()
        raw = "%r|%r|%d|%r|%s" % (spec, STYLES[spec["style"]], SR, info[1:], AUDIO_VERSION)
        key = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
        path = os.path.join(CACHE_DIR, "%s_%s.pcm" % (name, key))
        try:
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    data = f.read()
                if data:
                    return pygame.mixer.Sound(buffer=data)
        except Exception:
            pass
        data = to_bytes(render_track(spec))
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
        except Exception:
            pass
        return pygame.mixer.Sound(buffer=data)

    # --- muzika
    def find_ext(self, name):
        cands = [name]
        if name in ("game1", "game2"):
            cands.append("game")
        for c in cands:
            for e in EXT:
                p = os.path.join(MUSIC_DIR, c + e)
                if os.path.isfile(p):
                    return p
        return None

    def effective_music_vol(self):
        if self.muted:
            return 0.0
        return self.music_vol * MUSIC_GAIN * (0.35 if self.duck else 1.0)

    def apply_volume(self):
        if not self.mixer_ok:
            return
        v = self.effective_music_vol()
        if self.ch is not None:
            self.ch.set_volume(v)
        try:
            pygame.mixer.music.set_volume(min(1.0, v * 1.4))
        except Exception:
            pass

    def music(self, name, fade=700):
        if not self.mixer_ok or name == self.cur:
            return
        self.cur = name
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        if self.ch is not None:
            self.ch.stop()
        ext = self.find_ext(name)
        if ext:
            try:
                pygame.mixer.music.load(ext)
                pygame.mixer.music.play(-1, fade_ms=fade)
                self.apply_volume()
                return
            except Exception:
                pass
        t = self.tracks.get(name)
        if t is not None and self.ch is not None:
            self.ch.play(t, loops=-1, fade_ms=fade)
            self.apply_volume()

    def set_duck(self, flag):
        self.duck = flag
        self.apply_volume()

    def toggle_mute(self):
        self.muted = not self.muted
        self.apply_volume()

    def set_music_vol(self, v):
        self.music_vol = min(1.0, max(0.0, v))
        SAVE.music = self.music_vol
        SAVE.write()
        self.apply_volume()

    def set_sfx_vol(self, v):
        self.sfx_vol = min(1.0, max(0.0, v))
        SAVE.sfx = self.sfx_vol
        SAVE.write()

    # --- efektai
    def sfx(self, name, vol=1.0):
        if not self.synth_ok or self.muted:
            return
        s = self.sfx_snd.get(name)
        if s is None:
            return
        if isinstance(s, list):
            s = random.choice(s)
        s.set_volume(min(1.0, self.sfx_vol * vol))
        s.play()
