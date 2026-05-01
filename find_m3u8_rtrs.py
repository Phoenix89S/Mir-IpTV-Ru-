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
    "https://tva.org.ua/ip/sam/poznavatelni.m3u",
    "https://tva.org.ua/ip/sam/avto-full.m3u",
    "https://tva.org.ua/free-full.html",
    "https://dtv.plus/rabochiy-iptv-pleylist-tv-kanaly/",
    "https://live.iptv-free.com/iptv/categories/kids.m3u",
    "https://live.iptv-free.com/iptv/languages/rus.m3u",
    "http://rafail1982.uz/playlists/TELEKARTA.m3u",
    "http://rafail1982.uz/playlists/TELECIFRA.m3u"
]

EPG_SOURCES = "https://epg.one/epg.xml.gz,https://iptvx.one/EPG"
OUTPUT_FILE = "Super_RTRS_2026.m3u"
MAIN_GROUP_NAME = "Эфирные ТВ плюс"
OTHER_GROUP_NAME = "Общие"

# Чёрный список
BLACKLIST = [
    "T.ME/", "TELEGRAM", "JOINCHAT", "NEXO", "ПОДПИШИСЬ",
    "ЗЕРКАЛО", "РЕЗЕРВ", "CHAT", "INFO", "ПОСМОТРИ!!!"
]

