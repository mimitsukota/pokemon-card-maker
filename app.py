import io
import os
import json
import random
import textwrap
import numpy as np
import cv2
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import google.generativeai as genai

# ページ設定
st.set_page_config(page_title="TogoMoN GO カードメーカー", page_icon="🎴", layout="wide")

# 作成したロゴ画像の表示
if os.path.exists("logo.png"):
    st.image("logo.png", width=350)
else:
    st.title("🎴 TogoMoN GO")

st.caption("写真を1枚アップロードするだけで、AIが本格TogoMoNカードを自動作成します！")

# 日本語フォント設定
def get_japanese_font(size):
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "C:\\Windows\\Fonts\\meiryo.ttc"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
    return ImageFont.load_default()

api_key = st.secrets.get("GEMINI_API_KEY", "")

uploaded_file = st.file_uploader("📷 写真をアップロードしてください", type=["jpg", "jpeg", "png"])

def detect_face_center(pil_img):
    try:
        cv_img = np.array(pil_img)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
        
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) > 0:
            largest_face = max(faces, key=lambda b: b[2] * b[3])
            x, y, w, h = largest_face
            eye_y = y + (h * 0.35)
            return eye_y / float(pil_img.height)
    except Exception:
        pass
        
    return 0.4

def analyze_image_with_gemini(pil_image, api_key_val):
    default_data = {
        "card_name": "おもしろモンスター",
        "hp": "120",
        "type": "超",
        "skill_name": "へんしんアタック",
        "damage": "60",
        "desc": "いつものにこやかな 表情の うらには\nすさまじい 集中力と 技が ひめられている。\nとくいわざの くりだしは とても すばやい。\nであうと みんなが 笑顔に なってしまうぞ！",
        "dex_no": "001",
        "height": "1.0m",
        "weight": "15.0kg",
        "weakness": "悪 ×2",
        "resistance": "-30",
        "escape": "●●",
        "card_no": "001/050"
    }

    if not api_key_val:
        return default_data

    try:
        genai.configure(api_key=api_key_val)
        
        prompt = """
        添付された画像を深く分析して、この写真の人物や対象の特徴・性格・ステータスを盛り込んだTogoMoNカード用テキストを作成してください。
        以下のJSON形式のみを出力してください。

        {
          "card_name": "写真の特徴を表した面白い名前（8文字以内）",
          "hp": "100〜200の数値",
          "type": "草/炎/水/雷/超/闘 のどれかひとつ",
          "skill_name": "写真のポーズや雰囲気に関連したワザ名（8文字以内）",
          "damage": "30〜120の数値",
          "desc": "写真の特徴や得意技の凄さを表す解説文（改行コード\\nを使ってちょうど4行。1行あたり18〜22文字程度。）",
          "dex_no": "001〜150の3桁数値（例: 025）",
          "height": "写真の印象に合わせた高さ（例: 0.5m や 1.6m）",
          "weight": "写真の印象に合わせた重さ（例: 4.2kg や 55.0kg）",
          "weakness": "属性に合わせた弱点（例: 炎 ×2 や 水 ×2 や 悪 ×2）",
          "resistance": "抵抗力（例: -20 や -30 や なし）",
          "escape": "にげるエネルギー（例: ● や ●● や ●●●）",
          "card_no": "図鑑番号に合わせたカード番号（例: 025/050）"
        }
        """
        
        model_names = ['gemini-2.0-flash', 'gemini-1.5-flash', 'models/gemini-1.5-flash']
        response = None
        
        for m_name in model_names:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content([prompt, pil_image])
                if response and response.text:
                    break
            except:
                continue

        if response and response.text:
            text = response.text.strip()
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = text[start_idx:end_idx+1]
                parsed = json.loads(json_str)
                for k in default_data.keys():
                    if k in parsed:
                        default_data[k] = parsed[k]

    except Exception:
        pass
        
    return default_data

def crop_image(img, target_w, target_h, base_y_ratio, offset_pct):
    u_w, u_h = img.size
    
    scale = max(target_w / float(u_w), target_h / float(u_h))
    new_w = int(u_w * scale)
    new_h = int(u_h * scale)
    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    adjusted_ratio = base_y_ratio + (offset_pct / 100.0)
    adjusted_ratio = max(0.0, min(1.0, adjusted_ratio))
    
    center_y = new_h * adjusted_ratio
    
    crop_x1 = (new_w - target_w) / 2.0
    crop_y1 = center_y - (target_h / 2.0)
    
    crop_x1 = max(0, min(crop_x1, new_w - target_w))
    crop_y1 = max(0, min(crop_y1, new_h - target_h))
    
    crop_x2 = crop_x1 + target_w
    crop_y2 = crop_y1 + target_h
    
    return resized_img.crop((int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)))

