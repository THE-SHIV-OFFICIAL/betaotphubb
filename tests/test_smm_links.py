import os, sys
os.environ.update(API_ID="1", API_HASH="x", BOT_TOKEN="1:x", ADMIN_ID="1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.smm import service_kind, check_link, normalize_tg, username_from_link

def test_kinds():
    assert service_kind("Positive reactions", "Telegram • Reactions") == "post"
    assert service_kind("Post Views", "Telegram • Views") == "post"
    assert service_kind("Channel Members", "Telegram • Members") == "channel"
    assert service_kind("Instagram Likes", "Instagram • Likes") == "other"

def test_post_link_found_inside_text():
    assert normalize_tg(". https://t.me/betabot_hub/6617 text")[0] == "https://t.me/betabot_hub/6617"
    assert check_link("post", "t.me/betabot_hub/6617") == ("https://t.me/betabot_hub/6617", None)

def test_post_rejects_channel_link():
    assert check_link("post", "@betabot_hub")[1] is not None

def test_channel_strips_post_id():
    assert check_link("channel", "https://t.me/betabot_hub/6617")[0] == "https://t.me/betabot_hub"

def test_username_sent():
    assert username_from_link("https://t.me/betabot_hub/6617") == "betabot_hub"
