"""Social Media Services hub + Virtual OTP Numbers (Grizzly SMS).

User flow
  🚀 Social Media Services  ->  Telegram / Instagram / Facebook / YouTube / WhatsApp
                            ->  service type (Members, Reactions, Followers ...)
                            ->  service -> Order (link + qty) -> Confirm -> charged
  📲 Virtual Numbers        ->  platform -> buy number -> OTP arrives automatically

Admin commands
  /plist                         Telegram/WhatsApp live server-wise country prices
  /smmlist                       list all social services with local IDs
  /setsmm <id> <fansmm_id> [price_per_1000] [cost_per_1000]   connect a service to CheapestSMMPanels
  /smmoff <id>  /smmon <id>      hide / show a service
  /addacc <tg|wa> <price> <cost> <details>   add Server 1 ready account
  /accstock  /delacc <id>        view / remove Server 1 stock
  /setnumprice <tg|wa|ig|fb|go> <2|3> <price|auto>
  /stockcost <country|all> <cost>   buying cost of Telegram session stock
  /numprices                     live cost, price & profit per server
  /addbal <user_id> <amount> [reason]   add money to any user
  /cutbal <user_id> <amount> [reason]   deduct money from any user
  /checkbal <user_id>            see a user balance
"""
import asyncio
import html
import os
from telethon import events, Button
from telethon.errors import MessageNotModifiedError
from database import cur, db, to_usd, get_flag_by_country_name
from config import (PE_LIGHTNING, PE_CHECK, PE_GIFT, PE_CROWN, PE_HEART, PE_FLOWER,
                    PE_ANGEL, P_INR, P_WARN, P_NO, ADMIN_IDS, logger, tg_emoji)
from utils.keyboards import style_btn, style_url
from utils.delivery import send_delivery_thanks
from utils.states import get_user_lock
from database import get_plain_flag_by_country_name
from premium_emojis import premium_flag_id, premium_service_id

PE_ROCKET = tg_emoji("lightning", "🚀")
PE_STAR = tg_emoji("flower", "✨")

# id (custom premium emoji) used as button icons
ICON = {
    "telegram": premium_service_id("✈️", 5350433153687235163), "instagram": premium_service_id("📲", 5900192223160438756),
    "facebook": 5409166771330494453, "youtube": 5375125990118793401,
    "whatsapp": premium_service_id("💬", 5206384258431599552), "status": premium_service_id("✅", 6100650042060707109),
    "history": 5440627033111557670, "close": 6064310143380625195,
    "back": 6129812419028982717, "buy": 5409320020058584473,
    "type": 6203982793379154737, "crown": 5409166771330494453,
}

PLATFORMS = {
    "telegram": ("✈️", "Telegram"),
    "instagram": ("📸", "Instagram"),
    "facebook": ("📘", "Facebook"),
    "youtube": ("▶️", "YouTube"),
    "whatsapp": ("💬", "WhatsApp"),
    "tiktok": ("🎵", "TikTok"),
    "twitter": ("🐦", "Twitter"),
    "spotify": ("🎧", "Spotify"),
    "others": ("🌐", "Others"),
}

# name, type, min, max, price_per_1000 (INR), description
CATALOG = {
    "Telegram": [
        ("Channel / Group Members", "Members", 100, 50000, 120, "Real-looking members for channel or group. Send public t.me link."),
        ("Premium Members (Non-Drop)", "Members", 100, 20000, 450, "High quality, low drop members."),
        ("Post Views (Last 1 Post)", "Views", 100, 1000000, 8, "Views on a single post. Send post link."),
        ("Views (Last 10 Posts)", "Views", 100, 100000, 40, "Views spread on last 10 posts."),
        ("Positive Reactions 👍❤️🔥", "Reactions", 50, 100000, 25, "Mixed positive reactions on a post."),
        ("Premium Emoji Reactions", "Reactions", 50, 50000, 60, "Premium animated reactions."),
        ("Custom Reaction (Single emoji)", "Reactions", 50, 50000, 35, "One chosen reaction emoji."),
        ("Post Shares", "Shares", 100, 100000, 30, "Shares / forwards on a post."),
        ("Poll Votes", "Votes", 50, 50000, 90, "Votes on a poll option."),
        ("Bot Start / Referral", "Bot Starts", 50, 20000, 150, "Starts on your bot link."),
        ("Story Views", "Views", 100, 50000, 50, "Views on your story."),
        ("Channel Boosts", "Boosts", 1, 1000, 9000, "Premium boosts for your channel. Send channel link."),
        ("Heart Reactions ❤️", "Reactions", 50, 100000, 30, "Heart reactions on a post."),
        ("Negative Reactions 👎💩", "Reactions", 50, 100000, 30, "Mixed negative reactions."),
        ("Fire Reaction 🔥", "Reactions", 50, 100000, 30, "Fire reactions on a post."),
    ],
    "Instagram": [
        ("Followers (Real Mix)", "Followers", 100, 100000, 180, "Send profile link. Account must be public."),
        ("Followers (Non-Drop)", "Followers", 100, 50000, 320, "Refill-quality followers."),
        ("Post Likes", "Likes", 50, 100000, 40, "Likes on post / reel."),
        ("Reel Views", "Views", 100, 10000000, 6, "Views on reels."),
        ("Story Views", "Views", 100, 100000, 25, "Views on all active stories."),
        ("Custom Comments", "Comments", 10, 5000, 600, "Your own comments."),
        ("Random Comments", "Comments", 10, 5000, 350, "Positive random comments."),
        ("Saves", "Saves", 100, 50000, 30, "Post saves."),
        ("Shares", "Shares", 100, 100000, 25, "Post shares."),
        ("Live Views (30 min)", "Live", 50, 5000, 900, "Live stream viewers."),
    ],
    "Facebook": [
        ("Page Likes + Followers", "Followers", 100, 50000, 260, "Send page link."),
        ("Profile Followers", "Followers", 100, 50000, 220, "Send profile link."),
        ("Post Likes", "Likes", 50, 50000, 90, "Likes on a post."),
        ("Post Reactions (Love/Wow)", "Reactions", 50, 50000, 110, "Mixed emoji reactions."),
        ("Video Views", "Views", 500, 1000000, 20, "Views on video / reel."),
        ("Custom Comments", "Comments", 10, 2000, 700, "Your own comments."),
        ("Group Members", "Members", 100, 20000, 350, "Members for public group."),
        ("Post Shares", "Shares", 100, 50000, 120, "Shares on a post."),
    ],
    "YouTube": [
        ("Subscribers", "Subscribers", 50, 20000, 1800, "Send channel link."),
        ("Video Views", "Views", 500, 1000000, 120, "Views on video."),
        ("Shorts Views", "Views", 500, 1000000, 60, "Views on Shorts."),
        ("Video Likes", "Likes", 50, 50000, 140, "Likes on a video."),
        ("Custom Comments", "Comments", 10, 2000, 900, "Your own comments."),
        ("Watch Time (Hours)", "Watch Time", 100, 4000, 2500, "Watch hours for monetisation."),
        ("Live Stream Views", "Live", 50, 10000, 700, "Concurrent live viewers."),
    ],
    "WhatsApp": [
        ("Channel Followers", "Followers", 100, 50000, 280, "Send WhatsApp channel link."),
        ("Channel Post Reactions", "Reactions", 50, 20000, 150, "Emoji reactions on channel post."),
        ("Group Members", "Members", 50, 5000, 900, "Members for invite link group."),
    ],
}


def seed_catalog():
    for platform, items in CATALOG.items():
        for name, typ, mn, mx, price, desc in items:
            cat = f"{platform} • {typ}"
            exists = cur.execute("SELECT 1 FROM smm_services WHERE category=? AND name=?", (cat, name)).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO smm_services (name, category, fansmm_service_id, min_qty, max_qty, price_per_1000, description, available) VALUES (?,?,?,?,?,?,?,1)",
                    (name, cat, "", mn, mx, price, desc))
    db.commit()


async def _edit_or_send(e, msg, btns):
    if isinstance(e, events.CallbackQuery.Event):
        try:
            return await e.edit(msg, buttons=btns)
        except MessageNotModifiedError:
            return
        except Exception:
            pass
    return await e.respond(msg, buttons=btns)


def _bal(uid):
    r = cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    return r[0] if r else 0


# ───────────── SOCIAL HUB ─────────────
async def show_social_hub(e):
    uid = e.sender_id
    open_orders = cur.execute(
        "SELECT COUNT(*) FROM smm_orders WHERE user_id=? AND lower(status) NOT IN ('completed','canceled','cancelled','refunded','partial')",
        (uid,)).fetchone()[0]
    msg = (f"<blockquote>{PE_ROCKET} <b>𝐒ᴏᴄɪᴀʟ 𝐌ᴇᴅɪᴀ 𝐒ᴇʀᴠɪᴄᴇs</b></blockquote>\n\n"
           f"<blockquote>{PE_STAR} 𝐅ᴀsᴛ ᴅᴇʟɪᴠᴇʀʏ · ʏᴏᴜ ᴀʀᴇ ᴄʜᴀʀɢᴇᴅ ᴏɴʟʏ ᴀғᴛᴇʀ ᴄᴏɴғɪʀᴍ\n"
           f"👇 𝐂ʜᴏᴏsᴇ ᴀ ᴘʟᴀᴛғᴏʀᴍ ᴛᴏ sᴛᴀʀᴛ\n"
           f"{PE_ANGEL} <b>𝐔sᴇʀ 𝐈𝐃:</b> <code>{uid}</code>\n"
           f"{PE_CROWN} <b>𝐁ᴀʟᴀɴᴄᴇ:</b> {P_INR}{_bal(uid)} | ${to_usd(_bal(uid)):.2f}\n"
           f"📦 <b>𝐎ᴘᴇɴ ᴏʀᴅᴇʀs:</b> {open_orders}</blockquote>")
    btns = [
        [style_btn("Telegram", b"soc_p|telegram", "primary", ICON["telegram"]),
         style_btn("Instagram", b"soc_p|instagram", "primary", ICON["instagram"])],
        [style_btn("Facebook", b"soc_p|facebook", "primary", ICON["facebook"]),
         style_btn("YouTube", b"soc_p|youtube", "danger", ICON["youtube"])],
        [style_btn("WhatsApp", b"soc_p|whatsapp", "success", ICON["whatsapp"]),
         style_btn("TikTok", b"soc_p|tiktok", "primary", ICON["type"])],
        [style_btn("Twitter / X", b"soc_p|twitter", "primary", ICON["type"]),
         style_btn("Spotify", b"soc_p|spotify", "success", ICON["type"])],
        [style_btn("Other Platforms", b"soc_p|others", "primary", ICON["type"])],
        [style_btn("Check Order Status", b"soc_status", None, ICON["status"]),
         style_btn("History", b"soc_hist", None, ICON["history"])],
        [style_btn("Close", b"soc_close", "danger", ICON["close"])],
    ]
    await _edit_or_send(e, msg, btns)


