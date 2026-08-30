import io
import os
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import google.generativeai as genai

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
        "desc": "ふしぎな めがねで みんなを びっくり させるぞ！"
    }

    if not api_key_val:
        return default_data

    try:
        genai.configure(api_key=api_key_val)
        
        prompt = """
        添付された画像を分析して、Togomonのカード風データを作成してください。
        以下のフォーマットを厳密に守って日本語で出力してください。

        カード名: (写真の特徴を表した可愛い/かっこいい名前)
        HP: (80 〜 180 の数字のみ)
        タイプ: (草 / 炎 / 水 / 雷 / 超 / 闘 の中から1つ)
        ワザ名: (写真の状況や表情に合わせた面白いワザ名)
        ダメージ: (30 〜 120 の数字のみ)
        説明: (2行程度のワザの説明文。1行18文字以内)
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
            lines = response.text.strip().split("\n")
            for line in lines:
                if "カード名:" in line:
                    default_data["card_name"] = line.split("カード名:")[1].strip()
                elif "HP:" in line:
                    hp_val = line.split("HP:")[1].strip()
                    default_data["hp"] = ''.join(filter(str.isdigit, hp_val)) or "120"
                elif "タイプ:" in line:
                    default_data["type"] = line.split("タイプ:")[1].strip()
                elif "ワザ名:" in line:
                    default_data["skill_name"] = line.split("ワザ名:")[1].strip()
                elif "ダメージ:" in line:
                    dmg_val = line.split("ダメージ:")[1].strip()
                    default_data["damage"] = ''.join(filter(str.isdigit, dmg_val)) or "60"
                elif "説明:" in line:
                    default_data["desc"] = line.split("説明:")[1].strip()
                    
    except Exception:
        pass
        
    return default_data

def generate_card(user_img, card_data):
    # 高解像度キャンバス (750x1050)
    card_w, card_h = 750, 1050
    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)

    # タイプ別カラーテーマ
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
        if k in card_data["type"]:
            t_key = k
            break
    style = type_styles[t_key]

    # 1. イエロー／ゴールドの外枠
    draw.rectangle([(0, 0), (card_w, card_h)], fill="#F1C40F")
    draw.rectangle([(18, 18), (card_w-18, card_h-18)], fill="#D4AC0D")
    
    # 2. カード本体ベース背景
    draw.rectangle([(26, 26), (card_w-26, card_h-26)], fill=style["card_bg"])

    # 3. ヘッダー帯（名前＆HP）
    draw.rectangle([(40, 42), (card_w-40, 115)], fill=style["bg"])
    
    # フォント準備
    font_name = get_japanese_font(34)
    font_hp_label = get_japanese_font(20)
    font_hp_val = get_japanese_font(38)
    font_skill = get_japanese_font(30)
    font_dmg = get_japanese_font(36)
    font_desc = get_japanese_font(22)
    font_footer = get_japanese_font(18)

    # カード名
    draw.text((55, 56), card_data["card_name"], fill="#FFFFFF", font=font_name)
    
    # HP & タイプ
    draw.text((490, 68), "HP", fill="#FFEB3B", font=font_hp_label)
    draw.text((525, 52), card_data["hp"], fill="#FFFFFF", font=font_hp_val)
    
    # タイプアイコン風の丸マーク
    draw.ellipse([(645, 52), (695, 102)], fill=style["accent"], outline="#FFFFFF", width=2)
    draw.text((656, 58), style["symbol"], fill="#FFFFFF", font=font_hp_label)

    # 4. メイン写真領域
    user_img_fixed = ImageOps.exif_transpose(user_img)
    
    img_x1, img_y1, img_x2, img_y2 = 45, 130, card_w-45, 570
    img_w, img_h = img_x2 - img_x1, img_y2 - img_y1
    
    # 写真外枠
    draw.rectangle([(img_x1-5, img_y1-5), (img_x2+5, img_y2+5)], fill="#B7950B")
    draw.rectangle([(img_x1, img_y1), (img_x2, img_y2)], fill="#000000")

    # 写真のリサイズ & アスペクト比維持配置
    u_w, u_h = user_img_fixed.size
    ratio = max(img_w / u_w, img_h / u_h)
    new_w, new_h = int(u_w * ratio), int(u_h * ratio)
    resized_img = user_img_fixed.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 中央切り抜き
    crop_x = (new_w - img_w) // 2
    crop_y = (new_h - img_h) // 2
    cropped_img = resized_img.crop((crop_x, crop_y, crop_x + img_w, crop_y + img_h))

    card.paste(cropped_img, (img_x1, img_y1))

    # 5. サブ情報バー
    draw.rectangle([(50, 580), (card_w-50, 615)], fill="#FFFFFF", outline="#B7950B", width=2)
    draw.text((65, 586), f"たねTogomon  /  全国図鑑 NO.001  /  たかさ: 1.0m  おもさ: 15.0kg", fill="#555555", font=font_footer)

    # 6. ワザ表示エリア
    draw.rectangle([(45, 630), (card_w-45, 890)], fill="#FFFFFF", outline=style["bg"], width=3)

    # ワザ用エネルギーマーク（2個）
    draw.ellipse([(65, 660), (105, 700)], fill=style["bg"])
    draw.ellipse([(115, 660), (155, 700)], fill=style["accent"])
    
    # ワザ名
    draw.text((175, 662), card_data["skill_name"], fill="#111111", font=font_skill)
    # ダメージ
    draw.text((600, 658), card_data["damage"], fill="#111111", font=font_dmg)

    # ワザ説明文
    desc_text = card_data["desc"].replace("\\n", "\n")
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
    with st.spinner("🤖 AIがTogomonカードをデザイン中..."):
        user_img = Image.open(uploaded_file).convert("RGB")
        
        card_data = analyze_image_with_gemini(user_img, api_key)
        card_img = generate_card(user_img, card_data)

        with col1:
            st.subheader("🖼️ 完成したカード")
            st.image(card_img, use_container_width=True)

        buf = io.BytesIO()
        card_img.save(buf, format="PNG")
        
        with col2:
            st.subheader("📋 AI生成データ")
            st.write(card_data)
            st.download_button(
                label="🎴 カード画像を保存する (PNG)",
                data=buf.getvalue(),
                file_name=f"{card_data['card_name']}_card.png",
                mime="image/png"
            )
