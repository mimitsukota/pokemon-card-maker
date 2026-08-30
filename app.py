import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io

st.set_page_config(page_title="ポケモンカード風メーカー", page_icon="🎴", layout="wide")

st.title("🎴 おまごちゃん ポケモンカード風メーカー")
st.caption("アップロードしたお写真を加工せずそのままカードフレームに合成します！")

st.sidebar.header("⚙️ カードの設定")

card_name = st.sidebar.text_input("なまえ", value="すまいる ボーイ")
card_hp = st.sidebar.text_input("HP", value="HP 120")
card_type = st.sidebar.selectbox("タイプ (枠の色)", ["パープル (超/悪)", "レッド (ほのお)", "ブルー (みず)", "グリーン (くさ)", "イエロー (でんき)"])

st.sidebar.subheader("⚔️ ワザ設定")
skill_name = st.sidebar.text_input("ワザの名前", value="ぎょろぎょろスマイル")
skill_damage = st.sidebar.text_input("ダメージ", value="60")
skill_desc = st.sidebar.text_area("ワザの説明", value="おちゃめな メガネで みんなの\nげんきを 100ばいに するぞ！")

# テーマカラー設定
color_schemes = {
    "パープル (超/悪)": {"main": "#5C2D91", "inner": "#7B3FBF", "bg": "#F8F4FF", "header": "#EAE0F8"},
    "レッド (ほのお)": {"main": "#C0392B", "inner": "#E74C3C", "bg": "#FDEDEC", "header": "#FADBD8"},
    "ブルー (みず)": {"main": "#2980B9", "inner": "#3498DB", "bg": "#EBF5FB", "header": "#D4E6F1"},
    "グリーン (くさ)": {"main": "#27AE60", "inner": "#2ECC71", "bg": "#EAFAF1", "header": "#D5F5E3"},
    "イエロー (でんき)": {"main": "#F39C12", "inner": "#F1C40F", "bg": "#FEF9E7", "header": "#FCF3CF"}
}
colors = color_schemes[card_type]

uploaded_file = st.file_uploader("📷 お孫さんの写真をアップロードしてください（※加工せずそのまま入ります）", type=["jpg", "jpeg", "png"])

def generate_card(image_file):
    user_img = Image.open(image_file).convert("RGBA")
    
    card_w, card_h = 750, 1050
    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)

    # 枠線の描画
    draw.rectangle([(0, 0), (card_w, card_h)], fill=colors["main"])
    draw.rectangle([(25, 25), (card_w-25, card_h-25)], fill=colors["inner"], outline="#FFD700", width=8)

    # ヘッダー領域
    draw.rectangle([(45, 45), (card_w-45, 115)], fill=colors["header"], outline="#3D1A6A", width=4)

    # 写真配置エリア (50, 135) -> (700, 565)
    frame_x1, frame_y1, frame_x2, frame_y2 = 50, 135, card_w-50, 565
    frame_w, frame_h = frame_x2 - frame_x1, frame_y2 - frame_y1

    # 写真の無加工リサイズ＆クロップ
    img_w, img_h = user_img.size
    aspect_user = img_w / img_h
    aspect_frame = frame_w / frame_h

    if aspect_user > aspect_frame:
        new_h = frame_h
        new_w = int(new_h * aspect_user)
    else:
        new_w = frame_w
        new_h = int(new_w / aspect_user)

    resized_user_img = user_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    crop_x = (new_w - frame_w) // 2
    crop_y = (new_h - frame_h) // 2
    cropped_user_img = resized_user_img.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))

    # 完全無加工の写真をそのまま合成
    card.paste(cropped_user_img, (frame_x1, frame_y1))

    # 写真枠のゴールド装飾
    draw.rectangle([(frame_x1, frame_y1), (frame_x2, frame_y2)], outline="#FFD700", width=8)
    draw.rectangle([(frame_x1-4, frame_y1-4), (frame_x2+4, frame_y2+4)], outline="#3D1A6A", width=3)

    # サブヘッダーリボン
    draw.rectangle([(120, 545), (card_w-120, 595)], fill="#FFEAA7", outline="#3D1A6A", width=3)

    # ワザ説明ボックス
    draw.rectangle([(50, 615), (card_w-50, 860)], fill=colors["bg"], outline="#3D1A6A", width=4)

    # ステータスボックス
    draw.rectangle([(50, 875), (card_w-50, 990)], fill=colors["header"], outline="#3D1A6A", width=3)

    # フォント設定
    try:
        font_title = ImageFont.truetype("meiryo.ttc", 36)
        font_hp = ImageFont.truetype("meiryob.ttc", 32)
        font_bold = ImageFont.truetype("meiryob.ttc", 28)
        font_main = ImageFont.truetype("meiryo.ttc", 22)
    except:
        font_title = font_hp = font_bold = font_main = ImageFont.load_default()

    # テキスト描画
    draw.text((70, 58), card_name, fill="#000000", font=font_title)
    draw.text((510, 62), card_hp, fill="#D63031", font=font_hp)
    draw.text((270, 553), card_name, fill="#2D3436", font=font_bold)

    # ワザテキスト
    draw.text((80, 635), f"【ワザ】 {skill_name}", fill="#000000", font=font_bold)
    draw.text((610, 635), skill_damage, fill="#000000", font=font_hp)
    
    # 改行テキストの処理
    lines = skill_desc.split("\n")
    y_offset = 700
    for line in lines:
        draw.text((80, y_offset), line, fill="#2D3436", font=font_main)
        y_offset += 40

    # フッター
    draw.text((70, 895), "弱点 : 水", fill="#2D3436", font=font_main)
    draw.text((270, 895), "抵抗力 : なし", fill="#2D3436", font=font_main)
    draw.text((500, 895), "にげる : ★", fill="#2D3436", font=font_main)

    return card.convert("RGB")

col1, col2 = st.columns([1, 1])

if uploaded_file is not None:
    card_img = generate_card(uploaded_file)
    with col1:
        st.subheader("🖼️ 完成カードイメージ")
        st.image(card_img, use_container_width=True)

    buf = io.BytesIO()
    card_img.save(buf, format="PNG")
    byte_im = buf.getvalue()

    with col2:
        st.subheader("💾 ダウンロード")
        st.download_button(
            label="カード画像をダウンロード (PNG)",
            data=byte_im,
            file_name=f"{card_name}_card.png",
            mime="image/png"
        )
else:
    with col1:
        st.info("👈 左側のサイドバーで設定を行い、上から写真をアップロードしてください。")
