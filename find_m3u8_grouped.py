import requests
import re
from collections import defaultdict
from datetime import datetime

# Источники плейлистов
GITHUB_PLAYLISTS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/channels/ru.m3u",
    "http://rafail1982.uz/playlists/LIST2.m3u",
    "https://raw.githubusercontent.com/Phoenix89S/Mir-IpTV-Ru-/main/code",
]

# Группы для сортировки
CHANNEL_GROUPS = {
    "НТВ": {
        "4.1": "НТВ",
        "4.2": "НТВ Мир",
        "4.3": "НТВ Стиль",
        "4.4": "НТВ Право",
        "4.5": "НТВ Хит",
        "4.6": "НТВ HD",
    },
}

OUTPUT_FILE = "Test_Channels_Mir_2026.m3u8"

def get_links_from_m3u(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        print(f"   ⏳ Загружаю {url}...")
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        content = resp.text

        # Универсальный парсинг
        pattern = re.compile(r'#EXTINF:(.*)(?:\n#.*)*\n(https?://\S+)', re.IGNORECASE)
        items = pattern.findall(content)

        return items
    except Exception as e:
        print(f"   ⚠️ Ошибка: {e}")
        return []

def extract_channel_name(meta):
    """Извлекаем название канала из метаданных"""
    # Название обычно после последней запятой
    if ',' in meta:
        return meta.rsplit(',', 1)[-1].strip()
    return meta

def find_group_and_orbit(full_meta, channel_groups):
    """Ищем совпадение по названию канала"""
    channel_name = extract_channel_name(full_meta)
    
    for group_name, orbits in channel_groups.items():
        for orbit, keyword in orbits.items():
            if keyword.lower() in channel_name.lower():
                return group_name, orbit, channel_name
    
    return "Прочее", "999", channel_name

def main():
    print(f"🚀 Старт: {datetime.now().strftime('%H:%M:%S')}")
    
    # Группа -> Орбита -> Список (Метаданные, Ссылка)
    all_channels = defaultdict(lambda: defaultdict(list))
    seen_links = set()
    total_found = 0

    for url in GITHUB_PLAYLISTS:
        print(f"📥 Источник: {url}")
        items = get_links_from_m3u(url)
        
        if not items:
            print(f"   ⚠️ Не найдено каналов")
            continue
        
        print(f"   ✅ Найдено {len(items)} каналов")
        total_found += len(items)

        for meta, link in items:
            meta = meta.strip()
            link = link.strip()

            # Пропускаем дубликаты
            if link in seen_links:
                continue
            seen_links.add(link)

            group, orbit, name = find_group_and_orbit(meta, CHANNEL_GROUPS)
            all_channels[group][orbit].append((meta, link, name))

    print(f"\n{'='*60}")
    print(f"📊 Статистика:")
    print(f"   Всего найдено: {total_found}")
    print(f"   Уникальных: {len(seen_links)}")
    print(f"{'='*60}\n")

    # Запись в файл
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        count = 0
        
        # Сортировка групп (по числовому коду орбиты)
        sorted_groups = sorted(all_channels.items(), 
                              key=lambda x: min(float(o.split('.')[0]) for o in x[1].keys() if o != "999") 
                                              if any(o != "999" for o in x[1].keys()) else 999)
        
        for group_idx, (group_name, orbits) in enumerate(sorted_groups, 1):
            print(f"📺 Группа {group_idx}: {group_name}")
            
            # Сортировка орбит (внутри группы)
            sorted_orbits = sorted(orbits.items(), 
                                  key=lambda x: tuple(map(int, x[0].split('.'))) if x[0] != "999" else (999,))
            
            for orbit, channels_list in sorted_orbits:
                # Нумеруем каналы с одинаковой орбитой
                for ch_idx, (meta, link, name) in enumerate(channels_list, 1):
                    
                    # Добавляем номер орбиты
                    if orbit != "999":
                        if len(channels_list) > 1:
                            # Если несколько каналов - добавляем подномер
                            full_orbit = f"{orbit}.{ch_idx}"
                        else:
                            full_orbit = orbit
                        
                        display_name = f"{full_orbit} {name}"
                        
                        # Извлекаем группу-название и другие параметры
                        if ',' in meta:
                            meta_parts = meta.rsplit(',', 1)
                            final_meta = f"{meta_parts[0]},{display_name}"
                        else:
                            final_meta = f"-1 group-title=\"{group_name}\",{display_name}"
                    else:
                        # Для "Прочего"
                        final_meta = f"{meta}"
                    
                    # Записываем в файл
                    f.write(f'#EXTINF:{final_meta}\n{link}\n')
                    print(f"  ✅ {display_name if orbit != '999' else name}")
                    count += 1
    
    print(f"\n✨ Готово! {OUTPUT_FILE} обновлен. Собрано {count} уникальных каналов.")
    print(f"⏰ Завершено: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()