async def show_platform(e, key):
    emoji, name = PLATFORMS[key]
    rows = cur.execute(
        "SELECT category, COUNT(*) FROM smm_services WHERE category LIKE ? AND available=1 AND trim(coalesce(fansmm_service_id,''))<>'' GROUP BY category ORDER BY category",
        (f"{name} •%",)).fetchall()
    btns, row = [], []
    for cat, cnt in rows:
        typ = cat.split("•", 1)[1].strip()
        row.append(style_btn(f"{typ} ({cnt})", f"soc_t|{key}|{typ}".encode(), "primary", ICON["type"]))
        if len(row) == 2:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([style_btn("Back", b"soc_home", "danger", ICON["back"])])
    msg = (f"<blockquote>{emoji} <b>{name} 𝐒ᴇʀᴠɪᴄᴇs</b></blockquote>\n\n"
           f"<blockquote>{PE_LIGHTNING} 𝐒ᴇʟᴇᴄᴛ ᴡʜᴀᴛ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɪɴᴄʀᴇᴀsᴇ:</blockquote>")
    if not rows:
        msg += f"\n<blockquote>{P_WARN} 𝐍ᴏ sᴇʀᴠɪᴄᴇs ʀɪɢʜᴛ ɴᴏᴡ.</blockquote>"
    await _edit_or_send(e, msg, btns)


PAGE_SIZE = 10


