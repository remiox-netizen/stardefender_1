# -*- coding: utf-8 -*-
"""Laivai, pasiekimai ir ilgalaikė pažanga (statistika tarp žaidimų)."""

SHIPS = [
    dict(name="Sakalas", tag="Universalus", unlock=None, speed=1.0, cool=1.0,
         desc=["Klasikinis šūvis,", "pusiausvyra tarp galios", "ir greičio."]),
    dict(name="Šturmas", tag="Šratai", unlock="veteran", speed=1.15, cool=1.1,
         desc=["Platus šūvių vėduoklė,", "trumpas nuotolis,", "greitas laivas."]),
    dict(name="Spindulys", tag="Pramušantis", unlock="boss_hunter", speed=1.0, cool=0.9,
         desc=["Kulkos pramuša priešus", "ir pataiko į kelis,", "šaudo labai greitai."]),
    dict(name="Raketa", tag="Nukreipiamos", unlock="rich", speed=0.95, cool=1.0,
         desc=["Raketos pačios", "suranda taikinį,", "šaudo lėčiau."]),
]

# stat - statistikos laukas, target - kiek reikia
ACH = [
    dict(id="first_blood", name="Pirmas kraujas", desc="Nušauk pirmą priešą", stat="kills", target=1),
    dict(id="hundred", name="Šimtininkas", desc="Nušauk iš viso 100 priešų", stat="kills", target=100),
    dict(id="veteran", name="Veteranas", desc="Pasiek 5 bangą", stat="best_wave", target=5),
    dict(id="boss_hunter", name="Bosų medžiotojas", desc="Nugalėk bosą", stat="bosses", target=1),
    dict(id="rich", name="Turtuolis", desc="Surink iš viso 300 monetų", stat="coins", target=300),
    dict(id="combo", name="Kombo meistras", desc="Pasiek x5 kombo daugiklį", stat="best_combo", target=20),
    dict(id="daredevil", name="Šaltakraujis", desc="Vos nepataikė 50 kartų iš viso", stat="grazes", target=50),
    dict(id="perfect_bonus", name="Bonuso karalius", desc="Sunaikink visus bonuso etapo priešus",
         stat="bonus_perfect", target=1),
    dict(id="flawless", name="Nepaliesta", desc="Nugalėk bosą nenukentėjęs", stat="boss_nohit", target=1),
    dict(id="survivor", name="Išgyvenęs", desc="Pasiek 10 bangą", stat="best_wave", target=10),
]
ACH_BY_ID = {a["id"]: a for a in ACH}

SUM_STATS = ("kills", "coins", "grazes", "bosses", "bonus_perfect", "boss_nohit")
MAX_STATS = ("best_wave", "best_combo")


def new_run():
    return {k: 0 for k in SUM_STATS + MAX_STATS}


def merged(save, run):
    m = {}
    for k in SUM_STATS:
        m[k] = save.stats.get(k, 0) + run.get(k, 0)
    for k in MAX_STATS:
        m[k] = max(save.stats.get(k, 0), run.get(k, 0))
    return m


def check(save, run):
    """Grąžina naujai atrakintus pasiekimus ir iškart juos išsaugo."""
    m = merged(save, run)
    new = []
    for a in ACH:
        if a["id"] not in save.ach and m[a["stat"]] >= a["target"]:
            save.ach.append(a["id"])
            new.append(a)
    if new:
        save.write()
    return new


def commit_run(save, run):
    """Prideda žaidimo statistiką prie bendros ir išsaugo."""
    for k in SUM_STATS:
        save.stats[k] = save.stats.get(k, 0) + run.get(k, 0)
    for k in MAX_STATS:
        save.stats[k] = max(save.stats.get(k, 0), run.get(k, 0))
    save.stats["games"] = save.stats.get("games", 0) + 1
    save.write()


def ship_unlocked(save, i):
    u = SHIPS[i]["unlock"]
    return u is None or u in save.ach


def ship_for_achievement(ach_id):
    for i, s in enumerate(SHIPS):
        if s["unlock"] == ach_id:
            return i
    return None


def ach_progress(save, a):
    """(dabartinė reikšmė, tikslas) rodymui."""
    m = merged(save, new_run())
    return min(m[a["stat"]], a["target"]), a["target"]
