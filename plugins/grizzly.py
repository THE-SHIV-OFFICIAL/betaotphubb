"""Grizzly SMS integration (https://grizzlysms.com).

Admin commands:
  /gbalance                      - Grizzly account balance
  /gbuy <service> <country>      - get a virtual number (e.g. /gbuy tg 22)
  /gstatus <id>                  - check SMS code for activation id
  /gcancel <id>                  - cancel activation
  /gdone <id>                    - finish activation
  /grizzly                       - website link
"""
import asyncio
import urllib.parse
import urllib.request
from telethon import events, Button
from config import ADMIN_ID, ADMIN_IDS, GRIZZLY_API_KEY, GRIZZLY_API_URL, GRIZZLY_WEB_URL, logger


def _call_sync(params):
    params = {"api_key": GRIZZLY_API_KEY, **params}
    url = f"{GRIZZLY_API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (BetaBot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode().strip()


async def grizzly_call(**params):
    return await asyncio.to_thread(_call_sync, params)


async def get_balance():
    res = await grizzly_call(action="getBalance")
    return res.split(":", 1)[1] if res.startswith("ACCESS_BALANCE") else res


async def get_number(service, country):
    res = await grizzly_call(action="getNumber", service=service, country=country)
    if res.startswith("ACCESS_NUMBER"):
        _, act_id, phone = res.split(":")
        return act_id, phone
    raise Exception(res)


async def get_status(act_id):
    return await grizzly_call(action="getStatus", id=act_id)


async def set_status(act_id, status):
    return await grizzly_call(action="setStatus", id=act_id, status=status)


def register_grizzly(bot):
    def is_admin(e):
        return e.sender_id in ADMIN_IDS

    @bot.on(events.NewMessage(pattern=r"^/grizzly$"))
    async def _site(e):
        await e.respond("🐻 <b>Grizzly SMS</b>\nEarning with SIM Cards and SMS Codes",
                        buttons=[Button.url("Open Grizzly SMS", GRIZZLY_WEB_URL)])

    @bot.on(events.NewMessage(pattern=r"^/gbalance$"))
    async def _bal(e):
        if not is_admin(e): return
        try: await e.respond(f"💰 Grizzly balance: <b>${await get_balance()}</b>")
        except Exception as ex: await e.respond(f"❌ {ex}")

    @bot.on(events.NewMessage(pattern=r"^/gbuy (\S+) (\S+)$"))
    async def _buy(e):
        if not is_admin(e): return
        try:
            act_id, phone = await get_number(e.pattern_match.group(1), e.pattern_match.group(2))
            await e.respond(f"📱 Number: <code>+{phone}</code>\n🆔 ID: <code>{act_id}</code>\nUse /gstatus {act_id}")
        except Exception as ex: await e.respond(f"❌ {ex}")

    @bot.on(events.NewMessage(pattern=r"^/gstatus (\d+)$"))
    async def _st(e):
        if not is_admin(e): return
        res = await get_status(e.pattern_match.group(1))
        if res.startswith("STATUS_OK"):
            await e.respond(f"🔢 Code: <code>{res.split(':',1)[1]}</code>")
        else:
            await e.respond(f"⏳ {res}")

    @bot.on(events.NewMessage(pattern=r"^/gcancel (\d+)$"))
    async def _cancel(e):
        if not is_admin(e): return
        await e.respond(f"🔴 {await set_status(e.pattern_match.group(1), 8)}")

    @bot.on(events.NewMessage(pattern=r"^/gdone (\d+)$"))
    async def _done(e):
        if not is_admin(e): return
        await e.respond(f"✅ {await set_status(e.pattern_match.group(1), 6)}")

    logger.info("Grizzly SMS handlers registered")
