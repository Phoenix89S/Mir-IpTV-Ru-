import requests
import re
from collections import defaultdict
from datetime import datetime

# Множество источников плейлистов (любые типы!)
GITHUB_PLAYLISTS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/channels/ru.m3u",
    "http://rafail1982.uz/playlists/LIST2.m3u",
    "http://другой-источник.com/playlist.m3u",
    # Добавляйте сюда свои источники
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
}

OUTPUT_FILE = "Test_Channels_Mir_2026.m3u8"

def get_links_from_m3u(url):
    """
    Получить каналы из m3u файла с универсальным парсингом.
    Работает с любыми источниками (GitHub, обычные сайты и т.д.)
    """
    try:
        print(f"   ⏳ Загружаю {url}...")
        resp = requests.get(url, timeout=20)
        resp.encoding = 'utf-8'
        content = resp.text
        
        # Универсальный regex для парсинга m3u
        # Ищет: #EXTINF:-1 ... ,название
        #       ссылка на поток (любой формат)
        items = re.findall(
            r'#EXTINF:[^,]*,\s*(.+?)\s*\n((?:https?|rtmp|rtsp):\/\/[^\s\n]+)',
            content,
            re.IGNORECASE | re.MULTILINE
        )
        
        return items
    except requests.exceptions.Timeout:
        print(f"   ⚠️ Timeout при загрузке {url}")
        return []
    except requests.exceptions.ConnectionError:
        print(f"   ⚠️ Ошибка соединения с {url}")
        return []
    except Exception as e:
        print(f"   ⚠️ Ошибка при обработке {url}: {e}")
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
    print(f"🚀 Начало обновления плейлиста: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 Всего источников: {len(GITHUB_PLAYLISTS)}\n")
    
    all_channels = defaultdict(lambda: defaultdict(list))  # group -> orbit -> [(name, link)]
    seen_links = set()  # Для отслеживания дубликатов
    total_found = 0

    # Собираем каналы со всех источников
    for url in GITHUB_PLAYLISTS:
        print(f"📥 Источник: {url}")
        items = get_links_from_m3u(url)
        
        if items:
            print(f"   ✅ Найдено {len(items)} каналов из этого источника")
            total_found += len(items)
        else:
            print(f"   ⚠️ Каналы не найдены или источник недоступен")
        
        for name, link in items:
            name = name.strip()
            link = link.strip()
            
            # Пропускаем пустые записи
            if not name or not link:
                continue
            
            # Пропускаем дубли (если ссылка уже есть)
            if link in seen_links:
                continue
            
            seen_links.add(link)
            group, orbit, keyword = find_group_and_orbit(name, CHANNEL_GROUPS)
            all_channels[group][orbit].append((name, link))

    print(f"\n{'='*60}")
    print(f"📊 Статистика:")
    print(f"   Всего найдено потоков: {total_found}")
    print(f"   Уникальных (без дубликатов): {len(seen_links)}")
    print(f"{'='*60}\n")

    # Формируем итоговый плейлист в файл
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        # Сортируем группы по приоритету (числовому коду первой орбиты)
        sorted_groups = sorted(all_channels.items(), 
                               key=lambda x: (float(list(x[1].keys())[0].split('.')[0]) 
                                             if list(x[1].keys()) and list(x[1].keys())[0][0].isdigit() 
                                             else float('inf'), x[0]))
        
        for group_idx, (group_name, orbits) in enumerate(sorted_groups, 1):
            print(f"📺 Группа {group_idx}: {group_name}")
            
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
    print(f"\n✅ Готово! Всего уникальных каналов в плейлисте: {total_channels}")
    print(f"📁 Файл сохранён: {OUTPUT_FILE}")
    print(f"⏰ Обновление завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()