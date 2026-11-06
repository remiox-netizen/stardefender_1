# STAR DEFENDER

Cartoon stiliaus kosminė šaudyklė (Python + pygame). Visa grafika, garso efektai ir
muzika sukuriami kodu - papildomų failų nereikia.

## Paleidimas

    pip install -r requirements.txt
    python main.py

(Windows: dukart spustelėkite `run.bat`; Linux/macOS: `./run.sh`)

Reikia: Python 3.8+, pygame 2.1+, numpy (be numpy nebus garso). Pirmą kartą paleidus,
~7 sek. kuriama muzika.

## Android (telefonas)

Žaidimas pritaikytas telefonui (lietimo valdymas, našumo režimas). Kaip gauti APK failą -
žr. **README_ANDROID.md** (kompiliavimas internete per GitHub arba savo kompiuteryje).
Kompiuteryje lietimo režimą galima išbandyti:  `python main.py --touch`
(pelė imituoja pirštą), o našumo režimą - `python main.py --mobile`.

## Valdymas

| Klaviatūra             | Valdiklis (gamepad)      | Veiksmas                         |
|------------------------|--------------------------|----------------------------------|
| Rodyklės / W A S D     | kairė lazdelė / D-pad    | valdyti laivą                    |
| Tarpas                 | A                        | šaudyti (laikant - šaudo nuolat) |
| B arba X               | B / X / Y                | paleisti bombą                   |
| P arba Esc             | Start                    | pauzė (Q - į meniu)              |
| M                      | -                        | nutildyti / įjungti garsą        |
| F11                    | -                        | pilnas ekranas                   |

Meniu: rodyklės arba pelė / lazdelė; ←→ keičia garsumą (ir laivą ties "Angaras").
Angare: kairė/dešinė - rinktis, Enter - patvirtinti. Parduotuvėje: aukštyn/žemyn,
Enter - pirkti, Esc - tęsti. Vardo įvedime: klaviatūra arba valdiklis.

## Kas naujo (šioje versijoje): bangos nebesikartoja

- **6 bangų tipai, keičiasi kas bangą** (pasikartoti du kartus iš eilės negali):
  - *Formacija* - klasikinė, bet dabar...
  - *Atakos iš viršaus* - grupės (linija, V, poros) leidžiasi žemyn savo trajektorijomis
    (tiesiai, įstrižai, zigzagu)
  - *Žemyn slenkančios eilės* - priešų eilės slenka juostomis su properšomis, pasirink kur lįsti
  - *Apsupimas* - priešai įskrenda iš šonų, apsuka ekraną ir išskrenda žemyn
  - *Orbitos* - didelė šerdis, aplink kurią sukasi priešų žiedai; sunaikink šerdį
  - *Srautai* - zigzagai, spiralės, praskridimai ir įstrižos linijos
- **Atsitiktinė kompozicija** - formacijų yra 12 formų (tinklelis, banga, V, deimantas,
  kolonos, šachmatų lenta, išbarstyti taškai, pleištas, žiedai, rombai, arka...), o jų dydis,
  tarpai ir properšos kiekvieną kartą kitokie, todėl dvi bangos niekada nesutampa
- Judančiose bangose priešai nešaudo tik retkarčiais, bet jų prisilietimas žeidžia;
  **niekas nepabėgo** = papildomi taškai
- Prisitaikantis sunkumas taip pat didina grupių skaičių ir greitį

## Ankstesnė versija: žaidimas nebeužsibosta

- **Prisitaikantis sunkumas** - jei bangą išvalai greitai ir be smūgių, kita bus sunkesnė
  (daugiau priešų, daugiau gyvybių, greitesnės kulkos, stipresni bosai); jei daug
  smūgių - kiek lengviau. Apačioje rodomas **Grėsmės** lygis (1-5).
  Be to, nuo 8, 14 ir 20 bangos visi priešai gauna papildomą gyvybę.
- **4 nauji priešai**:
  - *Skydininkas* - slankiojantis skydas blokuoja šūvius iš apačios, pataikyk iš šono
  - *Regeneratorius* - jei ilgai nepataikai, gyvybės atsistato
  - *Šokliukas* - teleportuojasi, kai į jį skrenda šūvis
  - *Gydytojas* - gydo kitus priešus (šauk pirmiausia jį!)
