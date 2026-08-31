import json
import re
from google import genai
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st

# ページ設定
st.set_page_config(page_title="TogoMoN GO カードメーカー", page_icon="🎴", layout="wide")

# 作成したロゴ画像の表示
import os
if os.path.exists("logo.png"):
    st.image("logo.png", width=350)
else:
    st.title("🎴 TogoMoN GO")

st.caption("写真を1枚アップロードするだけで、AIが本格TogoMoNカードを自動作成します！")

# 日本語フォント準備
@st.cache_resource
def prepare_japanese_font_file():
    font_paths = [
        "C:\\Windows\\Fonts\\msgothic.ttc",
        "C:\\Windows\\Fonts\\meiryo.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            return p
    return None

FONT_PATH = prepare_japanese_font_file()

def get_font(size):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()

def create_card_image(card_data, uploaded_image):
    base_path = "card_base.png"
    if os.path.exists(base_path):
        card = Image.open(base_path).convert("RGBA")
    else:
        card = Image.new("RGBA", (750, 1050), (240, 240, 240, 255))
    
    img = uploaded_image.convert("RGBA")
    img_width, img_height = 580, 430
    img_resized = ImageOps.fit(img, (img_width, img_height), Image.Resampling.LANCZOS)
    card.paste(img_resized, (85, 185))

    draw = ImageDraw.Draw(card)
    
    font_title = get_font(42)
    font_hp = get_font(36)
    font_skill = get_font(32)
    font_desc = get_font(22)
    font_small = get_font(20)

    draw.text((90, 105), card_data.get("card_name", ""), fill=(20, 20, 20), font=font_title)
    draw.text((540, 110), f"HP {card_data.get('hp', '100')}", fill=(200, 30, 30), font=font_hp)
    draw.text((140, 680), card_data.get("skill_name", ""), fill=(20, 20, 20), font=font_skill)
    draw.text((610, 680), str(card_data.get("damage", "")), fill=(20, 20, 20), font=font_skill)
    draw.text((100, 740), card_data.get("description", ""), fill=(50, 50, 50), font=font_desc)
    
    draw.text((140, 895), card_data.get("weakness", ""), fill=(20, 20, 20), font=font_small)
    draw.text((350, 895), card_data.get("resistance", ""), fill=(20, 20, 20), font=font_small)
    draw.text((560, 895), card_data.get("escape", ""), fill=(20, 20, 20), font=font_small)
    draw.text((590, 975), card_data.get("card_no", ""), fill=(80, 80, 80), font=font_small)

    return card

def analyze_image_and_generate_data(pil_image, api_key_val):
    default_data = {
        "card_name": "ナゾノモブ",
        "hp": "120",
        "type": "超",
        "skill_name": "ひらめき",
        "damage": "80",
        "description": "画像解析がスキップされた時に現れるカード。",
        "weakness": "悪 ×2",
        "resistance": "-30",
        "escape": "●●",
        "card_no": "001/050"
    }

    if not api_key_val:
        st.error("⚠️ GEMINI_API_KEY が設定されていません。StreamlitのSecretsを確認してください。")
        return default_data

    try:
        client = genai.Client(api_key=api_key_val)
        
        prompt = """
添付された画像を分析して、この写真の人物や対象の特徴を表したTogoMoNカード用テキストを作成してください。
必ず以下のJSONフォーマットのみで出力してください。

{
    "card_name": "写真の特徴を表した面白い名前（8文字以内）",
    "hp": "120",
    "type": "超",
    "skill_name": "写真のポーズに関連したワザ名（8文字以内）",
    "damage": "80",
    "description": "ワザの効果や解説（30文字以内）",
    "weakness": "悪 ×2",
    "resistance": "-30",
    "escape": "●●",
    "card_no": "001/050"
}
"""
        # モデル名のみを gemini-2.5-flash に更新
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, pil_image]
        )
        
        res_text = response.text.strip()
        json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if json_match:
            res_text = json_match.group(0)
            
        data = json.loads(res_text)
        return data

    except Exception as e:
        st.error(f"Gemini API呼び出しエラー: {e}")
        return default_data

# メイン画面処理
api_key = st.secrets.get("GEMINI_API_KEY", "")

uploaded_file = st.file_uploader("写真をえらんでね", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    user_image = Image.open(uploaded_file)
    st.image(user_image, caption="アップロード画像", width=300)
    
    if st.button("🎴 TogoMoNカードを作成する！", type="primary"):
        with st.spinner("AIが画像を分析してカードを作成中..."):
            card_data = analyze_image_and_generate_data(user_image, api_key)
            final_card = create_card_image(card_data, user_image)
            
            st.success("完成しました！")
            st.image(final_card, caption="完成したカード", use_container_width=True)
            
            import io
            buf = io.BytesIO()
            final_card.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 カード画像を保存する",
                data=byte_im,
                file_name="togomon_card.png",
                mime="image/png"
            )
