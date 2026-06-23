# Проект консольного клиента и библиотеки Python для AmneziaWG 2.0

## Краткий обзор

AmneziaVPN — это мультипротокольный open-source VPN‑клиент (desktop + mobile), который умеет как подключаться к готовым серверам, так и разворачивать self‑hosted VPN на VPS через Docker. Один из ключевых протоколов — AmneziaWG, форк WireGuard-Go с продвинутой обфускацией и полным «мимикрирующим» режимом в версии 2.0. Исходники клиента и реализации протокола доступны на GitHub, что позволяет спроектировать вендоронезависимый CLI/библиотеку поверх существующей кодовой базы.[^1][^2][^3][^4]

Цель этого исследования — разбрать архитектуру AmneziaVPN/AmneziaWG, вычленить точки расширения и конфигурационный слой протокола 2.0, а затем предложить реалистичный план проекта по созданию консольного клиента и/или Python‑библиотеки. Акцент — на вендоронезависимости, конфиденциальности и удобной интеграции с существующими инфраструктурами (Linux, Arch, DevOps, agentic‑системы).

## Архитектура проекта AmneziaVPN

### Общая структура клиента

Основной репозиторий клиента — `amnezia-vpn/amnezia-client`, написан преимущественно на C++/Qt, с использованием QML для UI и Kotlin/Java для Android‑компонентов. Клиент реализует мултипротокольный стек: OpenVPN, WireGuard, IKEv2, Shadowsocks, OpenVPN over Cloak, AmneziaWG, XRay Reality, с возможностью настройки self‑hosted серверов через SSH и Docker.[^5][^1]

Клиент выступает «толстым» фронтендом: он хранит конфигурации, управляет установку контейнеров на VPS, обновляет протоколы и проводит пользователя через мастер настройки. С точки зрения AmneziaWG 2.0, он генерирует или редактирует WireGuard‑подобные конфиги с расширенным набором параметров обфускации и передает их в серверные контейнеры/клиентские реализации.[^1][^5]

### Используемые внешние проекты

В README клиента прямо указаны внешние зависимости: OpenSSL, OpenVPN, Shadowsocks, Qt, LibSsh (форк из Qt Creator) и другие. Для AmneziaWG используется отдельная реализация на Go (репозиторий `amneziawg-go`) и утилиты в стиле `wireguard-tools` (`amneziawg-tools` с утилитами `awg` и `awg-quick`).[^3][^6][^1]

Такое разделение — GUI/оркестрация (Qt) + протокольный движок (Go / kmod + userspace tools) — уже задаёт естественную точку входа для CLI‑клиента: работать напрямую с `amneziawg-go` и `amneziawg-tools`, не трогая Qt‑часть.

## Реализация AmneziaWG

### Базовая реализация: amneziawg-go

Репозиторий `amnezia-vpn/amneziawg-go` является форком `wireguard-go` и реализует протокол AmneziaWG в виде отдельного бинарника.[^3]

```bash
amneziawg-go wg0
```

Это создаёт интерфейс `wg0`, форкает процесс в фон и позволяет конфигурировать туннель через `amneziawg-tools` (`awg`, `awg-quick`) и стандартные утилиты `ip`/`ifconfig`. Поддерживаются Linux, macOS (utun), Windows; на Linux рекомендуют использовать AmneziaWG вместо стандартного Кернелым модулем WireGuard.[^6][^3]

### Userspace‑утилиты: amneziawg-tools

Репозиторий `amneziawg-tools` — форк `wireguard-tools` с переименованными утилитами `awg` и `awg-quick`. Это стандартный CLI‑слой для конфигурирования туннелей, совместимым с `amneziawg-go` и AmneziaWG‑ядром. На Arch уже существует AUR‑пакет `amneziawg-tools`, который ставит эти утилиты и ман‑страницы.[^7][^6]

Почти все операции — создание конфигов, поднятие интерфейсов, просмотр статуса — выполняются командами `awg` и `awg-quick`, по аналогии с WireGuard (`wg`/`wg-quick`).[^6]

### Кроссплатформенные клиенты и embeddable библиотеки

Для Windows существует отдельный репозиторий `amneziawg-windows-client`, форк `wireguard-windows`, который предоставляет «embeddable WireGuard Tunnel Library» и полноценный AmneziaWG‑клиент на базе Wintun. Это показывает, что архитектурно AmneziaWG уже адаптирован под сценарий «встраиваемой библиотеки» — в Windows‑мире это DLL с API управления туннелями.[^8][^9]