def draw_star(draw, cx, cy, size, fill_color):
    points = []
    for i in range(10):
        r = size if i % 2 == 0 else size / 2.0
        angle = i * np.pi / 5 - np.pi / 2
        x = cx + r * np.cos(angle)
        y = cy + r * np.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=fill_color)

def generate_card(user_img, card_data, base_y_ratio, y_offset):
    card_w, card_h = 750, 1050
    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)

    type_styles = {
        "草": {"bg": "#2E7D32", "card_bg": "#E8F5E9", "accent": "#81C784", "symbol": "草"},
        "炎": {"bg": "#C62828", "card_bg": "#FFEBEE", "accent": "#E57373", "symbol": "炎"},
        "水": {"bg": "#1565C0", "card_bg": "#E3F2FD", "accent": "#64B5F6", "symbol": "水"},
        "雷": {"bg": "#F57F17", "card_bg": "#FFFDE7", "accent": "#FFF176", "symbol": "雷"},
        "超": {"bg": "#6A1B9A", "card_bg": "#F3E5F5", "accent": "#BA68C8", "symbol": "超"},
        "闘": {"bg": "#D84315", "card_bg": "#FBE9E7", "accent": "#FF8A65", "symbol": "闘"},
    }

    t_key = "超"
    for k in type_styles.keys():
        if k in str(card_data.get("type", "")):
            t_key = k
            break
    style = type_styles[t_key]

    # 1. ハデハデ外枠
    border_margin = 48
    
    draw.rectangle([(0, 0), (card_w, card_h)], fill="#FFD700")
    draw.rectangle([(8, 8), (card_w-8, card_h-8)], fill="#FFF066")
    draw.rectangle([(18, 18), (card_w-18, card_h-18)], fill="#DAA520")
    draw.rectangle([(28, 28), (card_w-28, card_h-28)], fill="#FF8C00")
    draw.rectangle([(38, 38), (card_w-38, card_h-38)], fill="#B8860B")

    random.seed(42)
    star_colors = ["#FFFFFF", "#FFFF99", "#FFE066", "#FFD700", "#FF69B4", "#00FFFF"]
    for _ in range(500):
        sx = random.randint(0, card_w)
        sy = random.randint(0, card_h)
        if sx < border_margin or sx > card_w - border_margin or sy < border_margin or sy > card_h - border_margin:
            ssize = random.randint(4, 12)
            scolor = random.choice(star_colors)
            draw_star(draw, sx, sy, ssize, scolor)

    # 2. 内側カード本体
    draw.rectangle([(border_margin, border_margin), (card_w-border_margin, card_h-border_margin)], fill=style["card_bg"])

    # 3. ヘッダー帯
    header_x1, header_y1 = 58, 60
    header_x2, header_y2 = card_w - 58, 125
    draw.rectangle([(header_x1, header_y1), (header_x2, header_y2)], fill=style["bg"])
    
    font_name = get_japanese_font(30)
    font_hp_label = get_japanese_font(18)
    font_hp_val = get_japanese_font(32)
    font_skill = get_japanese_font(26)
    font_dmg = get_japanese_font(32)
    font_desc = get_japanese_font(18)
    font_footer = get_japanese_font(16)

    c_name = str(card_data.get("card_name", "おもしろモンスター"))
    if len(c_name) > 10:
        c_name = c_name[:9] + "…"
    draw.text((70, 75), c_name, fill="#FFFFFF", font=font_name)
    
    draw.text((455, 82), "HP", fill="#FFEB3B", font=font_hp_label)
    draw.text((485, 70), str(card_data.get("hp", "120")), fill="#FFFFFF", font=font_hp_val)
    
    draw.ellipse([(625-72, 68), (670-72, 113)], fill=style["accent"], outline="#FFFFFF", width=2)
    draw.text((634-72, 75), style["symbol"], fill="#FFFFFF", font=font_hp_label)

    # 4. メイン写真領域
    user_img_fixed = ImageOps.exif_transpose(user_img)
    
    img_x1, img_y1, img_x2, img_y2 = 60, 138, card_w-60, 550
    img_w, img_h = img_x2 - img_x1, img_y2 - img_y1
    
    draw.rectangle([(img_x1-4, img_y1-4), (img_x2+4, img_y2+4)], fill="#B7950B")
    draw.rectangle([(img_x1, img_y1), (img_x2, img_y2)], fill="#000000")

    cropped_img = crop_image(user_img_fixed, img_w, img_h, base_y_ratio, y_offset)
    card.paste(cropped_img, (img_x1, img_y1))

    # 5. サブ情報バー（可変対応）
    dex_no = card_data.get("dex_no", "001")
    height = card_data.get("height", "1.0m")
    weight = card_data.get("weight", "15.0kg")
    sub_info_text = f"たねTogoMoN  /  全国図鑑 NO.{dex_no}  /  たかさ: {height}  おもさ: {weight}"
    
    draw.rectangle([(62, 560), (card_w-62, 592)], fill="#FFFFFF", outline="#B7950B", width=2)
    draw.text((72, 567), sub_info_text, fill="#555555", font=font_footer)

    # 6. ワザ・説明エリア
    draw.rectangle([(60, 605), (card_w-60, 882)], fill="#FFFFFF", outline=style["bg"], width=3)

    # ワザシンボル
    draw.ellipse([(75, 620), (110, 655)], fill=style["bg"])
    draw.ellipse([(118, 620), (153, 655)], fill=style["accent"])
    
    s_name = str(card_data.get("skill_name", "へんしんアタック"))
    if len(s_name) > 10:
        s_name = s_name[:9] + "…"
    draw.text((165, 622), s_name, fill="#111111", font=font_skill)
    draw.text((card_w - 120, 618), str(card_data.get("damage", "60")), fill="#111111", font=font_dmg)

    # 区切り線
    draw.line([(75, 670), (card_w-75, 670)], fill="#EEEEEE", width=2)

    # 4行説明文
    raw_desc = str(card_data.get("desc", "")).replace("\\n", "\n")
    lines = []
    for paragraph in raw_desc.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=24))
    
    y_off = 685
    for l in lines[:4]:
        draw.text((75, y_off), l, fill="#333333", font=font_desc)
        y_off += 30

    # 7. フッター（可変対応）
    weakness = card_data.get("weakness", "悪 ×2")
    resistance = card_data.get("resistance", "-30")
    escape = card_data.get("escape", "●●")
    card_no = card_data.get("card_no", "001/050")

    draw.rectangle([(60, 890), (card_w-60, 975)], fill="#F4F4F4", outline="#CCCCCC", width=2)

    draw.text((75, 905), f"弱点 : {weakness}", fill="#333333", font=font_footer)
    draw.text((250, 905), f"抵抗力 : {resistance}", fill="#333333", font=font_footer)
    draw.text((430, 905), f"にげる : {escape}", fill="#333333", font=font_footer)

    draw.text((75, 940), "Illus. TogoMoN Maker", fill="#777777", font=font_footer)
    draw.text((500, 940), f"{card_no} RR ★", fill="#111111", font=font_footer)

    return card.convert("RGB")

