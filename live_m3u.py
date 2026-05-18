#!/usr/bin/env python3
# live_m3u.py — версия с adult-фильтром, РТРС, RED Media, Bridge Media, отчётами
# и Phoenix Edition:
# - РТРС Плюс (единая группа)
# - Кнопки X.X внутри названия
# - Матч-семейство: 3, 3.1, 3.2, 3.3...
# - Нормализация названий (с HD)
# - EXTINF формат C1
# - Без символов "|"

import requests
import argparse
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urljoin

TIMEOUT = 4
THREADS = 25

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# === ЖЁСТКИЙ ФИЛЬТР ADULT-КОНТЕНТА ===

ADULT_KEYWORDS = [
    "xxx", "sex", "porn", "porno", "порно", "эрот", "эротика", "18+", "18plus",
    "brazzers", "hustler", "playboy", "venus", "dorcel", "private", "eros", "erotic",
    "fetish", "bdsm", "softcore", "hardcore",
    "cam", "webcam", "livecam",
    "nsfw",
    "barelylegal", "barely_legal", "bluehustler", "russian_night", "russkaya_noch"
]

# === ФИЛЬТР ЗАПРЕЩЁННОГО КОНТЕНТА ===

BAD_KEYWORDS = [
    "shop", "магазин", "телемагазин",
    "test", "тест", "404", "error",
    "t.me", "telegram", "cdn-telegram", "tg://",
    "spam", "junk", "garbage"
]


def is_adult(info: str, url: str) -> bool:
    text = (info + " " + url).lower()
    return any(bad in text for bad in ADULT_KEYWORDS)


def is_bad(info: str, url: str) -> bool:
    text = (info + " " + url).lower()
    return any(bad in text for bad in BAD_KEYWORDS)


# === РТРС 1–37 (федералка + кабель) ===

RTRS_BUTTONS = {
    1: "Первый канал",
    2: "Россия 1",
    3: "Матч ТВ",
    4: "НТВ",
    5: "Пятый канал",
    6: "Россия К",
    7: "Россия 24",
    8: "Карусель",
    9: "ОТР",
    10: "ТВ Центр",
    11: "РЕН ТВ",
    12: "Спас",
    13: "СТС",
    14: "Домашний",
    15: "ТВ-3",
    16: "Пятница",
    17: "Звезда",
    18: "Мир",
    19: "ТНТ",
    20: "Муз-ТВ",

    23: "Mezzo",
    24: "2x2",
    25: "RTG",
    26: "Дождь",
    27: "Техно 24",
    28: "Мульт",
    29: "360",
    30: "Доктор",
    31: "Моя Планета",
    32: "Че!",
    33: "Футбол",
    34: "Tiji",
    35: "Ностальгия",
    36: "Eurosport",
    37: "Охотник и рыболов"
}

RTRS_KEYWORDS = {
    "Первый канал": ["1tv", "pervyj", "pervyi", "channel1", "pervy"],
    "Россия 1": ["rossiya1", "russia1", "rtr1"],
    "Матч ТВ": ["matchtv", "match_tv", "match"],
    "НТВ": ["ntv"],
    "Пятый канал": ["5kanal", "5channel", "peterburg5", "5 kanal"],
    "Россия К": ["rossiya_k", "russia_k", "kultura"],
    "Россия 24": ["rossiya24", "russia24", "vesti24"],
    "Карусель": ["karusel", "carousel"],
    "ОТР": ["otr"],
    "ТВ Центр": ["tvc", "tvcentr", "tvcenter"],
    "РЕН ТВ": ["rentv", "ren_tv"],
    "Спас": ["spas"],
    "СТС": ["ctc"],
    "Домашний": ["domashniy", "domashny", "domashni"],
    "ТВ-3": ["tv3"],
    "Пятница": ["pyatnica", "pyatnitsa", "fridaytv"],
    "Звезда": ["zvezda"],
    "Мир": ["mir"],
    "ТНТ": ["tnt"],
    "Муз-ТВ": ["muztv", "muz_tv"],

    "Mezzo": ["mezzo"],
    "2x2": ["2x2", "2x2tv"],
    "RTG": ["rtg", "rtg_tv"],
    "Дождь": ["dozhd", "tvrain"],
    "Техно 24": ["techno24", "tekno24"],
    "Мульт": ["mult", "mult_tv"],
    "360": ["360tv", "360_channel"],
    "Доктор": ["doctor", "doktor"],
    "Моя Планета": ["moya_planeta", "myplanet"],
    "Че!": ["che", "chetv"],
    "Футбол": ["futbol", "football"],
    "Tiji": ["tiji"],
    "Ностальгия": ["nostalgia", "nostalgiya"],
    "Eurosport": ["eurosport"],
    "Охотник и рыболов": ["ohotnik", "rybolov", "hunter_fisher"]
}


