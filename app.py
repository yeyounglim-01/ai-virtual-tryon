import streamlit as st
from PIL import Image
from gradio_client import Client, handle_file
from huggingface_hub import InferenceClient
import os, io, tempfile, requests, time

st.set_page_config(page_title="AI Virtual Try-On", page_icon="👕", layout="wide")

# ── 테마 CSS (블랙 & 실버) ───────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background-color: #0D0D0D; }

    /* 헤더 */
    .hero {
        text-align: center;
        padding: 3rem 0 1rem 0;
    }
    .hero-title {
        font-size: 3rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -1px;
    }
    .hero-title span { color: #A0A0A0; }
    .hero-sub {
        color: #666;
        font-size: 1rem;
        margin-top: 0.5rem;
    }

    /* 스텝 인디케이터 */
    .steps {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0;
        margin: 2rem 0;
    }
    .step {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #444;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .step.active { color: #FFFFFF; }
    .step.done { color: #888; }
    .step-num {
        width: 28px; height: 28px;
        border-radius: 50%;
        background: #222;
        border: 1px solid #333;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.75rem; font-weight: 600; color: #555;
    }
    .step.active .step-num {
        background: #FFFFFF;
        color: #000;
        border-color: #FFFFFF;
    }
    .step.done .step-num {
        background: #333;
        color: #888;
        border-color: #444;
    }
    .step-divider {
        width: 60px; height: 1px;
        background: #2A2A2A;
        margin: 0 0.75rem;
    }

    /* 카드 */
    .card {
        background: #141414;
        border: 1px solid #222;
        border-radius: 16px;
        padding: 2rem;
    }

    /* 섹션 레이블 */
    .label {
        font-size: 0.7rem;
        font-weight: 600;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 1rem;
    }

    /* 옷 카드 */
    .garment-card {
        background: #F5F5F5;
        border-radius: 12px;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.2s;
    }
    .garment-card:hover { transform: scale(1.02); }
    .garment-selected-border {
        outline: 2px solid #FFFFFF;
        outline-offset: 3px;
        border-radius: 12px;
    }

    /* 버튼 */
    .stButton > button {
        background: #FFFFFF !important;
        color: #000000 !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 1.5rem !important;
        width: 100% !important;
        transition: opacity 0.2s !important;
    }
    .stButton > button:hover { opacity: 0.85 !important; }

    /* 보조 버튼 */
    div[data-testid="stButton"] button[kind="secondary"] {
        background: #1A1A1A !important;
        color: #888 !important;
        border: 1px solid #333 !important;
    }

    /* 라디오 */
    .stRadio label { color: #AAA !important; font-size: 0.9rem !important; }
    .stRadio [data-baseweb="radio"] { gap: 1.5rem !important; }

    /* 인풋 */
    .stTextInput input {
        background: #1A1A1A !important;
        border: 1px solid #2A2A2A !important;
        color: #FFF !important;
        border-radius: 10px !important;
    }

    /* 결과 비교 */
    .result-label {
        font-size: 0.75rem;
        color: #555;
        text-align: center;
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 구분선 */
    hr { border-color: #1E1E1E !important; }

    /* 업로더 */
    .stFileUploader {
        background: #141414 !important;
        border: 1px dashed #2A2A2A !important;
        border-radius: 12px !important;
    }
    [data-testid="stFileUploadDropzone"] {
        background: #141414 !important;
        border: 1px dashed #2A2A2A !important;
    }

    /* 에러/경고 */
    .stAlert { border-radius: 10px !important; }

    /* 스피너 */
    .stSpinner { color: #888 !important; }

    /* 푸터 */
    .footer {
        text-align: center;
        color: #333;
        font-size: 0.75rem;
        padding: 2rem 0;
        margin-top: 3rem;
        border-top: 1px solid #1A1A1A;
    }
</style>
""", unsafe_allow_html=True)

# ── 세션 초기화 ──────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 1
if "person_image" not in st.session_state:
    st.session_state.person_image = None
if "selected_garment" not in st.session_state:
    st.session_state.selected_garment = None
if "result_image" not in st.session_state:
    st.session_state.result_image = None

# ── 헬퍼 ────────────────────────────────────────────────────
GITHUB_RAW = "https://raw.githubusercontent.com/yeyounglim-01/ai-virtual-tryon/main/garments"
GARMENT_DIR = os.path.join(os.path.dirname(__file__), "garments")
GARMENT_FILES = [f"tshirt_{str(i).zfill(2)}.png" for i in range(1, 15)]

def open_image(path_or_url):
    if path_or_url.startswith("http"):
        return Image.open(io.BytesIO(requests.get(path_or_url).content))
    return Image.open(path_or_url)

def load_garments():
    garments = {}
    for f in GARMENT_FILES:
        name = os.path.splitext(f)[0].replace("_", " ").title()
        local = os.path.join(GARMENT_DIR, f)
        garments[name] = local if os.path.exists(local) else f"{GITHUB_RAW}/{f}"
    return garments

@st.cache_resource
def get_vto_client():
    return Client("yisol/IDM-VTON")

def generate_person(prompt):
    token = os.environ.get("HF_TOKEN", "")
    client = InferenceClient(
        model="stabilityai/stable-diffusion-xl-base-1.0",
        token=token if token else None
    )
    full = f"{prompt}, wearing a plain white t-shirt, full body shot, standing straight, arms slightly away from body, plain light gray background, fashion photography, photorealistic, 8k"
    return client.text_to_image(full)

def run_vto(person_img, garment_path):
    client = get_vto_client()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
        person_img.convert("RGB").save(t.name)
        p_tmp = t.name
    if garment_path.startswith("http"):
        r = requests.get(garment_path)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
            t.write(r.content)
            g_tmp = t.name
    else:
        g_tmp = garment_path

    last_error = None
    for attempt in range(3):
        try:
            result = get_vto_client().predict(
                dict={"background": handle_file(p_tmp), "layers": [], "composite": None},
                garm_img=handle_file(g_tmp),
                garment_des="upper body t-shirt",
                is_checked=True,
                is_checked_crop=True,
                denoise_steps=30,
                seed=-1,
                api_name="/tryon"
            )
            os.unlink(p_tmp)
            if garment_path.startswith("http"):
                os.unlink(g_tmp)
            return Image.open(result[0])
        except Exception as e:
            last_error = e
            if attempt < 2:
                wait = (attempt + 1) * 5
                time.sleep(wait)

    os.unlink(p_tmp)
    if garment_path.startswith("http"):
        os.unlink(g_tmp)
    raise last_error

def img_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ── 헤더 ────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-title">AI Virtual <span>Try-On</span></div>
    <div class="hero-sub">아바타를 만들고 원하는 옷을 가상으로 입어보세요</div>
</div>
""", unsafe_allow_html=True)

# ── 스텝 인디케이터 ──────────────────────────────────────────
step = st.session_state.step

def step_class(n):
    if n < step: return "step done"
    if n == step: return "step active"
    return "step"

st.markdown(f"""
<div class="steps">
    <div class="{step_class(1)}">
        <div class="step-num">{"✓" if step > 1 else "1"}</div>
        <span>나 설정</span>
    </div>
    <div class="step-divider"></div>
    <div class="{step_class(2)}">
        <div class="step-num">{"✓" if step > 2 else "2"}</div>
        <span>옷 선택</span>
    </div>
    <div class="step-divider"></div>
    <div class="{step_class(3)}">
        <div class="step-num">3</div>
        <span>결과</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════
# STEP 1: 아바타 설정
# ══════════════════════════════════════════════════════════
if step == 1:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="label">Step 01 — 나를 설정하세요</div>', unsafe_allow_html=True)

        mode = st.radio("입력 방식", ["📷  사진 업로드", "✏️  텍스트로 생성"], label_visibility="collapsed", horizontal=True)

        if mode == "📷  사진 업로드":
            uploaded = st.file_uploader("전신 사진 업로드 (흰 배경 권장)", type=["jpg","jpeg","png"], label_visibility="collapsed")
            if uploaded:
                st.session_state.person_image = Image.open(uploaded).convert("RGB")
                st.image(st.session_state.person_image, use_column_width=True)

        else:
            prompt = st.text_input("", placeholder="예: a young korean woman, slim body, short hair")
            if st.button("✨  아바타 생성"):
                if prompt.strip():
                    with st.spinner("아바타 생성 중... (30초 소요)"):
                        try:
                            st.session_state.person_image = generate_person(prompt)
                        except Exception as e:
                            st.error(f"생성 실패: {e}")
                else:
                    st.warning("텍스트를 입력해주세요.")

            if st.session_state.person_image:
                st.image(st.session_state.person_image, use_column_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.session_state.person_image:
            if st.button("다음 단계 →  옷 선택"):
                st.session_state.step = 2
                st.rerun()
        else:
            st.markdown('<p style="color:#444;text-align:center;font-size:0.85rem;">사진을 업로드하거나 아바타를 생성하면 다음으로 넘어갈 수 있어요.</p>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# STEP 2: 옷 선택
# ══════════════════════════════════════════════════════════
elif step == 2:
    st.markdown('<div class="label" style="text-align:center">Step 02 — 입고 싶은 옷을 선택하세요</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    garments = load_garments()
    names = list(garments.keys())

    if "selected_garment_name" not in st.session_state:
        st.session_state.selected_garment_name = names[0]

    cols = st.columns(4)
    for i, name in enumerate(names):
        with cols[i % 4]:
            is_sel = st.session_state.selected_garment_name == name
            border = "outline: 2px solid #FFFFFF; outline-offset: 3px;" if is_sel else ""
            st.markdown(f'<div style="border-radius:12px;overflow:hidden;background:#F0F0F0;{border}">', unsafe_allow_html=True)
            img = open_image(garments[name])
            st.image(img, use_column_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button(f"{'✓ ' if is_sel else ''}{name}", key=f"g_{i}"):
                st.session_state.selected_garment_name = name
                st.session_state.selected_garment = garments[name]
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns([1, 1, 1])
    with b1:
        if st.button("← 이전"):
            st.session_state.step = 1
            st.rerun()
    with b3:
        sel = st.session_state.selected_garment_name
        if st.button(f"선택 완료: {sel}  →"):
            st.session_state.selected_garment = garments[sel]
            st.session_state.step = 3
            st.rerun()

# ══════════════════════════════════════════════════════════
# STEP 3: VTO 결과
# ══════════════════════════════════════════════════════════
elif step == 3:
    st.markdown('<div class="label" style="text-align:center">Step 03 — 가상 피팅 결과</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.result_image is None:
        with st.spinner("옷을 입히는 중... (약 30~60초 소요)"):
            try:
                st.session_state.result_image = run_vto(
                    st.session_state.person_image,
                    st.session_state.selected_garment
                )
            except Exception as e:
                st.error(f"VTO 실패: {e}")
                if st.button("← 다시 시도"):
                    st.session_state.step = 2
                    st.rerun()

    if st.session_state.result_image:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.image(st.session_state.person_image, use_column_width=True)
            st.markdown('<div class="result-label">원본</div>', unsafe_allow_html=True)
        with c2:
            st.image(st.session_state.result_image, use_column_width=True)
            st.markdown('<div class="result-label">VTO 결과</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        d1, d2, d3 = st.columns([1, 1, 1])
        with d1:
            if st.button("← 옷 다시 선택"):
                st.session_state.result_image = None
                st.session_state.step = 2
                st.rerun()
        with d2:
            st.download_button(
                "⬇  결과 저장",
                data=img_to_bytes(st.session_state.result_image),
                file_name="vto_result.png",
                mime="image/png"
            )
        with d3:
            if st.button("처음부터 다시"):
                st.session_state.step = 1
                st.session_state.person_image = None
                st.session_state.selected_garment = None
                st.session_state.result_image = None
                st.rerun()

# ── 푸터 ────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    Powered by IDM-VTON · Stable Diffusion XL · Built with Streamlit
</div>
""", unsafe_allow_html=True)
