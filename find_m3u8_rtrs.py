# ================================
# ИМПОРТЫ
# ================================
# Базовые библиотеки:
#  - requests  — HTTP-запросы к плейлистам и потокам
#  - re        — регулярные выражения (нормализация имён)
#  - time      — паузы, ожидание расписания
#  - datetime  — работа с датой/временем (МСК)
#  - defaultdict — удобная группировка каналов по кнопкам
import requests
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict
import sys  # для разбора аргументов командной строки (--stage)

# ==============================
#   РЕЖИМЫ ОБНОВЛЕНИЯ (ТРИ РЕЖИМА)
# ==============================
# Здесь задаётся, как часто должен работать основной цикл main():
#  - daily   — раз в день в 03:00 МСК
#  - every2  — раз в два дня в 04:00 МСК
#  - monthly — 1-го числа в 05:00 МСК
UPDATE_MODE = "daily"   # ← по умолчанию, но можно менять

# Время запуска (МСК) для каждого режима
DAILY_HOUR = 3
DAILY_MINUTE = 0

EVERY2_HOUR = 4
EVERY2_MINUTE = 0

MONTHLY_HOUR = 5
MONTHLY_MINUTE = 0

# ==============================
#   ГЛАВНЫЕ ПРАВИЛА ЗАЩИТЫ ССЫЛОК
# ==============================
# Эти правила реализованы в merge_channels() и логике обработки:
# ❗ 1. Старая ссылка НИКОГДА не удаляется
# ❗ 2. Пустые EXTINF из источников игнорируются
# ❗ 3. Новые мёртвые ссылки игнорируются
# ❗ 4. Новые живые ссылки обновляют старые
# ❗ 5. Если канал пропал — помечаем [OLD], но НЕ удаляем
# ❗ 6. MANUAL — неприкасаемый
# ❗ 7. Источники НЕ могут удалять рабочие ссылки
# ❗ 8. Источники НЕ могут обнулять каналы
# ❗ 9. Источники НЕ могут заменять MANUAL
# ❗ 10. Источники НЕ могут создавать пустые каналы

MANUAL_TAG = "[MANUAL]"
OLD_TAG = "[OLD]"

# ==============================
#   ИСТОЧНИКИ
# ==============================
# Список всех плейлистов, которые парсятся и объединяются.
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

    # --- Новые добавленные ---
    "https://raw.githubusercontent.com/MaximKiselev/iptv/refs/heads/main/playlist.m3u",
    "https://github.com/smolnp/IPTV-1/blob/master/playlists%2Fplaylist_ukraine.m3u8",
    "https://smolnp.github.io/IPTVru//IPTVstable.m3u8",
    "https://telekarta-tv.ru/wp-content/uploads/strah.m3u",

    # --- TVA ---
    "https://tva.org.ua/ip/sam/poznavatelni.m3u",
    "https://tva.org.ua/ip/sam/avto-full.m3u",

    # --- IPTV-free ---
    "https://live.iptv-free.com/iptv/categories/kids.m3u",
    "https://live.iptv-free.com/iptv/languages/rus.m3u"
]

# Имя итогового файла, который и есть твой главный плейлист
OUTPUT_FILE = "Super_RTRS_2026.m3u"

# ==============================
#   WINK FIX
# ==============================
# Специальная обработка ссылок Wink/Zabava/NTV, чтобы добавлять нужные заголовки.
WINK_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0; ru-RU) Gecko/20100101 Firefox/117.0"
WINK_REF = "https://wink.ru/"
WINK_IP = "95.24.0.1"

def fix_wink(url: str) -> str:
    """
    Если ссылка относится к Wink/Забава/NTV — добавляем User-Agent, Referer, X-Forwarded-For.
    """
    base = url.split("|", 1)[0].lower()
    if any(x in base for x in ["wink", "zabava", "cdn.ntv.ru", "ntv.ru"]):
        parts = []
        if "user-agent=" not in url.lower():
            parts.append(f"User-Agent={WINK_UA}")
        if "referer=" not in url.lower():
            parts.append(f"Referer={WINK_REF}")
        if "x-forwarded-for=" not in url.lower():
            parts.append(f"X-Forwarded-For={WINK_IP}")
        if "|" in url:
            return url + "&" + "&".join(parts)
        return url + "|" + "&".join(parts)
    return url