Кроме того, в экосистеме есть сторонние библиотеки вроде `amneziawg-android` (embeddable tunnel library для Android) и инструменты вроде `amnezigo` — CLI и Go‑библиотека для генерации и управления конфигураций AmneziaWG v2.0. Это подтверждает возможность вынесения логики протокола в отдельный модуль и создания чисто консольных клиентов без привязки к основой GUI.[^10][^11]

## Протокол AmneziaWG 2.0: параметры и семантика

### Общее описание

AmneziaWG — форк WireGuard-Go, который устраняет распознаваемые сигнатуры трафика и добавляет многоуровнюю обфускацией/мимикрию. В версии 2.0 протокол:[^12][^4]

- заменяет статические заголовы пакетов на динамические диапазонов значений (`H1-H4`);
- добавляет псевдослучайные преефиксы к разным типам пакетов (`S1-S4`);
- вводит цепочку "signature packets" `I1-I5` (CPS — Custom Protocol Signature) перед handshake;
- добавляет "junk train" (`Jc`, `Jmin`, `Jmax`) для размытие профиля handshake;
- сохраняет криптографическое ядро WireGuard (Noise_IK, Curve25519, ChaCha20-Poly1305).[^4][^12]

В документации подчёркивается, что при всех параметрах, равных нулю, поведение сводится к стандартному ВиреГуарду, что обеспечивает обратную совместимость.[^12][^4]

### Параметры H1–H4 (dynamic заголовки)

Для четырёх типов пакетов WireGuard — Init, Response, Cookie, Data — AmneziaWG генерирует случайные значений из заданных диапазонов `H1-H4`. Эти значения:[^4]

- заменяют предсказуемые идентификаторы пакетов WireGuard;
- смещают позиции полей Version/Type;
- изменяют «зарезервированные» биты.

Важно, что диапазоны `H1-H4` не должны пересекаться; это гарантирует отсутствие унифицированных правил для DPI по заголовкам. Для каждого пакета выбирается случайное значение из диапазона; на приёме принимается любое значение внутри диапазона.[^4]

### Параметры S1–S4 (randomization длины)

Путём добавления псевдослучайные преефиксы S1–S4 протокол меняет длину handshake и других мессежей:

- Init: `len(init) = 148 + S1`;
- Response: `len(resp) = 92 + S2`;
- Cookie Reply: `len(cookie) = 64 + S3`;
- Data: `len(data) = payload + S4`.[^4]

Это ломает сигнатуру WireGuard по размерам пакетов, усложняя DPI‑анализ.

### Параметры I1–I5 и CPS (Custom Protocol Signature)

Перед каждым handshake (примерно каждые 120 секунд) клиент может отправить до пяти UDP‑пакетов `I1-I5`, описанных в формате CPS. Первый пакет `I1` обычно содержит hex‑снимок настоящего протокола — например, QUIC Initial — остальные (`I2-I5`) увеличивают энтропию (счётчики, timestamps, рандомные байты).[^12][^4]

Синтаксис CPS:

```text
i{n} = <tag1><tag2>...<tagN>
```

Теги:

- `b` — статические байты (`<b hex_data>`), для имитации конкретного протокола;
- `t` — Unix‑timestamp (`<t>`);
- `r` — криптографически стойкие случайные байты (`<r length>`);
- `rc` — случайные ASCII‑буквы, useful для имитации текстовых протоколов;
- `rd` — случайные десятичные цифры.[^4]

Пример CPS (из доки):

```text
i1 = <b 0xd100000001><rc 8><t><r 50>
```

Документация подчёркивает что пример не должно использоваться литерально; он демонстрирует синтаксис.[^4]

### Параметры Jc, Jmin, Jmax (junk train)

После CPS‑цепочки отправляется серия из Jc псевдослучайные "junk"‑пакетов с дленами в диапазоне `[Jmin, Jmax]`. Цель — размытие профиля начала сессии по времени и размерам, еще больше усложняя распознавание handshake.[^12][^4]

### Версионой отличия и сигнатуры AmneziaWG 2.0

В документации GL.iNet по AmneziaWG описано, как отличь версии:

- v1.0 — отсутствуют параметры `S3-S4`, `H1-H4` — фиксированные значения;
- v2.0 — добавлены `S3-S4`, `H1-H4` задаются диапазонами; поддерживаются `I1-I5`.[^13]

Кроме того, AmneziaWG 2.0 усиливает обфускацию, используя динамические заголовоки (H1–H4 как диапазоны) и расширенный паддинг (включая новые S‑параметры).[^14][^13]