def detect_rtrs_button(info: str, url: str):
    text = (info + " " + url).lower()
    for btn, title in RTRS_BUTTONS.items():
        t = title.lower()
        if t in text:
            return btn, title
    for title, keys in RTRS_KEYWORDS.items():
        for k in keys:
            if k in text:
                for btn, t in RTRS_BUTTONS.items():
                    if t == title:
                        return btn, title
    return None, None


# === RED Media + Bridge Media (РТРС Плюс) ===

RED_MEDIA_CHANNELS = [
    "КИНОХИТ",
    "КИНОКОМЕДИЯ",
    "КИНОМИКС",
    "КИНОПРЕМЬЕРА",
    "КИНОСЕМЬЯ",
    "МУЖСКОЕ КИНО",
    "КИНОСЕРИЯ",
    "КИНОСВИДАНИЕ",
    "НАШЕ НОВОЕ КИНО",
    "ИНДИЙСКОЕ КИНО",
    "РОДНОЕ КИНО",
    "КИНОУЖАС",
    "ДОРАМА",
    "НИНДЗЯ",
    "KINO LIVING",
    "SAGA",
    "АВТО ПЛЮС",
    "КУХНЯ",
    "ЖИВИ",
    "НОСТАЛЬГИЯ",
    "КТО ЕСТЬ КТО",
    "365",
    "ПЛАНЕТА",
    "BIG PLANET",
    "ЖЕНСКИЙ ЖУРНАЛ",
    "КВН",
    "ТОЧКА РФ",
    "EUROPA PLUS TV",
    "LIVE МУЗЫКА",
    "СУПЕР ГЕРОИ",
    "В ГОСТЯХ У СКАЗКИ",
    "РУССКАЯ НОЧЬ",
    "BARELY LEGAL TV",
    "BLUE HUSTLER"
]

RED_MEDIA_KEYWORDS = {
    "КИНОХИТ": ["kinohit", "kino_hit"],
    "КИНОКОМЕДИЯ": ["kinokomedia", "kino_komedia", "kinocomedy"],
    "КИНОМИКС": ["kinomix", "kino_mix"],
    "КИНОПРЕМЬЕРА": ["kinopremiera", "kino_premiera"],
    "КИНОСЕМЬЯ": ["kinosemya", "kino_semya"],
    "МУЖСКОЕ КИНО": ["muzhskoe_kino", "muzhskoekino"],
    "КИНОСЕРИЯ": ["kinoseriya", "kino_seriya"],
    "КИНОСВИДАНИЕ": ["kinosvidanie", "kino_svidanie"],
    "НАШЕ НОВОЕ КИНО": ["nashe_novoe_kino", "nashenovoekino"],
    "ИНДИЙСКОЕ КИНО": ["indiyskoe_kino", "indiyskoye_kino"],
    "РОДНОЕ КИНО": ["rodnoe_kino", "rodnoekino"],
    "КИНОУЖАС": ["kinoujas", "kino_ujas", "kinoujas"],
    "ДОРАМА": ["dorama"],
    "НИНДЗЯ": ["nindzya", "ninja"],
    "KINO LIVING": ["kino_living", "kinoliving"],
    "SAGA": ["saga"],
    "АВТО ПЛЮС": ["avtoplus", "avto_plus"],
    "КУХНЯ": ["kuhnya", "kuhnya_tv"],
    "ЖИВИ": ["zhivi", "zhivi_tv"],
    "НОСТАЛЬГИЯ": ["nostalgia", "nostalgiya"],
    "КТО ЕСТЬ КТО": ["kto_est_kto", "ktoestkto"],
    "365": ["365", "365tv"],
    "ПЛАНЕТА": ["planeta"],
    "BIG PLANET": ["bigplanet"],
    "ЖЕНСКИЙ ЖУРНАЛ": ["zhenskiy_zhurnal", "zhenskiyzhurnal"],
    "КВН": ["kvn", "kvntv"],
    "ТОЧКА РФ": ["tochka", "tochka_rf"],
    "EUROPA PLUS TV": ["europa_plus", "europaplustv"],
    "LIVE МУЗЫКА": ["live_music", "livemusic"],
    "СУПЕР ГЕРОИ": ["supergeroi", "super_geroi"],
    "В ГОСТЯХ У СКАЗКИ": ["v_gostyah_u_skazki", "skazki"],
    "РУССКАЯ НОЧЬ": ["russkaya_noch", "russian_night"],
    "BARELY LEGAL TV": ["barelylegal", "barely_legal"],
    "BLUE HUSTLER": ["bluehustler", "hustler"]
}

