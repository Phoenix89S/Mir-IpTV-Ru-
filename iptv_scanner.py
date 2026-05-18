#!/usr/bin/env python3
# iptv_scanner.py
# Исправленная версия с гарантированным созданием плейлиста

import requests
import csv
import json
import sqlite3
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

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
    """Загружает M3U8 контент и проверяет доступность потока"""
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True)
        if r.status_code >= 400:
            return None
        ct = r.headers.get("Content-Type", "").lower()
        if "text/html" in ct:
            return None
        chunk = next(r.iter_content(chunk_size=4096), b"")
        return chunk.decode("utf-8", errors="ignore")
    except Exception as e:
        return None


# ============================
# 3. Извлечение названия канала
# ============================

def extract_channel_name(m3u8_text: str) -> str | None:
    """Извлекает название канала из M3U8 метаданных"""
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
            if name:
                return name
    return None


# ============================
# 4. Обработка одного URL
# ============================

def process_url(url: str, cdn: str) -> dict | None:
    """Обрабатывает один URL кандидата"""
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
    """Генерирует список URL кандидатов для сканирования"""
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
    """Многопоточное сканирование URL кандидатов"""
    results = []

    def worker(item):
        return process_url(item["url"], item["cdn"])

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(worker, c): c for c in candidates}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                print(f"[OK] {res['name']} | {res['cdn']} | {res['url']}")
                results.append(res)

    return results


# ============================
# 7. Сохранение БД
# ============================

def save_json(path: str, data: list):
    """Сохраняет данные в JSON"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(path: str, data: list):
    """Сохраняет данные в CSV"""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["name", "url", "cdn", "timestamp"])
        for row in data:
            w.writerow([row["name"], row["url"], row["cdn"], row["timestamp"]])


def init_sqlite(path: str):
    """Инициализирует SQLite БД"""
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
    """Сохраняет данные в SQLite"""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for row in data:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO streams (name, url, cdn, timestamp)
                VALUES (?, ?, ?, ?)
            """, (row["name"], row["url"], row["cdn"], row["timestamp"]))
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()


# ============================
# 8. Итоговый плейлист (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ============================

def save_m3u(path: str, data: list):
    """Сохраняет плейлист в M3U формат с группировкой по CDN"""
    if not data:
        print(f"⚠️  Нет данных для сохранения плейлиста")
        return False

    try:
        # Группировать по CDN
        by_cdn = {}
        for row in data:
            cdn = row["cdn"]
            if cdn not in by_cdn:
                by_cdn[cdn] = []
            by_cdn[cdn].append(row)

        # Записать плейлист
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            # Писать группами по CDN
            for cdn in sorted(by_cdn.keys()):
                channels = by_cdn[cdn]
                for row in channels:
                    name = row["name"]
                    url = row["url"]
                    f.write(f'#EXTINF:-1 tvg-name="{name}" group-title="{cdn}",{name}\n')
                    f.write(url + "\n")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении плейлиста: {e}")
        return False


def save_m3u_advanced(path: str, data: list):
    """Сохраняет плейлист с дедупликацией и сортировкой"""
    if not data:
        print(f"⚠️  Нет данных для сохранения плейлиста")
        return False

    try:
        # Убрать дубликаты по названию канала
        seen = {}
        for row in data:
            key = row["name"].lower()
            if key not in seen:
                seen[key] = row
        
        # Отсортировать по названию
        sorted_data = sorted(seen.values(), key=lambda x: x["name"])
        
        # Группировать по CDN
        by_cdn = {}
        for row in sorted_data:
            cdn = row["cdn"]
            if cdn not in by_cdn:
                by_cdn[cdn] = []
            by_cdn[cdn].append(row)

        # Записать плейлист
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            # Писать группами по CDN
            for cdn in sorted(by_cdn.keys()):
                for row in by_cdn[cdn]:
                    name = row["name"]
                    url = row["url"]
                    f.write(f'#EXTINF:-1 tvg-name="{name}" group-title="{cdn}",{name}\n')
                    f.write(url + "\n")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении плейлиста: {e}")
        return False


# ============================
# 9. Слияние плейлистов (БОНУС)
# ============================

def merge_playlists(playlist_files: list, output: str) -> bool:
    """Объединяет несколько M3U плейлистов в один"""
    all_entries = []
    
    for pfile in playlist_files:
        try:
            with open(pfile, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            i = 0
            while i < len(lines):
                if lines[i].startswith("#EXTINF"):
                    extinf = lines[i]
                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()
                        if url and not url.startswith("#"):
                            all_entries.append((extinf, url))
                    i += 2
                else:
                    i += 1
        except FileNotFoundError:
            print(f"⚠️  Файл не найден: {pfile}")
    
    if not all_entries:
        print(f"⚠️  Нет данных для слияния плейлистов")
        return False

    # Записать объединённый плейлист
    try:
        with open(output, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for extinf, url in all_entries:
                f.write(extinf)
                f.write(url + "\n")
        
        print(f"✔️  Плейлист объединён: {output} ({len(all_entries)} каналов)")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении объединённого плейлиста: {e}")
        return False


# ============================
# 10. MAIN
# ============================

def main():
    print("=" * 60)
    print("IPTV SCANNER v2.0 - Исправленная версия")
    print("=" * 60)
    
    print("\n📋 Генерация URL-кандидатов...")
    candidates = generate_candidates()
    print(f"✔️  Всего кандидатов: {len(candidates)}")

    print("\n🔍 Сканирование потоков...")
    results = scan_all(candidates)

    print(f"\n✅ Найдено живых потоков: {len(results)}")

    if not results:
        print("\n⚠️  Нечего сохранять. Результатов не найдено.")
        return

    # Инициализация SQLite
    init_sqlite(DB_SQLITE)

    # Сохранение во все форматы
    print("\n💾 Сохранение данных...")
    
    save_json(DB_JSON, results)
    print(f"✔️  {DB_JSON}")
    
    save_csv(DB_CSV, results)
    print(f"✔️  {DB_CSV}")
    
    save_sqlite(DB_SQLITE, results)
    print(f"✔️  {DB_SQLITE}")
    
    # ГЛАВНОЕ: Сохранение плейлиста
    if save_m3u(PLAYLIST_NAME, results):
        print(f"✔️  {PLAYLIST_NAME}")
    else:
        print(f"❌ Ошибка при сохранении {PLAYLIST_NAME}")

    print("\n" + "=" * 60)
    print("✅ СКАНИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    print("\n📁 Сохранённые файлы:")
    print(f"   • {DB_JSON}")
    print(f"   • {DB_CSV}")
    print(f"   • {DB_SQLITE}")
    print(f"   • {PLAYLIST_NAME}")
    print(f"\n💡 Используйте {PLAYLIST_NAME} в плеере (VLC, Kodi, etc.)")


if __name__ == "__main__":
    main()