## Точки расширения: где "zaцепитьсь" за протокол

### Конфигурационный слой

Практический уровенќ из аймодействаа AmneziaWG — это конфигурационные файлы, пожожие на WireGuard‑конфиги, но с дополнительными полями для параметров обфускации (`H1-H4`, `S1-S4`, `Jc`, `Jmin`, `Jmax`, `I1-I5`). Эти конфиги обрабатываются `amneziawg-tools` (`awg-quick`) и `amneziawg-go`, а также сторонние библиотеки (naprimer, `amnezigo` для генерации конфигов).[^10][^13][^3][^4]

CLI‑клиент и Python‑библиотека могут вопрать именно на этоусровени: 

- парсить/валидировать конфиги AmneziaWG 2.0;
- генерировать безопасные значения диапазонов и CPS;
- манажироть жизненный цикл туннеля (поднять/опустить) через `awg`/`awg-quick` или через прамой вызов `amneziawg-go`.

### Управление туннелей как процессум

`amneziawg-go` запускает интерфейс и оркаетск Фон, поддерживают режим foreground (`-f`), и уравляют ему утилиты `amneziawg-tools`. На Linux/Arch это дает несколько вариантов интеграции:

- прамой вызов `amneziawg-go wg0` и дальнейшая работа через `awg`;
- использование готового системд‑юнита длля туннелей (kak это обычно делается с WireGuard);
- манажирование через Python (subprocess) или через Go‑CLI/библиотеку.

Таким образом, наш CLI‑клиент может быть тонким слоем над уже существующими двоичниками, а Пятон‑библиотека — абстракцией над конфигами и процессатов.

## Требования проекта: консольного клиент / Python‑библиотека

### Фнкциональные рекоментации
1. **Поддержка протокола AmneziaWG 2.0**
   - Чтение/запись конфигов с параметрами `H1-H4`, `S1-S4`, `Jc`, `Jmin`, `Jmax`, `I1-I5`.[^4]
   - Генерация безопасных и корректных значений диапазонов/паддинга.
   - Управление туннелей через `amneziawg-tools` или прямой всаимодейства с `amneziawg-go`.

2. **Вендоронезависимостости**
   - Отсутствие жёсткой привязки к омкрентомого Amnezia GUI‑клиента; работа с любыми AmneziaWG‑конфигами (self‑hosted, сторонние панели, ручная генерация).
   - Возможность подключения к серверам, созданных бы̶ AmneziaVPN, но без требования наличия GUI.

3. **Конфиденциальность и минимизация доверия**
   - Клиент не отправляет телеметрию, не хранит чувствительные дату вне конфигов/секрет‑хранилищ.
   - Опционаьная интеграция с локальными секрет‑хранилищами (Pass, KeePassXC, sops).
   - Прозрачный формат конфигов, без «магических» полей.

4. **Кроссплатформенностосты**
   - Linux (v tom числе Arch), macOS, потенциально Windows (pri ispol'zovanii embeddable biblioteki).[^8][^3]
   - Dlya Python — sovmestimost' s populyarnymi distro, prostaya ustanovka cherez `pip`.

5. **Интеграция s DevOps/agentic‑системами**
   - Udobnyy CLI dlya ispol'zovaniya v CI/CD, Ansible, Terraform, agentic loops.
   - Python‑API dlya programmnogo upravleniya tunnel'yami.

### Nefunktsional'nye trebovaniya

- **Bezopasnost'** — minimizatsiya attack surface, yavnoye upravleniye pravami (sudo), proverka konfiguratsiy pered podnyatiyem tunnel'ya.[^12][^4]
- **Prozrachnost'** — open-source litsenziya (naprimer, GPLv3 ili Apache 2.0, uchytyvaya sovmestimost' s AmneziaWG‑kodom).[^1][^3]
- **Nadezhnost'** — ustoychivost' k oshibkam konfiguratsii, akkuratnoye osvobozhdeniye resursov (udalenie interfeisa, ostanovka protsessov).[^3]

## Arkhitektura konsol'nogo klienta

### Vysokourovnevaya skhema

Predlagayemaya arkhitektura CLI‑klienta:

- **Core‑modul' konfiguratsiy**
  - Struktury dannykh dlya AmneziaWG 2.0 konfiguratsiy.
  - Parser/validator failov `.conf`.
  - Generator parametrov obfuskatsii.