# ---------------------------------------------------------
# 🔥 CHANNEL_GROUPS — полностью ручной
# ---------------------------------------------------------
CHANNEL_GROUPS = {
    "Кнопка 1": {
        "1.0": "Первый канал",
        "1.1": "Первый HD",
        "1.2": "Первый +2",
        "1.3": "Первый +4",
        "1.4": "Первый +6",
        "1.5": "Первый +8",
        "1.6": "Первый +9",
        "1.7": "Первый СНГ"
    },

    "Кнопка 2": {
        "2.0": "Россия 1",
        "2.0.1": "Россия 1 (Калининград)",
        "2.0.2": "Россия 1 (Ростов-на-Дону)",
        "2.0.3": "Россия 1 (Санкт-Петербург)",
        "2.0.4": "Россия 1 (Ярославль)",

        "2.1": "Россия 24",
        "2.1.0.1": "Россия 24",
        "2.1.0.2": "Россия 24 (Калининград)",
        "2.1.0.3": "Россия 24 (Ростов-на-Дону)",
        "2.1.0.4": "Россия 24 (Санкт-Петербург)",
        "2.1.0.5": "Россия 24 (Ярославль)",

        "2.2": "Россия К HD",
        "2.2.0.1": "Россия К HD",
        "2.2.1": "Россия К",
        "2.2.2": "Культура",
        "2.2.3": "Культура HD",

        "2.3.1": "Арктика 24 HD",
        "2.3.1.1": "Арктика 24",
        "2.3.2": "Башкортостан 24 HD",
        "2.3.3": "Волгоград 24 HD",
        "2.3.4": "Восток 24 HD",
        "2.3.4.1": "Восток 24",
        "2.3.5": "Запад 24 HD",
        "2.3.5.1": "Запад 24 SD",
        "2.3.6": "ЛенТВ24 HD",
        "2.3.7": "Сибирь 24 HD (Крск)",
        "2.3.8": "Сибирь 24 HD (Нск)",
        "2.3.9": "Урал 24 HD",
        "2.3.9.1": "Урал 24",
        "2.3.10": "Якутия 24",

        "2.4.1": "Planeta RTR",
        "2.4.2": "Planeta RTR",
        "2.4.3": "Planeta RTR EU",
        "2.4.4": "Россия РТР",
        "2.4.5": "Россия РТР",
        "2.4.6": "Россия 24 International",

        "2.5": "Вести FM",
        "2.5.1": "Вести ФМ (Смотрим)"
    },

    # Расширенная Кнопка 3 (C1A)
    "Кнопка 3": {
        "3.0": "Матч ТВ",
        "3.0.1": "Матч Планета",
        "3.0.2": "Матч Премьер",
        "3.0.3": "Матч Арена",
        "3.0.4": "Матч Игра",
        "3.0.5": "Матч Страна",
        "3.0.6": "Матч Футбол",
        "3.0.7": "Матч Футбол 1",
        "3.0.8": "Матч Футбол 2",
        "3.0.9": "Матч Футбол 3",
        "3.0.10": "Наш спорт",
        "3.0.11": "Боец"
    },

    "Кнопка 4": {
        "4.1": "НТВ",
        "4.2": "Неизвестная Россия",
        "4.8": "НТВ HD"
    },

    "Кнопка 5": {
        "5.0": "Пятый канал"
    },

    "Кнопка 6": {
        "6.0": "Россия К",
        "6.1": "Россия К HD",
        "6.2": "Культура",
        "6.3": "Культура HD",
        "6.4": "Россия К +2",
        "6.5": "Россия К +4",
        "6.6": "Россия К +7",
        "6.7": "Культура +2",
        "6.8": "Культура +4",
        "6.9": "Культура +7"
    },

    "Кнопка 7": {
        "7.0": "Россия 24",
        "7.1": "Россия 24 HD",
        "7.2": "Россия 24 +2",
        "7.3": "Россия 24 +4",
        "7.4": "Россия 24 +7",
        "7.5": "Россия 24 International"
    },

    "Кнопка 8": {
        "8.0": "Карусель",
        "8.1": "Карусель +2",
        "8.2": "Карусель +4",
        "8.3": "Карусель +7",
        "8.4": "Carousel International"
    },

    "Кнопка 9": {"9.0": "ОТР"},
    "Кнопка 10": {
        "10.0": "ТВЦ",
        "10.1": "ТВ Центр",
        "10.2": "ТВЦ +2",
        "10.3": "ТВЦ +4",
        "10.4": "ТВЦ +7",
        "10.5": "ТВ Центр International"
    },
    "Кнопка 11": {
        "11.0": "РЕН ТВ",
        "11.1": "РЕН ТВ HD",
        "11.2": "РЕН ТВ +2",
        "11.3": "РЕН ТВ +4",
        "11.4": "РЕН ТВ +7",
        "11.5": "REN TV International"
    },
    "Кнопка 12": {"12.0": "Спас"},
    "Кнопка 13": {
        "13.0": "СТС",
        "13.1": "СТС HD",
        "13.2": "СТС +2",
        "13.3": "СТС +4",
        "13.4": "СТС +7",
        "13.5": "СТС Kids",
        "13.6": "СТС Love",
        "13.7": "СТС International"
    },
    "Кнопка 14": {
        "14.0": "Домашний",
        "14.1": "Домашний HD",
        "14.2": "Домашний +2",
        "14.3": "Домашний +4",
        "14.4": "Домашний +7",
        "14.5": "Домашний International"
    },
    "Кнопка 15": {
        "15.0": "ТВ-3",
        "15.1": "ТВ-3 HD",
        "15.2": "ТВ-3 +2",
        "15.3": "ТВ-3 +4",
        "15.4": "ТВ-3 +7",
        "15.5": "ТВ-3 International"
    },
    "Кнопка 16": {
        "16.0": "Пятница",
        "16.1": "Пятница HD",
        "16.2": "Пятница +2",
        "16.3": "Пятница +4",
        "16.4": "Пятница International"
    },
    "Кнопка 17": {
        "17.0": "Звезда",
        "17.1": "Звезда HD",
        "17.2": "Звезда Плюс",
        "17.3": "Звезда Плюс HD"
    },
    "Кнопка 18": {
        "18.0": "Мир",
        "18.1": "Мир HD",
        "18.2": "Мир +2",
        "18.3": "Мир +4",
        "18.4": "Мир 24"
    },
    "Кнопка 19": {
        "19.0": "ТНТ",
        "19.1": "ТНТ HD",
        "19.2": "ТНТ +2",
        "19.3": "ТНТ +4",
        "19.4": "ТНТ4",
        "19.5": "ТНТ4 HD",
        "19.6": "ТНТ International"
    },
    "Кнопка 20": {"20.0": "Муз-ТВ"},
    "Кнопка 21": {"21.0": "РТС", "21.1": "Абакан"},
    "Кнопка 22": {
        "22.0": "Че",
        "22.1": "Че +2",
        "22.2": "Че +4",
        "22.5": "Перец",
        "22.6": "Перец International"
    },
    "Кнопка 23": {
        "23.0": "Солнце",
        "23.1": "Солнце +2",
        "23.2": "Солнце +4"
    },
    "Кнопка 24": {
        "24.0": "2х2",
        "24.1": "2x2 +2"
    },
    "Кнопка 25": {"25.0": "RU.TV"},
    "Кнопка 28": {"28.0": "SMOTRIM"}
}

