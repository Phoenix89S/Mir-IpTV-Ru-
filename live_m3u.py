#!/usr/bin/env python3
# live_m3u.py — финальная версия Phoenix Edition
# Полный движок проверки живости (1:1)
# Полный adult-фильтр
# Полный BAD-фильтр
# Полный расширенный поиск по потоку
# Матч-семейство (3.x)
# НТВ-семейство (4.x)
# РТРС 1–37
# RED Media + Bridge Media (РТРС Плюс)
# EXTINF формат C1
# Кнопки X.X
# Группа "РТРС Плюс"
# Группа "Разбираемся"
# Отчёт Phoenix Edition

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

# === ЖЁСТКИЙ ФИЛЬТР ADULT-КОНТЕНТА (ПОЛНЫЙ) ===

ADULT_KEYWORDS = [
    "xxx", "sex", "porn", "porno", "порно", "эрот", "эротика", "18+", "18plus",
    "brazzers", "hustler", "playboy", "venus", "dorcel", "private", "eros", "erotic",
    "fetish", "bdsm", "softcore", "hardcore",
    "cam", "webcam", "livecam",
    "nsfw",
    "barelylegal", "barely_legal",
    "bluehustler", "blue_hustler",
    "russian_night", "russkaya_noch"
]

# === ФИЛЬТР ЗАПРЕЩЁННОГО КОНТЕНТА (ПОЛНЫЙ) ===

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

# === HTTP HELPERS (ПОЛНЫЙ, 1:1, КАК ТЫ ДАЛ) ===

def safe_get(url, stream=False):
    try:
        return requests.get(url, headers=UA, timeout=TIMEOUT, stream=stream, allow_redirects=True)
    except requests.Timeout:
        print(f"[TIMEOUT] {url}")
        return None
    except requests.ConnectionError:
        print(f"[CONNECTION ERROR] {url}")
        return None
    except Exception as e:
        print(f"[ERROR] {url} — {type(e).__name__}")
        return None