col1, col2 = st.columns([1, 1])

if uploaded_file is not None:
    # ファイル識別用のユニークキーを作成（バイトデータから判定）
    file_bytes = uploaded_file.getvalue()
    file_id = f"{uploaded_file.name}_{len(file_bytes)}"
    
    user_img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    user_img_fixed = ImageOps.exif_transpose(user_img)

    # ファイルが変わったかどうか判定
    if "last_file_id" not in st.session_state or st.session_state["last_file_id"] != file_id:
        st.session_state["last_file_id"] = file_id
        st.session_state["base_y_ratio"] = detect_face_center(user_img_fixed)
        
        with st.spinner("カードデータを生成中..."):
            st.session_state["card_data"] = analyze_image_with_gemini(user_img_fixed, api_key)

    base_y_ratio = st.session_state.get("base_y_ratio", 0.4)
    card_data = st.session_state.get("card_data", {})

    with col2:
        st.subheader("⚙️ 写真の位置調整")
        y_offset = st.slider("↕️ 写真の位置を上下に微調整", min_value=-100, max_value=100, value=0, help="顔・目が中央に来るようにスライダーを動かしてください")

    card_img = generate_card(user_img_fixed, card_data, base_y_ratio, y_offset)

    with col1:
        st.image(card_img, use_container_width=True)

    buf = io.BytesIO()
    card_img.save(buf, format="PNG")
    
    with col2:
        st.write("---")
        st.download_button(
            label="🎴 カード画像を保存する (PNG)",
            data=buf.getvalue(),
            file_name=f"{card_data.get('card_name', 'togomon')}_card.png",
            mime="image/png"
        )