# ==============================
#   ПРОВЕРКА ЖИВОСТИ ССЫЛКИ
# ==============================
def is_live(url: str) -> bool:
    """
    Быстрая проверка, жив ли поток:
    - режем параметры после '|'
    - шлём HEAD/GET с User-Agent
    - считаем живым, если код 200 или 206
    """
    try:
        base = url.split("|", 1)[0]
        r = requests.get(base, headers={"User-Agent": WINK_UA}, timeout=2, stream=True)
        return r.status_code in (200, 206)
    except:
        return False

# ==============================
#   ПАРСЕР M3U
# ==============================
def parse_m3u(url: str):
    """
    Скачивает M3U по URL и возвращает список (meta, url),
    где meta — строка #EXTINF, а url — ссылка на поток.
    """
    try:
        r = requests.get(url, timeout=20)
        r.encoding = "utf-8"
        lines = r.text.replace("\r", "").split("\n")
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

# ==============================
#   ЗАГРУЗКА СТАРОГО ПЛЕЙЛИСТА
# ==============================
def load_old_playlist():
    """
    Читает старый итоговый плейлист OUTPUT_FILE и возвращает словарь:
    name -> {meta, url, manual}
    """
    old = {}
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        meta = None
        for line in lines:
            if line.startswith("#EXTINF"):
                meta = line
            elif meta and line.startswith("http"):
                name = meta.split(",", 1)[-1].strip()
                old[name] = {
                    "meta": meta,
                    "url": line.strip(),
                    "manual": MANUAL_TAG in meta,
                }
                meta = None
    except:
        # Если файла нет — просто возвращаем пустой словарь
        pass

    return old

# ==============================
#   CHANNEL_GROUPS (СЛОВАРЬ КНОПОК)
#   ВСТАВЛЕН 1:1, БЕЗ ЕДИНОЙ ПРАВКИ
# ==============================
# Здесь твоя полная схема кнопок и каналов.
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
        "4.8": "НТВ HD",
        "4.9": "НТВ Стиль",
        "4.10": "НТВ Мир",
        "4.11": "НТВ Беларусь",
        "4.12": "НТВ Америка",
        "4.13": "НТВ Сериал",
        "4.14": "НТВ Хит",
        "4.15": "НТВ Право"
    },

    "Кнопка 5": {
        "5.0": "Пятый канал",
        "5.0.1": "Пятый канал +2",
        "5.0.2": "Пятый канал +4",
        "5.0.3": "Пятый канал +7",

        "5.1": "Пятый канал HD",
        "5.1.1": "Пятый канал HD +2",
        "5.1.2": "Пятый канал HD +4",
        "5.1.3": "Пятый канал HD +7",

        "5.2": "Пятый канал International",
        "5.2.1": "Пятый канал International +2",
        "5.2.2": "Пятый канал International +4",
        "5.2.3": "Пятый канал International +7"
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

    "Кнопка 9": {
        "9.0": "ОТР",
        "9.0.1": "ОТР +2",
        "9.0.2": "ОТР +4",
        "9.0.3": "ОТР +7"
    },

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

    "Кнопка 12": {
        "12.0": "Спас"
    },

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

    "Кнопка 20": {
        "20.0": "Муз-ТВ"
    },

    "Кнопка 21": {
        "21.0": "Каскад SD",
        "21.1": "Каскад HD",
        "21.2": "Запад 24 HD",
        "21.2.1": "Запад 24 SD"
    },

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

    "Кнопка 25": {
        "25.0": "RU.TV"
    },

    "Кнопка 26": {
        "26.0": "Viju Premium",
        "26.0.1": "Viju Premium HD",

        "26.1": "Viju Hits",
        "26.1.1": "Viju Hits HD",

        "26.2": "Viju Family",
        "26.2.1": "Viju Family HD",

        "26.3": "Viju Comedy",
        "26.3.1": "Viju Comedy HD",

        "26.4": "Viju World",
        "26.4.1": "Viju World HD",

        "26.5": "TV1000",
        "26.5.1": "TV1000 HD",

        "26.6": "TV1000 Русское кино",
        "26.6.1": "TV1000 Русское кино HD",

        "26.7": "TV1000 Action",
        "26.7.1": "TV1000 Action HD",

        "26.8": "Viasat Explore",
        "26.8.1": "Viasat Explore HD",

        "26.9": "Viasat History",
        "26.9.1": "Viasat History HD",

        "26.10": "Viasat Nature",
        "26.10.1": "Viasat Nature HD",

        "26.11": "Viasat Ultra",
        "26.11.1": "Viasat Ultra HD",

        "26.12": "Epic Drama",
        "26.12.1": "Epic Drama HD"
    },

    "Кнопка 28": {
        "28.0": "SMOTRIM"
    }
}

