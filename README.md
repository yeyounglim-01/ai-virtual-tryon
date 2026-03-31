# 👕 AI Virtual Try-On

> 전신 사진 또는 텍스트 프롬프트로 아바타를 생성하고, 원하는 옷을 가상으로 입어볼 수 있는 AI 기반 가상 피팅 서비스

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

---

## 📸 주요 기능

| 기능 | 설명 |
|------|------|
| **사진 업로드** | 내 전신 사진에 원하는 옷 가상 착장 |
| **텍스트 생성** | 텍스트 프롬프트로 아바타 생성 후 옷 입히기 |
| **옷 갤러리** | 쇼핑몰처럼 옷을 선택하는 그리드 UI |
| **결과 다운로드** | 완성된 가상 착장 이미지 저장 |

---

## 🔧 기술 스택

```
사용자 입력 (사진 or 텍스트)
        ↓
[Stable Diffusion XL]  ← 텍스트 → 아바타 생성
        ↓
[ControlNet + OpenPose] ← 포즈 추출
        ↓
[HMR2.0 / SMPL]        ← 3D 체형 추정
        ↓
[OOTDiffusion]         ← 가상 착장 합성 (AAAI 2025)
        ↓
결과 이미지
```

| 분류 | 기술 |
|------|------|
| UI / 배포 | Streamlit, HuggingFace Spaces |
| VTO 모델 | OOTDiffusion (AAAI 2025) |
| 아바타 생성 | Stable Diffusion XL |
| 포즈 추정 | ControlNet + OpenPose |
| 3D 체형 추정 | HMR2.0 (SMPL) |
| 커스텀 모델 | LoRA fine-tuned on fashion dataset |

---

## 🚀 로컬 실행

```bash
git clone https://github.com/yeyounglim-01/ai-virtual-tryon
cd ai-virtual-tryon
pip install -r requirements.txt
streamlit run app.py
```

---

## 🗂 프로젝트 구조

```
ai-virtual-tryon/
├── app.py                  # 메인 Streamlit 앱
├── requirements.txt        # 패키지 목록
├── garments/               # 제공 옷 이미지 (jpg/png 추가 시 자동 표시)
│   ├── tshirt_white.jpg
│   └── ...
├── .streamlit/
│   └── config.toml         # 다크 테마 설정
└── README.md
```

### garments 폴더에 옷 추가하기

`garments/` 폴더에 흰 배경의 옷 이미지를 넣으면 자동으로 갤러리에 표시됩니다.

```
garments/
├── tshirt_white.jpg    → "Tshirt White" 로 표시
├── tshirt_black.jpg    → "Tshirt Black" 로 표시
└── hoodie_gray.jpg     → "Hoodie Gray" 로 표시
```

---

## ⚙️ HuggingFace Spaces 배포

1. [HuggingFace](https://huggingface.co/new-space) 에서 새 Space 생성
   - SDK: **Streamlit**
   - Visibility: **Public**
2. 이 GitHub 레포 연동
3. Spaces Settings > Secrets에 `HF_TOKEN` 추가 (텍스트 생성 기능 활성화)
4. 자동 빌드 완료 후 URL 생성

---

## 📌 개발 배경

패션 이커머스에서 반품률을 줄이기 위한 가상 피팅 기술에 관심을 가지고, LoRA 모델 학습부터 3D SMPL 체형 추정, 최신 VTO 모델 적용까지 전체 파이프라인을 직접 구현한 개인 프로젝트입니다.

---

<p align="center">Powered by OOTDiffusion · Stable Diffusion · Built with Streamlit</p>