async def show_type(e, key, typ, page=1):
    emoji, name = PLATFORMS[key]
    cat = f"{name} • {typ}"
    rows = cur.execute(
        "SELECT id, name, price_per_1000 FROM smm_services WHERE category=? AND available=1 "
        "AND trim(coalesce(fansmm_service_id,''))<>'' ORDER BY price_per_1000, id",
        (cat,)).fetchall()
    pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(1, page), pages)
    chunk = rows[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
    btns = [[style_btn(f"{html.unescape(n)[:32]} — {P_INR}{p}/1K", f"smm_svc|{sid}".encode(), "primary", ICON["buy"])]
            for sid, n, p in chunk]
    if pages > 1:
        nav = []
        if page > 1: nav.append(style_btn("⬅️ Prev", f"soc_tp|{key}|{page-1}|{typ}".encode()[:64]))
        nav.append(style_btn(f"{page}/{pages}", b"num_na"))
        if page < pages: nav.append(style_btn("Next ➡️", f"soc_tp|{key}|{page+1}|{typ}".encode()[:64]))
        btns.append(nav)
    btns.append([style_btn("Back", f"soc_p|{key}".encode(), "danger", ICON["back"])])
    note = "𝐏ʀɪᴄᴇ sʜᴏᴡɴ ᴘᴇʀ 1000. 𝐓ᴀᴘ ᴀ sᴇʀᴠɪᴄᴇ ғᴏʀ ᴅᴇᴛᴀɪʟs." if rows else "𝐍ᴏ sᴇʀᴠɪᴄᴇ ʜᴇʀᴇ ʏᴇᴛ. 𝐂ʜᴇᴄᴋ ʙᴀᴄᴋ sᴏᴏɴ."
    msg = (f"<blockquote>{emoji} <b>{name} → {typ}</b></blockquote>\n\n"
           f"<blockquote>{PE_GIFT} {note}</blockquote>")
    await _edit_or_send(e, msg, btns)


async def show_history(e):
    uid = e.sender_id
    rows = cur.execute(
        "SELECT fansmm_order_id, service_name, quantity, price, status, date FROM smm_orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (uid,)).fetchall()
    if not rows:
        msg = f"<blockquote>{PE_GIFT} <b>𝐇ɪsᴛᴏʀʏ</b></blockquote>\n\n<blockquote>𝐍ᴏ ᴏʀᴅᴇʀs ʏᴇᴛ.</blockquote>"
    else:
        msg = f"<blockquote>{PE_GIFT} <b>𝐇ɪsᴛᴏʀʏ</b> (𝐋ᴀsᴛ 10)</blockquote>\n"
        for oid, sn, q, p, st, dt in rows:
            msg += (f"<blockquote>🆔 <code>{oid}</code> · {html.escape(str(sn))}\n"
                    f"📊 {q} · {P_INR}{p} · <b>{st}</b> · 📅 {str(dt)[:10]}</blockquote>\n")
    await _edit_or_send(e, msg, [[style_btn("Back", b"soc_home", "danger", ICON["back"])]])


async def show_status_list(e):
    uid = e.sender_id
    rows = cur.execute(
        "SELECT fansmm_order_id, service_name FROM smm_orders WHERE user_id=? ORDER BY id DESC LIMIT 8", (uid,)).fetchall()
    btns = [[style_btn(f"🔄 #{oid} · {str(sn)[:25]}", f"soc_chk|{oid}".encode(), "primary")] for oid, sn in rows]
    btns.append([style_btn("Back", b"soc_home", "danger", ICON["back"])])
    msg = (f"<blockquote>{PE_CHECK} <b>𝐂ʜᴇᴄᴋ 𝐎ʀᴅᴇʀ 𝐒ᴛᴀᴛᴜs</b></blockquote>\n\n"
           f"<blockquote>{'𝐓ᴀᴘ ᴀɴ ᴏʀᴅᴇʀ ᴛᴏ ʀᴇғʀᴇsʜ ʟɪᴠᴇ sᴛᴀᴛᴜs.' if rows else '𝐍ᴏ ᴏʀᴅᴇʀs ʏᴇᴛ.'}</blockquote>")
    await _edit_or_send(e, msg, btns)


# ───────────── VIRTUAL NUMBERS — SERVER 1 / 2 / 3 ─────────────
# Server 1 ⭐ Ready accounts added manually by owner/admin (best, instant)
# Server 2 💎 Premium OTP (Grizzly, higher price limit = more stock, faster)
# Server 3 ⚡ Economy OTP (Grizzly, cheapest provider only)
import math
import time as _time

NUM_SERVICES = {  # grizzly service code
    "tg": ("✈️", "Telegram"), "wa": ("💬", "WhatsApp"), "ig": ("📸", "Instagram"),
    "fb": ("📘", "Facebook"), "go": ("▶️", "YouTube / Google"),
}
SERVER1_PLATFORMS = {"tg", "wa"}
MARKUP = {2: float(os.getenv("NUM_MARKUP_S2", "2.0")), 3: float(os.getenv("NUM_MARKUP_S3", "1.6"))}
_price_cache = {}
_number_menu_back_to = {}


async def grizzly_prices(code):
    """Returns (min_usd, max_usd, count) for a service in GRIZZLY_COUNTRY. Cached 5 min."""
    from plugins.grizzly import grizzly_call
    from config import GRIZZLY_API_KEY
    import json
    if not GRIZZLY_API_KEY:
        raise Exception("GRIZZLY_API_KEY not set in variables")
    country = str(os.getenv("GRIZZLY_COUNTRY", "22")).strip()
    k = (code, country)
    if k in _price_cache and _time.time() - _price_cache[k][0] < 300:
        return _price_cache[k][1]
    prices, count, last = [], 0, ""
    for action in ("getPricesV3", "getPrices"):
        try:
            res = await grizzly_call(action=action, service=code, country=country)
            last = res
            data = json.loads(res)
        except Exception as ex:
            last = str(ex); continue
        if not isinstance(data, dict): continue
        d = data.get(country) or data.get(int(country) if country.isdigit() else country) or {}
        d = d.get(code) or {}
        if not d: continue
        for pr in (d.get("providers") or {}).values():
            if int(pr.get("count") or 0) > 0:
                pv = pr.get("price") or pr.get("cost")
                prices += [float(x) for x in (pv if isinstance(pv, list) else [pv]) if x is not None]
        count = int(d.get("count") or 0)
        base = d.get("price", d.get("cost"))
        if not prices and base is not None and count > 0:
            prices = [float(base)]
        if prices: break
    if not prices:
        raise Exception(f"no stock / bad response: {str(last)[:120]}")
    val = (min(prices), max(prices), count)
    _price_cache[k] = (_time.time(), val)
    return val


def _setting(key):
    r = cur.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r[0] if r else None


async def server_offer(code, server):
    """(sell_inr, cost_inr, max_usd) for server 2 / 3."""
    from database import get_usdt_rate
    mn, mx, _ = await grizzly_prices(code)
    # premium: allow better / pricier providers but cap at 2.5x the cheapest so price stays sane
    max_usd = mn if server == 3 else round(min(mx, mn * float(os.getenv("NUM_PREMIUM_CAP", "2.5"))), 4)
    rate = get_usdt_rate()
    cost_inr = round(max_usd * rate, 2)
    fixed = _setting(f"num_price_{code}_{server}")
    sell = float(fixed) if fixed else max(math.ceil(cost_inr * MARKUP[server]), math.ceil(cost_inr) + 5)
    return int(sell), cost_inr, max_usd


# ───────────── GRIZZLY: ALL COUNTRIES (Server 2 / 3) ─────────────
GZ_PER_PAGE = 20
_gz_countries = {"t": 0, "data": {}}
_gz_lists = {}
_iso_cache = {}
gz_search_state = {}


async def gz_country_names():
    """{country_id: english_name} from Grizzly. Cached 1h."""
    from plugins.grizzly import grizzly_call
    import json
    if _gz_countries["data"] and _time.time() - _gz_countries["t"] < 3600:
        return _gz_countries["data"]
    data = {}
    try:
        raw = json.loads(await grizzly_call(action="getCountries"))
        items = raw.values() if isinstance(raw, dict) else raw
        for v in items:
            if isinstance(v, dict) and "id" in v:
                data[str(v["id"])] = v.get("eng") or v.get("name") or v.get("rus") or str(v["id"])
    except Exception as ex:
        logger.warning("grizzly getCountries: %s", ex)
    if data: _gz_countries.update(t=_time.time(), data=data)
    return data


def gz_iso(name):
    """English country name -> ISO2 (for flag + search)."""
    if name in _iso_cache: return _iso_cache[name]
    alias = {"ivory coast": "CI", "cote d'ivoire": "CI", "russia": "RU", "usa": "US", "uk": "GB", "england": "GB",
             "south korea": "KR", "north korea": "KP", "laos": "LA", "vietnam": "VN", "iran": "IR", "syria": "SY",
             "congo": "CG", "dr congo": "CD", "drc": "CD", "papua new gvineya": "PG", "papua new guinea": "PG",
             "macedonia": "MK", "moldova": "MD", "tanzania": "TZ", "bolivia": "BO", "venezuela": "VE", "taiwan": "TW",
             "palestine": "PS", "kosovo": "XK", "eswatini": "SZ", "swaziland": "SZ", "turkey": "TR", "czech": "CZ",
             "hong kong": "HK", "macau": "MO", "burma": "MM", "myanmar": "MM", "east timor": "TL", "cape verde": "CV"}
    iso = alias.get(name.strip().lower(), "")
    if iso:
        _iso_cache[name] = iso
        return iso
    try:
        import pycountry
        try: iso = pycountry.countries.lookup(name).alpha_2
        except LookupError: iso = pycountry.countries.search_fuzzy(name.split("(")[0].strip())[0].alpha_2
    except Exception:
        pass
    _iso_cache[name] = iso
    return iso


async def gz_list(code):
    """[(cid, name, iso, cost_usd, count)] for every country that has stock. Cached 5 min."""
    from plugins.grizzly import grizzly_call
    from config import GRIZZLY_API_KEY
    import json
    if not GRIZZLY_API_KEY:
        raise Exception("GRIZZLY_API_KEY not set in variables")
    if code in _gz_lists and _time.time() - _gz_lists[code][0] < 300:
        return _gz_lists[code][1]
    res = await grizzly_call(action="getPrices", service=code)
    try: data = json.loads(res)
    except Exception: raise Exception(f"bad response: {res[:120]}")
    names = await gz_country_names()
    out = []
    for cid, svcs in (data or {}).items():
        d = (svcs or {}).get(code) or {}
        cost, cnt = d.get("cost", d.get("price")), int(d.get("count") or 0)
        if cost is None or cnt <= 0: continue
        name = names.get(str(cid), f"Country {cid}")
        out.append((str(cid), name, gz_iso(name), float(cost), cnt))
    out.sort(key=lambda x: x[3])
    if not out: raise Exception("no stock")
    _gz_lists[code] = (_time.time(), out)
    return out


def gz_offer(code, server, cost_usd):
    """(sell_inr, cost_inr, max_usd) for one country."""
    from database import get_usdt_rate
    max_usd = cost_usd if server == 3 else round(cost_usd * float(os.getenv("NUM_PREMIUM_CAP_S2", "1.5")), 4)
    cost_inr = round(max_usd * get_usdt_rate(), 2)
    sell = max(math.ceil(cost_inr * MARKUP[server]), math.ceil(cost_inr) + 5)
    return int(sell), cost_inr, max_usd


def _gz_buttons(code, server, rows):
    btns, row = [], []
    for cid, name, iso, cost, cnt in rows:
        sell, _, _ = gz_offer(code, server, cost)
        flag = _flag_from_cc(iso)
        icon = premium_flag_id(flag)
        label = f"{name} {P_INR}{sell}" if icon else f"{flag} {name} {P_INR}{sell}"
        row.append(style_btn(label[:40], f"gz_c|{code}|{server}|{cid}".encode(), "primary", icon))
        if len(row) == 2: btns.append(row); row = []
    if row: btns.append(row)
    return btns


async def gz_show_list(e, code, server, page=1):
    em, name = NUM_SERVICES[code]
    try:
        rows = await gz_list(code)
    except Exception as ex:
        logger.warning("grizzly list %s: %s", code, ex)
        return await e.answer("No numbers available on this server right now.", alert=True)
    pages = max(1, math.ceil(len(rows) / GZ_PER_PAGE))
    page = max(1, min(page, pages))
    btns = _gz_buttons(code, server, rows[(page - 1) * GZ_PER_PAGE: page * GZ_PER_PAGE])
    nav = []
    if page > 1: nav.append(style_btn("𝐏ʀᴇᴠ", f"gz_l|{code}|{server}|{page-1}".encode(), "primary", 6129627894349045589))
    if page < pages: nav.append(style_btn("𝐍ᴇxᴛ", f"gz_l|{code}|{server}|{page+1}".encode(), "primary", 6129732880529628243))
    if nav: btns.append(nav)
    btns.append([style_btn("🔍 𝐒ᴇᴀʀᴄʜ 𝐂ᴏᴜɴᴛʀʏ", f"gz_s|{code}|{server}".encode(), "success", ICON["type"])])
    btns.append([style_btn("Back", f"num_p|{code}".encode(), "danger", ICON["back"])])
    title = "💎 𝐒ᴇʀᴠᴇʀ 2 · 𝐏ʀᴇᴍɪᴜᴍ" if server == 2 else "⚡ 𝐒ᴇʀᴠᴇʀ 3 · 𝐄ᴄᴏɴᴏᴍʏ"
    await _edit_or_send(e, f"<blockquote>{em} <b>{name} · {title}</b> (𝐏ᴀɢᴇ {page}/{pages})</blockquote>\n\n"
                           f"<blockquote>{PE_LIGHTNING} {len(rows)} ᴄᴏᴜɴᴛʀɪᴇs ᴀᴠᴀɪʟᴀʙʟᴇ. 𝐏ɪᴄᴋ ᴏɴᴇ ᴏʀ ᴛᴀᴘ 🔍 𝐒ᴇᴀʀᴄʜ.</blockquote>", btns)


async def gz_search(e, code, server, query):
    q = query.strip().lower().lstrip("+")
    rows = await gz_list(code)
    res = []
    for r in rows:
        cid, name, iso = r[0], r[1].lower(), r[2]
        if (q.isdigit() and _dial_code(iso) == q) or (iso and q == iso.lower()) or (len(q) >= 2 and q in name):
            res.append(r)
    btns = _gz_buttons(code, server, res[:40])
    btns.append([style_btn("🔍 𝐒ᴇᴀʀᴄʜ 𝐀ɢᴀɪɴ", f"gz_s|{code}|{server}".encode(), "success", ICON["type"])])
    btns.append([style_btn("Back", f"gz_l|{code}|{server}|1".encode(), "danger", ICON["back"])])
    head = f"<blockquote>🔍 <b>𝐑ᴇsᴜʟᴛs ғᴏʀ:</b> <code>{html.escape(query)}</code> ({len(res)})</blockquote>"
    if not res: head += "\n\n<blockquote>𝐍ᴏ ᴄᴏᴜɴᴛʀʏ ғᴏᴜɴᴅ. 𝐓ʀʏ ɴᴀᴍᴇ (India), ᴄᴏᴅᴇ (IN) ᴏʀ ᴅɪᴀʟ (+91).</blockquote>"
    await e.respond(head, buttons=btns)


# ───────────── SERVER 2 (Telegram) — TG-Lion ─────────────
TL_PER_PAGE = 20
tl_search_state = set()


def _flag_from_cc(cc):
    cc = (cc or "").upper()
    if len(cc) != 2 or not cc.isalpha(): return "🌍"
    return "".join(chr(0x1F1E6 + ord(ch) - 65) for ch in cc)


def _dial_code(cc):
    try:
        import phonenumbers
        return str(phonenumbers.country_code_for_region(cc.upper()) or "")
    except Exception:
        from database import COUNTRY_CODES
        return ""


def _tl_buttons(items):
    from plugins.tglion import tl_sell_price
    btns, row = [], []
    for cc, v in items:
        sell, _ = tl_sell_price(v["price"])
        flag = _flag_from_cc(cc)
        icon = premium_flag_id(flag) or premium_flag_id(get_plain_flag_by_country_name(v["name"]))
        label = f"{v['name']} {P_INR}{sell}" if icon else f"{flag} {v['name']} {P_INR}{sell}"
        row.append(style_btn(label, f"tl_c|{cc}".encode(), "primary", icon))
        if len(row) == 2: btns.append(row); row = []
    if row: btns.append(row)
    return btns


async def _tl_sorted():
    from plugins.tglion import tl_countries
    cs = await tl_countries()
    return sorted(cs.items(), key=lambda kv: float(kv[1]["price"]))


async def tl_show_list(e, page=1):
    try:
        items = await _tl_sorted()
    except Exception as ex:
        logger.warning("tglion: %s", ex)
        return await e.answer("BETA is busy, try again.", alert=True)
    pages = max(1, math.ceil(len(items) / TL_PER_PAGE))
    page = max(1, min(page, pages))
    btns = _tl_buttons(items[(page - 1) * TL_PER_PAGE: page * TL_PER_PAGE])
    nav = []
    if page > 1: nav.append(style_btn("𝐏ʀᴇᴠ", f"tl_pg|{page-1}".encode(), "primary", 6129627894349045589))
    if page < pages: nav.append(style_btn("𝐍ᴇxᴛ", f"tl_pg|{page+1}".encode(), "primary", 6129732880529628243))
    if nav: btns.append(nav)
    btns.append([style_btn("🔍 𝐒ᴇᴀʀᴄʜ 𝐂ᴏᴜɴᴛʀʏ", b"tl_search", "success", premium_service_id("🔍", ICON["type"]))])
    btns.append([style_btn("Back", b"num_p|tg", "danger", ICON["back"])])
    await _edit_or_send(e, f"<blockquote>🦁 <b>𝐒ᴇʀᴠᴇʀ 2 · 𝐁𝐄𝐓𝐀 𝐓ᴇʟᴇɢʀᴀᴍ 𝐀ᴄᴄᴏᴜɴᴛ</b> (𝐏ᴀɢᴇ {page}/{pages})</blockquote>\n\n"
                           f"<blockquote>{PE_LIGHTNING} 𝐏ɪᴄᴋ ᴀ ᴄᴏᴜɴᴛʀʏ ᴏʀ ᴛᴀᴘ 🔍 𝐒ᴇᴀʀᴄʜ. 𝐘ᴏᴜ ɢᴇᴛ ᴀ ɴᴜᴍʙᴇʀ → ʟᴏɢɪɴ ɪɴ 𝐓ᴇʟᴇɢʀᴀᴍ → ᴛᴀᴘ <b>𝐆ᴇᴛ 𝐂ᴏᴅᴇ</b>.</blockquote>", btns)


async def tl_search(e, query):
    q = query.strip().lower().lstrip("+")
    items = await _tl_sorted()
    res = []
    for cc, v in items:
        name = str(v["name"]).lower()
        if (q.isdigit() and _dial_code(cc) == q) or q == cc.lower() or (len(q) >= 2 and q in name):
            res.append((cc, v))
    btns = _tl_buttons(res[:40])
    btns.append([style_btn("🔍 𝐒ᴇᴀʀᴄʜ 𝐀ɢᴀɪɴ", b"tl_search", "success", premium_service_id("🔍", ICON["type"]))])
    btns.append([style_btn("Back", b"tl_list", "danger", ICON["back"])])
    head = f"<blockquote>🔍 <b>𝐑ᴇsᴜʟᴛs ғᴏʀ:</b> <code>{html.escape(query)}</code> ({len(res)})</blockquote>"
    if not res: head += "\n\n<blockquote>𝐍ᴏ ᴄᴏᴜɴᴛʀʏ ғᴏᴜɴᴅ. 𝐓ʀʏ ɴᴀᴍᴇ (India), ᴄᴏᴅᴇ (IN) ᴏʀ ᴅɪᴀʟ (+91).</blockquote>"
    await e.respond(head, buttons=btns)


async def tl_buy_flow(e, cc):
    from plugins.tglion import tl_countries, tl_sell_price, tl_buy
    from plugins.profit import notify_profit
    uid = e.sender_id
    cs = await tl_countries()
    v = cs.get(cc.upper())
    if not v: return await e.answer("Out of stock for this country.", alert=True)
    price, cost = tl_sell_price(v["price"])
    async with get_user_lock(uid):
        cur.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (price, uid, price))
        if cur.rowcount == 0:
            return await e.answer("❌ Insufficient Balance! Please recharge.", alert=True)
        db.commit()
    try:
        r = await tl_buy(cc)
        phone = str(r["Number"]).replace(" ", "")
        from database import get_usdt_rate
        cost = round(float(r.get("price", v["price"])) * get_usdt_rate(), 2)
    except Exception as ex:
        async with get_user_lock(uid):
            cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (price, uid)); db.commit()
        logger.warning("tglion getNumber: %s", ex)
        return await e.answer("No number available right now. Balance returned.", alert=True)
    cur.execute("INSERT INTO number_orders (user_id, platform, server, activation_id, phone, price, cost, status) VALUES (?,?,?,?,?,?,?,?)",
                (uid, "tg", 2, phone, phone.lstrip("+"), price, cost, "waiting")); db.commit()
    await e.edit(f"<blockquote>🦁 <b>𝐁𝐄𝐓𝐀 · 𝐓ᴇʟᴇɢʀᴀᴍ</b> · {v['name']}</blockquote>\n\n"
                 f"<blockquote>📱 <code>{phone}</code>\n{P_INR}{price} ᴘᴀɪᴅ\n\n"
                 f"1️⃣ 𝐄ɴᴛᴇʀ ᴛʜɪs ɴᴜᴍʙᴇʀ ɪɴ 𝐓ᴇʟᴇɢʀᴀᴍ\n2️⃣ 𝐓ᴀᴘ <b>𝐆ᴇᴛ 𝐂ᴏᴅᴇ</b> ʙᴇʟᴏᴡ</blockquote>",
                 buttons=[[style_btn("🔢 Get Code", f"tl_g|{phone}".encode(), "success", ICON["buy"])]])
    await notify_profit(uid, "BETA · Telegram", phone, price, cost)