# ==============================
#   НОРМАЛИЗАЦИЯ ИМЁН
# ==============================
def normalize_name(name: str) -> str:
    """
    Нормализует имя канала:
    - обрезает пробелы по краям
    - схлопывает повторяющиеся пробелы
    """
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name

# ==============================
#   ОПРЕДЕЛЕНИЕ КНОПКИ ПО ИМЕНИ
# ==============================
def detect_group(name: str) -> str:
    """
    По имени канала определяет, к какой "Кнопке" он относится.
    Если не найдено — отправляем в группу "Общие".
    """
    for button, mapping in CHANNEL_GROUPS.items():
        for _, channel_name in mapping.items():
            if channel_name.lower() in name.lower():
                return button
    return "Общие"

# ==============================
#   САМОВОССТАНОВЛЕНИЕ / ЗАЩИТА ССЫЛОК
# ==============================
def merge_channels(old_channels, new_channels):
    """
    Объединяет старые и новые каналы по правилам защиты:
    - старые каналы сохраняются
    - новые мёртвые игнорируются
    - новые живые обновляют старые
    - MANUAL не трогаем
    - пропавшие помечаем OLD
    """
    merged = {}

    # 1. Переносим все старые каналы
    for name, data in old_channels.items():
        merged[name] = {
            "meta": data["meta"],
            "url": data["url"],
            "manual": data["manual"],
            "old": False,
        }

    # 2. Обрабатываем новые каналы
    for name, data in new_channels.items():
        norm = normalize_name(name)

        # Новый канал
        if norm not in merged:
            if not data["url"]:
                continue
            if not is_live(data["url"]):
                continue

            merged[norm] = {
                "meta": data["meta"],
                "url": fix_wink(data["url"]),
                "manual": False,
                "old": False,
            }
            continue

        # Канал уже есть
        old = merged[norm]

        # MANUAL — неприкасаемый
        if old["manual"]:
            continue

        if not data["url"]:
            continue

        if not is_live(data["url"]):
            continue

        # Обновляем ссылку и мету
        merged[norm]["meta"] = data["meta"]
        merged[norm]["url"] = fix_wink(data["url"])

    # 3. Помечаем пропавшие каналы
    for name in merged:
        if name not in new_channels:
            merged[name]["old"] = True

    return merged