BRIDGE_MEDIA_CHANNELS = [
    "BRIDGE TV",
    "BRIDGE TV HITS",
    "BRIDGE TV CLASSIC",
    "BRIDGE TV DELUXE",
    "BRIDGE TV DANCE",
    "BRIDGE TV RUSSIAN HITS",
    "BRIDGE TV BABY TIME"
]

BRIDGE_MEDIA_KEYWORDS = {
    "BRIDGE TV": ["bridge_tv", "bridgetv", "bridge"],
    "BRIDGE TV HITS": ["bridge_tv_hits", "bridge_hits", "bridge_tvhits", "bridge_tv_hits"],
    "BRIDGE TV CLASSIC": ["bridge_tv_classic", "bridge_classic"],
    "BRIDGE TV DELUXE": ["bridge_tv_deluxe", "bridge_deluxe"],
    "BRIDGE TV DANCE": ["bridge_tv_dance", "bridge_dance"],
    "BRIDGE TV RUSSIAN HITS": ["bridge_russian_hits", "bridge_rus_hits"],
    "BRIDGE TV BABY TIME": ["bridge_baby", "bridge_baby_time"]
}


def generate_rtrs_plus_buttons():
    mapping = {}
    btn = 38
    for ch in RED_MEDIA_CHANNELS:
        mapping[ch] = btn
        btn += 1
    for ch in BRIDGE_MEDIA_CHANNELS:
        mapping[ch] = btn
        btn += 1
    return mapping


RTRS_PLUS_BUTTONS = generate_rtrs_plus_buttons()


def detect_rtrs_plus(info: str, url: str):
    text = (info + " " + url).lower()

    for title, keys in RED_MEDIA_KEYWORDS.items():
        for k in keys:
            if k in text:
                btn = RTRS_PLUS_BUTTONS.get(title)
                if btn:
                    return btn, title, "RED Media"

    for title, keys in BRIDGE_MEDIA_KEYWORDS.items():
        for k in keys:
            if k in text:
                btn = RTRS_PLUS_BUTTONS.get(title)
                if btn:
                    return btn, title, "Bridge Media"

    return None, None, None

# === HTTP HELPERS ===

def safe_get(url, stream=False):
    try:
        return requests.get(url, headers=UA, timeout=TIMEOUT, stream=stream, allow_redirects=True)
    except:
        return None