async def tl_get_code(e, phone):
    from plugins.tglion import tl_code
    row = cur.execute("SELECT id FROM number_orders WHERE activation_id=? AND user_id=? AND server=2 AND platform='tg'",
                      (phone, e.sender_id)).fetchone()
    if not row: return await e.answer("Order not found.", alert=True)
    try:
        r = await tl_code(phone)
    except Exception:
        r = None
    if not r or not r.get("code"):
        return await e.answer("⏳ Code not received yet. Send the code in Telegram first, then tap again.", alert=True)
    cur.execute("UPDATE number_orders SET otp=?, status='done' WHERE id=?", (r["code"], row[0])); db.commit()
    pw = f"\n🔐 2FA: <code>{html.escape(str(r.get('pass')))}</code>" if r.get("pass") else ""
    await e.edit(f"<blockquote>{PE_CHECK} <b>𝐋ᴏɢɪɴ 𝐂ᴏᴅᴇ</b>\n📱 <code>{phone}</code>\n🔢 <code>{r['code']}</code>{pw}</blockquote>",
                 buttons=[[style_btn("🔄 Get Again", f"tl_g|{phone}".encode(), "primary", ICON["buy"])]])
    from config import bot
    await send_delivery_thanks(bot, e.sender_id, f"number:{row[0]}")


def manual_count(code):
    return cur.execute("SELECT COUNT(*) FROM manual_stock WHERE platform=? AND available=1", (code,)).fetchone()[0]


async def show_numbers(e):
    _number_menu_back_to[e.sender_id] = "menu_numbers"
    btns = [[style_btn(f"{em} {n}", f"num_p|{c}".encode(), "primary", ICON["buy"])] for c, (em, n) in NUM_SERVICES.items()]
    btns.append([style_btn("Back", b"menu_more", "danger", ICON["back"])])
    msg = (f"<blockquote>📲 <b>𝐕ɪʀᴛᴜᴀʟ 𝐍ᴜᴍʙᴇʀs & 𝐀ᴄᴄᴏᴜɴᴛs</b></blockquote>\n\n"
           f"<blockquote>{PE_LIGHTNING} 𝐂ʜᴏᴏsᴇ ᴀ ᴘʟᴀᴛғᴏʀᴍ, ᴛʜᴇɴ ᴀ sᴇʀᴠᴇʀ.\n"
           f"📖 𝐎ɴʟʏ ᴡᴏʀᴋɪɴɢ sᴇʀᴠᴇʀs ᴀʀᴇ sʜᴏᴡɴ.</blockquote>")
    await _edit_or_send(e, msg, btns)


