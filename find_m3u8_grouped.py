import requests
import re
from collections import defaultdict
from datetime import datetime

# Источники плейлистов
GITHUB_PLAYLISTS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/channels/ru.m3u",
    "http://rafail1982.uz/playlists/LIST2.m3u",
    "https://raw.githubusercontent.com/Phoenix89S/Mir-IpTV-Ru-/main/code",
    "http://rafail1982.uz/playlists/DIMONOVICH.m3u",
    "https://raw.githubusercontent.com/Zet2009/MOJE1/gh-pages/IPTVmir.m3u8",
]

# Группы для сортировки
CHANNEL_GROUPS = {
    "Кнопка 3 РТРС: Матч": {
        "3.0": "Матч",
        "3.1": "Матч SD",
        "3.2": "Матч HD",
        "3.3.1": "Матч +0",
        "3.3.2": "Матч +1",
        "3.3.3": "Матч +2",
        "3.3.4": "Матч +3",
        "3.3.5": "Матч +4",
        "3.3.6": "Матч +5",
        "3.3.7": "Матч +6",
        "3.3.8": "Матч +7",
        "3.3.9": "Матч +8",
        "3.4.1": "Матч Футбол 1",
        "3.4.2": "Матч Футбол 2",
        "3.4.3": "Матч Футбол 3",
        "3.5": "Матч Страна",
        "3.6": "Матч Планета",
        "3.7": "Матч Игра",
        "3.8": "Матч Боец",
    },
    "Кнопка 4 РТРС: НТВ": {
        "4.1": "НТВ",
        "4.2": "НТВ Мир",
        "4.3": "НТВ Стиль",
        "4.4": "НТВ Право",
        "4.5": "НТВ Хит",
        "4.6": "НТВ HD",
    },
}

OUTPUT_FILE = "Test_Channels_Mir_2026.m3u8"
STABLE_OUTPUT_FILE = "Mir_iptv_stable.m3u"

def get_links_from_m3u(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        print(f"   ⏳ Загружаю {url}...")
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        content = resp.text
        pattern = re.compile(r'#EXTINF:(.*)(?:\n#.*)*\n(https?://\S+)', re.IGNORECASE)
        return pattern.findall(content)
    except Exception as e:
        print(f"   ⚠️ Ошибка: {e}")
        return []

def extract_channel_name(meta):
    if ',' in meta:
        return meta.rsplit(',', 1)[-1].strip()
    return meta

def find_group_and_orbit(full_meta, channel_groups):
    channel_name = extract_channel_name(full_meta)
    for group_name, orbits in channel_groups.items():
        for orbit, keyword in orbits.items():
            if keyword.lower() in channel_name.lower():
                return group_name, orbit, channel_name
    return "Прочее", "999", channel_name

def create_stable_playlist_with_sorting(all_channels):
    """Создаёт второй (стабильный) плейлист с аналогичной сортировкой"""
    print(f"\n{'='*60}\n🔧 Создаю стабильный плейлист: {STABLE_OUTPUT_FILE}...")
    
    with open(STABLE_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        count = 0

        # Сортировка групп по номеру первой кнопки
        sorted_groups = sorted(
            all_channels.items(),
            key=lambda x: min(float(o.split('.')[0]) for o in x[1].keys() if o != "999") 
            if any(o != "999" for o in x[1].keys()) else 999
        )

        for group_name, orbits in sorted_groups:
            # Сортировка орбит (внутри группы)
            sorted_orbits = sorted(
                orbits.items(),
                key=lambda x: tuple(map(int, x[0].split('.'))) if x[0] != "999" else (999,)
            )

            for orbit, channels_list in sorted_orbits:
                for ch_idx, (meta, link, name) in enumerate(channels_list, 1):
                    # В стабильном варианте тоже сохраняем красивое имя
                    display_name = name
                    if orbit != "999":
                        full_orbit = f"{orbit}.{ch_idx}" if len(channels_list) > 1 else orbit
                        display_name = f"{full_orbit} {name}"
                    
                    # Собираем финальную строку метаданных
                    if ',' in meta:
                        meta_parts = meta.rsplit(',', 1)
                        final_meta = f"{meta_parts[0]},{display_name}"
                    else:
                        final_meta = f"-1 group-title=\"{group_name}\",{display_name}"
                    
                    f.write(f'#EXTINF:{final_meta}\n{link}\n')
                    count += 1
    return count

def main():
    print(f"🚀 Старт: {datetime.now().strftime('%H:%M:%S')}")
    all_channels = defaultdict(lambda: defaultdict(list))
    seen_links = set()
    total_found = 0

    # 1. СБОР ДАННЫХ
    for url in GITHUB_PLAYLISTS:
        items = get_links_from_m3u(url)
        total_found += len(items)
        for meta, link in items:
            link = link.strip()
            if link in seen_links: continue
            seen_links.add(link)
            
            group, orbit, name = find_group_and_orbit(meta.strip(), CHANNEL_GROUPS)
            all_channels[group][orbit].append((meta.strip(), link, name))

    print(f"\n📊 Статистика: Уникальных ссылок {len(seen_links)} из {total_found}")

    # 2. ЗАПИСЬ ОСНОВНОГО ФАЙЛА
    print(f"\n📝 Записываю основной файл: {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        main_count = 0
        
        sorted_groups = sorted(
            all_channels.items(),
            key=lambda x: min(float(o.split('.')[0]) for o in x[1].keys() if o != "999") 
            if any(o != "999" for o in x[1].keys()) else 999
        )

        for group_name, orbits in sorted_groups:
            sorted_orbits = sorted(orbits.items(), key=lambda x: tuple(map(int, x[0].split('.'))) if x[0] != "999" else (999,))
            for orbit, channels_list in sorted_orbits:
                for ch_idx, (meta, link, name) in enumerate(channels_list, 1):
                    display_name = name
                    if orbit != "999":
                        full_orbit = f"{orbit}.{ch_idx}" if len(channels_list) > 1 else orbit
                        display_name = f"{full_orbit} {name}"
                    
                    if ',' in meta:
                        final_meta = f"{meta.rsplit(',', 1)[0]},{display_name}"
                    else:
                        final_meta = f"-1 group-title=\"{group_name}\",{display_name}"
                        
                    f.write(f'#EXTINF:{final_meta}\n{link}\n')
                    main_count += 1

    # 3. ЗАПИСЬ СТАБИЛЬНОГО ФАЙЛА (Вызов функции)
    stable_count = create_stable_playlist_with_sorting(all_channels)

    print(f"\n{'='*60}")
    print(f"✨ Готово!")
    print(f"📁 Файл 1 (Основной): {OUTPUT_FILE} ({main_count} каналов)")
    print(f"📁 Файл 2 (Стабильный): {STABLE_OUTPUT_FILE} ({stable_count} каналов)")
    print(f"⏰ Завершено в {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
