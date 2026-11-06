# Star Defender - Android (APK)

Šis projektas jau pritaikytas telefonui: lietimo valdymas, našumo režimas,
išsaugojimas privačiame programos aplanke. **Pats APK failas sukuriamas
kompiliavimo metu** (jam reikia Android SDK/NDK ir kelių GB atsisiuntimų), todėl yra
du būdai jį gauti. Pirmasis nereikalauja nieko diegti kompiuteryje.

> Svarbu: šis paketas **nebuvo išbandytas tikrame telefone** (kūrimo aplinkoje nėra
> Android įrankių). Žaidimo logika ir lietimo valdymas patikrinti automatiniais
> testais, bet APK kompiliavimas gali prireikti nedidelių pataisymų. Jei klaida -
> atsiųsk kompiliavimo žurnalą (log), ir pataisysime.

## 1 būdas (rekomenduojama): kompiliavimas internete per GitHub (nemokamai)

1. Susikurk nemokamą paskyrą https://github.com
2. Sukurk naują saugyklą (**New repository**, pavadinimas pvz. `stardefender`).
3. Išpakuok `StarDefender.zip` ir įkelk **visus** failus į saugyklą
   (**Add file -> Upload files**; vilk visą aplanko turinį, įskaitant paslėptą
   aplanką `.github`). Jei `.github` neįsikėlė:
   **Add file -> Create new file**, kaip pavadinimą įrašyk
   `.github/workflows/build-apk.yml` ir įklijuok to failo turinį.
4. Atidaryk skirtuką **Actions** -> kairėje **Build Android APK** -> **Run workflow**.
5. Palauk ~20-40 min (pirmas kartas ilgiausias). Kai atsiras žalia varnelė, atidaryk
   paleidimą ir apačioje skiltyje **Artifacts** atsisiųsk `StarDefender-apk`
   (tai zip su `.apk` failu).
6. Perkelk `.apk` į telefoną (laidu, el. paštu, Google Drive...), jį atidaryk ir leisk
   **Įdiegti iš nežinomų šaltinių** (Settings -> Security / Install unknown apps).

## 2 būdas: kompiliavimas savo kompiuteryje (Linux arba Windows su WSL2/Ubuntu)

    sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config \
        zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
    pip3 install --user buildozer cython
    cd StarDefender
    buildozer android debug

Baigus APK bus aplanke `bin/` (pvz. `bin/stardefender-1.0-arm64-v8a-debug.apk`).
Tiesiai į prijungtą telefoną (su USB derinimu):  `buildozer android debug deploy run`.

## Valdymas telefone

- **Laikyk pirštą ant ekrano** - laivas seka tavo piršto judėjimą ir šaudo.
  Pakėlus pirštą šaudymas sustoja (tai svarbu 5 lygio ginklui - jis kaista).
- **Bomba** - apvalus mygtukas apačioje dešinėje. **Pauzė** - mygtukas viršuje dešinėje.
- Meniu, parduotuvė, angaras - tiesiog liesk. Vardui įvesti - ekraninė klaviatūra.
- Telefono mygtukas **Atgal** = pauzė / grįžimas. Išėjus į foną žaidimas pats sustoja.
- Meniu **Kokybė: ŽEMA / AUKŠTA** - jei žaidimas stringa, palik ŽEMĄ (mažiau švytėjimų ir
  dalelių). Telefone numatytoji kokybė - žema.

## Pastabos

- Muzika sugeneruojama paleidus pirmą kartą (gali užtrukti iki ~30 s), vėliau įrašoma į
  talpyklą ir kraunasi akimirksniu.
- Rezultatai, pasiekimai ir nustatymai saugomi privačiame programos aplanke
  (pašalinus programą jie dingsta).
- Savo muziką galima pridėti į `assets/music/` prieš kompiliuojant (žr. pagrindinį README).
- Jei kompiliavimas nepavyksta ties `pygame` arba `numpy`, atsiųsk žurnalo paskutines
  ~100 eilučių - tai greičiausiai tik receptų versijų klausimas.