- **Maksimalaus ginklo perkaitimas** - 5 lygio ginklas kaista šaudant be pertraukos
  ir trumpam išsijungia (temperatūros juosta apačioje). Parduotuvėje naujas
  patobulinimas **Aušinimas** (3 lygiai).
- Meniu pasirinkimas pervadintas į **Angaras**

## Ankstesnė versija

- **4 laivai su skirtingais ginklais** (angaras meniu), atrakinami pasiekimais:
  - *Sakalas* - klasikinis šūvis (nuo pradžių)
  - *Šturmas* - platus šratų vėduoklė, trumpas nuotolis, greitas laivas (pasiek 5 bangą)
  - *Spindulys* - kulkos pramuša kelis priešus, šaudo labai greitai (nugalėk bosą)
  - *Raketa* - nukreipiamos raketos, kurios pačios suranda taikinį (surink 300 monetų)
- **10 pasiekimų** su pranešimais žaidimo metu ir ilgalaike statistika
- **"Vos nepataikė" bonusas** - praskriesk visai arti priešo kulkos: taškai, kombo
  pratęsimas, kas 10 kartų - monetos
- **Bonuso etapai** (po 3, 8, 13... bangos) - nešaudantys priešai skrenda įvairiomis
  trajektorijomis, sušaudyk kuo daugiau dėl monetų; visi sunaikinti = +1000
- **5 priešų formacijos**: tinklelis, banga, V, deimantas, kolonos
- **Pavojai**: asteroidai (didelis skyla į du) ir meteoritų lietus
- **Sektoriai** - fonas ir pavadinimas keičiasi kas 3 bangas
- Nauja bonuso muzika; bosas nugalėtas nenukentėjus = +500

## Žaidimo savybės (iš anksčiau)

- 5 pradinės gyvybės, taškai, kombo daugiklis iki x5, Top 10 su vardais
- Parduotuvė ir monetos; 10 priešų tipų; 3 skirtingi bosai (kas 5-a banga)
- Skraidantis UFO, prizai (ginklas, skydas, gyvybė, bomba), dronai 5-o lygio ginklui
- Daugiasluoksniai sprogimai, parallax fonas, 5 sintezuoti muzikos kūriniai ir ~30 efektų
- Valdiklio (gamepad) palaikymas visur

## Savo muzika

Įdėkite failus į `assets/music/` - jie automatiškai pakeis sintezuotą muziką:

    menu.ogg    meniu ir parduotuvė
    game1.ogg   žaidimas (nelyginės bangos)   (arba game.ogg abiem)
    game2.ogg   žaidimas (lyginės bangos)
    boss.ogg    boso kova
    bonus.ogg   bonuso etapas

Formatai: .ogg (rekomenduojama), .mp3, .wav, .flac.

## Failų struktūra

    main.py            paleidimo failas
    sd/settings.py     konstantos, išsaugojimas (Top 10, pasiekimai, statistika)
    sd/progress.py     laivai, pasiekimai, ilgalaikė pažanga
    sd/gfx.py          sprite'ai, tekstas, švytėjimai
    sd/effects.py      sprogimai, dalelės, parallax fonas
    sd/entities.py     kulkos, monetos, asteroidai, priešai, UFO, bosai, prizai
    sd/game.py         žaidimo logika, ginklai, formacijos, bonuso etapas, parduotuvė
    sd/audio.py        garso sintezė ir muzikos valdymas
    sd/screens.py      meniu, angaras, pasiekimai, rezultatai, parduotuvė, vardas...
    sd/app.py          pagrindinis ciklas, įvestis (klaviatūra, pelė, valdiklis)
    buildozer.spec     Android (APK) kompiliavimo nustatymai
    .github/workflows  automatinis APK kompiliavimas GitHub'e
    README_ANDROID.md  instrukcija, kaip gauti APK
    assets/            piktograma, pradžios ekranas, muzikos aplankas
    tests/             smoke testas (be pygame, su stub)