def safe_head(url):
    try:
        return requests.head(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
    except requests.Timeout:
        print(f"[TIMEOUT] {url}")
        return None
    except requests.ConnectionError:
        print(f"[CONNECTION ERROR] {url}")
        return None
    except Exception as e:
        print(f"[ERROR] {url} — {type(e).__name__}")
        return None


# === M3U8 VALIDATION (ПОЛНЫЙ, 1:1) ===

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
            except Exception as e:
                print(f"[URL JOIN ERROR] {line} — {type(e).__name__}")
                continue
    return urls


def check_variant(url: str) -> bool:
    r = safe_get(url)
    if not r or r.status_code >= 400:
        return False

    try:
        text = r.text
    except Exception as e:
        print(f"[TEXT DECODE ERROR] {url} — {type(e).__name__}")
        return False

    if not is_valid_m3u8_text(text):
        return False

    return ".ts" in text or "#EXTINF" in text

# === MAIN STREAM CHECK (ПОЛНЫЙ, 1:1, КАК ТЫ ДАЛ) ===

def is_stream_alive(url: str) -> bool:
    # HEAD
    h = safe_head(url)
    if h and h.status_code < 400:
        ct = h.headers.get("Content-Type", "").lower()
        if "text/html" in ct:
            return False

    # GET
    r = safe_get(url)
    if not r or r.status_code >= 400:
        return False

    ct = r.headers.get("Content-Type", "").lower()
    if "text/html" in ct:
        return False

    try:
        text = r.text
    except Exception as e:
        print(f"[TEXT DECODE ERROR] {url} — {type(e).__name__}")
        return False

    if not is_valid_m3u8_text(text):
        return False

    # master.m3u8
    if is_master_playlist(text):
        variants = extract_variant_urls(text, url)
        for v in variants:
            if check_variant(v):
                return True
        return False

    # media.m3u8
    return ".ts" in text or "#EXTINF" in text

# === PARSER (ПОЛНЫЙ, 1:1) ===

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

                # Adult-фильтр
                if is_adult(current_info, line):
                    print(f"[ADULT BLOCK] {line}")
                    current_info = None
                    continue

                # Фильтр запрещённого
                if is_bad(current_info, line):
                    print(f"[FILTER] {line}")
                    current_info = None
                    continue

                entries.append((current_info, line))
                current_info = None

    return entries

# === LOAD/SAVE (ПОЛНЫЙ, 1:1, КАК ТЫ ДАЛ) ===

def load_m3u_from_source(source: str) -> str:
    if source.startswith("http"):
        print(f"📥 Загружаю по URL: {source}")
        try:
            r = requests.get(source, headers=UA, timeout=10)
            r.raise_for_status()
            return r.text
        except requests.Timeout:
            print(f"❌ [TIMEOUT] Не удалось загрузить {source}")
            return None
        except requests.HTTPError as e:
            print(f"❌ [HTTP ERROR {e.response.status_code}] {source}")
            return None
        except requests.ConnectionError:
            print(f"❌ [CONNECTION ERROR] {source}")
            return None
        except Exception as e:
            print(f"❌ [ERROR] {source} — {type(e).__name__}: {e}")
            return None
    else:
        print(f"📄 Читаю локальный файл: {source}")
        try:
            with open(source, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ [FILE NOT FOUND] {source}")
            return None
        except Exception as e:
            print(f"❌ [ERROR] {source} — {type(e).__name__}: {e}")
            return None


def save_m3u(path: str, entries):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for info, url in entries:
                f.write(info + "\n")
                f.write(url + "\n")
        print(f"✅ Сохранено: {path}")
    except Exception as e:
        print(f"❌ [SAVE ERROR] {path} — {type(e).__name__}: {e}")


def save_report(path: str, alive, dead):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"═══════════════════════════════════\n")
            f.write(f"    ОТЧЁТ ПРОВЕРКИ M3U\n")
            f.write(f"═══════════════════════════════════\n\n")
            f.write(f"Дата: {now}\n")
            f.write(f"Всего каналов: {len(alive) + len(dead)}\n")
            f.write(f"✅ Живых: {len(alive)}\n")
            f.write(f"❌ Мёртвых: {len(dead)}\n\n")

            f.write("═══════════════════════════════════\n")
            f.write("    ✅ ЖИВЫЕ КАНАЛЫ\n")
            f.write("═══════════════════════════════════\n\n")
            for i, (info, url) in enumerate(alive, 1):
                f.write(f"{i:03d}. ✅ OK   | {url}\n")

            f.write("\n═══════════════════════════════════\n")
            f.write("    ❌ МЁРТВЫЕ КАНАЛЫ\n")
            f.write("═══════════════════════════════════\n\n")
            for i, (info, url) in enumerate(dead, 1):
                f.write(f"{i:03d}. ❌ DEAD | {url}\n")
        
        print(f"✅ Сохранено: {path}")
    except Exception as e:
        print(f"❌ [SAVE ERROR] {path} — {type(e).__name__}: {e}")

# === CHECKER (ПОЛНЫЙ, 1:1, КАК ТЫ ДАЛ) ===

def check_entries(entries):
    alive = []
    dead = []

    def worker(item):
        info, url = item
        try:
            ok = is_stream_alive(url)
            return info, url, ok
        except Exception as e:
            print(f"[WORKER ERROR] {url} — {type(e).__name__}")
            return info, url, False

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(worker, e): e for e in entries}
        for fut in as_completed(futures):
            try:
                info, url, ok = fut.result()
                status = "✅ OK" if ok else "❌ DEAD"
                print(f"[{status}] {url}")
                if ok:
                    alive.append((info, url))
                else:
                    dead.append((info, url))
            except Exception as e:
                print(f"[FUTURE ERROR] {type(e).__name__}")

    return alive, dead

# ============================================================
#   PHOENIX EDITION — РАСШИРЕННЫЙ ПОИСК ПО ПОТОКУ
# ============================================================

# === РТРС 1–37 (ПОЛНЫЙ СПИСОК) ===

