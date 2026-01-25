import streamlit as st
from PIL import Image
import numpy as np
import cv2
import easyocr

# --- [1. 깃북 기반 통합 가이드 데이터] ---
ASSET_GUIDE = {
    "광고 목록화면": {"size": (720, 360), "kb": 200, "page": "4p"},
    "광고 상세화면": {"size": (720, 780), "kb": 400, "page": "9p"},
    "참여중 영역": {"size": (144, 144), "kb": 100, "page": "19p"},
    "퀴즈상품": {"size": (720, 780), "kb": 400, "page": "12p"},
    "영상형 띠배너": {"size": (720, 210), "kb": 200, "page": "16p"},
    "2차 팝업": {"size": (720, 360), "kb": 200, "page": "25p"},
    "상세 화면 설명": {"size": (720, -1), "kb": 400, "page": "20p"} 
}

FORBIDDEN_COLORS = ["#fefefe", "#f6f6f6", "#000000", "#f7f7f7"]
BAN_WORDS = ['설치', '실행', '다운', '다운로드']

# --- [2. 핵심 검수 함수] ---
def hex_to_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

def check_mockup_v2(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 30, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if 4 <= len(approx) <= 8:
            x, y, w, h = cv2.boundingRect(approx)
            if h > 0:
                aspect_ratio = float(w) / h
                if 0.4 <= aspect_ratio <= 0.6 and h > img_np.shape[0] * 0.3:
                    return True
    return False

def check_bg_color(img):
    img_rgb = img.convert('RGB')
    w, h = img_rgb.size
    pixels = []
    for x in range(0, w, 10): pixels.append(img_rgb.getpixel((x, 0)))
    for x in range(0, w, 10): pixels.append(img_rgb.getpixel((x, h-1)))
    for y in range(0, h, 10): pixels.append(img_rgb.getpixel((0, y)))
    for y in range(0, h, 10): pixels.append(img_rgb.getpixel((w-1, y)))
    
    avg_color = np.mean(pixels, axis=0)
    for f_hex in FORBIDDEN_COLORS:
        target_rgb = hex_to_rgb(f_hex)
        if np.all(np.abs(avg_color - target_rgb) < 15):
            return f_hex
    return None

# --- [3. Streamlit 메인 화면] ---
st.set_page_config(page_title="쿠키오븐 검수 v4.0", layout="wide")
st.title("🍪 쿠키오븐 제작가이드 통합 검수 (v4.0)")
st.caption("모든 가이드북 수치와 시각 요소(목업, 색상)를 동시에 검수합니다.")

file = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'])

if file:
    img = Image.open(file)
    img_np = np.array(img.convert('RGB'))
    w, h = img.size
    kb = len(file.getvalue()) / 1024
    
    res_type = "미분류"
    for name, spec in ASSET_GUIDE.items():
        if spec['size'][1] == -1:
            if w == spec['size'][0]: res_type = name
        elif (w, h) == spec['size']:
            res_type = name
            break

    col1, col2 = st.columns(2)
    with col1:
        st.image(img, use_container_width=True, caption=f"분석 대상: {res_type} ({w}x{h})")

    with col2:
        st.subheader(f"📊 검수 리포트: {res_type}")
        errors = []
        passes = []

        # --- A. 규격 및 용량 검수 (메시지 강화) ---
        if res_type in ASSET_GUIDE:
            passes.append(f"이미지 규격 일치 ({w}x{h}px)")
            limit_kb = ASSET_GUIDE[res_type]['kb']
            if kb <= limit_kb:
                passes.append(f"용량 준수: {kb:.1f}KB (기준 {limit_kb}KB 이하)")
            else:
                errors.append(f"용량 초과: 현재 {kb:.1f}KB (기준 {limit_kb}KB 이하)")
        else:
            errors.append(f"규격 위반: {w}x{h}px은 표준 규격이 아닙니다.")

        # --- B. 배경색 및 목업 검수 ---
        bad_bg = check_bg_color(img)
        if bad_bg:
            errors.append(f"배경색 위반: 금지된 단색 배경({bad_bg})이 감지되었습니다.")
        else:
            passes.append("배경색 규정 준수")

        if check_mockup_v2(img_np):
            errors.append("🚨 디바이스 목업 감지: 스마트폰 형태가 발견되었습니다. 제거하세요.")
        else:
            passes.append("목업 이미지 미포함 확인")

        # --- C. 텍스트 및 용어 검수 ---
        with st.spinner("OCR 분석 중..."):
            reader = easyocr.Reader(['ko','en'])
            ocr_res = reader.readtext(img_np, detail=0)
            full_txt = "".join(ocr_res).replace(" ", "")

        if any(bad in full_txt for bad in ['포인트', '캐시', '리워드', '혜택']):
            errors.append("🚨 명칭 위반: '쿠키' 외 명칭 사용 금지 (포인트/캐시 등 감지)")
        else:
            passes.append("리워드 명칭 '쿠키' 준수")
        
        if any(ban in full_txt for ban in BAN_WORDS):
            errors.append("🚨 금지 문구: '설치/다운로드' 대신 '접속하기'를 사용하세요.")
        else:
            passes.append("금지 문구 미포함 확인")

        # 결과 출력
        st.divider()
        if not errors:
            st.success("🎉 모든 가이드를 통과했습니다! 수정 권고 사항이 없습니다.")
            st.balloons()
        else:
            st.error("🚨 수정이 필요한 항목이 있습니다.")
            for err in errors:
                st.write(f"- {err}")
        
        with st.expander("✅ 합격 항목 상세 확인"):
            for p in passes:
                st.write(f"✔️ {p}")

    with st.sidebar:
        st.markdown("### 📝 최종 제출 체크리스트")
        st.write("- 원본 PSD 파일 동봉")
        st.write("- 리워드 명칭 '쿠키' 고정")
        st.write("- 쿠키 아이콘 여백 준수")