def safe_head(url):
    try:
        return requests.head(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
    except:
        return None


# === M3U8 VALIDATION ===

def is_valid_m3u8_text(text: str) -> bool:
    if not text:
        return False
    return text.startswith("#EXTM3U")


def is_master_playlist(text: str) -> bool:
    return "#EXT-X-STREAM-INF" in text


def extract_variant_urls(text: str, base_url: str):
    urls = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("http"):
            urls.append(line)
        elif line.endswith(".m3u8"):
            try:
                urls.append(urljoin(base_url, line))
            except:
                continue
    return urls


def check_variant(url: str) -> bool:
    r = safe_get(url)
    if not r or r.status_code >= 400:
        return False

    try:
        text = r.text
    except:
        return False

    if not is_valid_m3u8_text(text):
        return False

    return ".ts" in text or "#EXTINF" in text


# === MAIN STREAM CHECK ===

def is_stream_alive(url: str) -> bool:
    h = safe_head(url)
    if h and h.status_code < 400:
        ct = h.headers.get("Content-Type", "").lower()
        if "text/html" in ct:
            return False

    r = safe_get(url)
    if not r or r.status_code >= 400:
        return False

    ct = r.headers.get("Content-Type", "").lower()
    if "text/html" in ct:
        return False

    try:
        text = r.text
    except:
        return False

    if not is_valid_m3u8_text(text):
        return False

    if is_master_playlist(text):
        variants = extract_variant_urls(text, url)
        for v in variants:
            if check_variant(v):
                return True
        return False

    return ".ts" in text or "#EXTINF" in text


# === PARSER ===

def parse_m3u(text: str):
    lines = text.splitlines()
    entries = []
    current_info = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            current_info = line

        elif line.startswith("http"):
            if current_info:

                if is_adult(current_info, line):
                    print(f"[ADULT BLOCK] {line}")
                    current_info = None
                    continue

                if is_bad(current_info, line):
                    print(f"[FILTER] {line}")
                    current_info = None
                    continue

                entries.append((current_info, line))
                current_info = None

    return entries

# === LOAD/SAVE ===

def load_m3u_from_source(source: str) -> str:
    if source.startswith("http"):
        try:
            r = requests.get(source, headers=UA, timeout=10)
            r.raise_for_status()
            return r.text
        except:
            return None
    else:
        try:
            with open(source, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except:
            return None


def save_m3u(path: str, entries):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for info, url in entries:
            f.write(info + "\n")
            f.write(url + "\n")


def save_report(path: str, alive, dead, adult, rtrs, rtrs_plus):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "w", encoding="utf-8") as f:
        f.write("═══════════════════════════════════\n")
        f.write("    ОТЧЁТ ПРОВЕРКИ M3U\n")
        f.write("═══════════════════════════════════\n\n")
        f.write(f"Дата: {now}\n")
        f.write(f"Всего каналов (без adult): {len(alive) + len(dead)}\n")
        f.write(f"✅ Живых: {len(alive)}\n")
        f.write(f"❌ Мёртвых: {len(dead)}\n")
        f.write(f"🚫 Заблокировано (18+): {len(adult)}\n")
        f.write(f"📡 РТРС (1–37): {len(rtrs)}\n")
        f.write(f"📡 РТРС Плюс (RED + Bridge): {len(rtrs_plus)}\n\n")

        f.write("═══════════════════════════════════\n")
        f.write("    🚫 ЗАБЛОКИРОВАННЫЙ КОНТЕНТ (18+)\n")
        f.write("═══════════════════════════════════\n\n")
        if adult:
            for i, (info, url) in enumerate(adult, 1):
                f.write(f"{i:03d}. 🔞 ADULT | {url}\n")
        else:
            f.write("Нет adult-каналов.\n")

        f.write("\n═══════════════════════════════════\n")
        f.write("    📡 КАНАЛЫ РТРС (1–37)\n")
        f.write("═══════════════════════════════════\n\n")
        if rtrs:
            for btn, title, info, url in sorted(rtrs, key=lambda x: x[0]):
                f.write(f'Группа: "Кнопка {btn} РТРС Плюс" | {title} | {url}\n')
        else:
            f.write("Нет каналов РТРС.\n")

        f.write("\n═══════════════════════════════════\n")
        f.write("    📡 РТРС ПЛЮС (RED Media + Bridge)\n")
        f.write("═══════════════════════════════════\n\n")
        if rtrs_plus:
            for btn, group, title, info, url in sorted(rtrs_plus, key=lambda x: x[0]):
                f.write(f'Группа: "Кнопка {btn} РТРС Плюс" | {group} | {title} | {url}\n')
        else:
            f.write("Нет каналов РТРС Плюс.\n")

        f.write("\n═══════════════════════════════════\n")
        f.write("    ✅ ЖИВЫЕ КАНАЛЫ\n")
        f.write("═══════════════════════════════════\n\n")
        for i, (info, url) in enumerate(alive, 1):
            f.write(f"{i:03d}. OK   | {url}\n")

        f.write("\n═══════════════════════════════════\n")
        f.write("    ❌ МЁРТВЫЕ КАНАЛЫ\n")
        f.write("═══════════════════════════════════\n\n")
        for i, (info, url) in enumerate(dead, 1):
            f.write(f"{i:03d}. DEAD | {url}\n")


# === CHECKER ===

def check_entries(entries):
    alive = []
    dead = []

    def worker(item):
        info, url = item
        ok = is_stream_alive(url)
        return info, url, ok

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(worker, e): e for e in entries}
        for fut in as_completed(futures):
            info, url, ok = fut.result()
            if ok:
                alive.append((info, url))
            else:
                dead.append((info, url))

    return alive, dead

# === MAIN ===

