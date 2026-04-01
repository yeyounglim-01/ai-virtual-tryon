import streamlit as st
from PIL import Image
from gradio_client import Client, handle_file
from huggingface_hub import InferenceClient
import os
import io
import base64
import tempfile
import requests

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="AI Virtual Try-On",
    page_icon="👕",
    layout="wide",
)

# ── 커스텀 CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    /* 헤더 */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FF4B4B, #FF8C42);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-title {
        color: #888;
        font-size: 1rem;
        margin-top: 0;
        margin-bottom: 2rem;
    }
    /* 섹션 타이틀 */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #FF4B4B;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    /* 옷 카드 */
    .garment-selected {
        border: 3px solid #FF4B4B;
        border-radius: 12px;
    }
    /* Try On 버튼 */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #FF4B4B, #FF8C42);
        color: white;
        font-size: 1.1rem;
        font-weight: 700;
        border: none;
        border-radius: 12px;
        padding: 0.8rem;
        cursor: pointer;
        transition: opacity 0.2s;
    }
    .stButton > button:hover {
        opacity: 0.85;
    }
    /* 결과 이미지 */
    .result-box {
        background: #1A1C2E;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
    }
    /* 구분선 */
    hr {
        border-color: #2A2D45;
    }
    /* 라디오 버튼 */
    .stRadio > div {
        flex-direction: row;
        gap: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ────────────────────────────────────────────────────
st.markdown('<p class="main-title">👕 AI Virtual Try-On</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">사진을 올리거나 텍스트로 아바타를 만들고, 원하는 옷을 가상으로 입어보세요.</p>', unsafe_allow_html=True)
st.markdown("---")

# ── 옷 이미지 로드 ───────────────────────────────────────────
GITHUB_RAW = "https://raw.githubusercontent.com/yeyounglim-01/ai-virtual-tryon/main/garments"
GARMENT_DIR = os.path.join(os.path.dirname(__file__), "garments")

GARMENT_FILES = [
    "tshirt_01.png", "tshirt_02.png", "tshirt_03.png", "tshirt_04.png",
    "tshirt_05.png", "tshirt_06.png", "tshirt_07.png", "tshirt_08.png",
    "tshirt_09.png", "tshirt_10.png", "tshirt_11.png", "tshirt_12.png",
    "tshirt_13.png", "tshirt_14.png",
]

def load_garments():
    garments = {}
    # 로컬 파일 우선, 없으면 GitHub URL 사용
    for f in GARMENT_FILES:
        name = os.path.splitext(f)[0].replace("_", " ").title()
        local_path = os.path.join(GARMENT_DIR, f)
        if os.path.exists(local_path):
            garments[name] = local_path
        else:
            garments[name] = f"{GITHUB_RAW}/{f}"
    return garments

garments = load_garments()

def open_image(path_or_url: str) -> Image.Image:
    if path_or_url.startswith("http"):
        response = requests.get(path_or_url)
        return Image.open(io.BytesIO(response.content))
    return Image.open(path_or_url)

# ── OOTDiffusion API ─────────────────────────────────────────
@st.cache_resource
def get_ootd_client():
    return Client("levihsu/OOTDiffusion")

# ── SD 텍스트 → 이미지 생성 ──────────────────────────────────
def generate_person_from_text(prompt: str) -> Image.Image:
    hf_token = os.environ.get("HF_TOKEN", "")
    client = InferenceClient(
        model="stabilityai/stable-diffusion-xl-base-1.0",
        token=hf_token if hf_token else None,
    )
    full_prompt = f"{prompt}, wearing a plain white t-shirt, full body shot, standing straight, arms at sides, white background, fashion photography, photorealistic"
    result = client.text_to_image(full_prompt)
    return result

# ── VTO 실행 ─────────────────────────────────────────────────
def run_vto(person_img: Image.Image, garment_path: str) -> Image.Image:
    client = get_ootd_client()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        person_img.convert("RGB").save(tmp.name)
        person_tmp = tmp.name

    result = client.predict(
        vton_img=handle_file(person_tmp),
        garm_img=handle_file(garment_path),
        n_samples=1,
        n_steps=20,
        image_scale=2.0,
        seed=-1,
        api_name="/process_hd"
    )
    os.unlink(person_tmp)
    return Image.open(result[0]["image"])

# ── 이미지 → 다운로드용 base64 ───────────────────────────────
def img_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ── 레이아웃: 왼쪽(입력) / 오른쪽(옷 선택) ─────────────────
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.markdown('<p class="section-title">01 / 나 설정</p>', unsafe_allow_html=True)

    input_mode = st.radio(
        "입력 방식",
        ["📷 사진 업로드", "✏️ 텍스트로 생성"],
        label_visibility="collapsed"
    )

    person_image = None

    if input_mode == "📷 사진 업로드":
        uploaded = st.file_uploader(
            "전신 사진을 올려주세요",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed"
        )
        if uploaded:
            person_image = Image.open(uploaded).convert("RGB")
            st.image(person_image, caption="업로드된 사진", use_column_width=True)

    else:
        text_prompt = st.text_input(
            "어떤 사람을 만들까요?",
            placeholder="예: a young korean woman, slim, standing straight",
        )
        if st.button("🎨 아바타 생성", key="gen_avatar"):
            if text_prompt.strip():
                with st.spinner("아바타 생성 중..."):
                    try:
                        person_image = generate_person_from_text(text_prompt)
                        st.session_state["generated_person"] = person_image
                    except Exception as e:
                        st.error(f"생성 실패: {e}")
            else:
                st.warning("텍스트를 입력해주세요.")

        if "generated_person" in st.session_state:
            person_image = st.session_state["generated_person"]
            st.image(person_image, caption="생성된 아바타", use_column_width=True)

with right_col:
    st.markdown('<p class="section-title">02 / 옷 선택</p>', unsafe_allow_html=True)

    selected_garment = None

    if not garments:
        st.info("garments/ 폴더에 옷 이미지를 추가해주세요.")
    else:
        cols = st.columns(3)
        garment_names = list(garments.keys())

        if "selected_garment_name" not in st.session_state:
            st.session_state["selected_garment_name"] = garment_names[0]

        for i, name in enumerate(garment_names):
            with cols[i % 3]:
                img = open_image(garments[name])
                is_selected = (st.session_state["selected_garment_name"] == name)
                border = "3px solid #FF4B4B" if is_selected else "3px solid transparent"
                st.markdown(
                    f'<div style="border:{border};border-radius:12px;padding:4px;">',
                    unsafe_allow_html=True
                )
                st.image(img, use_column_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                if st.button(f"{'✅ ' if is_selected else ''}{name}", key=f"garment_{i}"):
                    st.session_state["selected_garment_name"] = name
                    st.rerun()

        selected_garment = garments[st.session_state["selected_garment_name"]]

# ── Try On 버튼 ──────────────────────────────────────────────
st.markdown("---")
btn_col = st.columns([1, 2, 1])[1]

with btn_col:
    tryon_btn = st.button("✨ Try On!")

# ── 결과 ────────────────────────────────────────────────────
if tryon_btn:
    if person_image is None:
        st.warning("사진을 업로드하거나 아바타를 먼저 생성해주세요.")
    elif selected_garment is None:
        st.warning("옷을 선택해주세요.")
    else:
        with st.spinner("옷을 입히는 중... (약 30초 소요)"):
            try:
                result_img = run_vto(person_image, selected_garment)
                st.session_state["result_img"] = result_img
            except Exception as e:
                st.error(f"VTO 실패: {e}")

if "result_img" in st.session_state:
    st.markdown("---")
    st.markdown('<p class="section-title">03 / 결과</p>', unsafe_allow_html=True)

    res_left, res_right = st.columns(2, gap="large")
    with res_left:
        if person_image:
            st.image(person_image, caption="입력 이미지", use_column_width=True)
    with res_right:
        st.image(st.session_state["result_img"], caption="VTO 결과", use_column_width=True)
        st.download_button(
            label="⬇️ 결과 다운로드",
            data=img_to_bytes(st.session_state["result_img"]),
            file_name="vto_result.png",
            mime="image/png",
        )

# ── 푸터 ────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#555;font-size:0.8rem;">'
    'Powered by OOTDiffusion · Stable Diffusion · Built with Streamlit'
    '</p>',
    unsafe_allow_html=True
)
