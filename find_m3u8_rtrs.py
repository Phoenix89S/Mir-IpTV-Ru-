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
# Группы
MAIN_GROUP_NAME = "Эфирные ТВ плюс"
OTHER_GROUP_NAME = "Общие"

# Список запрещенного мусора (Blacklist) - ЖЁСТКИЙ РЕГЛАМЕНТ (!!!!!!)
BLACKLIST = [
    "T.ME/", "TELEGRAM", "JOINCHAT", "NEXO", 
    "ПОДПИШИСЬ", "ЗЕРКАЛО", "РЕЗЕРВ", "CHAT", "INFO", "ПОСМОТРИ!!!"
]

# Структура групп по кнопкам РТРС (!!!!!!)
CHANNEL_GROUPS = {
    "Кнопка 1": {
        "1.0": "Первый канал", "1.1": "Первый HD", "1.2": "Первый +2", "1.3": "Первый +4",
        "1.4": "Первый +6", "1.5": "Первый +8", "1.6": "Первый +9", "1.7": "Первый СНГ",
    },
    "Кнопка 2": {
        "2.0": "Россия 1", "2.0.1": "Россия 1 (Калининград)", "2.1": "Россия 24", 
        "2.2": "Россия К", "2.2.1": "Культура",
        "2.3.1": "Арктика 24", "2.3.2": "Башкортостан 24", "2.3.3": "Волгоград 24",
        "2.3.4": "Восток 24", "2.3.5": "Запад 24", "2.3.6": "Кавказ 24", "2.3.7": "Сибирь 24", "2.3.9": "Урал 24",
        "2.4": "Planeta RTR", "2.5": "Вести FM"
    },
    "Кнопка 3": {"3.0": "Матч ТВ", "3.1": "Матч HD"},
    "Кнопка 4": {"4.1": "НТВ", "4.2": "Неизвестная Россия", "4.8": "НТВ HD"},
    "Кнопка 5": {"5.0": "Пятый канал"},
    "Кнопка 6": {"6.0": "Россия К", "6.1": "Культура"},
    "Кнопка 7": {"7.0": "Россия 24"},
    "Кнопка 8": {"8.0": "Карусель"},
    "Кнопка 9": {"9.0": "ОТР"},
    "Кнопка 10": {"10.0": "ТВЦ", "10.1": "ТВ Центр"},
    "Кнопка 11": {"11.0": "РЕН ТВ"},
    "Кнопка 12": {"12.0": "Спас"},
    "Кнопка 13": {"13.0": "СТС"},
    "Кнопка 14": {"14.0": "Домашний"},
    "Кнопка 15": {"15.0": "ТВ-3"},
    "Кнопка 16": {"16.0": "Пятница"},
    "Кнопка 17": {"17.0": "Звезда"},
    "Кнопка 18": {"18.0": "Мир"},
    "Кнопка 19": {"19.0": "ТНТ"},
    "Кнопка 20": {"20.0": "Муз-ТВ"},
    "Кнопка 21": {"21.0": "РТС", "21.1": "Абакан"},
    "Кнопка 22": {
        "22.0": "Че", "22.1": "Че +", "22.2": "Че International", 
        "22.5": "Перец", "22.6": "Перец +", "22.7": "Перец International"
    },
    "Кнопка 23": {"23.0": "Солнце", "23.1": "Солнце +"},
    "Кнопка 24": {"24.0": "2х2", "24.1": "2x2"},
    "Кнопка 25": {"25.0": "RU.TV", "25.1": "RU TV HD", "25.2": "RU TV"},
    "Кнопка 28": {"28.0": "SMOTRIM"}
}

def get_links_from_m3u(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        return re.findall(r'#EXTINF:(.*)(?:\n#.*)*\n(https?://\S+)', resp.text, re.IGNORECASE)
    except:
        return []

def extract_channel_name(meta):
    return meta.rsplit(',', 1)[-1].strip() if ',' in meta else meta

def is_garbage(meta, link):
    combined = (meta + link).upper()
    return any(trash in combined for trash in BLACKLIST)

def find_group_and_orbit(full_meta, link):
    name = extract_channel_name(full_meta)
    n_up = name.upper()
    link_up = link.upper()

    # Сначала проверяем мусор Смотрим на 28 кнопку (!!!!!!)
    smotrim_trash = ["100%", "КИНО", "СЕРИАЛ", "ДЕТСКОЕ", "КЛАССИКА", "ФАКТЫ", "МУЖСКОЕ"]
    if "SMOTRIM" in n_up or "SMOTRIM" in link_up:
        is_main = any(x in n_up for x in ["РОССИЯ 1", "РОССИЯ 24", "РОССИЯ К", "ВЕСТИ ФМ", "КАВКАЗ 24", "ЗАПАД 24", "PLANETA"])
        if not is_main or any(trash in n_up for trash in smotrim_trash):
            return MAIN_GROUP_NAME, "28.0", name

    # Проверка основной сетки (!!!!!!)
    for g_id, orbits in CHANNEL_GROUPS.items():
        if "28" in g_id: continue
        sorted_keys = sorted(orbits.keys(), key=lambda k: len(orbits[k]), reverse=True)
        for orbit in sorted_keys:
            keyw = orbits[orbit].upper()
            if keyw in n_up:
                if "РОССИЯ 24" in n_up and keyw == "РОССИЯ 1": continue
                if keyw == "ОТР" and ("СМОТРИМ" in n_up or "100%" in n_up): continue
                return MAIN_GROUP_NAME, orbit, name

    # Если не попал в кнопки - летит в Общие (!!!!!!)
    return OTHER_GROUP_NAME, "999", name

def main():
    print(f"🚀 Парсинг: {datetime.now().strftime('%H:%M:%S')}")
    all_channels = defaultdict(lambda: defaultdict(list))
    seen_links = set()

    for url in GITHUB_PLAYLISTS:
        items = get_links_from_m3u(url)
        for meta, link in items:
            link = link.strip()
            if link in seen_links or is_garbage(meta, link): continue

            group, orbit, name = find_group_and_orbit(meta, link)
            seen_links.add(link)
            all_channels[group][orbit].append((meta.strip(), link, name))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        count = 0

        # Сначала пишем группу "Эфирные ТВ плюс" по порядку кнопок (!!!!!!)
        rtrs_orbits = all_channels[MAIN_GROUP_NAME]
        sorted_orbits = sorted(rtrs_orbits.items(), key=lambda x: [int(d) for d in re.findall(r'\d+', x[0])])

        for orbit, ch_list in sorted_orbits:
            for idx, (meta, link, name) in enumerate(ch_list, 1):
                final_name = f"Кнопка {orbit}.{idx} {name}"
                f.write(f'#EXTINF:-1 group-title="{MAIN_GROUP_NAME}",{final_name}\n{link}\n')
                count += 1

        # Затем пишем группу "Общие" (!!!!!!)
        for idx, (meta, link, name) in enumerate(all_channels[OTHER_GROUP_NAME]["999"], 1):
            f.write(f'#EXTINF:-1 group-title="{OTHER_GROUP_NAME}",{name}\n{link}\n')
            count += 1

    print(f"✨ Готово! Всего каналов: {count}. Кнопки в '{MAIN_GROUP_NAME}', остальное в '{OTHER_GROUP_NAME}'.")

if __name__ == "__main__":
    main()
