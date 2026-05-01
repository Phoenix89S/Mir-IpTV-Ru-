import requests
import re
from collections import defaultdict
from datetime import datetime

# Источники плейлистов (Дополнено строго в конец списка) (!!!!!!)
GITHUB_PLAYLISTS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/channels/ru.m3u",
    "http://rafail1982.uz/playlists/LIST2.m3u",
    "https://raw.githubusercontent.com/Phoenix89S/Mir-IpTV-Ru-/main/code",
    "http://rafail1982.uz/playlists/DIMONOVICH.m3u",
    "https://raw.githubusercontent.com/Zet2009/MOJE1/gh-pages/IPTVmir.m3u8",
    "https://raw.githubusercontent.com/smolnp/IPTVru/gh-pages/IPTVstable.m3u8",
    "https://tva.org.ua/ip/sam/poznavatelni.m3u",
    "https://tva.org.ua/ip/sam/avto-full.m3u",
    "https://tva.org.ua/free-full.html#google_vignette",
    "https://dtv.plus/rabochiy-iptv-pleylist-tv-kanaly/",
    "https://live.iptv-free.com/iptv/categories/kids.m3u",
    "https://live.iptv-free.com/iptv/languages/rus.m3u",
    "http://rafail1982.uz/playlists/TELEKARTA.m3u",
    "http://rafail1982.uz/playlists/TELECIFRA.m3u"
]


# ИСТОЧНИКИ EPG (!!!!!!)
EPG_SOURCES = "https://epg.one/epg.xml.gz,https://iptvx.one/EPG"

# Функция проверки потока
def is_live(url):
    try:
        response = requests.head(url, timeout=3, allow_redirects=True)
        return response.status_code == 200
    except:
        try:
            response = requests.get(url, timeout=3, stream=True)
            return response.status_code == 200
        except: return False

OUTPUT_FILE = "Super_RTRS_2026.m3u"
MAIN_GROUP_NAME = "Эфирные ТВ плюс"
OTHER_GROUP_NAME = "Общие"
BLACKLIST = ["T.ME/", "TELEGRAM", "JOINCHAT", "NEXO", "ПОДПИШИСЬ", "ЗЕРКАЛО", "РЕЗЕРВ", "CHAT", "INFO", "ПОСМОТРИ!!!"]

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
    try:
        resp = requests.get(url, timeout=30)
        resp.encoding = 'utf-8'
        return re.findall(r'#EXTINF:(.*)(?:\n#.*)*\n(https?://\S+)', resp.text, re.IGNORECASE)
    except: return []

def extract_channel_name(meta):
    return meta.rsplit(',', 1)[-1].strip() if ',' in meta else meta

def extract_tvg_id(meta):
    match = re.search(r'tvg-id="([^"]+)"', meta, re.IGNORECASE)
    return match.group(1) if match else ""

def find_group_and_orbit(full_meta, link):
    name = extract_channel_name(full_meta)
    n_up = name.upper()
    link_up = link.upper()
    smotrim_trash = ["100%", "КИНО", "СЕРИАЛ", "ДЕТСКОЕ", "КЛАССИКА", "ФАКТЫ", "МУЖСКОЕ"]
    
    if "SMOTRIM" in n_up or "SMOTRIM" in link_up:
        is_main = any(x in n_up for x in ["РОССИЯ 1", "РОССИЯ 24", "РОССИЯ К", "ВЕСТИ ФМ", "КАВКАЗ 24", "ЗАПАД 24", "PLANETA"])
        if not is_main or any(trash in n_up for trash in smotrim_trash):
            return MAIN_GROUP_NAME, "28.0", name

    for g_id, orbits in CHANNEL_GROUPS.items():
        if "28" in g_id: continue
        for orbit, keyw in orbits.items():
            if keyw.upper() in n_up:
                if "РОССИЯ 24" in n_up and keyw.upper() == "РОССИЯ 1": continue
                return MAIN_GROUP_NAME, orbit, name
    return OTHER_GROUP_NAME, "999", name

def main():
    print(f"🚀 Запуск сборки с EPG: {datetime.now().strftime('%H:%M:%S')}")
    all_channels = defaultdict(lambda: defaultdict(list))
    seen_links = set()

    for url in GITHUB_PLAYLISTS:
        items = get_links_from_m3u(url)
        for meta, link in items:
            link = link.strip()
            if link in seen_links or any(b in (meta + link).upper() for b in BLACKLIST): 
                continue

            if is_live(link):
                group, orbit, name = find_group_and_orbit(meta, link)
                tvg_id = extract_tvg_id(meta)
                seen_links.add(link)
                all_channels[group][orbit].append({
                    'name': name, 
                    'link': link, 
                    'tvg_id': tvg_id if tvg_id else name
                })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U x-tvg-url="{EPG_SOURCES}"\n') # ПРОПИСАЛИ ЕПГ (!!!!!!)
        count = 0
        rtrs_orbits = all_channels[MAIN_GROUP_NAME]
        sorted_orbits = sorted(rtrs_orbits.items(), key=lambda x: [int(d) for d in re.findall(r'\d+', x[0])])

        for orbit, ch_list in sorted_orbits:
            for idx, ch in enumerate(ch_list, 1):
                f.write(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["tvg_id"]}" group-title="{MAIN_GROUP_NAME}",Кнопка {orbit}.{idx} {ch["name"]}\n{ch["link"]}\n')
                count += 1
        for ch in all_channels[OTHER_GROUP_NAME]["999"]:
            f.write(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["tvg_id"]}" group-title="{OTHER_GROUP_NAME}",{ch["name"]}\n{ch["link"]}\n')
            count += 1

    print(f"\n✨ Готово! Плейлист с EPG готов. Всего каналов: {count}. (!!!!!!)")

if __name__ == "__main__":
    main()
