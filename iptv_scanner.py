#!/usr/bin/env python3
# iptv_scanner.py

import requests
import csv
import json
import sqlite3
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

TIMEOUT = 4
THREADS = 20

DB_JSON = "iptv_db.json"
DB_CSV = "iptv_db.csv"
DB_SQLITE = "iptv_db.sqlite"
PLAYLIST_NAME = "Test_Donor_2026.m3u"


# ============================
# 1. CDN МАСКИ ДЛЯ СКАНЕРА
# ============================

CDN_PATTERNS = [
    {
        "cdn": "ngenix",
        "pattern": "https://a3569457567-s70378.cdn.ngenix.net/hls/{id}/index.m3u8",
        "range": [1000, 1200]
    },
    {
        "cdn": "cdnvideo",
        "pattern": "https://edge01.cdnvideo.ru/channel/{id}/index.m3u8",
        "range": [1, 200]
    }
    # сюда добавишь свои CDN
]


# ============================
# 2. Проверка потока
# ============================

def fetch_m3u8(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True)
        if r.status_code >= 400:
            return None
        ct = r.headers.get("Content-Type", "").lower()
        if "text/html" in ct:
            return None
        chunk = next(r.iter_content(chunk_size=4096), b"")
        return chunk.decode("utf-8", errors="ignore")
    except Exception:
        return None


# ============================
# 3. Извлечение названия канала
# ============================

def extract_channel_name(m3u8_text: str) -> str | None:
    patterns = [
        r'NAME="([^"]+)"',
        r'#EXTINF:[^,]*,(.+)',
        r'group-title="([^"]+)"',
        r'title="([^"]+)"'
    ]
    for p in patterns:
        m = re.search(p, m3u8_text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            name = re.sub(r'\b(HD|FHD|UHD|4K|1080p|720p)\b', '', name, flags=re.I)
            name = re.sub(r'\s+', ' ', name).strip()
            return name
    return None


# ============================
# 4. Обработка одного URL
# ============================

def process_url(url: str, cdn: str) -> dict | None:
    text = fetch_m3u8(url)
    if not text:
        return None

    name = extract_channel_name(text)
    if not name:
        return None

    return {
        "url": url,
        "name": name,
        "cdn": cdn,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }


# ============================
# 5. Генерация URL по маскам
# ============================

def generate_candidates() -> list:
    candidates = []
    for item in CDN_PATTERNS:
        cdn = item["cdn"]
        pattern = item["pattern"]
        start, end = item["range"]

        for i in range(start, end + 1):
            url = pattern.format(id=i)
            candidates.append({"url": url, "cdn": cdn})

    return candidates


# ============================
# 6. Многопоточный сбор
# ============================

def scan_all(candidates: list) -> list:
    results = []

    def worker(item):
        return process_url(item["url"], item["cdn"])

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(worker, c): c for c in candidates}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                print(f"[OK] {res['name']} | {res['url']}")
                results.append(res)

    return results


# ============================
# 7. Сохранение БД
# ============================

def save_json(path: str, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(path: str, data: list):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["name", "url", "cdn", "timestamp"])
        for row in data:
            w.writerow([row["name"], row["url"], row["cdn"], row["timestamp"]])


def init_sqlite(path: str):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT UNIQUE,
            cdn TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_sqlite(path: str, data: list):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for row in data:
        cur.execute("""
            INSERT OR REPLACE INTO streams (name, url, cdn, timestamp)
            VALUES (?, ?, ?, ?)
        """, (row["name"], row["url"], row["cdn"], row["timestamp"]))
    conn.commit()
    conn.close()


# ============================
# 8. Итоговый плейлист
# ============================

def save_m3u(path: str, data: list):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for row in data:
            name = row["name"]
            url = row["url"]
            cdn = row["cdn"]
            f.write(f'#EXTINF:-1 tvg-name="{name}" group-title="{cdn}",{name}\n')
            f.write(url + "\n")


# ============================
# 9. MAIN
# ============================

def main():
    print("Генерация URL-кандидатов...")
    candidates = generate_candidates()
    print(f"Всего кандидатов: {len(candidates)}")

    print("Сканирование...")
    results = scan_all(candidates)

    print(f"\nНайдено живых потоков: {len(results)}")

    if not results:
        print("Нечего сохранять.")
        return

    init_sqlite(DB_SQLITE)

    save_json(DB_JSON, results)
    save_csv(DB_CSV, results)
    save_sqlite(DB_SQLITE, results)
    save_m3u(PLAYLIST_NAME, results)

    print("\nСохранено:")
    print(f" ✔ {DB_JSON}")
    print(f" ✔ {DB_CSV}")
    print(f" ✔ {DB_SQLITE}")
    print(f" ✔ {PLAYLIST_NAME}")


if __name__ == "__main__":
    main()