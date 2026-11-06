[app]

# --- Programos informacija ---
title = Star Defender
package.name = stardefender
package.domain = org.stardefender
version = 1.0

# --- Šaltinio failai ---
source.dir = .
source.include_exts = py,png,jpg,ogg,mp3,wav,flac,json,txt,md
source.exclude_dirs = tests,bin,.git,.github,.buildozer,audiocache,__pycache__

# --- Priklausomybės ---
# pygame - žaidimas; numpy - garso ir muzikos sintezė.
requirements = python3,pygame,numpy

# --- Išvaizda ---
orientation = landscape
fullscreen = 1
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #100834

# --- Android ---
# Žaidimui nereikia jokių leidimų (išsaugojimas - privačiame aplanke).
android.permissions =
android.api = 33
android.minapi = 21
android.ndk_api = 21
# arm64-v8a tinka beveik visiems šiuolaikiniams telefonams. Seniems 32 bitų telefonams
# pridėk:  android.archs = arm64-v8a, armeabi-v7a   (kompiliavimas užtruks ilgiau)
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

# --- python-for-android ---
p4a.bootstrap = sdl2
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
