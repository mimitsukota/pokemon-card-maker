import io
import os
import urllib.request
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import google.generativeai as genai

st.set_page_config(page_title="AIポケモンカード風メーカー", page_icon="🎴", layout="wide")

st.title("🎴 AIおまごちゃん ポケモンカードメーカー")
st.caption("写真を入れるとAIが自動分析して、名前やワザを自動生成します！")

# 日本語フォントの自動ダウンロード関数
@st.cache_resource
def get_japanese_font(size):
    font_path = "NotoSansJP-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP-Bold.ttf"
        urllib.request.urlretrieve(url, font_path)
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

# APIキーの設定
api_key = st.sidebar.text_input("Gemini API Key", type="password")

uploaded_file = st.file_uploader("📷 写真をアップロードしてください", type=["jpg", "jpeg", "png"])

def analyze_image_with_gemini(pil_image, api_key_val):
    default_data = {
        "card_name": "めがね ボーイ",
        "hp": "HP 120",
        "type": "パープル",
        "skill_name": "へんしんビーム",
        "damage": "60",
        "desc": "ふしぎな めがねで みんなを\nびっくり させるぞ！"
    }

    try:
        genai.configure(api_key=api_key_val)
        
        prompt = """
        添付された画像を分析して、オリジナルのポケモンカード風データを作成してください。
        以下のフォーマットを厳密に守ってテキストのみを出力してください（余計な解説は不要です）。

        カード名: (写真の特徴を表した可愛い/かっこいい名前)
        HP: (HP 80 〜 HP 150 程度)
        タイプ: (パープル / レッド / ブルー / グリーン / イエロー の中から1つ)
        ワザ名: (写真の状況や表情に合わせた面白いワザ名)
        ダメージ: (30 〜 100 程度の数字)
        説明: (2行程度のワザの説明文。1行は20文字以内)
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
                    default_data["hp"] = line.split("HP:")[1].strip()
                elif "タイプ:" in line:
                    default_data["type"] = line.split("タイプ:")[1].strip()
                elif "ワザ名:" in line:
                    default_data["skill_name"] = line.split("ワザ名:")[1].strip()
                elif "ダメージ:" in line:
                    default_data["damage"] = line.split("ダメージ:")[1].strip()
                elif "説明:" in line:
                    default_data["desc"] = line.split("説明:")[1].strip()
                    
    except Exception:
        pass
        
    return default_data

def generate_card(user_img, card_data):
    card_w, card_h = 750, 1050
    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)

    color_schemes = {
        "レッド": {"main": "#C0392B", "inner": "#E74C3C", "bg": "#FDEDEC", "header": "#FADBD8"},
        "ブルー": {"main": "#2980B9", "inner": "#3498DB", "bg": "#EBF5FB", "header": "#D4E6F1"},
        "グリーン": {"main": "#27AE60", "inner": "#2ECC71", "bg": "#EAFAF1", "header": "#D5F5E3"},
        "イエロー": {"main": "#F39C12", "inner": "#F1C40F", "bg": "#FEF9E7", "header": "#FCF3CF"},
        "パープル": {"main": "#5C2D91", "inner": "#7B3FBF", "bg": "#F8F4FF", "header": "#EAE0F8"}
    }
    
    t_key = "パープル"
    for k in color_schemes.keys():
        if k in card_data["type"]:
            t_key = k
            break
    colors = color_schemes[t_key]

    # 1. 枠線
    draw.rectangle([(0, 0), (card_w, card_h)], fill=colors["main"])
    draw.rectangle([(25, 25), (card_w-25, card_h-25)], fill=colors["inner"], outline="#FFD700", width=8)

    # 2. ヘッダー
    draw.rectangle([(45, 45), (card_w-45, 115)], fill=colors["header"], outline="#3D1A6A", width=4)

    # 3. 写真配置 (向きの自動修正)
    user_img_fixed = ImageOps.exif_transpose(user_img)
    
    frame_x1, frame_y1, frame_x2, frame_y2 = 50, 135, card_w-50, 565
    frame_w, frame_h = frame_x2 - frame_x1, frame_y2 - frame_y1
    draw.rectangle([(frame_x1, frame_y1), (frame_x2, frame_y2)], fill="#FFFFFF")

    img_w, img_h = user_img_fixed.size
    ratio = min(frame_w / img_w, frame_h / img_h)
    new_w, new_h = int(img_w * ratio), int(img_h * ratio)
    resized_user_img = user_img_fixed.resize((new_w, new_h), Image.Resampling.LANCZOS)

    paste_x = frame_x1 + (frame_w - new_w) // 2
    paste_y = frame_y1 + (frame_h - new_h) // 2
    card.paste(resized_user_img, (paste_x, paste_y), mask=resized_user_img if resized_user_img.mode == 'RGBA' else None)

    draw.rectangle([(frame_x1, frame_y1), (frame_x2, frame_y2)], outline="#FFD700", width=8)

    # 4. ワザ・ステータス領域
    draw.rectangle([(120, 545), (card_w-120, 595)], fill="#FFEAA7", outline="#3D1A6A", width=3)
    draw.rectangle([(50, 615), (card_w-50, 860)], fill=colors["bg"], outline="#3D1A6A", width=4)
    draw.rectangle([(50, 875), (card_w-50, 990)], fill=colors["header"], outline="#3D1A6A", width=3)

    # フォントの取得
    font_title = get_japanese_font(36)
    font_hp = get_japanese_font(32)
    font_bold = get_japanese_font(28)
    font_main = get_japanese_font(22)

    # 文字の描画
    draw.text((70, 58), card_data["card_name"], fill="#000000", font=font_title)
    draw.text((510, 62), card_data["hp"], fill="#D63031", font=font_hp)
    draw.text((270, 553), card_data["card_name"], fill="#2D3436", font=font_bold)

    draw.text((80, 635), f"【ワザ】 {card_data['skill_name']}", fill="#000000", font=font_bold)
    draw.text((610, 635), card_data["damage"], fill="#000000", font=font_hp)
    
    desc_text = card_data["desc"].replace("\\n", "\n")
    lines = desc_text.split("\n")
    y_off = 700
    for l in lines:
        draw.text((80, y_off), l, fill="#2D3436", font=font_main)
        y_off += 35

    draw.text((70, 895), "弱点 : 水", fill="#2D3436", font=font_main)
    draw.text((270, 895), "抵抗力 : なし", fill="#2D3436", font=font_main)
    draw.text((500, 895), "にげる : ★", fill="#2D3436", font=font_main)

    return card.convert("RGB")

col1, col2 = st.columns([1, 1])

if uploaded_file is not None:
    if not api_key:
        st.warning("👈 左側のサイドバーに Gemini API キーを入力してください。")
    else:
        with st.spinner("🤖 AIが写真を分析してカードを作成中..."):
            user_img = Image.open(uploaded_file).convert("RGB")
            
            card_data = analyze_image_with_gemini(user_img, api_key)
            card_img = generate_card(user_img, card_data)

            with col1:
                st.subheader("🖼️ AI作成カード")
                st.image(card_img, use_container_width=True)

            buf = io.BytesIO()
            card_img.save(buf, format="PNG")
            
            with col2:
                st.subheader("📋 生成されたデータ")
                st.write(card_data)
                st.download_button(
                    label="カード画像をダウンロード (PNG)",
                    data=buf.getvalue(),
                    file_name=f"{card_data['card_name']}_card.png",
                    mime="image/png"
                )