- **Execution‑modul'**
  - Abstraktsiya nad `amneziawg-go` i `amneziawg-tools`.
  - Interfeisy: `start_tunnel`, `stop_tunnel`, `status`.

- **CLI‑interfeis**
  - Komandy `init`, `up`, `down`, `show`, `validate`, `gen-config`.
  - Format konfiguratsiy sovmestim s WireGuard/AmneziaWG.

- **Security‑modul'**
  - Rabota s sekretami (klyuchi, PSK, obfuskatsionnye parametry).
  - Politiki khraneniya/loggirovaniya.

### Model' dannykh konfiguratsii

Konfig mozhno predstavit' kak ob"yedineniye standartnogo WireGuard‑konfiga i sektsii obfuscation:

```ini
[Interface]
PrivateKey = ...
Address = ...
ListenPort = ...

[Peer]
PublicKey = ...
Endpoint = ...
AllowedIPs = ...

[AmneziaWG]
H1 = 100000-200000
H2 = 200001-300000
H3 = 300001-400000
H4 = 400001-500000
S1 = 16
S2 = 16
S3 = 16
S4 = 32
Jc = 4
Jmin = 128
Jmax = 1024
I1 = <b ...><t><r 50>
I2 = <b ...><rc 8>
...
```

Chast' etikh parametrov opisana neposredstvenno v AmneziaWG dokakh (diapazony i ogranicheniya dlya S‑ i J‑parametrov, trebovaniya k H‑diapazonam). CLI dolzhen vypolnyat' proverku validnosti (naprimer, neperesekayushchiyesya diapazony H, korrektnyy CPS‑sintaksis).[^13][^4]

### Vzaimodeystviye s amneziawg-go/awg-quick

Bazovyye operatsii:

- `awg-quick up awg0` — podnyatiye tunnel'ya po configu `awg0.conf`.
- `awg-quick down awg0` — ostanovka tunnel'ya.
- `awg show awg0` — status.[^7][^6]

CLI mozhet libo oborachivat' eti komandy, libo ispol'zovat' pryamoy vyzov `amneziawg-go` s upravleniyem cherez soket `/var/run/amneziawg/wg0.sock`. Dlya Python‑biblioteki — otdel'nyy modul' dlya raboty s subprocess i parsinga vyvoda.[^3]

## Arkhitektura Python‑biblioteki

### Osnovnyye komponenty

1. **`config`**
   - Klassy `InterfaceConfig`, `PeerConfig`, `AmneziaWGObfuscationConfig`.
   - Metody `from_file(path)`, `to_file(path)`, `validate()`.

2. **`obfuscation`**
   - Funktsii dlya generatsii diapazonov H1–H4 (s proverkoj peresecheniy).
   - Funktsii dlya generatsii S‑ i J‑parametrov v bezopasnykh predelakh.
   - CPS‑builder dlya `I1–I5` (builder‑pattern: `CPSPacket().add_bytes(...).add_timestamp().add_random(...).build()`).

3. **`tunnel`**
   - Klassy `TunnelManager`, `TunnelProcess`.
   - Metody `up`, `down`, `status`.
   - Podderzhka raznykh platform (Linux, macOS, Windows) cherez pluggable backend'y (systemd, pryamoy zapusk, Windows‑API).