# ==============================
#   ФОРМИРОВАНИЕ ИТОГОВОГО ПЛЕЙЛИСТА
# ==============================
def build_playlist(merged_channels):
    """
    Формирует итоговый текст плейлиста:
    - #EXTM3U
    - блоки по кнопкам
    - сортировка внутри кнопки по твоей нумерации (1.0, 1.1, 1.2…)
    - проставление [OLD] и [MANUAL]
    """
    output = ["#EXTM3U"]

    # Группировка по кнопкам
    grouped = defaultdict(list)

    for name, data in merged_channels.items():
        group = detect_group(name)
        grouped[group].append((name, data))

    # Сортировка кнопок по порядку (Кнопка 1, Кнопка 2, …)
    def button_sort_key(btn):
        try:
            return int(btn.replace("Кнопка ", ""))
        except:
            return 9999

    for button in sorted(grouped.keys(), key=button_sort_key):

        # Добавляем комментарий-кнопку
        output.append(f"\n# ===== {button} =====")

        # Сортировка внутри кнопки по твоей нумерации (1.0, 1.1, 1.2…)
        def channel_sort_key(item):
            name, data = item
            mapping = CHANNEL_GROUPS.get(button, {})
            for key, cname in mapping.items():
                if cname.lower() == name.lower():
                    # ключ вида "3.0.7" → [3, 0, 7]
                    return [int(x) for x in key.split(".")]
            return [9999]

        for name, data in sorted(grouped[button], key=channel_sort_key):

            meta = data["meta"]
            url = data["url"]

            # Пометка OLD
            if data["old"] and OLD_TAG not in meta:
                meta = meta.replace(",", f" {OLD_TAG},")

            # MANUAL не трогаем
            if data["manual"] and MANUAL_TAG not in meta:
                meta = meta.replace(",", f" {MANUAL_TAG},")

            output.append(meta)
            output.append(url)

    return "\n".join(output)

# ==============================
#   ЗАПИСЬ ФАЙЛА
# ==============================
def save_playlist(text):
    """
    Записывает итоговый текст плейлиста в OUTPUT_FILE.
    """
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(text)

# ==============================
#   РАСПИСАНИЕ ОБНОВЛЕНИЙ
#   daily / every2 / monthly
# ==============================
# Здесь логика, которая считает, когда запускать следующий цикл обновления.
MSK_OFFSET = 3  # Москва = UTC+3 (для простоты фиксируем)

def now_msk() -> datetime:
    return datetime.utcnow() + timedelta(hours=MSK_OFFSET)

def today_msk() -> datetime:
    n = now_msk()
    return datetime(year=n.year, month=n.month, day=n.day)

def first_day_next_month_msk() -> datetime:
    n = now_msk()
    year = n.year
    month = n.month + 1
    if month == 13:
        month = 1
        year += 1
    return datetime(year=year, month=month, day=1)

def next_daily_run() -> datetime:
    base = today_msk().replace(hour=DAILY_HOUR, minute=DAILY_MINUTE, second=0, microsecond=0)
    if now_msk() >= base:
        base += timedelta(days=1)
    return base

def next_every2_run(last_run: datetime | None) -> datetime:
    if last_run is None:
        base_day = today_msk()
    else:
        base_day = datetime(year=last_run.year, month=last_run.month, day=last_run.day) + timedelta(days=2)
    return base_day.replace(hour=EVERY2_HOUR, minute=EVERY2_MINUTE, second=0, microsecond=0)

def next_monthly_run() -> datetime:
    n = now_msk()
    candidate = datetime(year=n.year, month=n.month, day=1,
                         hour=MONTHLY_HOUR, minute=MONTHLY_MINUTE, second=0, microsecond=0)
    if n >= candidate:
        candidate = first_day_next_month_msk().replace(
            hour=MONTHLY_HOUR, minute=MONTHLY_MINUTE, second=0, microsecond=0
        )
    return candidate

def calc_next_run(update_mode: str, last_run: datetime | None) -> datetime:
    """
    Возвращает дату/время следующего запуска в МСК.
    """
    if update_mode == "daily":
        return next_daily_run()
    elif update_mode == "every2":
        return next_every2_run(last_run)
    elif update_mode == "monthly":
        return next_monthly_run()
    else:
        # fallback — раз в день
        return next_daily_run()

def should_run_now(update_mode: str, last_run: datetime | None) -> bool:
    """
    Проверка, пора ли запускать обновление.
    Никаких 3-минутных циклов: проверяем раз в минуту/реже.
    """
    n = now_msk()
    next_run = calc_next_run(update_mode, last_run)
    return n >= next_run

# ==============================
#   ЦИКЛ ОЖИДАНИЯ ЗАПУСКА
# ==============================
def wait_for_schedule(update_mode: str, last_run: datetime | None) -> datetime:
    """
    Блокирующий цикл ожидания следующего запуска.
    Возвращает фактическое время запуска (МСК).
    """
    while True:
        if should_run_now(update_mode, last_run):
            return now_msk()
        # Спим 60 секунд — этого достаточно, чтобы не дёргать CPU
        time.sleep(60)

