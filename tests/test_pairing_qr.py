from io import BytesIO
from urllib.parse import parse_qs, urlsplit

import pytest
import zxingcpp
from conftest import hidden_fields
from PIL import Image

from jellyfin_msx.pairing_qr import activation_png


def rendered_qr(portal):
    root = portal.client.get("/msx/pair.json").json()
    assert "template" not in root and "items" not in root
    page = root["pages"][0]
    image = next(item["image"] for item in page["items"] if "image" in item)
    response = portal.client.get(image)
    assert response.status_code == 200
    decoded = zxingcpp.read_barcode(Image.open(BytesIO(response.content)))
    assert decoded is not None and decoded.format == zxingcpp.BarcodeFormat.QRCode
    return page, image, response, decoded.text


def test_actual_png_decodes_to_pending_only_activation_and_normal_staged_flow(portal, caplog):
    page, image, response, activation_url = rendered_qr(portal)
    parsed = urlsplit(activation_url)
    activation = parse_qs(parsed.query)["activation"][0]
    device = portal.state.pending(activation=activation)
    secret = page["items"][2]["action"].split("/device/")[1].split("/")[0]
    assert activation != secret and activation != device.code
    assert parsed.scheme == "https" and parsed.netloc == "portal.test" and parsed.path == "/pair"
    assert image.startswith(portal.settings.public_url + "/msx/pair/image/")
    assert secret not in activation_url and secret not in image
    for header, value in (
        ("cache-control", "no-store, private"),
        ("referrer-policy", "no-referrer"),
    ):
        assert response.headers[header] == value
    assert response.headers["content-type"] == "image/png"
    assert portal.state.get(secret, authenticated=False).token is None
    assert not portal.fake.requests
    assert (
        portal.client.get(f"/msx/device/{secret}/home.json").json()["headline"]
        == "Waiting for pairing"
    )
    form = portal.client.get(activation_url)
    assert form.url.path == "/pair" and not form.url.query
    assert 'name="password"' in form.text and 'name="code"' not in form.text
    assert not portal.fake.requests and device.token is None
    result = portal.client.post(
        "/pair",
        data={**hidden_fields(form), "username": "viewer", "password": "test-password"},
        headers={"Origin": portal.settings.public_url},
    )
    assert "TV paired" in result.text
    assert (
        portal.client.get(f"/msx/device/{secret}/home.json").json()["headline"]
        == "Jellyfin libraries"
    )
    assert portal.client.get(image).status_code == 400
    assert all(value not in caplog.text for value in (activation, device.token, secret))


@pytest.mark.parametrize(
    "unavailable", ["expiry", "removed", "claimed", "paired", "session-secret", "invalid"]
)
def test_qr_delivery_denies_unavailable_or_wrong_authority(portal, unavailable):
    _, image, _, _ = rendered_qr(portal)
    secret, device = portal.state.pair()
    activation = image.rsplit("/", 1)[1].removesuffix(".png")
    original = portal.state.pending(activation=activation)
    if unavailable == "expiry":
        portal.now[0] += portal.settings.pairing_ttl
    elif unavailable == "removed":
        portal.state.devices = {
            key: value for key, value in portal.state.devices.items() if value is not original
        }
    elif unavailable == "claimed":
        original.claiming = True
    elif unavailable == "paired":
        portal.state.complete(original, "1" * 32, "synthetic-token")
    else:
        image = image.replace(activation, secret if unavailable == "session-secret" else "invalid")
    result = portal.client.get(image)
    assert result.status_code == 400 and result.headers["content-type"] == "application/json"
    assert result.headers["cache-control"] == "no-store, private"
    assert not portal.fake.requests and device.token is None


def test_qr_cannot_retarget_an_existing_stage_and_other_tv_stays_pending(portal):
    _, _, _, first_url = rendered_qr(portal)
    first = portal.state.pending(activation=parse_qs(urlsplit(first_url).query)["activation"][0])
    _, _, _, second_url = rendered_qr(portal)
    second = portal.state.pending(activation=parse_qs(urlsplit(second_url).query)["activation"][0])
    fields = hidden_fields(portal.client.get(first_url))
    result = portal.client.post(
        "/pair",
        data={
            **fields,
            "activation": second.activation,
            "code": second.code,
            "username": "viewer",
            "password": "test-password",
        },
        headers={"Origin": portal.settings.public_url},
    )
    assert "TV paired" in result.text and first.token and second.token is None
    replay = portal.client.get(first_url)
    assert replay.status_code == 400 and 'name="password"' not in replay.text


def test_qr_rate_limit_and_manual_fallback(portal):
    page, image, _, _ = rendered_qr(portal)
    assert portal.settings.public_url + "/pair" in page["items"][0]["title"]
    assert "TV code:" in page["items"][1]["title"]
    assert "Create new code" == page["items"][3]["title"]
    for _ in range(29):
        assert portal.client.get(image).status_code == 200
    assert portal.client.get(image).status_code == 429
    assert not portal.fake.requests


def test_public_non_secret_visual_qr_and_long_operator_origin_decode():
    # Pure encoder regression: long deployment origins still fit a standard QR.
    value = "https://" + "x" * 63 + ".example.test/pair?activation=" + "a" * 43
    decoded = zxingcpp.read_barcode(Image.open(BytesIO(activation_png(value))))
    assert decoded is not None and bool(decoded.text == value)
