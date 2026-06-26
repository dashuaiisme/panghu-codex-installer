from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_H


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_URL = "https://aitokenapi.cc/deployer/download"
QR_OUTPUT = ROOT / "assets" / "deployer-download-qr.png"
CARD_OUTPUT = ROOT / "docs" / "胖虎AI下载二维码.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msyhbd.ttc") if bold else Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    text_font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    width = draw.textbbox((0, 0), text, font=text_font)[2]
    draw.text((xy[0] - width // 2, xy[1]), text, font=text_font, fill=fill)


def make_qr() -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=18,
        border=4,
    )
    qr.add_data(DOWNLOAD_URL)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#101828", back_color="white").convert("RGB")

    logo_path = ROOT / "assets" / "panghu-avatar-64.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA").resize((86, 86), Image.LANCZOS)
        x = (image.width - logo.width) // 2
        y = (image.height - logo.height) // 2
        badge = Image.new("RGBA", (118, 118), (255, 255, 255, 255))
        badge_draw = ImageDraw.Draw(badge)
        badge_draw.rounded_rectangle((0, 0, 117, 117), radius=28, fill=(255, 255, 255, 255))
        badge.paste(logo, ((badge.width - logo.width) // 2, (badge.height - logo.height) // 2), logo)
        image.paste(badge.convert("RGB"), (x - 16, y - 16))

    return image


def make_card(qr_image: Image.Image) -> Image.Image:
    width, height = 900, 1180
    canvas = Image.new("RGB", (width, height), "#F7FAFC")
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((42, 42, width - 42, height - 42), radius=36, fill="#FFFFFF")
    draw.rounded_rectangle((42, 42, width - 42, 236), radius=36, fill="#111827")
    draw.rectangle((42, 160, width - 42, 236), fill="#111827")

    centered_text(draw, (width // 2, 82), "胖虎AI", font(44, bold=True), "#FFFFFF")
    centered_text(draw, (width // 2, 152), "扫码选择 Windows / Mac 客户版", font(30), "#D1FAE5")

    qr_size = 620
    qr_resized = qr_image.resize((qr_size, qr_size), Image.Resampling.NEAREST)
    qr_x = (width - qr_size) // 2
    qr_y = 300
    draw.rounded_rectangle((qr_x - 28, qr_y - 28, qr_x + qr_size + 28, qr_y + qr_size + 28), radius=30, fill="#F3F4F6")
    draw.rounded_rectangle((qr_x - 10, qr_y - 10, qr_x + qr_size + 10, qr_y + qr_size + 10), radius=22, fill="#FFFFFF")
    canvas.paste(qr_resized, (qr_x, qr_y))

    centered_text(draw, (width // 2, 988), "打开后按自己的电脑系统选择版本", font(32, bold=True), "#111827")
    centered_text(draw, (width // 2, 1040), "Windows 和 Mac 都从这个入口下载", font(28), "#475467")
    centered_text(draw, (width // 2, 1092), "无需复制链接，直接扫码进入下载页", font(26), "#047857")

    return canvas


def main() -> None:
    QR_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    CARD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    qr_image = make_qr()
    qr_image.save(QR_OUTPUT)
    make_card(qr_image).save(CARD_OUTPUT)

    print(QR_OUTPUT)
    print(CARD_OUTPUT)


if __name__ == "__main__":
    main()
