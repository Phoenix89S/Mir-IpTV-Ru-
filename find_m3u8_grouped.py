import requests
import re
from collections import defaultdict

# Множество источников плейлистов
GITHUB_PLAYLISTS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/channels/ru.m3u",
    # Добавьте сюда другие источники, если есть
    # "https://example.com/playlist.m3u",
]

# Структура групп с орбитами
CHANNEL_GROUPS = {
    "НТВ": {
        "4.1": "НТВ",
        "4.2": "НТВ Мир",
        "4.3": "НТВ Стиль",
        "4.4": "НТВ Право",
        "4.5": "НТВ Хит",
        "4.6": "НТВ HD",
    },
    # Добавьте сюда другие группы по аналогии
    # "Первый канал": {
    #     "1.1": "Первый канал",
    #     "1.2": "Первый канал HD",
    # },
}

def get_links_from_m3u(url):
    """Получить каналы из m3u файла"""
    try:
        resp = requests.get(url, timeout=15)
        content = resp.text
        # Парсим: EXTINF + имя канала + ссылка на m3u8
        items = re.findall(r'#EXTINF:-?\d+.*?,(.*?)\n(https?://[^\s]+\.m3u8)', content)
        return items
    except Exception as e:
        print(f"⚠️ Ошибка при обработке {url}: {e}")
        return []

def find_group_and_orbit(channel_name, channel_groups):
    """Найти группу и орбиту для канала"""
    for group_name, orbits in channel_groups.items():
        for orbit, keyword in orbits.items():
            # Проверяем, есть ли ключевое слово в названии канала (игнорируя регистр)
            if keyword.lower() in channel_name.lower():
                return group_name, orbit, keyword
    return "Прочее", None, channel_name

def main():
    all_channels = defaultdict(lambda: defaultdict(list))  # group -> orbit -> [(name, link)]
    seen_links = set()  # Для отслеживания дубликатов

    # Собираем каналы со всех источников
    for url in GITHUB_PLAYLISTS:
        print(f"📥 Загружаю из: {url}")
        items = get_links_from_m3u(url)
        for name, link in items:
            name = name.strip()
            link = link.strip()
            
            # Пропускаем дубли (если ссылка уже есть)
            if link in seen_links:
                print(f"⏭️  Пропуск дубля: {name}")
                continue
            
            seen_links.add(link)
            group, orbit, keyword = find_group_and_orbit(name, CHANNEL_GROUPS)
            all_channels[group][orbit].append((name, link))

    # Формируем итоговый плейлист
    with open("playlist.m3u8", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        # Сортируем группы по приоритету (числовому коду первой орбиты)
        sorted_groups = sorted(all_channels.items(), 
                               key=lambda x: (float(list(x[1].keys())[0].split('.')[0]), x[0]))
        
        for group_idx, (group_name, orbits) in enumerate(sorted_groups, 1):
            print(f"\n📺 Группа {group_idx}: {group_name}")
            
            # Сортируем орбиты внутри группы
            sorted_orbits = sorted(orbits.items(), 
                                   key=lambda x: tuple(map(int, x[0].split('.'))))
            
            for orbit_idx, (orbit, channels) in enumerate(sorted_orbits, 1):
                for ch_idx, (name, link) in enumerate(channels, 1):
                    # Формируем номер: орбита + подномер (если несколько каналов)
                    if len(channels) > 1:
                        full_orbit = f"{orbit}.{ch_idx}"
                    else:
                        full_orbit = orbit
                    
                    display_name = f"{full_orbit} {name}"
                    f.write(f'#EXTINF:-1 group-title="{group_name}",{display_name}\n{link}\n')
                    print(f"  ✅ {display_name}")

    total_channels = sum(len(channels) for orbits in all_channels.values() 
                        for channels in orbits.values())
    print(f"\n✅ Готово! Всего уникальных каналов: {total_channels}")

if __name__ == "__main__":
    main()