# ==============================
#   ГЛАВНЫЙ РАННЕР ОБНОВЛЕНИЯ
# ==============================
def run_update():
    """
    Один полный цикл обновления:
    - загрузка старого плейлиста
    - загрузка всех источников
    - merge старых и новых каналов
    - формирование итогового плейлиста
    - сохранение в OUTPUT_FILE
    """
    print("=== Запуск обновления плейлиста ===")

    # 1. Загружаем старый плейлист
    print("Загрузка старого плейлиста...")
    old_channels = load_old_playlist()
    print(f"Старых каналов загружено: {len(old_channels)}")

    # 2. Загружаем новые источники
    print("Загрузка новых источников...")
    new_channels = {}

    for src in GITHUB_PLAYLISTS:
        print(f" → источник: {src}")
        parsed = parse_m3u(src)
        print(f"   найдено каналов: {len(parsed)}")

        for meta, url in parsed:
            name = meta.split(",", 1)[-1].strip()
            if name not in new_channels:
                new_channels[name] = {
                    "meta": meta,
                    "url": url,
                }

    print(f"Всего новых каналов собрано: {len(new_channels)}")

    # 3. Объединяем старые и новые каналы
    print("Объединение каналов (самовосстановление)...")
    merged = merge_channels(old_channels, new_channels)
    print(f"Итоговых каналов после merge: {len(merged)}")

    # 4. Формируем итоговый плейлист
    print("Формирование итогового плейлиста...")
    playlist_text = build_playlist(merged)

    # 5. Сохраняем файл
    print("Сохранение файла...")
    save_playlist(playlist_text)

    print("=== Обновление завершено успешно ===")

    # Возвращаем время запуска (МСК)
    return now_msk()

# ================================
# ОБРАБОТКА РЕЖИМОВ ЗАПУСКА (STAGE)
# ================================
# ВАЖНО:
#  - здесь мы только читаем аргумент --stage
#  - сами действия по стадиям выполняем НИЖЕ, после определения всех функций
stage = None
if "--stage" in sys.argv:
    try:
        stage = sys.argv[sys.argv.index("--stage") + 1]
    except Exception:
        stage = None

# ==============================
#   ЧАСТЬ 6 — ФИНАЛЬНЫЙ ЦИКЛ
#   РАБОТА ПО РАСПИСАНИЮ
# ==============================
def main():
    """
    Основной режим работы:
    - крутится в бесконечном цикле
    - ждёт расписание
    - запускает run_update()
    - никогда не падает, только логирует ошибки
    """
    print("=== Super_RTRS_2026 — старт ===")
    print(f"Режим обновления: {UPDATE_MODE}")
    last_run = None

    while True:
        # ждём следующего окна запуска по расписанию
        print("Ожидание следующего запуска по расписанию...")
        start_time = wait_for_schedule(UPDATE_MODE, last_run)
        print(f"Время запуска (МСК): {start_time}")

        try:
            # один полный цикл обновления
            last_run = run_update()
            print(f"Последний успешный запуск (МСК): {last_run}")
        except Exception as e:
            # падать нельзя — просто логируем и ждём следующего окна
            print("ОШИБКА ВО ВРЕМЯ ОБНОВЛЕНИЯ:", e)
            # last_run не обновляем, чтобы расписание считало от предыдущего

        # небольшая пауза, чтобы не дергать сразу же после запуска
        time.sleep(30)

# ================================
# РЕАЛИЗАЦИЯ STAGE-РЕЖИМОВ
# ================================
# Здесь уже можно безопасно использовать все функции выше:
#  - GITHUB_PLAYLISTS
#  - run_update()
#  - и т.д.
if stage == "download":
    # --------------------------------
    # ЭТАП 1 — СКАЧИВАНИЕ ИСТОЧНИКОВ
    # --------------------------------
    print("STAGE: download — скачивание источников")

    # Скачиваем все плейлисты из GITHUB_PLAYLISTS в один сырой файл
    for url in GITHUB_PLAYLISTS:
        try:
            print(f"Скачивание: {url}")
            r = requests.get(url, timeout=10)
            with open("sources_raw.m3u", "a", encoding="utf-8") as f:
                f.write(r.text + "\n")
        except Exception as e:
            print(f"Ошибка скачивания {url}: {e}")

    # После завершения — выходим, основной main() не запускаем
    exit()

