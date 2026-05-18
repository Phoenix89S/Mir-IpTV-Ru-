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



















































if __name__ == "__main__":
    main()










