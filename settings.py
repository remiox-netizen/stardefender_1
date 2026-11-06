# -*- coding: utf-8 -*-
"""Bendros konstantos ir išsaugojimo (rekordas, garso lygiai) valdymas."""
import json
import os
import sys

W, H = 800, 700
FPS = 60
OUT = (25, 20, 55)          # cartoon kontūro spalva
START_LIVES = 5
MAX_LIVES = 9
MAX_BOMBS = 3
BOSS_EVERY = 5              # kas kelintą bangą pasirodo bosas

# Android (python-for-android) nustato šiuos kintamuosius. "--mobile" / "--touch" - išbandymui kompiuteryje.
MOBILE = ("ANDROID_ARGUMENT" in os.environ) or ("ANDROID_PRIVATE" in os.environ) or ("--mobile" in sys.argv)
TOUCH = MOBILE or ("--touch" in sys.argv)
LOW_FX = MOBILE                     # supaprastinti efektai silpnesniems įrenginiams (galima perjungti meniu)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
MUSIC_DIR = os.path.join(ASSET_DIR, "music")
DATA_DIR = os.environ.get("ANDROID_PRIVATE") or BASE_DIR      # čia galima rašyti
SAVE_FILE = os.path.join(DATA_DIR, "stardefender_save.json")
CACHE_DIR = os.path.join(DATA_DIR, "audiocache")              # sugeneruotos muzikos talpykla


class Save:
    """Rekordai (Top 10) ir garso nustatymai, saugomi JSON faile."""

    def __init__(self):
        self.hi = 0
        self.music = 0.7
        self.sfx = 0.8
        self.scores = []            # [{"name", "score", "wave"}], rūšiuota mažėjančiai
        self.ship = 0               # pasirinktas laivas
        self.ach = []               # atrakinti pasiekimai (id)
        self.stats = {}             # visų žaidimų statistika
        self.load()

    def load(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.hi = max(0, int(d.get("hi", 0)))
            self.music = min(1.0, max(0.0, float(d.get("music", 0.7))))
            self.sfx = min(1.0, max(0.0, float(d.get("sfx", 0.8))))
            for sc in d.get("scores", []):
                if isinstance(sc, dict):
                    self.scores.append({"name": str(sc.get("name", "???"))[:10],
                                        "score": int(sc.get("score", 0)),
                                        "wave": int(sc.get("wave", 1))})
            self.scores.sort(key=lambda e: -e["score"])
            self.scores = self.scores[:10]
            self.ship = max(0, int(d.get("ship", 0)))
            self.ach = [str(a) for a in d.get("ach", [])]
            st = d.get("stats", {})
            if isinstance(st, dict):
                self.stats = {str(k): int(v) for k, v in st.items()}
        except Exception:
            pass
        if self.scores:
            self.hi = max(self.hi, self.scores[0]["score"])

    def qualifies(self, score):
        return score > 0 and (len(self.scores) < 10 or score > self.scores[-1]["score"])

    def add_score(self, name, score, wave):
        """Įrašo rezultatą; grąžina vietą lentelėje (0 = pirma) arba None."""
        entry = {"name": (name or "ŽAIDĖJAS")[:10], "score": int(score), "wave": int(wave)}
        self.scores.append(entry)
        self.scores.sort(key=lambda e: -e["score"])
        self.scores = self.scores[:10]
        self.hi = max(self.hi, int(score))
        self.write()
        for i, e in enumerate(self.scores):
            if e is entry:
                return i
        return None

    def write(self):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump({"hi": int(self.hi), "music": round(self.music, 2),
                           "sfx": round(self.sfx, 2), "scores": self.scores,
                           "ship": self.ship, "ach": self.ach, "stats": self.stats}, f,
                          ensure_ascii=False)
        except Exception:
            pass


SAVE = Save()