if stage == "filter":
    # --------------------------------
    # ЭТАП 2 — УМНЫЙ ФИЛЬТР
    # --------------------------------
    print("STAGE: filter — умный фильтр")

    clean_lines = []
    try:
        with open("sources_raw.m3u", "r", encoding="utf-8") as f:
            for line in f:
                # Отбрасываем HTML-мусор
                if "<html" in line.lower():
                    continue
                # Отбрасываем пустые строки
                if line.strip() == "":
                    continue
                clean_lines.append(line)
    except FileNotFoundError:
        print("Файл sources_raw.m3u не найден. Сначала нужно выполнить stage=download.")
        exit(1)

    with open("sources_clean.m3u", "w", encoding="utf-8") as f:
        f.writelines(clean_lines)

    print("Фильтрация завершена, результат в sources_clean.m3u")
    exit()

if stage == "check":
    # --------------------------------
    # ЭТАП 3 — ПРОВЕРКА ПОТОКОВ
    # --------------------------------
    print("STAGE: check — turbo-проверка потоков")

    import aiohttp
    import asyncio

    async def check_url(session, url):
        """
        Асинхронная проверка одного URL:
        - пытаемся открыть поток
        - считаем живым, если статус 200
        """
        try:
            async with session.get(url, timeout=5) as r:
                return url, r.status == 200
        except:
            return url, False

    async def main_stage_check():
        """
        Читает sources_clean.m3u, проверяет все http-ссылки,
        и записывает только живые в sources_checked.m3u.
        """
        urls = []
        try:
            with open("sources_clean.m3u", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("http"):
                        urls.append(line.strip())
        except FileNotFoundError:
            print("Файл sources_clean.m3u не найден. Сначала нужно выполнить stage=filter.")
            return

        print(f"Всего ссылок для проверки: {len(urls)}")

        results = {}
        async with aiohttp.ClientSession() as session:
            tasks = [check_url(session, u) for u in urls]
            for coro in asyncio.as_completed(tasks):
                url, ok = await coro
                results[url] = ok
                print(f"[{'OK' if ok else 'BAD'}] {url}")

        alive = [u for u, ok in results.items() if ok]
        print(f"Живых ссылок: {len(alive)}")

        with open("sources_checked.m3u", "w", encoding="utf-8") as f:
            for url in alive:
                f.write(url + "\n")

        print("Результат проверки в sources_checked.m3u")

    asyncio.run(main_stage_check())
    exit()

if stage == "build":
    # --------------------------------
    # ЭТАП 4 — СБОРКА ФИНАЛЬНОГО ПЛЕЙЛИСТА
    # --------------------------------
    print("STAGE: build — сборка финального плейлиста через основной движок")

    # Вариант A: используем твой настоящий движок:
    # - run_update() сам:
    #   * загрузит старый плейлист
    #   * загрузит все источники
    #   * сделает merge
    #   * соберёт Super_RTRS_2026.m3u
    #
    # Файлы sources_raw/clean/checked здесь не обязательны —
    # они могут использоваться как вспомогательные, но
    # финальный плейлист всегда собирается по твоим правилам.
    try:
        run_update()
        print(f"Финальный плейлист собран: {OUTPUT_FILE}")
        exit(0)
    except Exception as e:
        print("Ошибка во время сборки плейлиста в stage=build:", e)
        exit(1)

# ==============================
#   ТОЧКА ВХОДА
# ==============================
if __name__ == "__main__":
    # Если указан stage — мы уже всё сделали выше и вышли через exit().
    # Если stage не указан — запускаем обычный режим по расписанию.
    if stage is None:
        main()