import requests
import re
from collections import defaultdict
from datetime import datetime

WINK_RU = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0; ru-RU) Gecko/20100101 Firefox/117.0"
WINK_REF = "https://wink.ru/"
WINK_IP = "95.24.0.1"

GITHUB_PLAYLISTS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/channels/ru.m3u",
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

    "http://rafail1982.uz/playlists/LIST2.m3u",
    "http://rafail1982.uz/playlists/DIMONOVICH.m3u",
    "http://rafail1982.uz/playlists/TELEKARTA.m3u",
    "http://rafail1982.uz/playlists/TELECIFRA.m3u",

    "https://raw.githubusercontent.com/Phoenix89S/Mir-IpTV-Ru-/main/code",
    "https://raw.githubusercontent.com/Phoenix89S/Iptv_Ru2026/main/Viju2test.m3u",

    "https://raw.githubusercontent.com/Zet2009/MOJE1/gh-pages/IPTVmir.m3u8",
    "https://raw.githubusercontent.com/smolnp/IPTVru/gh-pages/IPTVstable.m3u8",

    "https://tva.org.ua/ip/sam/poznavatelni.m3u",
    "https://tva.org.ua/ip/sam/avto-full.m3u",
    "https://tva.org.ua/free-full.html",

    "https://dtv.plus/rabochiy-iptv-pleylist-tv-kanaly/",
    "https://live.iptv-free.com/iptv/categories/kids.m3u",
    "https://live.iptv-free.com/iptv/languages/rus.m3u"
]

EPG_SOURCES = "https://epg.one/epg.xml.gz,https://iptvx.one/EPG"
OUTPUT_FILE = "Super_RTRS_2026.m3u"
MAIN_GROUP_NAME = "Эфирные ТВ плюс"
OTHER_GROUP_NAME = "Общие"

BLACKLIST = [
    "T.ME/", "TELEGRAM", "JOINCHAT", "NEXO", "ПОДПИШИСЬ",
    "ЗЕРКАЛО", "РЕЗЕРВ", "CHAT", "INFO", "ПОСМОТРИ!!!"
]

MANUAL_TAG = "[MANUAL]"
MANUAL_COMMENT = "# РУЧНАЯ ПРАВКА"

# ---------------------------------------------------------
# НОРМАЛИЗАЦИЯ ИМЁН
# ---------------------------------------------------------
def normalize_name(name: str) -> str:
    n = name.upper()
    n = re.sub(r'\b(HD|SD|FHD|UHD|4K)\b', '', n)
    n = re.sub(r'\+\d+', '', n)
    n = re.sub(r'\([^)]*\)', '', n)
    n = re.sub(r'\s+', ' ', n)
    return n.strip()

# ---------------------------------------------------------
# FIX WINK
# ---------------------------------------------------------
def fix_wink_link(url: str) -> str:
    base = url.split("|", 1)[0].lower()
    if any(x in base for x in ["wink", "cdn.ntv.ru", "zabava", "ntv.ru"]):
        parts = []
        if "user-agent=" not in url.lower():
            parts.append(f"User-Agent={WINK_RU}")
        if "referer=" not in url.lower():
            parts.append(f"Referer={WINK_REF}")
        if "x-forwarded-for=" not in url.lower():
            parts.append(f"X-Forwarded-For={WINK_IP}")
        if "|" in url:
            return url + "&" + "&".join(parts)
        else:
            return url + "|" + "&".join(parts)
    return url

# ---------------------------------------------------------
# ПРОВЕРКА ПОТОКА
# ---------------------------------------------------------
def is_live(url):
    base = url.split("|", 1)[0]
    try:
        r = requests.get(base, headers={'User-Agent': WINK_RU}, timeout=2, stream=True)
        return r.status_code in (200, 206)
    except:
        return False

# ---------------------------------------------------------
# ПАРСЕР M3U
# ---------------------------------------------------------
def get_links_from_m3u(url):
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        resp.encoding = 'utf-8'
        lines = resp.text.replace('\r', '').split('\n')
        result, meta = [], None
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
# ЗАГРУЗКА СТАРОГО ПЛЕЙЛИСТА
# ---------------------------------------------------------
def load_existing_playlist(path):
    existing = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        last_meta, manual_mode = None, False
        for line in lines:
            if line.strip() == MANUAL_COMMENT:
                manual_mode = True
                continue
            if line.startswith("#EXTINF"):
                last_meta = line
            elif last_meta and line.startswith("http"):
                name = last_meta.rsplit(",", 1)[-1].strip()
                existing[name] = {
                    "meta": last_meta,
                    "link": line.strip(),
                    "manual": manual_mode or (MANUAL_TAG in last_meta)
                }
                last_meta, manual_mode = None, False
    except:
        pass
    return existing

# ---------------------------------------------------------
# ОСНОВНАЯ ПРОГРАММА
# ---------------------------------------------------------
def main():
    print(f"🚀 Старт: {datetime.now().strftime('%H:%M:%S')}")

    existing = load_existing_playlist(OUTPUT_FILE)
    all_channels = defaultdict(lambda: defaultdict(list))
    seen_links = set()

    for url in GITHUB_PLAYLISTS:
        print(f"📥 Обработка: {url}")
        items = get_links_from_m3u(url)

        for meta, link in items:
            name = meta.rsplit(',', 1)[-1].strip()

            # Удаление дублей по ПОЛНОМУ URL (без параметров)
            clean_link = link.split("|", 1)[0].strip()
            if clean_link in seen_links:
                continue
            seen_links.add(clean_link)

            # Чёрный список
            if any(b in (meta + link).upper() for b in BLACKLIST):
                continue

            # tvg-id
            match_id = re.search(r'tvg-id="([^"]+)"', meta, re.IGNORECASE)
            tvg_id = match_id.group(1) if match_id else name

            # Ручная правка
            if name in existing and existing[name].get("manual"):
                all_channels[OTHER_GROUP_NAME]["999"].append({
                    'name': name,
                    'link': existing[name]["link"],
                    'tvg_id': tvg_id
                })
                continue

            # Wink fix
            link = fix_wink_link(link)

            # Проверка потока
            if not is_live(link):
                continue

            # Поиск по словарю
            norm_name = normalize_name(name)
            found = False

            for g_label, orbits in CHANNEL_GROUPS.items():
                for orbit, keyw in orbits.items():
                    if normalize_name(keyw) in norm_name:
                        all_channels[MAIN_GROUP_NAME][orbit].append({
                            'name': name,
                            'link': link,
                            'tvg_id': tvg_id
                        })
                        found = True
                        break
                if found:
                    break

            # 