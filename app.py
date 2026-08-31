import json
import re
from google import genai
from PIL import Image
import streamlit as st

# ページ設定
st.set_page_config(page_title="TogoMoN Card Generator", layout="centered")

st.title("🎴 TogoMoN カードジェネレーター")

# 1. APIキーの読み込み（Secretsから取得）
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error(
        "⚠️ GEMINI_API_KEY が設定されていません。StreamlitのSecretsを確認してください。"
    )
    st.stop()


# 2. 画像分析＆カードデータ生成関数
def generate_card_data(pil_image):
    # 新SDKのClient初期化（AQ.始まりのキーに対応）
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
        # 新SDKでの呼び出し（gemini-2.5-flashを指定）
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt, pil_image]
        )
        text = response.text.strip()

        # レスポンスからJSON部分だけを抽出
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        card_data = json.loads(text)
        return card_data

    except Exception as e:
        st.error(f"解析中にエラーが発生しました: {e}")
        # エラー発生時の予備データ
        return {
            "card_name": "ナゾノモブ",
            "hp": "100",
            "type": "無",
            "skill_name": "たいあたり",
            "damage": "30",
            "description": "データ解析に失敗した時に現れる謎の存在。",
            "weakness": "闘 ×2",
            "resistance": "なし",
            "escape": "●",
            "card_no": "000/000",
        }


# 3. メインUI処理
uploaded_file = st.file_uploader(
    "写真をアップロードしてください", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_container_width=True)

    if st.button("カードテキストを自動生成する"):
        with st.spinner("Geminiが画像を分析中..."):
            card_data = generate_card_data(image)

        st.success("生成完了！")
        st.json(card_data)