async def show_servers(e, code, back_to=None):
    """Only servers that are really working (API key set + stock) are shown,
    and only those servers are explained in the description."""
    if back_to in {"menu_home", "menu_numbers"}:
        _number_menu_back_to[e.sender_id] = back_to
    em, name = NUM_SERVICES[code]
    btns, guide = [], []
    if code in SERVER1_PLATFORMS:
        n = manual_count(code)
        if code == "tg":
            n += cur.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()[0]
        if n:
            btns.append([style_btn(f"⭐ Server 1 · Ready Account ({n})", f"num_s|{code}|1".encode(), "success", ICON["crown"] if "crown" in ICON else ICON["buy"])])
            guide.append(f"{PE_CROWN} <b>Server 1 · Ready Account:</b> ready accounts"
                         f"{' and Telegram country stock' if code == 'tg' else ''}; fake and scam tag accounts may also be available.")
    for s, title, tone in [(2, "💎 Server 2 · Premium OTP", "primary"), (3, "⚡ Server 3 · Economy OTP", None)]:
        if code == "tg" and s == 2:
            if not os.getenv("TGLION_API_KEY", "").strip():
                continue
            try:
                from plugins.tglion import tl_countries, tl_sell_price
                cs = await tl_countries()
                low = min(tl_sell_price(v["price"])[0] for v in cs.values())
                btns.append([style_btn(f"🦁 Server 2 · BETA Account — from {P_INR}{low}", b"tl_list", "primary", premium_service_id("🦁", ICON["buy"]))])
                guide.append("💎 <b>Server 2 · Premium OTP:</b> Premium BETA numbers.")
            except Exception as ex:
                logger.warning("tglion list failed: %s", ex)
            continue
        from config import GRIZZLY_API_KEY
        if not (GRIZZLY_API_KEY or "").strip():
            continue
        try:
            rows = await gz_list(code)
            low = min(gz_offer(code, s, r[3])[0] for r in rows)
            btns.append([style_btn(f"{title} — from {P_INR}{low} · {len(rows)} 🌍", f"num_s|{code}|{s}".encode(), tone, ICON["buy"])])
            if s == 2:
                guide.append("💎 <b>Server 2 · Premium OTP:</b> Premium OTP numbers.")
            else:
                guide.append(f"{PE_LIGHTNING} <b>Server 3 · Economy OTP:</b> economy numbers. No OTP in 10 minutes → auto-cancel and balance returned.")
        except Exception as ex:
            logger.warning("price fetch failed %s: %s", code, ex)
    if code == "tg":
        btns.append([style_btn("📦 Buy Bulk Acc", b"bulk_buy|tg", "success", ICON["buy"])])
        guide.append(f"{PE_HEART} <b>Bulk Telegram:</b> contact the owner for bulk-order details.")
    parent = _number_menu_back_to.get(e.sender_id, "menu_numbers")
    btns.append([style_btn("Back", parent.encode(), "danger", ICON["back"])])
    if not guide or (code == "tg" and len(guide) == 1):
        guide.insert(0, f"{P_WARN} No server is available right now. Please check back soon.")
    msg = (f"<blockquote>{em} <b>{name} — 𝐒ᴇʟᴇᴄᴛ 𝐒ᴇʀᴠᴇʀ</b></blockquote>\n\n"
           "<blockquote>📖 <b>𝐒ᴇʀᴠᴇʀ 𝐆ᴜɪᴅᴇ</b>\n" + "\n".join(guide) + "</blockquote>")
    await _edit_or_send(e, msg, btns)


# ───────────── LIVE PRICE LIST ─────────────
PLIST_PLATFORMS = {
    "tg": ("✈️", "Telegram"),
    "wa": ("💬", "WhatsApp"),
}


async def show_plist_platforms(e):
    btns = [
        [style_btn("✈️ Telegram", b"plist_p|tg", "primary", ICON["telegram"])],
        [style_btn("💬 WhatsApp", b"plist_p|wa", "success", ICON["whatsapp"])],
    ]
    await _edit_or_send(
        e,
        "<blockquote>📋 <b>𝐏ʀɪᴄᴇ 𝐋ɪsᴛ</b></blockquote>\n\n"
        "<blockquote>Choose a platform to see its server-wise country prices.</blockquote>",
        btns,
    )


async def show_plist_servers(e, code):
    emoji, name = PLIST_PLATFORMS[code]
    btns = [
        [style_btn("⭐ Server 1 · Ready Account", f"plist_s|{code}|1".encode(), "success", ICON["buy"])],
        [style_btn("💎 Server 2 · Premium", f"plist_s|{code}|2".encode(), "primary", ICON["buy"])],
        [style_btn("⚡ Server 3 · Economy", f"plist_s|{code}|3".encode(), "primary", ICON["buy"])],
        [style_btn("⬅️ Back", b"plist_home", "danger", ICON["back"])],
    ]
    await _edit_or_send(
        e,
        f"<blockquote>{emoji} <b>{name} · Select Server</b></blockquote>\n\n"
        "<blockquote>Choose a server to receive its current country price list.</blockquote>",
        btns,
    )


async def _plist_server1(code):
    """Return current server-1 inventory prices, using only records that can be bought."""
    lines = []
    if code == "tg":
        rows = cur.execute(
            "SELECT country_name, account_year, price, COUNT(*) "
            "FROM stock WHERE available=1 AND country_name IS NOT NULL "
            "GROUP BY country_name, account_year, price "
            "ORDER BY country_name, account_year, price"
        ).fetchall()
        for country, year, price, count in rows:
            flag = get_flag_by_country_name(country)
            year_label = f" · {year}" if year else ""
            lines.append(
                f"{flag} <b>{html.escape(str(country))}</b>{year_label} — "
                f"{P_INR}{price} · {count} available"
            )
        manual = cur.execute(
            "SELECT price, COUNT(*) FROM manual_stock "
            "WHERE platform='tg' AND available=1 GROUP BY price ORDER BY price"
        ).fetchall()
        for price, count in manual:
            lines.append(f"⭐ Telegram Ready Account — {P_INR}{price:g} · {count} available")
    else:
        manual = cur.execute(
            "SELECT price, COUNT(*) FROM manual_stock "
            "WHERE platform='wa' AND available=1 GROUP BY price ORDER BY price"
        ).fetchall()
        for price, count in manual:
            lines.append(f"⭐ WhatsApp Ready Account — {P_INR}{price:g} · {count} available")
    return lines


async def _plist_lines(code, server):
    if server == 1:
        lines = await _plist_server1(code)
        return lines or ["No Server 1 accounts are currently in stock."]

    if code == "tg" and server == 2:
        from plugins.tglion import tl_countries, tl_sell_price
        countries = await tl_countries()
        lines = []
        for cc, item in sorted(countries.items(), key=lambda kv: str(kv[1].get("name", kv[0])).lower()):
            name = str(item.get("name") or cc)
            qty = int(item.get("qty") or 0)
            sell, _ = tl_sell_price(item["price"])
            lines.append(
                f"{_flag_from_cc(cc)} <b>{html.escape(name)}</b> — {P_INR}{sell} · {qty} available"
            )
        return lines or ["No countries are currently available on this server."]

    rows = await gz_list(code)
    lines = []
    for _cid, name, iso, cost, count in rows:
        sell, _cost_inr, _max_usd = gz_offer(code, server, cost)
        flag = _flag_from_cc(iso)
        lines.append(
            f"{flag} <b>{html.escape(str(name))}</b> — {P_INR}{sell} · {count} available"
        )
    return lines or ["No countries are currently available on this server."]


def _split_plist(header, lines, footer, limit=3600):
    """Split HTML-safe lines below Telegram's message limit."""
    chunks, current = [], header
    for line in lines:
        candidate = f"{current}\n{line}"
        if len(candidate.encode("utf-16-le")) // 2 > limit and current != header:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if not chunks or current:
        chunks.append(current)
    chunks[-1] += f"\n\n<i>{footer}</i>"
    return chunks


async def send_price_list(e, code, server):
    emoji, name = PLIST_PLATFORMS[code]
    try:
        lines = await _plist_lines(code, server)
    except Exception as ex:
        logger.warning("price list unavailable %s server %s: %s", code, server, ex)
        return await e.respond(
            "<blockquote>⚠️ This server's live price list is unavailable right now. "
            "Please try again shortly.</blockquote>",
            buttons=[[style_btn("⬅️ Back to Servers", f"plist_p|{code}".encode(), "danger", ICON["back"])]],
        )
    header = (
        f"<blockquote>{emoji} <b>{html.escape(name)} · Server {server} Price List</b></blockquote>"
    )
    footer = "Price and availability are updated regularly and may go up or down."
    chunks = _split_plist(header, lines, footer)
    back = [[style_btn("⬅️ Back to Servers", f"plist_p|{code}".encode(), "danger", ICON["back"])]]
    await e.edit(chunks[0], buttons=back)
    for chunk in chunks[1:]:
        await e.respond(chunk)


async def show_bulk_buy(e):
    msg = (
        "<blockquote>📦 <b>Buy Bulk Telegram Accounts</b></blockquote>\n\n"
        "<blockquote>To buy bulk accounts, please contact our owner.\n"
        "Owner details: <a href=\"https://t.me/sukoon_s/2\">View owner information</a></blockquote>"
    )
    btns = [
        [style_url("👤 Contact Owner · @lll_SHIV_lll", "https://t.me/lll_SHIV_lll", "success")],
        [style_btn("⬅️ Back", b"num_p|tg", "danger", ICON["back"])],
    ]
    await _edit_or_send(e, msg, btns)


async def server1(bot, e, code):
    uid = e.sender_id
    row = cur.execute("SELECT id, price FROM manual_stock WHERE platform=? AND available=1 ORDER BY id LIMIT 1", (code,)).fetchone()
    if not row:
        if code == "tg":
            from plugins.buy import show_countries
            return await show_countries(e, "single", 1)
        return await e.answer("Server 1 is out of stock. Try Server 2 or 3.", alert=True)
    sid, price = row
    btns = [[style_btn(f"✅ Buy Now — {P_INR}{price:g}", f"num_m|{sid}".encode(), "success", ICON["buy"])]]
    if code == "tg" and cur.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()[0]:
        btns.append([style_btn("🌍 Session accounts by country", b"menu_buy", "primary", ICON["telegram"])])
    btns.append([style_btn("Back", f"num_p|{code}".encode(), "danger", ICON["back"])])
    em, name = NUM_SERVICES[code]
    await _edit_or_send(e, f"<blockquote>⭐ <b>{name} 𝐑ᴇᴀᴅʏ 𝐀ᴄᴄᴏᴜɴᴛ</b></blockquote>\n\n"
                           f"<blockquote>{PE_CHECK} 𝐈ɴsᴛᴀɴᴛ ᴅᴇʟɪᴠᴇʀʏ · {manual_count(code)} ɪɴ sᴛᴏᴄᴋ\n"
                           f"{PE_CROWN} 𝐏ʀɪᴄᴇ: {P_INR}{price:g}</blockquote>", btns)


