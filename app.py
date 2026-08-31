
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import io
import math

st.set_page_config(page_title="オリジナルカードメーカー", page_icon="✨", layout="centered")

# ---------- 文字フォント ----------
def get_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

# ---------- キラキラ背景 ----------
def make_holo_background(w, h):
    img = Image.new("RGB", (w, h), (245, 170, 70))
    px = img.load()

    for y in range(h):
        for x in range(w):
            # 金色ベース + 虹色っぽい変化
            wave = math.sin(x / 23) + math.sin(y / 31) + math.sin((x+y) / 47)
            r = int(215 + 30 * (wave + 3) / 6)
            g = int(125 + 80 * (wave + 3) / 6)
            b = int(45 + 95 * (wave + 3) / 6)
            px[x, y] = (min(255,r), min(255,g), min(255,b))

    draw = ImageDraw.Draw(img, "RGBA")
    random.seed(12)
    for _ in range(220):
        x = random.randrange(w)
        y = random.randrange(h)
        r = random.choice([1, 2, 3, 5])
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(255,255,255,random.randrange(35,120)))

    # 星
    for _ in range(45):
        x = random.randrange(w)
        y = random.randrange(h)
        s = random.choice([5, 7, 10])
        draw.polygon([(x,y-s),(x+2,y-2),(x+s,y),(x+2,y+2),
                      (x,y+s),(x-2,y+2),(x-s,y),(x-2,y-2)],
                     fill=(255,245,170,180))
    return img

def fit_crop(image, size):
    image = image.convert("RGB")
    iw, ih = image.size
    tw, th = size
    scale = max(tw/iw, th/ih)
    nw, nh = int(iw*scale), int(ih*scale)
    image = image.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw-tw)//2
    top = (nh-th)//2
    return image.crop((left, top, left+tw, top+th))

def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0,0,size[0]-1,size[1]-1), radius=radius, fill=255)
    return mask

def draw_wrapped(draw, text, xy, font, max_width, fill=(20,20,20), line_gap=6):
    words = list(text)
    lines = []
    current = ""
    for ch in words:
        test = current + ch
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    x, y = xy
    for line in lines:
        draw.text((x,y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y

def make_card(photo, name, hp, skill, attack, description, level):
    W, H = 900, 1260
    card = make_holo_background(W, H)
    draw = ImageDraw.Draw(card, "RGBA")

    # 外枠
    draw.rounded_rectangle((10,10,W-10,H-10), radius=45, fill=(255,220,130,210), outline=(90,60,20,255), width=8)
    draw.rounded_rectangle((28,28,W-28,H-28), radius=35, fill=(226,105,60,255), outline=(255,235,150,255), width=5)

    # ヘッダー
    draw.rectangle((55,55,W-55,170), fill=(245,190,90,255))
    draw.text((75,72), "オリジナルカード", font=get_font(30, True), fill=(70,40,20))
    draw.text((75,112), name, font=get_font(58, True), fill=(25,25,25))
    draw.text((W-300,118), f"LV.{level}", font=get_font(30, True), fill=(30,30,30))
    draw.text((W-165,108), f"HP{hp}", font=get_font(40, True), fill=(30,30,30))

    # 写真
    px, py, pw, ph = 70, 195, 760, 515
    draw.rounded_rectangle((px-12,py-12,px+pw+12,py+ph+12), radius=28, fill=(180,125,35,255))
    p = fit_crop(photo, (pw, ph))
    mask = rounded_mask((pw,ph), 20)
    card.paste(p, (px,py), mask)
    draw = ImageDraw.Draw(card, "RGBA")
    draw.rounded_rectangle((px,py,px+pw,py+ph), radius=20, outline=(255,235,160,255), width=8)

    # 写真下の説明
    draw.rounded_rectangle((90,735,W-90,795), radius=18, fill=(246,204,110,255), outline=(130,80,20,255), width=3)
    draw.text((120,748), "このカードは だいじな家族の たからもの！", font=get_font(25, True), fill=(40,30,20))

    # 特殊能力
    draw.text((80,825), "【特殊能力】", font=get_font(34, True), fill=(25,105,190))
    draw.text((285,820), skill, font=get_font(42, True), fill=(25,70,150))
    draw.line((80,875,W-80,875), fill=(60,35,20), width=3)

    # 技
    draw.text((85,900), "✨", font=get_font(38), fill=(20,20,20))
    draw.text((145,900), "スペシャルアタック", font=get_font(38, True), fill=(20,20,20))
    draw.text((W-180,895), str(attack), font=get_font(48, True), fill=(20,20,20))
    draw.line((80,965,W-80,965), fill=(60,35,20), width=3)

    # 説明
    draw.text((90,990), "このカードのせつめい", font=get_font(28, True), fill=(80,45,20))
    draw_wrapped(draw, description, (90,1030), get_font(27), 720, fill=(30,30,30), line_gap=5)

    # 下部
    draw.line((80,1150,W-80,1150), fill=(60,35,20), width=3)
    draw.text((85,1170), "SML 001/032", font=get_font(23, True), fill=(30,30,30))
    draw.text((W-310,1170), "Illus. Family Card", font=get_font(23), fill=(30,30,30))

    return card

st.title("✨ オリジナルカードメーカー")
st.write("写真を1枚選ぶだけで、キラキラのオリジナルカードを作れます！")

photo_file = st.file_uploader("📷 写真をアップロード", type=["jpg", "jpeg", "png", "webp"])

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("カードの名前", "えがおちゃん")
    hp = st.number_input("HP", min_value=10, max_value=999, value=120, step=10)
    level = st.number_input("LV.", min_value=1, max_value=999, value=76)

with col2:
    skill = st.text_input("特殊能力", "えがおパワー")
    attack = st.number_input("攻撃力", min_value=10, max_value=999, value=100, step=10)

description = st.text_area(
    "カードのせつめい",
    "いつもえがおで、みんなをしあわせにする。とってもたいせつな家族のたからもの！"
)

if st.button("✨ カードを作る！", use_container_width=True):
    if not photo_file:
        st.warning("まず写真を1枚アップロードしてください。")
    else:
        photo = Image.open(photo_file)
        card = make_card(photo, name, hp, skill, attack, description, level)

        st.session_state["card"] = card

if "card" in st.session_state:
    st.subheader("🎉 完成！")
    card = st.session_state["card"]
    st.image(card, use_container_width=True)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    st.download_button(
        "📥 カード画像を保存する",
        data=buf.getvalue(),
        file_name="original_card.png",
        mime="image/png",
        use_container_width=True
    )

st.caption("※オリジナルデザインのカードメーカーです。既存のカード商品そのものを再現するものではありません。")