def main():
    parser = argparse.ArgumentParser(
        description="🎬 Проверка M3U-плейлиста на живость ссылок + РТРС/RED/Bridge"
    )
    parser.add_argument("source", help="Путь к M3U-файлу или URL")
    parser.add_argument("-o", "--output", default="alive.m3u", help="Файл живых каналов (M3U)")
    parser.add_argument("-8", "--output8", default="alive.m3u8", help="Файл живых каналов (M3U8)")
    parser.add_argument("-r", "--report", default="report.txt", help="TXT отчёт")
    args = parser.parse_args()

    all_entries = []

    text = load_m3u_from_source(args.source)
    if not text:
        print("Ошибка загрузки основного источника.")
        return

    entries = parse_m3u(text)
    all_entries.extend(entries)

    if os.path.exists("vk.m3u"):
        vk_text = load_m3u_from_source("vk.m3u")
        if vk_text:
            vk_entries = parse_m3u(vk_text)
            all_entries.extend(vk_entries)

    # Сбор adult до фильтрации
    adult_entries = [
        (info, url) for info, url in all_entries
        if is_adult(info, url)
    ]

    # Фильтрация adult + мусор
    all_entries = [
        (info, url) for info, url in all_entries
        if not is_adult(info, url) and not is_bad(info, url)
    ]

    # Определение РТРС
    rtrs_detected = []
    for info, url in all_entries:
        btn, title = detect_rtrs_button(info, url)
        if btn:
            rtrs_detected.append((btn, title, info, url))

    # Определение РТРС Плюс (RED + Bridge)
    rtrs_plus_detected = []
    for info, url in all_entries:
        btn, title, group = detect_rtrs_plus(info, url)
        if btn:
            rtrs_plus_detected.append((btn, group, title, info, url))

    alive, dead = check_entries(all_entries)

# === PHOENIX EDITION — Матч-семейство ===

    MATCH_MAIN = ["match", "matchtv", "match_tv", "матч"]
    MATCH_SUB = {
        "игра": ["igra", "match-igra", "match_igra"],
        "страна": ["strana", "matchstrana"],
        "арена": ["arena", "matcharena"],
        "планета": ["planeta", "matchplaneta"],
        "премьер": ["premier", "matchpremier"],
        "футбол 1": ["football1", "futbol1"],
        "футбол 2": ["football2", "futbol2"],
        "футбол 3": ["football3", "futbol3"]
    }

    def normalize_match_name(info, url):
        t = (info + " " + url).lower()

        # основной Матч ТВ
        if any(x in t for x in MATCH_MAIN):
            return "Матч ТВ"

        # подканалы
        for name, keys in MATCH_SUB.items():
            if any(k in t for k in keys):
                if "hd" in t:
                    return f"Матч {name.capitalize()} HD"
                return f"Матч {name.capitalize()}"

        return None

    # === PHOENIX EDITION — кнопки X.X ===

    match_counter = 1
    match_map = {}

    def assign_button(info, url):
        nonlocal match_counter

        # Матч ТВ
        name = normalize_match_name(info, url)
        if name:
            if name == "Матч ТВ":
                return "3", name

            # подканалы Матч
            if name not in match_map:
                match_map[name] = f"3.{match_counter}"
                match_counter += 1
            return match_map[name], name

        # РТРС 1–37
        for btn, title in RTRS_BUTTONS.items():
            if title.lower() in (info + url).lower():
                return str(btn), title

        # RED + Bridge (РТРС Плюс)
        for title, btn in RTRS_PLUS_BUTTONS.items():
            if title.lower() in (info + url).lower():
                return str(btn), title

        return None, None

    # === СОХРАНЕНИЕ ПЛЕЙЛИСТА (EXTINF C1, кнопка внутри названия) ===

    def save_alive_playlist(path, alive):
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

            for info, url in alive:
                btn, name = assign_button(info, url)
                if not btn or not name:
                    continue

                tvg_id = re.sub(r"[^a-zA-Z0-9]+", "", name.lower())
                logo = ""

                # EXTINF формат Phoenix Edition (C1)
                f.write(
                    f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" '
                    f'group-title="РТРС Плюс",Кнопка {btn} {name}\n'
                )
                f.write(url + "\n")

    # === СОХРАНЕНИЕ ОТЧЁТА (Phoenix Edition) ===

    def save_phoenix_report(path, alive, dead):
        with open(path, "w", encoding="utf-8") as f:
            f.write("ОТЧЁТ ПРОВЕРКИ (Phoenix Edition)\n\n")

            for info, url in alive:
                btn, name = assign_button(info, url)
                if btn and name:
                    f.write(f'Группа: "РТРС Плюс" Кнопка {btn} {name} {url}\n')

            f.write("\nМёртвые:\n")
            for info, url in dead:
                f.write(f"DEAD {url}\n")

# === СОХРАНЕНИЕ РЕЗУЛЬТАТОВ (Phoenix Edition) ===

    # Сохраняем живые каналы в формате Phoenix Edition
    save_alive_playlist(args.output, alive)
    save_alive_playlist(args.output8, alive)

    # Сохраняем отчёт в формате Phoenix Edition
    save_phoenix_report(args.report, alive, dead)


if __name__ == "__main__":
    main()










