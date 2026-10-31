"""Local QR encoding. No network, filesystem, shared service or cached bearer data."""

from io import BytesIO

import segno


def activation_png(activation_url: str) -> bytes:
    output = BytesIO()
    # Full QR (not Micro QR), black/white, four-module quiet zone and integer pixels.
    segno.make_qr(activation_url, error="m").save(output, kind="png", scale=8, border=4)
    return output.getvalue()