async def buy_manual(bot, e, sid):
    from plugins.profit import notify_profit
    uid = e.sender_id
    async with get_user_lock(uid):
        row = cur.execute("SELECT platform, details, price, cost FROM manual_stock WHERE id=? AND available=1", (sid,)).fetchone()
        if not row:
            return await e.answer("Just sold out. Try again.", alert=True)
        code, details, price, cost = row
        cur.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (price, uid, price))
        if cur.rowcount == 0:
            return await e.answer("❌ Insufficient Balance! Please recharge.", alert=True)
        cur.execute("UPDATE manual_stock SET available=0, sold_to=? WHERE id=?", (uid, sid))
        db.commit()
    em, name = NUM_SERVICES[code]
    await e.edit(f"<blockquote>{PE_CHECK} <b>{name} 𝐀ᴄᴄᴏᴜɴᴛ 𝐃ᴇʟɪᴠᴇʀᴇᴅ</b></blockquote>\n\n"
                 f"<blockquote><code>{html.escape(details)}</code></blockquote>\n"
                 f"<blockquote>{P_INR}{price:g} ᴅᴇᴅᴜᴄᴛᴇᴅ · 𝐍ᴏ ʀᴇғᴜɴᴅ / ʀᴇᴛᴜʀɴ / ᴇxᴄʜᴀɴɢᴇ</blockquote>")
    await send_delivery_thanks(bot, uid, f"manual:{sid}")
    await notify_profit(uid, f"Server 1 · {name}", f"Ready account #{sid}", price, cost)


async def buy_number(bot, e, code, server, country=None):
    from plugins.grizzly import grizzly_call, get_status, set_status
    from plugins.profit import notify_profit
    import json
    uid = e.sender_id
    try:
        if country:
            row = next((r for r in await gz_list(code) if r[0] == str(country)), None)
            if not row: return await e.answer("Out of stock for this country. Pick another.", alert=True)
            price, cost_inr, max_usd = gz_offer(code, server, row[3])
        else:
            price, cost_inr, max_usd = await server_offer(code, server)
            country = os.getenv("GRIZZLY_COUNTRY", "22")
    except Exception:
        return await e.answer("Server busy, try again.", alert=True)
    async with get_user_lock(uid):
        cur.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (price, uid, price))
        if cur.rowcount == 0:
            return await e.answer("❌ Insufficient Balance! Please recharge.", alert=True)
        db.commit()
    try:
        res = await grizzly_call(action="getNumberV2", service=code, country=country, maxPrice=max_usd)
        if not res.startswith("{"):
            raise Exception(res)
        d = json.loads(res)
        act_id, phone = str(d["activationId"]), str(d["phoneNumber"])
        from database import get_usdt_rate
        cost_inr = round(float(d.get("activationCost", max_usd)) * get_usdt_rate(), 2)
    except Exception as ex:
        async with get_user_lock(uid):
            cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (price, uid)); db.commit()
        logger.warning("surver 3 getNumber: %s", ex)
        return await e.answer("No number available on this server now. Balance returned — try the other server.", alert=True)
    em, name = NUM_SERVICES[code]
    cur.execute("INSERT INTO number_orders (user_id, platform, server, activation_id, phone, price, cost, status) VALUES (?,?,?,?,?,?,?,?)",
                (uid, code, server, act_id, phone, price, cost_inr, "waiting")); db.commit()
    await e.edit(f"<blockquote>{em} <b>{name} · 𝐒ᴇʀᴠᴇʀ {server}</b></blockquote>\n\n"
                 f"<blockquote>📱 <code>+{phone}</code>\n🆔 <code>{act_id}</code>\n{P_INR}{price} ʜᴇʟᴅ\n\n⏳ 𝐖ᴀɪᴛɪɴɢ ғᴏʀ 𝐎𝐓𝐏…</blockquote>")
    for _ in range(120):  # 10 minutes
        await asyncio.sleep(5)
        try:
            res = await get_status(act_id)
        except Exception:
            continue
        if res.startswith("STATUS_OK"):
            otp = res.split(":", 1)[1]
            try: await set_status(act_id, 6)
            except Exception: pass
            cur.execute("UPDATE number_orders SET otp=?, status='done' WHERE activation_id=?", (otp, act_id)); db.commit()
            await bot.send_message(uid, f"<blockquote>{PE_CHECK} <b>𝐎𝐓𝐏 𝐑ᴇᴄᴇɪᴠᴇᴅ</b>\n📱 +{phone}\n🔢 <code>{otp}</code></blockquote>")
            order_id = cur.execute("SELECT id FROM number_orders WHERE activation_id=? AND user_id=? ORDER BY id DESC LIMIT 1", (act_id, uid)).fetchone()
            if order_id:
                await send_delivery_thanks(bot, uid, f"number:{order_id[0]}")
            return await notify_profit(uid, f"Server {server} · {name}", f"+{phone}", price, cost_inr)
        if res.startswith("STATUS_CANCEL"):
            break
    try: await set_status(act_id, 8)
    except Exception: pass
    async with get_user_lock(uid):
        cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (price, uid))
        cur.execute("UPDATE number_orders SET status='cancelled' WHERE activation_id=?", (act_id,))
        db.commit()
    await bot.send_message(uid, f"<blockquote>{P_WARN} 𝐍ᴏ 𝐎𝐓𝐏 ғᴏʀ +{phone}. 𝐍ᴜᴍʙᴇʀ ᴄᴀɴᴄᴇʟʟᴇᴅ, {P_INR}{price} ʀᴇᴛᴜʀɴᴇᴅ.</blockquote>")


# ───────────── TERMS ─────────────
TERMS_TEXT = (
    f"<blockquote>{PE_FLOWER} <b>𝐓ᴇʀᴍs & 𝐂ᴏɴᴅɪᴛɪᴏɴs</b></blockquote>\n\n"
    "<blockquote>1️⃣ <b>𝐍ᴏ 𝐑ᴇғᴜɴᴅ</b> — ᴏɴᴄᴇ ᴀɴ ᴏʀᴅᴇʀ ɪs ᴄᴏɴғɪʀᴍᴇᴅ, ᴍᴏɴᴇʏ ɪs ɴᴏᴛ ʀᴇғᴜɴᴅᴇᴅ.\n"
    "2️⃣ <b>𝐍ᴏ 𝐑ᴇᴛᴜʀɴ</b> — ᴅᴇʟɪᴠᴇʀᴇᴅ ᴀᴄᴄᴏᴜɴᴛs, ɴᴜᴍʙᴇʀs ᴀɴᴅ sᴇʀᴠɪᴄᴇs ᴄᴀɴɴᴏᴛ ʙᴇ ʀᴇᴛᴜʀɴᴇᴅ.\n"
    "3️⃣ <b>𝐍ᴏ 𝐄xᴄʜᴀɴɢᴇ</b> — ᴡᴇ ᴅᴏ ɴᴏᴛ ᴇxᴄʜᴀɴɢᴇ ᴏɴᴇ sᴇʀᴠɪᴄᴇ ғᴏʀ ᴀɴᴏᴛʜᴇʀ.</blockquote>\n"
    "<blockquote>• 𝐂ʜᴇᴄᴋ ʏᴏᴜʀ ʟɪɴᴋ ʙᴇғᴏʀᴇ ᴄᴏɴғɪʀᴍ — ᴡʀᴏɴɢ / ᴘʀɪᴠᴀᴛᴇ ʟɪɴᴋ = ɴᴏ ʀᴇғᴜɴᴅ.\n"
    "• 𝐃ᴏɴ'ᴛ ᴘʟᴀᴄᴇ 2 ᴏʀᴅᴇʀs ᴏɴ ᴛʜᴇ sᴀᴍᴇ ʟɪɴᴋ ᴀᴛ ᴛʜᴇ sᴀᴍᴇ ᴛɪᴍᴇ.\n"
    "• 𝐃ʀᴏᴘs ᴀғᴛᴇʀ ᴅᴇʟɪᴠᴇʀʏ ᴀʀᴇ ɴᴏᴛ ᴏᴜʀ ʀᴇsᴘᴏɴsɪʙɪʟɪᴛʏ.\n"
    "• 𝐃ᴇᴘᴏsɪᴛᴇᴅ ʙᴀʟᴀɴᴄᴇ ᴄᴀɴɴᴏᴛ ʙᴇ ᴡɪᴛʜᴅʀᴀᴡɴ.\n"
    "• 𝐎ɴʟʏ ɪғ ᴀ sᴇʀᴠɪᴄᴇ ғᴀɪʟs ᴛᴏ sᴛᴀʀᴛ / ɴᴏ 𝐎𝐓𝐏 ᴀʀʀɪᴠᴇs, ʙᴀʟᴀɴᴄᴇ ɪs ᴀᴜᴛᴏ-ʀᴇᴛᴜʀɴᴇᴅ ᴛᴏ ʙᴏᴛ ᴡᴀʟʟᴇᴛ.\n"
    "• 𝐌ɪsᴜsᴇ / ғʀᴀᴜᴅ = ᴘᴇʀᴍᴀɴᴇɴᴛ ʙᴀɴ.</blockquote>\n"
    f"<blockquote>{PE_HEART} 𝐁ʏ ᴛᴀᴘᴘɪɴɢ <b>𝐀ᴄᴄᴇᴘᴛ</b> ʏᴏᴜ ᴀɢʀᴇᴇ ᴛᴏ ᴀʟʟ ᴛᴇʀᴍs ᴀʙᴏᴠᴇ.</blockquote>"
)