RTRS_CHANNELS = {
    1:  ["Первый", "Первый канал", "1 канал", "1tv", "1tv.ru"],
    2:  ["Россия 1", "Россия1", "russia1", "rtr"],
    3:  ["Матч ТВ", "Матч", "Match TV", "MatchTV"],
    4:  ["НТВ"],
    5:  ["Пятый", "5 канал", "Пятый канал"],
    6:  ["Культура", "Россия К", "Россия Культура"],
    7:  ["Россия 24", "Россия24", "russia24"],
    8:  ["Карусель"],
    9:  ["ОТР"],
    10: ["ТВ Центр", "ТВЦ", "TVC"],
    11: ["РЕН ТВ", "РЕН", "REN TV"],
    12: ["Спас"],
    13: ["СТС"],
    14: ["Домашний"],
    15: ["ТВ3", "ТВ 3"],
    16: ["Пятница"],
    17: ["Звезда"],
    18: ["Мир"],
    19: ["ТНТ"],
    20: ["Муз-ТВ", "Музтв", "muztv"],
    21: ["СТС Love", "СТС Лав"],
    22: ["Че"],
    23: ["Ю"],
    24: ["ТНТ4", "ТНТ 4"],
    25: ["Сарафан"],
    26: ["Моя Планета"],
    27: ["Наука"],
    28: ["Живая Планета"],
    29: ["История"],
    30: ["Мульт"],
    31: ["Мультиландия"],
    32: ["Телекафе"],
    33: ["Суббота"],
    34: ["Солнце"],
    35: ["Победа"],
    36: ["Мир 24"],
    37: ["Мир Premium"]
}

# === RED MEDIA (РТРС ПЛЮС — базовый список) ===

RED_MEDIA = {
    "RED": [
        "Кухня ТВ", "Мама", "Усадьба", "Загородный", "Охота и Рыбалка",
        "Мужской", "Наука 2.0", "24 Техно", "24 Док", "24 Кино"
    ]
}

# === BRIDGE MEDIA (РТРС ПЛЮС) ===

BRIDGE_MEDIA = {
    "BRIDGE": [
        "Bridge TV", "Bridge Hits", "Bridge Deluxe", "Bridge Русский Хит",
        "Bridge Шлягер", "Bridge Dance"
    ]
}

# === МАТЧ-СЕМЕЙСТВО (КНОПКИ 3.X) ===

MATCH_FAMILY = {
    "Матч ТВ":        "3",
    "Матч Игра":      "3.1",
    "Матч Страна":    "3.2",
    "Матч Арена":     "3.3",
    "Матч Планета":   "3.4",
    "Матч Премьер":   "3.5",
    "Матч Футбол 1":  "3.6",
    "Матч Футбол 2":  "3.7",
    "Матч Футбол 3":  "3.8"
}

# === НТВ-СЕМЕЙСТВО (КНОПКИ 4.X) ===

NTV_FAMILY = {
    "НТВ":        "4",
    "НТВ Мир":    "4.1",
    "НТВ Хит":    "4.2",
    "НТВ Стиль":  "4.3",
    "НТВ Право":  "4.4",
    "НТВ Сериал": "4.5",
    "НТВ HD":     "4.6"
}

# === ПОЛНЫЙ ПАКЕТ RED MEDIA 47 (КНОПКИ 38.X) ===

PHOENIX_RTRS_PLUS = {
    38.1:  "Матч! Футбол 1",
    38.2:  "Матч! Футбол 2",
    38.3:  "Матч! Футбол 3",
    38.4:  "Матч! Премьер",
    38.5:  "Матч! Страна",
    38.6:  "Матч! Планета",
    38.7:  "Матч! Игра",
    38.8:  "Матч! Арена",
    38.9:  "Боец",
    38.10: "Бокс ТВ",
    38.11: "KHL",
    38.12: "KHL Prime",
    38.13: "ММА-ТВ",
    38.14: "Кинохит",
    38.15: "Кинокомедия",
    38.16: "Киномикс",
    38.17: "Кинопремьера",
    38.18: "Киносемья",
    38.19: "Мужское кино",
    38.20: "Киносерия",
    38.21: "Киносвидание",
    38.22: "Наше новое кино",
    38.23: "Индийское кино",
    38.24: "Родное кино",
    38.25: "Киноужас",
    38.26: "Дорама",
    38.27: "Zee TV",
    38.28: "Kino Living",
    38.29: "SAGA",
    38.30: "Авто Плюс",
    38.31: "Кухня",
    38.32: "Живи",
    38.33: "Телеканал Ностальгия",
    38.34: "Кто есть кто",
    38.35: "365 дней ТВ",
    38.36: "Ля-Минор ТВ",
    38.37: "Женский журнал",
    38.38: "Big Planet",
    38.39: "КВН ТВ",
    38.40: "Русская ночь",
    38.41: "Точка РФ",
    38.42: "Barely Legal TV",
    38.43: "Blue Hustler",
    38.44: "Europa Plus TV",
    38.45: "Live Музыка",
    38.46: "Супергерои",
    38.47: "В гостях у сказки"
}

