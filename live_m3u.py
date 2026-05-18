#!/usr/bin/env python3
# live_m3u.py — финальная версия с vk.m3u, adult-фильтром и улучшенной проверкой

import requests
import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

TIMEOUT = 4
THREADS = 25

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# === ЖЁСТКИЙ ФИЛЬТР ADULT-КОНТЕНТА ===

ADULT_KEYWORDS = [
    "xxx", "sex", "porn", "porno", "порно", "эрот", "эротика", "18+", "18plus",
    "brazzers", "hustler", "playboy", "venus", "dorcel", "private", "eros", "erotic",
    "hot", "night", "ночь", "ночной", "ночное",
    "love", "amour", "amore",
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
            if base_url.endswith("/"):
                urls.append(base_url + line)
            else:
                urls.append(base_url.rsplit("/", 1)[0] + "/" + line)
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
    except:
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


# === LOAD/SAVE ===

def load_m3u_from_source(source: str) -> str:
    if source.startswith("http"):
        print(f"Загружаю по URL: {source}")
        r = requests.get(source, headers=UA, timeout=10)
        r.raise_for_status()
        return r.text
    else:
        print(f"Читаю локальный файл: {source}")
        with open(source, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def save_m3u(path: str, entries):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for info, url in entries:
            f.write(info + "\n")
            f.write(url + "\n")


def save_report(path: str, alive, dead):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"ОТЧЁТ ПРОВЕРКИ M3U\n")
        f.write(f"Дата: {now}\n")
        f.write(f"Всего каналов: {len(alive) + len(dead)}\n")
        f.write(f"Живых: {len(alive)}\n")
        f.write(f"Мёртвых: {len(dead)}\n\n")

        f.write("=== ЖИВЫЕ КАНАЛЫ ===\n")
        for i, (info, url) in enumerate(alive, 1):
            f.write(f"{i:03d}. OK   | {url}\n")

        f.write("\n=== МЁРТВЫЕ КАНАЛЫ ===\n")
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
            status = "OK" if ok else "DEAD"
            print(f"[{status}] {url}")
            if ok:
                alive.append((info, url))
            else:
                dead.append((info, url))

    return alive, dead


# === MAIN ===

def main():
    parser = argparse.ArgumentParser(
        description="Проверка M3U-плейлиста на живость ссылок"
    )
    parser.add_argument("source", help="Путь к M3U-файлу или URL")
    parser.add_argument("-o", "--output", default="alive.m3u", help="Файл живых каналов")
    parser.add_argument("-8", "--output8", default="alive.m3u8", help="Файл M3U8")
    parser.add_argument("-r", "--report", default="report.txt", help="TXT отчёт")
    args = parser.parse_args()

    all_entries = []

    # === 1. Основной источник ===
    text = load_m3u_from_source(args.source)
    entries = parse_m3u(text)
    print(f"Найдено каналов: {len(entries)}")
    all_entries.extend(entries)

    # === 2. Автоподключение vk.m3u ===
    if os.path.exists("vk.m3u"):
        print("\n=== Найден vk.m3u — добавляю в проверку ===")
        vk_text = load_m3u_from_source("vk.m3u")
        vk_entries = parse_m3u(vk_text)
        print(f"VK каналов: {len(vk_entries)}")
        all_entries.extend(vk_entries)
    else:
        print("\nvk.m3u не найден — пропускаю")

    # === 3. Дополнительная зачистка adult и мусора ===
    all_entries = [
        (info, url) for info, url in all_entries
        if not is_adult(info, url) and not is_bad(info, url)
    ]

    print(f"\nВсего каналов к проверке: {len(all_entries)}")

    if not all_entries:
        print("Каналов не найдено.")
        return

    alive, dead = check_entries(all_entries)

    print("\n=== РЕЗУЛЬТАТ ===")
    print(f"Живых:   {len(alive)}")
    print(f"Мёртвых: {len(dead)}")

    save_m3u(args.output, alive)
    save_m3u(args.output8, alive)
    save_report(args.report, alive, dead)

    print("\nСоздано:")
    print(f" ✔ {args.output}")
    print(f" ✔ {args.output8}")
    print(f" ✔ {args.report}")


if __name__ == "__main__":
    main()