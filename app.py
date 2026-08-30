import io
import os
import json
import random
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
        "desc": "カメラを つけると げんきいっぱいに あらわれる ふしぎな モンスター！"
    }

    if not api_key_val:
        return default_data

    try:
        genai.configure(api_key=api_key_val)
        
        prompt = """
        添付された画像を深く分析して、この写真にぴったりのTogoMoNカード用テキストを作成してください。
        以下のJSON形式のみを出力してください。

        {
          "card_name": "写真に写っている人物や物・表情の特徴を表した面白い名前（10文字以内）",
          "hp": "100〜200の数値",
          "type": "草/炎/水/雷/超/闘 のどれかひとつ",
          "skill_name": "写真のポーズや雰囲気に関連したワザ名（10文字以内）",
          "damage": "30〜120の数値",
          "desc": "写真の状況やキャラクター性を表す2行程度の面白い説明文"
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

    # 1. 太枠・ハデハデ金ピカ外枠
    border_margin = 52
    
    draw.rectangle([(0, 0), (card_w, card_h)], fill="#FFD700")
    draw.rectangle([(10, 10), (card_w-10, card_h-10)], fill="#FFF066")
    draw.rectangle([(20, 20), (card_w-20, card_h-20)], fill="#DAA520")
    draw.rectangle([(32, 32), (card_w-32, card_h-32)], fill="#FF8C00")
    draw.rectangle([(42, 42), (card_w-42, card_h-42)], fill="#B8860B")

    random.seed(42)
    star_colors = ["#FFFFFF", "#FFFF99", "#FFE066", "#FFD700", "#FF69B4", "#00FFFF"]
    for _ in range(600):
        sx = random.randint(0, card_w)
        sy = random.randint(0, card_h)
        if sx < border_margin or sx > card_w - border_margin or sy < border_margin or sy > card_h - border_margin:
            ssize = random.randint(4, 14)
            scolor = random.choice(star_colors)
            draw_star(draw, sx, sy, ssize, scolor)

    # 2. 内側カード本体
    draw.rectangle([(border_margin, border_margin), (card_w-border_margin, card_h-border_margin)], fill=style["card_bg"])

    # 3. ヘッダー帯
    draw.rectangle([(62, 65), (card_w-62, 130)], fill=style["bg"])
    
    font_name = get_japanese_font(34)
    font_hp_label = get_japanese_font(20)
    font_hp_val = get_japanese_font(38)
    font_skill = get_japanese_font(30)
    font_dmg = get_japanese_font(36)
    font_desc = get_japanese_font(22)
    font_footer = get_japanese_font(18)

    draw.text((75, 76), str(card_data.get("card_name", "おもしろモンスター")), fill="#FFFFFF", font=font_name)
    
    draw.text((475, 83), "HP", fill="#FFEB3B", font=font_hp_label)
    draw.text((510, 67), str(card_data.get("hp", "120")), fill="#FFFFFF", font=font_hp_val)
    
    draw.ellipse([(625, 67), (675, 117)], fill=style["accent"], outline="#FFFFFF", width=2)
    draw.text((636, 73), style["symbol"], fill="#FFFFFF", font=font_hp_label)

    # 4. メイン写真領域
    user_img_fixed = ImageOps.exif_transpose(user_img)
    
    img_x1, img_y1, img_x2, img_y2 = 65, 145, card_w-65, 570
    img_w, img_h = img_x2 - img_x1, img_y2 - img_y1
    
    draw.rectangle([(img_x1-5, img_y1-5), (img_x2+5, img_y2+5)], fill="#B7950B")
    draw.rectangle([(img_x1, img_y1), (img_x2, img_y2)], fill="#000000")

    cropped_img = crop_image(user_img_fixed, img_w, img_h, base_y_ratio, y_offset)

    card.paste(cropped_img, (img_x1, img_y1))

    # 5. サブ情報バー
    draw.rectangle([(68, 580), (card_w-68, 615)], fill="#FFFFFF", outline="#B7950B", width=2)
    draw.text((80, 586), "たねTogoMoN  /  全国図鑑 NO.001  /  たかさ: 1.0m  おもさ: 15.0kg", fill="#555555", font=font_footer)

    # 6. ワザ表示エリア
    draw.rectangle([(65, 630), (card_w-65, 880)], fill="#FFFFFF", outline=style["bg"], width=3)

    draw.ellipse([(85, 655), (125, 695)], fill=style["bg"])
    draw.ellipse([(135, 655), (175, 695)], fill=style["accent"])
    
    draw.text((195, 657), str(card_data.get("skill_name", "へんしんアタック")), fill="#111111", font=font_skill)
    draw.text((580, 653), str(card_data.get("damage", "60")), fill="#111111", font=font_dmg)

    desc_text = str(card_data.get("desc", "")).replace("\\n", "\n")
    lines = desc_text.split("\n")
    y_off = 725
    for l in lines:
        draw.text((90, y_off), l, fill="#333333", font=font_desc)
        y_off += 38

    # 7. フッター
    draw.rectangle([(65, 890), (card_w-65, 975)], fill="#F4F4F4", outline="#CCCCCC", width=2)

    draw.text((80, 905), "弱点 : 悪 ×2", fill="#333333", font=font_footer)
    draw.text((270, 905), "抵抗力 : -30", fill="#333333", font=font_footer)
    draw.text((460, 905), "にげる : ●●", fill="#333333", font=font_footer)

    draw.text((80, 940), "Illus. TogoMoN Maker", fill="#777777", font=font_footer)
    draw.text((560, 940), "001/050 RR ★", fill="#111111", font=font_footer)

    return card.convert("RGB")

col1, col2 = st.columns([1, 1])

if uploaded_file is not None:
    # 画像ファイル自体が変わったことを識別するためのキー
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    
    user_img = Image.open(uploaded_file).convert("RGB")
    user_img_fixed = ImageOps.exif_transpose(user_img)

    # 新しい画像がアップロードされた場合、AI解析を強制的に実行
    if "last_file_id" not in st.session_state or st.session_state["last_file_id"] != file_id:
        st.session_state["last_file_id"] = file_id
        st.session_state["base_y_ratio"] = detect_face_center(user_img_fixed)
        
        with st.spinner("🤖 AIが新しい写真を分析してカードデータを生成中..."):
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