def register_social(bot):
    seed_catalog()
    from plugins.smm_sync import register_smm_sync
    register_smm_sync(bot)

    @bot.on(events.NewMessage(pattern=r"(?i)^/plist(?:@\w+)?$"))
    async def _plist_command(e):
        await show_plist_platforms(e)

    @bot.on(events.CallbackQuery(pattern=b"^plist_home$"))
    async def _plist_home(e):
        await e.answer()
        await show_plist_platforms(e)

    @bot.on(events.CallbackQuery(pattern=rb"^plist_p\|(tg|wa)$"))
    async def _plist_platform(e):
        await e.answer()
        await show_plist_servers(e, e.pattern_match.group(1).decode())

    @bot.on(events.CallbackQuery(pattern=rb"^plist_s\|(tg|wa)\|([123])$"))
    async def _plist_server(e):
        await e.answer("Loading the current price list…")
        await send_price_list(
            e,
            e.pattern_match.group(1).decode(),
            int(e.pattern_match.group(2).decode()),
        )

    @bot.on(events.CallbackQuery(pattern=b"^bulk_buy\\|tg$"))
    async def _bulk_buy(e):
        await e.answer()
        await show_bulk_buy(e)

    @bot.on(events.NewMessage(pattern=r"(?i)^(𝐒ᴏᴄɪᴀʟ 𝐌ᴇᴅɪᴀ|🚀 𝐒ᴏᴄɪᴀʟ 𝐌ᴇᴅɪᴀ|/social)$"))
    async def _m(e): await show_social_hub(e)

    @bot.on(events.NewMessage(pattern=r"^/terms$"))
    async def _t(e): await e.respond(TERMS_TEXT)

    @bot.on(events.CallbackQuery(pattern=b"^soc_home$"))
    async def _h(e): await show_social_hub(e)

    @bot.on(events.CallbackQuery(pattern=rb"^soc_p\|(\w+)$"))
    async def _p(e):
        key = e.pattern_match.group(1).decode()
        if key in PLATFORMS: await show_platform(e, key)

    @bot.on(events.CallbackQuery(pattern=rb"^soc_t\|(\w+)\|(.+)$"))
    async def _ty(e):
        key, typ = e.pattern_match.group(1).decode(), e.pattern_match.group(2).decode()
        if key in PLATFORMS: await show_type(e, key, typ)

    @bot.on(events.CallbackQuery(pattern=rb"^soc_tp\|(\w+)\|(\d+)\|(.+)$"))
    async def _typ_page(e):
        key, pg, typ = e.pattern_match.group(1).decode(), int(e.pattern_match.group(2)), e.pattern_match.group(3).decode()
        if key in PLATFORMS: await show_type(e, key, typ, pg)

    @bot.on(events.CallbackQuery(pattern=b"^soc_hist$"))
    async def _hi(e): await show_history(e)

    @bot.on(events.CallbackQuery(pattern=b"^soc_status$"))
    async def _st(e): await show_status_list(e)

    @bot.on(events.CallbackQuery(pattern=rb"^soc_chk\|(.+)$"))
    async def _chk(e):
        from plugins.smm import refresh_order, status_text, status_buttons
        oid = e.pattern_match.group(1).decode()
        try:
            info = await refresh_order(oid, e.sender_id)
        except Exception:
            row = cur.execute("SELECT status FROM smm_orders WHERE fansmm_order_id=? AND user_id=?", (oid, e.sender_id)).fetchone()
            return await e.answer(f"#{oid}\nLast status: {row[0] if row else '?'}", alert=True)
        if not info: return await e.answer("Order not found.", alert=True)
        await e.answer()
        await e.respond(status_text(info), buttons=status_buttons(oid))

    @bot.on(events.CallbackQuery(pattern=b"^soc_close$"))
    async def _c(e):
        try: await e.delete()
        except Exception: pass

    @bot.on(events.CallbackQuery(pattern=b"^menu_numbers$"))
    async def _n(e): await show_numbers(e)

    @bot.on(events.CallbackQuery(pattern=b"^menu_terms$"))
    async def _tt(e):
        await e.answer()
        await bot.send_message(e.sender_id, TERMS_TEXT)

    @bot.on(events.CallbackQuery(pattern=rb"^num_p\|(\w+)$"))
    async def _np(e):
        code = e.pattern_match.group(1).decode()
        if code in NUM_SERVICES: await show_servers(e, code)

    @bot.on(events.CallbackQuery(pattern=b"^num_na$"))
    async def _nna(e): await e.answer("This server is unavailable right now.", alert=True)

    @bot.on(events.CallbackQuery(pattern=rb"^num_s\|(\w+)\|([123])$"))
    async def _ns(e):
        from utils.helpers import require_join
        if not await require_join(bot, e): return
        code, server = e.pattern_match.group(1).decode(), int(e.pattern_match.group(2))
        if code not in NUM_SERVICES: return
        if server == 1:
            if code in SERVER1_PLATFORMS: await server1(bot, e, code)
            return
        if code == "tg" and server == 2:
            if not os.getenv("TGLION_API_KEY", "").strip():
                return await e.answer("This server is unavailable right now.", alert=True)
            return await tl_show_list(e)
        from config import GRIZZLY_API_KEY
        if not (GRIZZLY_API_KEY or "").strip():
            return await e.answer("This server is unavailable right now.", alert=True)
        await gz_show_list(e, code, server, 1)

    @bot.on(events.CallbackQuery(pattern=rb"^gz_l\|(\w+)\|([23])\|(\d+)$"))
    async def _gzl(e):
        gz_search_state.pop(e.sender_id, None)
        code = e.pattern_match.group(1).decode()
        if code in NUM_SERVICES:
            await gz_show_list(e, code, int(e.pattern_match.group(2)), int(e.pattern_match.group(3)))

    @bot.on(events.CallbackQuery(pattern=rb"^gz_c\|(\w+)\|([23])\|(\d+)$"))
    async def _gzc(e):
        from utils.helpers import require_join
        if not await require_join(bot, e): return
        code = e.pattern_match.group(1).decode()
        if code in NUM_SERVICES:
            asyncio.create_task(buy_number(bot, e, code, int(e.pattern_match.group(2)), e.pattern_match.group(3).decode()))

    @bot.on(events.CallbackQuery(pattern=rb"^gz_s\|(\w+)\|([23])$"))
    async def _gzs(e):
        gz_search_state[e.sender_id] = (e.pattern_match.group(1).decode(), int(e.pattern_match.group(2)))
        await e.answer()
        await e.respond("<blockquote>🔍 <b>𝐒ᴇᴀʀᴄʜ 𝐂ᴏᴜɴᴛʀʏ</b></blockquote>\n\n"
                        "<blockquote>𝐒ᴇɴᴅ ᴄᴏᴜɴᴛʀʏ <b>ɴᴀᴍᴇ</b> (India), <b>2-ʟᴇᴛᴛᴇʀ ᴄᴏᴅᴇ</b> (IN) ᴏʀ <b>ᴅɪᴀʟ ᴄᴏᴅᴇ</b> (+91).</blockquote>")

    @bot.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id in gz_search_state and not (e.text or "").startswith("/")))
    async def _gzsq(e):
        code, server = gz_search_state.pop(e.sender_id)
        try: await gz_search(e, code, server, e.text or "")
        except Exception as ex:
            logger.warning("gz search: %s", ex)
            await e.respond("Server busy, try again.")

    @bot.on(events.CallbackQuery(pattern=b"^tl_list$"))
    async def _tll(e):
        tl_search_state.discard(e.sender_id)
        from utils.helpers import require_join
        if not await require_join(bot, e): return
        await tl_show_list(e)

    @bot.on(events.CallbackQuery(pattern=rb"^tl_pg\|(\d+)$"))
    async def _tlpg(e):
        await tl_show_list(e, int(e.pattern_match.group(1)))

    @bot.on(events.CallbackQuery(pattern=b"^tl_search$"))
    async def _tls(e):
        tl_search_state.add(e.sender_id)
        await e.answer()
        await e.respond("<blockquote>🔍 <b>𝐒ᴇᴀʀᴄʜ 𝐂ᴏᴜɴᴛʀʏ</b></blockquote>\n\n"
                        "<blockquote>𝐒ᴇɴᴅ ᴄᴏᴜɴᴛʀʏ <b>ɴᴀᴍᴇ</b> (India), <b>2-ʟᴇᴛᴛᴇʀ ᴄᴏᴅᴇ</b> (IN) ᴏʀ <b>ᴅɪᴀʟ ᴄᴏᴅᴇ</b> (+91).</blockquote>",
                        buttons=[[style_btn("❌ Cancel", b"tl_list", "danger", ICON["back"])]])

    @bot.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id in tl_search_state and not (e.text or "").startswith("/")))
    async def _tlsq(e):
        tl_search_state.discard(e.sender_id)
        try:
            await tl_search(e, e.text or "")
        except Exception as ex:
            logger.warning("tl search: %s", ex)
            await e.respond("BETA is busy, try again.")

    @bot.on(events.CallbackQuery(pattern=rb"^tl_c\|([A-Za-z]{2})$"))
    async def _tlc(e):
        from utils.helpers import require_join
        if not await require_join(bot, e): return
        await tl_buy_flow(e, e.pattern_match.group(1).decode())

    @bot.on(events.CallbackQuery(pattern=rb"^tl_g\|(\+?\d+)$"))
    async def _tlg(e):
        await tl_get_code(e, e.pattern_match.group(1).decode())

    @bot.on(events.CallbackQuery(pattern=rb"^num_m\|(\d+)$"))
    async def _nm(e):
        from utils.helpers import require_join
        if not await require_join(bot, e): return
        await buy_manual(bot, e, int(e.pattern_match.group(1)))

    # ── Server 1 stock (owner/admin) ──
    @bot.on(events.NewMessage(pattern=r"^/addacc (tg|wa) (\d+(?:\.\d+)?) (\d+(?:\.\d+)?) ([\s\S]+)$"))
    async def _addacc(e):
        if e.sender_id not in ADMIN_IDS: return
        code, price, cost, details = e.pattern_match.group(1), float(e.pattern_match.group(2)), float(e.pattern_match.group(3)), e.pattern_match.group(4).strip()
        cur.execute("INSERT INTO manual_stock (platform, details, price, cost) VALUES (?,?,?,?)", (code, details, price, cost)); db.commit()
        await e.respond(f"{PE_CHECK} Server 1 {NUM_SERVICES[code][1]} account added · sell {P_INR}{price:g} · cost {P_INR}{cost:g} · profit {P_INR}{price-cost:g}\nIn stock: {manual_count(code)}")

    @bot.on(events.NewMessage(pattern=r"^/accstock$"))
    async def _accstock(e):
        if e.sender_id not in ADMIN_IDS: return
        rows = cur.execute("SELECT id, platform, price, cost, substr(details,1,30) FROM manual_stock WHERE available=1 ORDER BY platform, id").fetchall()
        await e.respond("\n".join(f"<code>{i}</code> {p} · {P_INR}{pr:g} (cost {c:g}) · {html.escape(d)}" for i, p, pr, c, d in rows) or "Server 1 stock is empty.")

    @bot.on(events.NewMessage(pattern=r"^/delacc (\d+)$"))
    async def _delacc(e):
        if e.sender_id not in ADMIN_IDS: return
        cur.execute("DELETE FROM manual_stock WHERE id=? AND available=1", (int(e.pattern_match.group(1)),)); db.commit()
        await e.respond(f"{PE_CHECK} Removed.")

    @bot.on(events.NewMessage(pattern=r"^/setnumprice (tg|wa|ig|fb|go) ([23]) (\d+|auto)$"))
    async def _snp(e):
        if e.sender_id not in ADMIN_IDS: return
        code, srv, val = e.pattern_match.group(1), e.pattern_match.group(2), e.pattern_match.group(3)
        key = f"num_price_{code}_{srv}"
        if val == "auto": cur.execute("DELETE FROM settings WHERE key=?", (key,))
        else: cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, val))
        db.commit()
        try:
            sell, cost, _ = await server_offer(code, int(srv))
            await e.respond(f"{PE_CHECK} {NUM_SERVICES[code][1]} Server {srv}: sell {P_INR}{sell} · cost ≈ {P_INR}{cost} · profit ≈ {P_INR}{round(sell-cost,2)}")
        except Exception as ex:
            await e.respond(f"{PE_CHECK} Saved. (Live cost not available: {ex})")

    @bot.on(events.NewMessage(pattern=r"^/stockcost (.+) (\d+(?:\.\d+)?)$"))
    async def _stc(e):
        if e.sender_id not in ADMIN_IDS: return
        country, cost = e.pattern_match.group(1).strip(), float(e.pattern_match.group(2))
        if country.lower() == "all": cur.execute("UPDATE stock SET cost=?", (cost,))
        else: cur.execute("UPDATE stock SET cost=? WHERE country_name=?", (cost, country))
        db.commit()
        await e.respond(f"{PE_CHECK} Cost {P_INR}{cost:g} set for {cur.rowcount} Telegram session accounts ({country}).")

    @bot.on(events.NewMessage(pattern=r"^/numprices$"))
    async def _nps(e):
        if e.sender_id not in ADMIN_IDS: return
        out = f"<blockquote>{PE_CROWN} <b>𝐍ᴜᴍʙᴇʀ 𝐏ʀɪᴄᴇs & 𝐏ʀᴏғɪᴛ</b></blockquote>\n"
        for c, (em, n) in NUM_SERVICES.items():
            for s in (2, 3):
                if c == "tg" and s == 2:
                    try:
                        from plugins.tglion import tl_countries, tl_sell_price
                        for cc, v in sorted((await tl_countries()).items(), key=lambda kv: float(kv[1]["price"]))[:8]:
                            sl, co = tl_sell_price(v["price"])
                            out += f"🦁 BETA {v['name']}: {P_INR}{sl} − {P_INR}{co} = <b>{P_INR}{round(sl-co,2)}</b>\n"
                    except Exception:
                        out += "🦁 BETA: unavailable\n"
                    continue
                try:
                    sell, cost, _ = await server_offer(c, s)
                    out += f"{em} {n} S{s}: {P_INR}{sell} − {P_INR}{cost} = <b>{P_INR}{round(sell-cost,2)}</b>\n"
                except Exception:
                    out += f"{em} {n} S{s}: unavailable\n"
        await e.respond(out)

    # ── admin helpers ──
    @bot.on(events.NewMessage(pattern=r"^/smmlist$"))
    async def _l(e):
        if e.sender_id not in ADMIN_IDS: return
        rows = cur.execute("SELECT id, category, name, fansmm_service_id, price_per_1000, available FROM smm_services ORDER BY category, id").fetchall()
        out = ""
        for sid, cat, n, fid, p, av in rows:
            out += f"{'🟢' if av else '🔴'} <code>{sid}</code> {cat} · {n} · ₹{p} · Panel: <code>{fid or '—'}</code>\n"
        for i in range(0, len(out) or 1, 3800):
            await e.respond(out[i:i + 3800] or "No services.")

    @bot.on(events.NewMessage(pattern=r"^/setsmm (\d+) (\S+)(?: (\d+))?(?: (\d+(?:\.\d+)?))?$"))
    async def _s(e):
        if e.sender_id not in ADMIN_IDS: return
        sid, fid, price = e.pattern_match.group(1), e.pattern_match.group(2), e.pattern_match.group(3)
        cur.execute("UPDATE smm_services SET fansmm_service_id=? WHERE id=?", (fid, sid))
        if price: cur.execute("UPDATE smm_services SET price_per_1000=? WHERE id=?", (int(price), sid))
        cost = e.pattern_match.group(4)
        if not cost:
            try:
                from plugins.smm import panel_rate
                cost = await panel_rate(fid)
            except Exception:
                cost = None
        if cost: cur.execute("UPDATE smm_services SET cost_per_1000=? WHERE id=?", (float(cost), sid))
        db.commit()
        sell = cur.execute("SELECT price_per_1000 FROM smm_services WHERE id=?", (sid,)).fetchone()
        extra = f"\n💵 Sell ₹{sell[0]}/1K · 🧾 Cost ₹{cost}/1K · 👑 Profit ₹{round(float(sell[0]) - float(cost), 2)}/1K" if (sell and cost) else ""
        await e.respond(f"{PE_CHECK} Service {sid} → Panel ID {fid}" + extra)

    @bot.on(events.NewMessage(pattern=r"^/smm(on|off) (\d+)$"))
    async def _o(e):
        if e.sender_id not in ADMIN_IDS: return
        on = e.pattern_match.group(1) == "on"
        cur.execute("UPDATE smm_services SET available=? WHERE id=?", (1 if on else 0, e.pattern_match.group(2))); db.commit()
        await e.respond(f"{PE_CHECK} Service {e.pattern_match.group(2)} {'enabled' if on else 'hidden'}")

    # ── admin / owner: add or deduct any user's balance ──
    @bot.on(events.NewMessage(pattern=r"^/(addbal|cutbal) (\d+) (\d+(?:\.\d+)?)(?: (.+))?$"))
    async def _bal_edit(e):
        if e.sender_id not in ADMIN_IDS: return
        act, t_uid = e.pattern_match.group(1), int(e.pattern_match.group(2))
        amt = float(e.pattern_match.group(3)); amt = int(amt) if amt.is_integer() else amt
        reason = e.pattern_match.group(4) or ""
        row = cur.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
        if not row: return await e.respond(f"{P_NO} User <code>{t_uid}</code> not found.")
        async with get_user_lock(t_uid):
            if act == "addbal":
                cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, t_uid))
            else:
                cur.execute("UPDATE users SET balance=MAX(balance-?,0) WHERE user_id=?", (amt, t_uid))
            db.commit()
        new = cur.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()[0]
        sign = "➕ Added" if act == "addbal" else "➖ Deducted"
        await e.respond(f"<blockquote>{PE_CHECK} <b>{sign} {P_INR}{amt}</b>\n👤 <code>{t_uid}</code>\n{PE_CROWN} New balance: <b>{P_INR}{new}</b></blockquote>")
        try:
            await bot.send_message(t_uid, f"<blockquote>{PE_CROWN} <b>𝐁ᴀʟᴀɴᴄᴇ 𝐔ᴘᴅᴀᴛᴇᴅ</b>\n{sign} {P_INR}{amt}" + (f"\n📝 {html.escape(reason)}" if reason else "") + f"\n💰 𝐍ᴇᴡ ʙᴀʟᴀɴᴄᴇ: <b>{P_INR}{new}</b></blockquote>")
        except Exception: pass

    @bot.on(events.NewMessage(pattern=r"^/(checkbal|userbal) (\d+)$"))
    async def _bal_chk(e):
        if e.sender_id not in ADMIN_IDS: return
        r = cur.execute("SELECT balance FROM users WHERE user_id=?", (int(e.pattern_match.group(2)),)).fetchone()
        await e.respond(f"👤 <code>{e.pattern_match.group(2)}</code> → {P_INR}{r[0]}" if r else f"{P_NO} User not found.")

    logger.info("Social Media hub registered")
