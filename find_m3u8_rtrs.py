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
    "https://raw.githubusercontent.com/smolnp/IPTVru/gh-pages/IPTVstable.m3u8",
]

# Имя выходного файла
OUTPUT_FILE = "Super_RTRS_2026.m3u"

# Структура групп по кнопкам РТРС
CHANNEL_GROUPS = {
    "Кнопка 1 РТРС: Первый канал": {
        "1.0": "Первый канал", "1.1": "Первый HD", "1.2": "Первый +2", "1.3": "Первый +4",
        "1.4": "Первый +6", "1.5": "Первый +8", "1.6": "Первый +9", "1.7": "Первый СНГ",
    },
    "Кнопка 2 РТРС: Россия / ВГТРК": {
        "2.0": "Россия 1", "2.1": "Россия HD", "2.2": "Россия 24", "2.3": "Россия К",
        "2.4": "Культура", "2.5": "РТР-Планета", "2.6": "ГТРК", "2.7": "Россия +",
    },
    "Кнопка 3 РТРС: Матч!": {
        "3.0": "Матч ТВ", "3.1": "Матч HD", "3.2": "Матч Арена", "3.3": "Матч Игра",
        "3.4": "Матч Боец", "3.5": "Матч Страна", "3.6": "Матч Планета", "3.7": "Матч Футбол",
    },
    "Кнопка 4 РТРС: НТВ": {
        "4.1": "НТВ", "4.2": "НТВ Мир", "4.3": "НТВ Стиль", "4.4": "НТВ Право",
        "4.5": "НТВ Хит", "4.6": "НТВ Сериал", "4.7": "НТВ HD",
    },
    "Кнопка 5 РТРС: Пятый канал": {"5.0": "Пятый канал", "5.1": "5 канал"},
    "Кнопка 6 РТРС: Россия К": {"6.0": "Россия К", "6.1": "Культура"},
    "Кнопка 7 РТРС: Россия 24": {"7.0": "Россия 24"},
    "Кнопка 8 РТРС: Карусель": {"8.0": "Карусель"},
    "Кнопка 9 РТРС: ОТР": {"9.0": "ОТР"},
    "Кнопка 10 РТРС: ТВ Центр": {"10.0": "ТВЦ", "10.1": "ТВ Центр"},
    "Кнопка 11 РТРС: РЕН ТВ": {"11.0": "РЕН ТВ"},
    "Кнопка 12 РТРС: Спас": {"12.0": "Спас"},
    "Кнопка 13 РТРС: СТС": {
        "13.0": "СТС", "13.1": "СТС HD", "13.2": "СТС +", "13.3": "СТС Love", 
        "13.4": "СТС Kids", "13.5": "СТС International"
    },
    "Кнопка 14 РТРС: Домашний": {"14.0": "Домашний"},
    "Кнопка 15 РТРС: ТВ-3": {"15.0": "ТВ-3", "15.1": "ТВ3"},
    "Кнопка 16 РТРС: Пятница": {"16.0": "Пятница"},
    "Кнопка 17 РТРС: Звезда": {"17.0": "Звезда"},
    "Кнопка 18 РТРС: Мир": {"18.0": "Мир"},
    "Кнопка 19 РТРС: ТНТ": {"19.0": "ТНТ", "19.1": "ТНТ HD", "19.2": "ТНТ4"},
    "Кнопка 20 РТРС: Муз-ТВ": {"20.0": "Муз-ТВ", "20.1": "Муз ТВ"},
    "Кнопка 21: Региональные (РТС)": {"21.0": "РТС", "21.1": "Абакан", "21.2": "Тивиком"},
    "Кнопка 22: Развлекательные": {
        "22.1": "2х2", "22.2": "Солнце", "22.3": "Ю ", "22.4": "Перец", "22.5": "Че", "22.6": "RU.TV"
    },
}

def get_links_from_m3u(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        print(f"   📥 Чтение {url}...")
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        return re.findall(r'#EXTINF:(.*)(?:\n#.*)*\n(https?://\S+)', resp.text, re.IGNORECASE)
    except:
        return []

def extract_channel_name(meta):
    return meta.rsplit(',', 1)[-1].strip() if ',' in meta else meta

def find_group_and_orbit(full_meta, channel_groups):
    name = extract_channel_name(full_meta)
    n_up = name.upper()
    for g_name, orbits in channel_groups.items():
        for orbit, keyw in orbits.items():
            if keyw.upper() in n_up:
                return g_name, orbit, name
    return "Прочее", "999", name

def main():
    print(f"🚀 Скрипт: find_m3u8_rtrs.py | Старт: {datetime.now().strftime('%H:%M:%S')}")
    all_channels = defaultdict(lambda: defaultdict(list))
    seen_links = set()

    for url in GITHUB_PLAYLISTS:
        items = get_links_from_m3u(url)
        for meta, link in items:
            link = link.strip()
            if link in seen_links: continue
            seen_links.add(link)
            group, orbit, name = find_group_and_orbit(meta, CHANNEL_GROUPS)
            all_channels[group][orbit].append((meta.strip(), link, name))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        count = 0
        
        # Сортировка по номеру кнопки
        sorted_groups = sorted(all_channels.items(), 
                              key=lambda x: int(re.search(r'\d+', x[0]).group()) if re.search(r'\d+', x[0]) else 999)

        for group_name, orbits in sorted_groups:
            sorted_orbits = sorted(orbits.items(), 
                                  key=lambda x: tuple(map(int, re.findall(r'\d+', x[0]))) if x[0] != "999" else (999,))
            for orbit, ch_list in sorted_orbits:
                for idx, (meta, link, name) in enumerate(ch_list, 1):
                    final_name = f"Кнопка {orbit}.{idx} {name}" if orbit != "999" else name
                    if ',' in meta:
                        m_parts = meta.rsplit(',', 1)
                        f_meta = f"{m_parts[0]},{final_name}"
                    else:
                        f_meta = f"-1 group-title=\"{group_name}\",{final_name}"
                    f.write(f'#EXTINF:{f_meta}\n{link}\n')
                    count += 1

    print(f"✨ Готово! Файл {OUTPUT_FILE} создан. Собрано каналов: {count}")

if __name__ == "__main__":
    main()
