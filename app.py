import io
import os
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import google.generativeai as genai
import json

st.set_page_config(page_title="Togomonカードメーカー", page_icon="🎴", layout="wide")

st.title("🎴 Togomonカードメーカー")
st.caption("写真を1枚アップロードするだけで、AIが本格Togomonカードを自動作成します！")

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

# Secretsからの自動読み込み対応
api_key = st.secrets.get("GEMINI_API_KEY", "")

uploaded_file = st.file_uploader("📷 写真をアップロードしてください", type=["jpg", "jpeg", "png"])

def analyze_image_with_gemini(pil_image, api_key_val):
    default_data = {
        "card_name": "めがねボーイ",
        "hp": "120",
        "type": "超",
        "skill_name": "へんしんビーム",
        "damage": "60",
        "desc": "ふしぎな めがねで みんなを びっくり させるぞ！",
        "eye_center": [500, 500]  # [y, x] 0-1000表記
    }

    if not api_key_val:
        return default_data

    try:
        genai.configure(api_key=api_key_val)
        
        prompt = """
        添付された画像を分析して、Togomonのカード風データを作成してください。
        また、画像内の主要な人物の「両目の中心位置（目元）」を 0〜1000 の数値座標 [y, x] で指定してください。

        以下のJSON形式のみを出力してください。

        {
          "card_name": "写真の特徴を表した名前",
          "hp": "120",
          "type": "超",
          "skill_name": "ワザ名",
          "damage": "60",
          "desc": "2行程度の説明文",
          "eye_center": [y, x]
        }

        ※ typeは (草 / 炎 / 水 / 雷 / 超 / 闘) の中から1つ選んでください。
        ※ eye_center は [上からの高さ, 左からの位置] を0〜1000の数値で表した座標です。見つからない場合は [500, 500] としてください。
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

def crop_eyes_centered(img, eye_center, target_w, target_h):
    """目の中心位置を基準にしてクロップする"""
    u_w, u_h = img.size
    
    eye_y, eye_x = eye_center
    
    # 目の座標を元の画像のピクセル位置に変換
    pixel_x = (eye_x / 1000.0) * u_w
    pixel_y = (eye_y / 1000.0) * u_h

    # 枠に収めるための拡大・縮小倍率
    scale = max(target_w / u_w, target_h / u_h)
    
    new_w = int(u_w * scale)
    new_h = int(u_h * scale)
    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # 拡大後の目の座標
    scaled_eye_x = pixel_x * scale
    scaled_eye_y = pixel_y * scale
    
    # 目の位置がカードの枠の「上から約35%」の位置に来るように切り抜く（収まりが良い位置）
    crop_x1 = scaled_eye_x - (target_w / 2.0)
    crop_y1 = scaled_eye_y - (target_h * 0.35)
    
    # 画像からはみ出さないよう限界調整
    crop_x1 = max(0, min(crop_x1, new_w - target_w))
    crop_y1 = max(0, min(crop_y1, new_h - target_h))
    
    crop_x2 = crop_x1 + target_w
    crop_y2 = crop_y1 + target_h
    
    return resized_img.crop((int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)))

def generate_card(user_img, card_data):
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

    # 1. 外枠
    draw.rectangle([(0, 0), (card_w, card_h)], fill="#F1C40F")
    draw.rectangle([(18, 18), (card_w-18, card_h-18)], fill="#D4AC0D")
    
    # 2. カード本体ベース背景
    draw.rectangle([(26, 26), (card_w-26, card_h-26)], fill=style["card_bg"])

    # 3. ヘッダー帯
    draw.rectangle([(40, 42), (card_w-40, 115)], fill=style["bg"])
    
    font_name = get_japanese_font(34)
    font_hp_label = get_japanese_font(20)
    font_hp_val = get_japanese_font(38)
    font_skill = get_japanese_font(30)
    font_dmg = get_japanese_font(36)
    font_desc = get_japanese_font(22)
    font_footer = get_japanese_font(18)

    draw.text((55, 56), str(card_data.get("card_name", "めがねボーイ")), fill="#FFFFFF", font=font_name)
    
    draw.text((490, 68), "HP", fill="#FFEB3B", font=font_hp_label)
    draw.text((525, 52), str(card_data.get("hp", "120")), fill="#FFFFFF", font=font_hp_val)
    
    draw.ellipse([(645, 52), (695, 102)], fill=style["accent"], outline="#FFFFFF", width=2)
    draw.text((656, 58), style["symbol"], fill="#FFFFFF", font=font_hp_label)

    # 4. メイン写真領域（目を基準にクロップ）
    user_img_fixed = ImageOps.exif_transpose(user_img)
    
    img_x1, img_y1, img_x2, img_y2 = 45, 130, card_w-45, 570
    img_w, img_h = img_x2 - img_x1, img_y2 - img_y1
    
    draw.rectangle([(img_x1-5, img_y1-5), (img_x2+5, img_y2+5)], fill="#B7950B")
    draw.rectangle([(img_x1, img_y1), (img_x2, img_y2)], fill="#000000")

    eye_center = card_data.get("eye_center", [500, 500])
    cropped_img = crop_eyes_centered(user_img_fixed, eye_center, img_w, img_h)

    card.paste(cropped_img, (img_x1, img_y1))

    # 5. サブ情報バー
    draw.rectangle([(50, 580), (card_w-50, 615)], fill="#FFFFFF", outline="#B7950B", width=2)
    draw.text((65, 586), "たねTogomon  /  全国図鑑 NO.001  /  たかさ: 1.0m  おもさ: 15.0kg", fill="#555555", font=font_footer)

    # 6. ワザ表示エリア
    draw.rectangle([(45, 630), (card_w-45, 890)], fill="#FFFFFF", outline=style["bg"], width=3)

    draw.ellipse([(65, 660), (105, 700)], fill=style["bg"])
    draw.ellipse([(115, 660), (155, 700)], fill=style["accent"])
    
    draw.text((175, 662), str(card_data.get("skill_name", "へんしんビーム")), fill="#111111", font=font_skill)
    draw.text((600, 658), str(card_data.get("damage", "60")), fill="#111111", font=font_dmg)

    desc_text = str(card_data.get("desc", "")).replace("\\n", "\n")
    lines = desc_text.split("\n")
    y_off = 730
    for l in lines:
        draw.text((70, y_off), l, fill="#333333", font=font_desc)
        y_off += 38

    # 7. フッター
    draw.rectangle([(45, 900), (card_w-45, 990)], fill="#F4F4F4", outline="#CCCCCC", width=2)

    draw.text((65, 920), "弱点 : 悪 ×2", fill="#333333", font=font_footer)
    draw.text((270, 920), "抵抗力 : -30", fill="#333333", font=font_footer)
    draw.text((480, 920), "にげる : ●●", fill="#333333", font=font_footer)

    draw.text((65, 955), "Illus. Togomon Maker", fill="#777777", font=font_footer)
    draw.text((580, 955), "001/050 RR ★", fill="#111111", font=font_footer)

    return card.convert("RGB")

col1, col2 = st.columns([1, 1])

if uploaded_file is not None:
    # メッセージを変更（「AIが顔の位置を検出して」を削除）
    with st.spinner("🎴 Togomonカードを作成中..."):
        user_img = Image.open(uploaded_file).convert("RGB")
        
        card_data = analyze_image_with_gemini(user_img, api_key)
        card_img = generate_card(user_img, card_data)

        with col1:
            st.image(card_img, use_container_width=True)

        buf = io.BytesIO()
        card_img.save(buf, format="PNG")
        
        with col2:
            st.download_button(
                label="🎴 カード画像を保存する (PNG)",
                data=buf.getvalue(),
                file_name=f"{card_data.get('card_name', 'togomon')}_card.png",
                mime="image/png"
            )
