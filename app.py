import json
import re
import io
import requests
from google import genai
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st

# ページ設定
st.set_page_config(page_title="TogoMoN Card Generator", layout="centered")

st.title("🎴 TogoMoN カードジェネレーター")

# --- 設定エリア ---
# カードのベース画像のURL（変更可能）
CARD_BASE_URL = "https://raw.githubusercontent.com/t-shogou/pokemon-card-maker/main/base_card.png"
# 日本語フォントのURL（Noto Sans JPなど）
FONT_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansJP/NotoSansJP-Bold.ttf"

# 1. APIキーの読み込み（Secretsから取得）
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ GEMINI_API_KEY が設定されていません。StreamlitのSecretsを確認してください。")
    st.stop()


# 2. アセット（画像・フォント）のキャッシュ読み込み
@st.cache_resource
def load_assets():
    # ベース画像のダウンロード
    try:
        response = requests.get(CARD_BASE_URL)
        card_base = Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        st.error(f"ベース画像の読み込みに失敗しました: {e}")
        st.stop()

    # フォントのダウンロードと登録
    try:
        response = requests.get(FONT_URL)
        font_data = io.BytesIO(response.content)
        # 必要なフォントサイズを定義
        fonts = {
            "name": ImageFont.truetype(font_data, 40),
            "hp": ImageFont.truetype(font_data, 34),
            "skill": ImageFont.truetype(font_data, 32),
            "desc": ImageFont.truetype(font_data, 22),
            "small": ImageFont.truetype(font_data, 18),
        }
    except Exception as e:
        st.error(f"フォントの読み込みに失敗しました: {e}")
        st.stop()

    return card_base, fonts

# 3. 画像分析＆カードデータ生成関数
def generate_card_data(pil_image):
    client = genai.Client(api_key=api_key)
    prompt = """
添付された画像を分析して、この写真の人物や対象の特徴を表したTogoMoNカード用テキストを作成してください。
必ず以下のJSONフォーマットのみで出力してください（余計な挨拶やMarkdownの装飾は含めないでください）。

{
    "card_name": "写真の特徴を表した面白い名前（8文字以内）",
    "hp": "120",
    "type": "超",
    "skill_name": "写真のポーズに関連したワザ名（8文字以内）",
    "damage": "80",
    "description": "ワザの効果や解説（30文字以内）",
    "weakness": "悪 ×2",
    "resistance": "闘 -30",
    "escape": "●●",
    "card_no": "001/050"
}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt, pil_image]
        )
        text = response.text.strip()
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        card_data = json.loads(text)
        return card_data
    except Exception as e:
        st.error(f"解析中にエラーが発生しました: {e}")
        return {
            "card_name": "ナゾノモブ", "hp": "100", "type": "無",
            "skill_name": "たいあたり", "damage": "30",
            "description": "データ解析に失敗した時に現れる謎の存在。",
            "weakness": "闘 ×2", "resistance": "なし", "escape": "●",
            "card_no": "000/000"
        }

# 4. 画像合成関数（ここが抜けていました！）
def draw_card(card_data, user_image, base_img, fonts):
    # ベース画像をコピー
    card = base_img.copy()
    draw = ImageDraw.Draw(card)

    # --- 1. ユーザー画像を配置 ---
    # 指定された枠サイズ (例: 590x420) に合わせてリサイズ
    frame_width, frame_height = 590, 420
    frame_x, frame_y = 65, 115 # 枠の位置

    # アスペクト比を保ったままクロップ＆リサイズ
    user_img_resized = ImageOps.fit(user_image, (frame_width, frame_height), Image.Resampling.LANCZOS)
    card.paste(user_img_resized, (frame_x, frame_y))

    # --- 2. 文字を描画 ---
    # 色の設定
    black = (0, 0, 0)
    red = (200, 0, 0)

    # カード名
    draw.text((70, 50), card_data["card_name"], font=fonts["name"], fill=black)
    
    # HP
    hp_text = f"HP {card_data['hp']}"
    draw.text((560, 55), hp_text, font=fonts["hp"], fill=red, anchor="ra") # 右詰め

    # タイプ (超、闘、etc) - 位置は調整が必要
    draw.text((640, 55), card_data["type"], font=fonts["hp"], fill=black)

    # ワザ名
    draw.text((120, 580), card_data["skill_name"], font=fonts["skill"], fill=black)

    # ダメージ
    draw.text((610, 580), card_data["damage"], font=fonts["skill"], fill=black, anchor="ra")

    # 解説文
    draw.text((80, 650), card_data["description"], font=fonts["desc"], fill=black)

    # 下部ステータス (弱点、抵抗力、にげる)
    draw.text((120, 775), card_data["weakness"], font=fonts["small"], fill=black)
    draw.text((320, 775), card_data["resistance"], font=fonts["small"], fill=black)
    draw.text((540, 775), card_data["escape"], font=fonts["small"], fill=black)

    # カード番号
    draw.text((620, 840), card_data["card_no"], font=fonts["small"], fill=black, anchor="ra")

    return card


# --- 5. メインUI処理 ---
# アセットの読み込み
with st.spinner("アセット（背景・フォント）を読み込み中..."):
    base_img, fonts = load_assets()

uploaded_file = st.file_uploader(
    "写真をアップロードしてください", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    # ユーザー画像の読み込み
    user_image = Image.open(uploaded_file).convert("RGBA")
    
    # アップロード画像を表示（確認用）
    st.image(user_image, caption="アップロードされた画像", use_container_width=True)

    # カード生成ボタン
    if st.button("TogoMoNカードを生成する！"):
        with st.spinner("AIが画像を分析してカードを作成中..."):
            # 1. AIでテキスト生成
            card_data = generate_card_data(user_image)
            
            # 2. 画像合成
            result_card = draw_card(card_data, user_image, base_img, fonts)

        st.success("生成完了！")
        
        # 完成したカード画像を表示
        st.image(result_card, caption="完成したTogoMoNカード", use_container_width=True)

        # ダウンロードボタン
        buf = io.BytesIO()
        result_card.convert("RGB").save(buf, format="JPEG")
        byte_im = buf.getvalue()
        
        st.download_button(
            label="カードを画像として保存",
            data=byte_im,
            file_name=f"togomon_{card_data['card_name']}.jpg",
            mime="image/jpeg",
        )