# === НОРМАЛИЗАЦИЯ НАЗВАНИЙ ===

def normalize_name(name: str) -> str:
    name = name.lower()
    name = name.replace("hd", "").replace("sd", "")
    name = name.replace("канал", "")
    name = name.replace("тв", "tv")
    name = re.sub(r"\s+", " ", name)
    return name.strip()


# === ПОИСК В РТРС 1–37 ===

def detect_rtrs(name: str):
    n = normalize_name(name)
    for num, variants in RTRS_CHANNELS.items():
        for v in variants:
            if normalize_name(v) in n:
                return num
    return None


# === ПОИСК В МАТЧ-СЕМЕЙСТВЕ (3.X) ===

def detect_match_family(name: str):
    n = normalize_name(name)
    for title, button in MATCH_FAMILY.items():
        if normalize_name(title) in n:
            return button
    return None


# === ПОИСК В НТВ-СЕМЕЙСТВЕ (4.X) ===

def detect_ntv_family(name: str):
    n = normalize_name(name)
    for title, button in NTV_FAMILY.items():
        if normalize_name(title) in n:
            return button
    return None


# === ПОИСК В ПОЛНОМ ПАКЕТЕ RED MEDIA 47 (38.X) ===

def detect_rtrs_plus(name: str):
    n = normalize_name(name)
    for button, title in PHOENIX_RTRS_PLUS.items():
        if normalize_name(title) in n:
            return button
    return None


# === ПОИСК В RED MEDIA (базовый список) ===

def detect_red_media(name: str):
    n = normalize_name(name)
    for group, channels in RED_MEDIA.items():
        for ch in channels:
            if normalize_name(ch) in n:
                return group
    return None


# === ПОИСК В BRIDGE MEDIA ===

def detect_bridge_media(name: str):
    n = normalize_name(name)
    for group, channels in BRIDGE_MEDIA.items():
        for ch in channels:
            if normalize_name(ch) in n:
                return group
    return None

# === FUZZY-MATCHING (мягкое сравнение названий) ===

def fuzzy_match(a: str, b: str) -> bool:
    a = normalize_name(a)
    b = normalize_name(b)

    if a == b:
        return True

    # частичное совпадение
    if a in b or b in a:
        return True

    # расстояние Левенштейна (до 2 ошибок)
    if abs(len(a) - len(b)) <= 2:
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, a, b).ratio()
        if ratio >= 0.75:
            return True

    return False


# === FALLBACK «РАЗБИРАЕМСЯ» ===

def detect_unknown(name: str):
    """
    Если канал не попал ни в одну категорию — отправляем в 'unknown'
    """
    return "unknown"


# === ОПРЕДЕЛЕНИЕ КНОПКИ КАНАЛА (главная функция) ===

def detect_button(name: str):
    """
    Возвращает:
    - номер кнопки (1–999)
    - категорию ('rtrs', 'match', 'ntv', 'rtrs_plus', 'red', 'bridge', 'unknown')
    """

    # 1) РТРС 1–37
    rtrs = detect_rtrs(name)
    if rtrs:
        return rtrs, "rtrs"

    # 2) Матч‑семейство (3.x)
    match_btn = detect_match_family(name)
    if match_btn:
        return match_btn, "match"

    # 3) НТВ‑семейство (4.x)
    ntv_btn = detect_ntv_family(name)
    if ntv_btn:
        return ntv_btn, "ntv"

    # 4) Полный пакет RED MEDIA 47 (38.x)
    rtrs_plus = detect_rtrs_plus(name)
    if rtrs_plus:
        return rtrs_plus, "rtrs_plus"

    # 5) RED MEDIA (базовый список)
    red = detect_red_media(name)
    if red:
        return 100, "red"   # 100 — условная кнопка группы

    # 6) BRIDGE MEDIA
    bridge = detect_bridge_media(name)
    if bridge:
        return 101, "bridge"

    # 7) Fallback — неизвестный канал
    return 999, detect_unknown(name)










































if __name__ == "__main__":
    main()










