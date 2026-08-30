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
        "face_box": [0, 0, 1000, 1000]
    }

    if not api_key_val:
        return default_data

    try:
        genai.configure(api_key=api_key_val)
        
        prompt = """
        添付された画像を分析して、Togomonのカード風データを作成してください。
        また、画像内の主要な人物の顔の位置（バウンディングボックス）を 0〜1000 の数値座標で検出してください。

        以下のJSON形式のみを出力してください。

        {
          "card_name": "写真の特徴を表した名前",
          "hp": "120",
          "type": "超",
          "skill_name": "ワザ名",
          "damage": "60",
          "desc": "2行程度の説明文",
          "face_box": [0, 0, 1000, 1000]
        }

        ※ typeは (草 / 炎 / 水 / 雷 / 超 / 闘) の中から1つ選んでください。
        ※ face_box は [上, 左, 下, 右] の0〜1000の範囲の整数値です。
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
            # JSON部分の抽出処理を安全に変更
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

def crop_face_centered(img, face_box, target_w, target_h):
    """顔を中心にして指定サイズにクロップする"""
    u_w, u_h = img.size
    
    ymin, xmin, ymax, xmax = face_box
    box_top = (ymin / 1000.0) * u_h
    box_left = (xmin / 1000.0) * u_w
    box_bottom = (ymax / 1000.0) * u_h
    box_right = (xmax / 1000.0) * u_w
    
    center_x = (box_left + box_right) / 2.0
    center_y = (box_top + box_bottom) / 2.0

    scale = max(target_w / u_w, target_h / u_h)
    
    new_w = int(u_w * scale)
    new_h = int(u_h * scale)
    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    center_x_scaled = center_x * scale
    center_y_scaled = center_y * scale
    
    crop_x1 = center_x_scaled - (target_w / 2.0)
    crop_y1 = center_y_scaled - (target_h * 0.4)
    
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
        "水": {"bg": "#1565C0", "card_bg": "#E3F2
