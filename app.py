import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

st.title("🎴 おまごちゃんカードメーカー")

# APIキーの設定
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY が secrets に設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

# 画像のアップロード
uploaded_file = st.file_uploader("おまごちゃんの写真をアップロードしてね", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた写真", use_container_width=True)
    
    if st.button("🎴 カードをせいさくする！"):
        with st.spinner("AIがおまごちゃんのカードをかんがえています..."):
            try:
                # 最新のモデル名を指定（非推奨エラーを回避）
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                prompt = """
                この写真に写っている人物（子供）の特徴を観察して、トレーディングカード風のステータスと技（わざ）を考えてください。
                以下のJSON形式のみで回答してください。余計な解説文やMarkdown表記（```json など）は含めないでください。

                {
                    "card_name": "おまごちゃんの名前や二つ名（例：ひがおしの ◯◯ちゃん）",
                    "hp": 100,
                    "type": "カードのタイプ（例：でんき、ほのお、スマイル、げんき）",
                    "skill_1_name": "わざ名1（例：にっこりスマイル）",
                    "skill_1_damage": 30,
                    "skill_1_desc": "わざの説明文",
                    "skill_2_name": "わざ名2（例：全力ダッシュ）",
                    "skill_2_damage": 60,
                    "skill_2_desc": "わざの説明文",
                    "comment": "おまごちゃんの魅力や一言コメント"
                }
                """
                
                response = model.generate_content([prompt, image])
                
                # レスポンスのクリーンアップとJSONパース
                res_text = response.text.strip()
                if res_text.startswith("```json"):
                    res_text = res_text[7:]
                if res_text.endswith("```"):
                    res_text = res_text[:-3]
                res_text = res_text.strip()
                
                card_data = json.loads(res_text)
                
                # カードの表示
                st.markdown("---")
                st.subheader(f"🎴 {card_data.get('card_name', 'おまごちゃんカード')}")
                st.write(f"**HP:** {card_data.get('hp', 100)} | **タイプ:** {card_data.get('type', 'ノーマル')}")
                
                st.write("---")
                st.write(f"⚔️ **{card_data.get('skill_1_name', 'わざ1')}** (ダメージ: {card_data.get('skill_1_damage', 10)})")
                st.caption(card_data.get('skill_1_desc', ''))
                
                st.write(f"⚔️ **{card_data.get('skill_2_name', 'わざ2')}** (ダメージ: {card_data.get('skill_2_damage', 30)})")
                st.caption(card_data.get('skill_2_desc', ''))
                
                st.write("---")
                st.info(f"💡 {card_data.get('comment', '')}")
                
            except Exception as e:
                st.error(f"カードの作成中にエラーが発生しました: {e}")
