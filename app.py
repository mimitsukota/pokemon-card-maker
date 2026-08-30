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
        "face_box": [0, 0, 1000, 1000] # [ymin, xmin, ymax, xmax] (0-1000の正規化座標)
    }

    if not api_key_val:
        return default_data

    try:
        genai.configure(api_key=api_key_val)
        
        prompt = """
        添付された画像を分析して、Togomonのカード風データを作成してください。
        また、画像内の主要な人物の顔の位置（バウンディングボックス）を 0〜1000 の数値座標で検出してください。

        以下のJSON形式のみを出力してください。不要なMarkdown記法や解説文は一切含めないでください。

        {
          "card_name": "写真の特徴を表した名前",
          "hp": "120",
          "type": "超",
          "skill_name": "ワザ名",
          "damage": "60",
          "desc": "2行程度の説明文",
          "face_box": [ymin, xmin, ymax, xmax]
        }

        ※ typeは (草 / 炎 / 水 / 雷 / 超 / 闘) の中から1つ選んでください。
        ※ face_box は [上, 左, 下, 右] の0〜1000の範囲の整数値です。顔が見つからない場合は [0, 0, 1000, 1000] としてください。
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
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("
