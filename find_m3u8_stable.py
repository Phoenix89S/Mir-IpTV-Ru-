import requests
import re
from collections import defaultdict
from datetime import datetime

GITHUB_PLAYLISTS = [
    # --- iptv-org основные ---
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/channels/ru.m3u",

    # --- iptv-org расширенные RU ---
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_15plusmg.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_bonustv.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_catcast.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_mylifeisgood.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_ntv.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_rt.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_smotrim.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_televizor24.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_tvbricks.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_tvteleport.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru_zabava.m3u",

    # --- Rafail1982 ---
    "http://rafail1982.uz/playlists/LIST2.m3u",
    "http://rafail1982.uz/playlists/DIMONOVICH.m3u",
    "http://rafail1982.uz/playlists/TELEKARTA.m3u",
    "http://rafail1982.uz/playlists/TELECIFRA.m3u",

    # --- Твои проекты ---
    "https://raw.githubusercontent.com/Phoenix89S/Mir-IpTV-Ru-/main/code",
    "https://raw.githubusercontent.com/Phoenix89S/Iptv_Ru2026/main/Viju2test.m3u",

    # --- Дополнительные источники ---
    "https://raw.githubusercontent.com/Zet2009/MOJE1/gh-pages/IPTVmir.m3u8",
    "https://raw.githubusercontent.com/smolnp/IPTVru/gh-pages/IPTVstable.m3u8",

    # --- tva.org.ua (M3U) ---
    "https://tva.org.ua/ip/sam/poznavatelni.m3u",
    "https://tva.org.ua/ip/sam/avto-full.m3u",

    # --- live.iptv-free.com ---
    "https://live.iptv-free.com/iptv/categories/kids.m3u",
    "https://live.iptv-free.com/iptv/languages/rus.m3u"
]

# Группы для сортировки
CHANNEL_GROUPS = {
    " Кнопка 3 РТРС:  Матч": {
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
    " Кнопка 4 РТРС:  НТВ": {
        "4.1": "НТВ",
        "4.2": "НТВ Мир",
        "4.3": "НТВ Стиль",
        "4.4": "НТВ Право",
        "4.5": "НТВ Хит",
        "4.6": "НТВ HD",
    },
}

# --- ИЗМЕНЕНО: Имя файла для стабильной версии ---
OUTPUT_FILE = "Mir_iptv_stable.m3u"

def get_links_from_m3u(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        print(f"   ⏳ Загружаю {url}...")
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        content = resp.text
        pattern = re.compile(r'#EXTINF:(.*)(?:\n#.*)*\n(https?://\S+)', re.IGNORECASE)
        items = pattern.findall(content)
        return items
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

def main():
    print(f"🚀 Старт генерации СТАБИЛЬНОГО плейлиста: {datetime.now().strftime('%H:%M:%S')}")

    all_channels = defaultdict(lambda: defaultdict(list))
    seen_links = set()
    total_found = 0

    for url in GITHUB_PLAYLISTS:
        items = get_links_from_m3u(url)
        if not items:
            continue
        total_found += len(items)

        for meta, link in items:
            meta = meta.strip()
            link = link.strip()
            if link in seen_links:
                continue
            seen_links.add(link)

            group, orbit, name = find_group_and_orbit(meta, CHANNEL_GROUPS)
            all_channels[group][orbit].append((meta, link, name))

    print(f"\n{'='*60}")
    print(f"📊 Статистика (Stable):")
    print(f"   Всего ссылок: {total_found}")
    print(f"   Уникальных: {len(seen_links)}")
    print(f"{'='*60}\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        count = 0

        # Сортировка групп
        sorted_groups = sorted(all_channels.items(), 
                              key=lambda x: min(float(o.split('.')[0]) for o in x[1].keys() if o != "999") 
                                              if any(o != "999" for o in x[1].keys()) else 999)

        for group_idx, (group_name, orbits) in enumerate(sorted_groups, 1):
            # Сортировка по номеру орбиты
            sorted_orbits = sorted(orbits.items(), 
                                  key=lambda x: tuple(map(int, x[0].split('.'))) if x[0] != "999" else (999,))

            for orbit, channels_list in sorted_orbits:
                for ch_idx, (meta, link, name) in enumerate(channels_list, 1):
                    display_name = name
                    if orbit != "999":
                        full_orbit = f"{orbit}.{ch_idx}" if len(channels_list) > 1 else orbit
                        display_name = f"{full_orbit} {name}"

                        if ',' in meta:
                            meta_parts = meta.rsplit(',', 1)
                            final_meta = f"{meta_parts[0]},{display_name}"
                        else:
                            final_meta = f"-1 group-title=\"{group_name}\",{display_name}"
                    else:
                        final_meta = meta

                    f.write(f'#EXTINF:{final_meta}\n{link}\n')
                    count += 1

    print(f"\n✨ Готово! Стабильный файл {OUTPUT_FILE} создан.")
    print(f"✅ Собрано {count} каналов.")
    print(f"⏰ Завершено: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
  