# ---------------------------------------------------------
# ✔ Проверка потока (без HEAD, без зависаний)
# ---------------------------------------------------------
def is_live(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=2, stream=True)
        return r.status_code in (200, 206)
    except:
        return False

# ---------------------------------------------------------
# ✔ Надёжный парсер M3U
# ---------------------------------------------------------
def get_links_from_m3u(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        text = resp.text.replace('\r', '')

        lines = text.split('\n')
        result = []
        meta = None

        for line in lines:
            if line.startswith("#EXTINF"):
                meta = line
            elif meta and line.startswith("http"):
                result.append((meta, line.strip()))
                meta = None

        return result
    except:
        return []

# ---------------------------------------------------------
# ✔ Основная программа
# ---------------------------------------------------------
def main():
    print(f"🚀 Старт: {datetime.now().strftime('%H:%M:%S')}")
    all_channels = defaultdict(lambda: defaultdict(list))
    seen_links = set()

    for url in GITHUB_PLAYLISTS:
        print(f"📥 Обработка: {url}")
        items = get_links_from_m3u(url)

        for meta, link in items:
            link = link.strip()
            if link in seen_links or any(b in (meta + link).upper() for b in BLACKLIST):
                continue

            if is_live(link):
                name = meta.rsplit(',', 1)[-1].strip()
                tvg_id = ""
                match_id = re.search(r'tvg-id="([^"]+)"', meta, re.IGNORECASE)
                if match_id:
                    tvg_id = match_id.group(1)

                found = False
                for g_label, orbits in CHANNEL_GROUPS.items():
                    for orbit, keyw in orbits.items():
                        if keyw.upper() in name.upper():

                            # Защита от смешивания Россия 1 ↔ Россия 24
                            if "РОССИЯ 24" in name.upper() and keyw.upper() == "РОССИЯ 1":
                                continue

                            all_channels[MAIN_GROUP_NAME][orbit].append({
                                'name': name,
                                'link': link,
                                'tvg_id': tvg_id if tvg_id else name
                            })
                            found = True
                            break
                    if found:
                        break

                if not found:
                    all_channels[OTHER_GROUP_NAME]["999"].append({
                        'name': name,
                        'link': link,
                        'tvg_id': tvg_id if tvg_id else name
                    })

                seen_links.add(link)

    # ---------------------------------------------------------
    # ✔ Правильная сортировка орбит
    # ---------------------------------------------------------
    def orbit_key(x):
        return tuple(int(n) for n in x.split('.'))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U x-tvg-url="{EPG_SOURCES}"\n')

        rtrs_data = all_channels[MAIN_GROUP_NAME]
        sorted_orbits = sorted(rtrs_data.keys(), key=orbit_key)

        for orbit in sorted_orbits:
            for idx, ch in enumerate(rtrs_data[orbit], 1):
                f.write(
                    f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" group-title="{MAIN_GROUP_NAME}",'
                    f'Кнопка {orbit}.{idx} {ch["name"]}\n{ch["link"]}\n'
                )

        for ch in all_channels[OTHER_GROUP_NAME]["999"]:
            f.write(
                f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" group-title="{OTHER_GROUP_NAME}",'
                f'{ch["name"]}\n{ch["link"]}\n'
            )

    print(f"✨ Готово! Файл {OUTPUT_FILE} создан.")

if __name__ == "__main__":
    main()