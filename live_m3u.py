#!/usr/bin/env python3
# live_m3u.py — версия с безопасностью, улучшениями и отчётом по adult-контенту

import requests
import argparse
import os
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
    "nsfw"
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


def save_report(path: str, alive, dead, adult):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "w", encoding="utf-8") as f:
        f.write("═══════════════════════════════════\n")
        f.write("    ОТЧЁТ ПРОВЕРКИ M3U\n")
        f.write("═══════════════════════════════════\n\n")
        f.write(f"Дата: {now}\n")
        f.write(f"Всего каналов: {len(alive) + len(dead) + len(adult)}\n")
        f.write(f"✅ Живых: {len(alive)}\n")
        f.write(f"❌ Мёртвых: {len(dead)}\n")
        f.write(f"🚫 Заблокировано (18+): {len(adult)}\n\n")

        f.write("═══════════════════════════════════\n")
        f.write("    🚫 ЗАБЛОКИРОВАННЫЙ КОНТЕНТ (18+)\n")
        f.write("═══════════════════════════════════\n\n")
        if adult:
            for i, (info, url) in enumerate(adult, 1):
                f.write(f"{i:03d}. 🔞 ADULT | {url}\n")
        else:
            f.write("Нет adult-каналов.\n")

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
        description="🎬 Проверка M3U-плейлиста на живость ссылок"
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

    # === Сбор adult-контента ДО фильтрации ===
    adult_entries = [
        (info, url) for info, url in all_entries
        if is_adult(info, url)
    ]

    # === Фильтрация ===
    all_entries = [
        (info, url) for info, url in all_entries
        if not is_adult(info, url) and not is_bad(info, url)
    ]

    alive, dead = check_entries(all_entries)

    save_m3u(args.output, alive)
    save_m3u(args.output8, alive)
    save_report(args.report, alive, dead, adult_entries)


if __name__ == "__main__":
    main()