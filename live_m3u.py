#!/usr/bin/env python3
# live_m3u.py

import requests
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

TIMEOUT = 3.5
THREADS = 20


def is_stream_alive(url: str) -> bool:
    try:
        # Сначала HEAD
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code < 400:
            ct = r.headers.get("Content-Type", "").lower()
            if "text/html" in ct:
                return False
            return True

        # Если HEAD не зашёл — пробуем GET
        r = requests.get(url, timeout=TIMEOUT, stream=True)
        if r.status_code < 400:
            ct = r.headers.get("Content-Type", "").lower()
            if "text/html" in ct:
                return False
            return True
    except Exception:
        return False
    return False


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
                entries.append((current_info, line))
                current_info = None
    return entries


def load_m3u_from_source(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        print(f"Загружаю по URL: {source}")
        r = requests.get(source, timeout=10)
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


def save_m3u8(path: str, entries):
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


def main():
    parser = argparse.ArgumentParser(
        description="Проверка M3U-плейлиста на живость ссылок"
    )
    parser.add_argument("source", help="Путь к M3U-файлу или URL")
    parser.add_argument("-o", "--output", default="alive.m3u", help="Файл живых каналов")
    parser.add_argument("-8", "--output8", default="alive.m3u8", help="Файл M3U8")
    parser.add_argument("-r", "--report", default="report.txt", help="TXT отчёт")
    args = parser.parse_args()

    text = load_m3u_from_source(args.source)
    entries = parse_m3u(text)

    print(f"Найдено каналов: {len(entries)}")
    if not entries:
        print("Каналов не найдено.")
        return

    alive, dead = check_entries(entries)

    print("\n=== РЕЗУЛЬТАТ ===")
    print(f"Живых:   {len(alive)}")
    print(f"Мёртвых: {len(dead)}")

    save_m3u(args.output, alive)
    save_m3u8(args.output8, alive)
    save_report(args.report, alive, dead)

    print("\nСоздано:")
    print(f" ✔ {args.output}")
    print(f" ✔ {args.output8}")
    print(f" ✔ {args.report}")


if __name__ == "__main__":
    main()