4. **`secrets`**
   - Integratsiya s vneshnimi khranilishchami (optsional'no).
   - Bezopasnaya generatsiya klyuchey i khraneniye.

5. **`cli` (optsional'no)**
   - Obörtka vokrug biblioteki, realizuyushchaya konsol'nyy interfeis.

### API‑primer

```python
from amneziawg import config, obfuscation, tunnel

cfg = config.AmneziaConfig.from_file("awg0.conf")

# Validatsiya i avtogeneratsiya obfuskatsii
if not cfg.obfuscation:
    cfg.obfuscation = obfuscation.generate_strong_profile()

cfg.validate()
cfg.to_file("/etc/amneziawg/awg0.conf")

# Podnyat' tunnel'
 mgr = tunnel.TunnelManager(interface="awg0")
mgr.up()
status = mgr.status()
print(status)

# Ostanovit' tunnel'
mgr.down()
```

Takoy API udoben dlya DevOps‑stsena riyev, CI/CD i agentic‑loop sistem, gde tunnel'i nuzhny kak vremennye resursy.

## Plan proekta: fazy i epiki

### Faza 0 — Issledovaniye i prototipirovaniye

- Epik **ARCH-RESEARCH**
  - Zadachi:
    - Izuchit' iskhodniki `amneziawg-go`, `amneziawg-tools`, Windows/Android‑klientov.[^6][^8][^10][^3]
    - Zafiksirovat' format konfiguratsiy AmneziaWG 2.0 (s primerami iz dokov).[^13][^4]
    - Otsenit' varianty litsenziy (GPLv3/Apache 2.0) i sovmestimost'.[^1][^3]

- Epik **POC-CLI**
  - Zadachi:
    - Napisat' minimal'nyy CLI, kotoryy umeet:
      - chitat' config; 
      - dergat' `awg-quick up/down`;
      - pokazyvat' status.
    - Proverit' rabotu na Arch s AUR‑paketami `amneziawg-tools`/`amneziawg-go`.[^7]

### Faza 1 — Konfiguratsionnyy sloy i validator

- Epik **CFG-PARSER**
  - Realizovat' parser AmneziaWG‑konfigov s sektsiyey `[AmneziaWG]`.
  - Realizovat' validator diapazonov H1–H4, parametrov S/J, CPS‑sintaksisa.[^13][^4]

- Epik **OBFUSCATION-PROFILES**
  - Opredelit' «profili» obfuskatsii (naprimer, `censorship_high`, `censorship_medium`, `default`).
  - Realizovat' generator profiley na osnove rekomendatsiy dokumentatsii (diapazony, chisla junk‑paketov i t.d.).[^12][^4]

### Faza 2 — Python‑biblioteka

- Epik **PY-LIB-CORE**
  - Realizovat' Python‑modul' `config` i `obfuscation`.
  - Dobavit' testy na parsing/validator.

- Epik **PY-LIB-TUNNEL**
  - Realizovat' backend dlya Linux (subprocess + `awg-quick`).
  - Dobavit' abstraktnyy interfeis dlya macOS/Windows (na budushcheye).[^8][^3]

- Epik **PY-LIB-SECURITY**
  - Integrirovat' bezopasnuyu generatsiyu klyuchey i bazovuyu politiku khraneniya.

### Faza 3 — Polnotsennyy CLI

- Epik **CLI-UX**
  - Sproektirovat' UX komand: `amneziawg-cli init`, `up`, `down`, `status`, `gen-config`, `validate`.
  - Realizovat' tsvetnoy vyvod, logirovaniye, rezhimy podrobnosti.

- Epik **CLI-INTEGRATIONS**
  - Dobavit' podderzhku generatsii konfiguratsiy dlya populyarnykh paneley/orkestratorov (naprimer, AmneziaWG‑paneley tipa `amnezia-wg-easy`).[^15][^11]

### Faza 4 — Vendor-agnostic i hardening

- Epik **VENDOR-AGNOSTIC**
  - Proverit' rabotu klienta s konfiguratsiyami, poluchennymi iz AmneziaVPN, GL.iNet, storonnikh bibliotek.[^16][^13]
  - Opisat' sovmestimost' i ogranicheniya v dokumentatsii.

- Epik **SEC-HARDENING**
  - Dobavit' proverki bezopasnosti (minimal'nye trebovaniya k parametrakh obfuskatsii).
  - Ogranichit' logirovaniye chuvstvitel'nykh dannykh.

### Faza 5 — Dokumentatsiya i reliz

- Epik **DOCS**
  - Sozdat' podrobnoye README, primery konfiguratsiy, retsepty dlya Arch/Ubuntu.
  - Opisat' integratsiyu s agentic‑sistemami i DevOps‑payplaynami.

- Epik **RELEASE**
  - Opublikovat' biblioteku na PyPI.
  - Podgotovit' paket dlya AUR (CLI‑klient).

## Riski i ogranicheniya

- **Zavisimost' ot nizkour ovnevoy realizatsii** — CLI i biblioteka zavis yat ot nalichiya `amneziawg-go`/kmod, chto nuzhno yavno dokumentirovat'.[^6][^3]
- **Evolyutsiya protokola 2.0+** — vozmozhny izmeneniya v parametrakh i rekomendovannykh diapazonakh; biblioteka dolzhna byt' versionno‑chuvstvitel'noy (polya dlya novykh parametrov, strogaya validatsiya).[^14][^16]
- **Yuridicheskiye aspekty** — neobkhodimo akkuratno vybirat' litsenziyu, uchityvaya GPL‑naslediye chastey steka.[^1][^6]

## Vyvody

Iskhodniki AmneziaVPN i AmneziaWG dayut dostatochno prozrachnuyu arkhitekturu: protokol realizovan kak otdel'nyy dvizhok (`amneziawg-go` + tools), a klient — kak UI/orkestrator. Eto pozvolyayet stroit' vendoronezavisimyy konsol'nyy klient i Python‑biblioteku, rabotayushchiye napryamuyu s konfiguratsiyami i tunnel'nymi protsessami. Klyuchevoy fokus proekta — korrektnaya podderzhka parametrov AmneziaWG 2.0 (H1–H4, S1–S4, Jc, Jmin/Jmax, I1–I5), obespecheniye konfidentsial'nosti i udobnaya integratsiya v DevOps/agentic‑stsena riyakh.[^6][^1][^3]

---

## References

1. [AUR (en) - amneziavpn-bin - Arch Linux](https://aur.archlinux.org/packages/amneziavpn-bin)

2. [Amnezia VPN client on Arch · Issue #1795](https://github.com/amnezia-vpn/amnezia-client/issues/1795) - Hello, there! How do I use amnezia client on Arch Linux ... Amnezia VPN client on Arch #1795. New is...

3. [Installing AmneziaVPN on Linux | Amnezia Docs](https://docs.amnezia.org/documentation/installing-app-on-linux/) - Overview

4. [Установка AmneziaVPN на Linux](https://docs.amnezia.org/ru/documentation/installing-app-on-linux/) - Podderzhivayemyye distributivy

5. [AUR (en) - amneziavpn-bin - Arch Linux](https://aur.archlinux.org/packages/amneziavpn-bin?O=10)

6. [Установка AmneziaVPN на Linux | Amnezia Docs](https://amneziavpn.org/ru/documentation/installing-app-on-linux/) - Podderzhivayemyye distributivy:

7. [Question about Amnezia VPN and amneziawg - EndeavourOS Forum](https://forum.endeavours.com/t/question-about-amnezia-vpn-and-amneziawg/73024) - Amnezia VPN doesn’t give any options how to install it on arch linux: However, it seems like Amnezia...

8. [AmneziaVPN не запускается на Linux](https://docs.amnezia.org/ru/troubleshooting/not-running-on-linux/) - AmneziaVPN podderzhivayet ogranichennyy nabor distributivov Linux. Ubedites', chto vash distributiv vkhodi...

9. [Podskazhite kak ustanovit Amnezia VPN](https://old.manjaro.ru/newby-corner/podskazhite-kak-ustanovit-amnezia-vpn.html) - Podskazhite kak ustanovit Amnezia VPN V Ayure net, pri skachivani...

10. [Problemy s podklyucheniyem na Linux : r/AmneziaVPN](https://www.reddit.com/r/AmneziaVPN/comments/1qi031n/%D0%BF%D1%80%D0%BE%D0%B1%D0%BB%D0%B5%D0%BC%D1%8B_%D1%81_%D0%BF%D0%BE%D0%B4%D0%BA%D0%BB%D1%8E%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%D0%BC_%D0%BD%D0%B0_linux/) - U menya pokhozhaya problema, tol'ko u menya Arch. Pytalsya nastroit' vpn cherez self-hosted na svoem vps, i...

11. [GitHub - indx0/AmneziaConverter: A CLI tool for converting AmneziaVPN configs.](https://github.com/indx0/AmneziaConverter) - A CLI tool for converting AmneziaVPN configs. Contribute to indx0/AmneziaConverter development by cr...

12. [Amnezia VPN](https://github.com/amnezia-vpn) - Amnezia VPN has 52 repositories available. Follow their code on GitHub.

13. [Хочу pomenyat' url v amnezia-vpn konfiguratsii #1712](https://github.com/amnezia-vpn/amnezia-client/issues/1712) - amnezia-vpn trebuyet ip adres servera dlya togo, chtoby nastroit' server. Ya zavel svoy sobstvennyy dome...

14. [AmneziaVPN doesn't start on Linux](https://docs.amnezia.org/troubleshooting/not-running-on-linux/) - AmneziaVPN only supports a limited set of Linux distributions. Make sure yours is on the supported l...

15. [How to use AmneziaVPN without GUI on CLI-only mode?](https://www.reddit.com/r/AmneziaVPN/comments/1d9drnb/how_to_use_amneziavpn_without_gui_on_clionly_mode/%3Ftl=ru) - How to use AmneziaVPN without GUI on CLI-only mode?

16. [Propustit' ustanovku](https://docs.amnezia.org/ru/documentation/instructions/install-vpn-on-server/) - Obshchaya informatsiya

---

