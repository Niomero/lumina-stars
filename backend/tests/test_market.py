from app.services.marketplace import _item, display_image, display_name


def test_username_item_strips_at_and_eq():
    item = _item(
        "username_rent",
        {
            "nft_address": "EQA9UkSsPqbl5qyr_PsVvtcqB5bWQ3pV1zCboe1htrGnliN2",
            "name": "@m5time",
            "image": "https://nft.fragment.com/username/m5time.webp",
            "price_per_day_rub": 7.59,
            "min_days": 1,
            "max_days": 180,
        },
        {"source": "tgstars"},
    )
    assert item["name"] == "m5time"
    assert item["address"].startswith("EQA9")
    assert item["image"].endswith("m5time.webp")
    assert item["length"] == 6


def test_number_item_keeps_plus_888():
    item = _item(
        "number_rent",
        {
            "nft_address": "EQBesqVyekNfjmxod596vGBFoF57XhRvwboHeIAV8rROdlV9",
            "name": "+888 0427 5863",
            "image": "https://nft.fragment.com/number/88804275863.webp",
            "price_per_day_rub": 166.04,
            "min_days": 34,
            "max_days": 90,
        },
        {"source": "tgstars"},
    )
    assert item["name"] == "+888 0427 5863"
    assert item["digits"] == "88804275863"
    assert not item["name"].startswith("EQ")


def test_nft_tgs_becomes_webp():
    assert display_image({"slug": "DurovsGlasses-3442", "image": "https://nft.fragment.com/gift/durov’sglasses-3442.tgs"}) == "https://nft.fragment.com/gift/durovsglasses-3442.webp"
    assert display_image("https://nft.fragment.com/gift/plushpepe-2388.tgs") == "https://nft.fragment.com/gift/plushpepe-2388.webp"
    name = display_name("nft_rent", {"name": "Plush Pepe #2388"}, "EQDyg")
    assert name == "Plush Pepe #2388"
    assert display_name("username_rent", {"name": "EQ-user-lume"}, "EQ-user-lume") != "EQ-user-lume"


def test_demo_username_list_uses_handle(client):
    headers = {"Authorization": f"Bearer {client.post('/api/v1/auth/demo', json={'name': 'A'}).json()['data']['token']}"}
    res = client.get("/api/v1/rent/username/list", headers=headers)
    assert res.status_code == 200, res.text
    items = res.json()["data"]["items"]
    assert items
    assert items[0]["name"] == "lume"
    assert not items[0]["name"].startswith("EQ")
