import streamlit as st
from PIL import Image
import numpy as np
import cv2  # 시각 분석용 라이브러리 추가
import easyocr

# --- 가이드 데이터 세팅 ---
FORBIDDEN_COLORS = ["#fefefe", "#f6f6f6", "#000000", "#f7f7f7"]
BAN_WORDS = ['설치', '다운로드', '다운', '실행']

def hex_to_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

def check_mockup(img_np):
    """이미지 내에 스마트폰 형태(목업)가 있는지 윤곽선 분석"""
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4: # 사각형 형태 감지
            x, y, w, h = cv2.boundingRect(cnt)
            ratio = float(w)/h
            if 0.4 < ratio < 0.6: # 스마트폰 비율과 유사할 경우
                return True
    return False

def check_background_color(image):
    """이미지 외곽 테두리 색상이 금지된 단색 배경인지 체크"""
    img_np = np.array(image.convert('RGB'))
    edges_pixels = np.concatenate([img_np[0, :], img_np[-1, :], img_np[:, 0], img_np[:, -1]])
    avg_color = np.mean(edges_pixels, axis=0)
    
    for f_color in FORBIDDEN_COLORS:
        target_rgb = hex_to_rgb(f_color)
        if np.all(np.abs(avg_color - target_rgb) < 10): # 오차범위 10 이내
            return f_color
    return None

# --- UI 및 메인 로직 ---
st.title("🍪 쿠키오븐 정밀 소재 검수 (v3.1)")
uploaded_file = st.file_uploader("검수할 소재 업로드", type=['png', 'jpg'])

if uploaded_file:
    img = Image.open(uploaded_file)
    img_np = np.array(img.convert('RGB'))
    
    col1, col2 = st.columns(2)
    with col1:
        st.image(img, use_container_width=True)
    
    with col2:
        errors = []
        
        # 1. 배경색 체크 
        bad_bg = check_background_color(img)
        if bad_bg:
            errors.append(f"🚨 **배경색 위반:** 금지된 단색 배경({bad_bg})이 감지되었습니다. 그라데이션이나 디자인 요소를 추가하세요.")
        
        # 2. 목업 이미지 체크 [cite: 69, 188]
        if check_mockup(img_np):
            errors.append("🚨 **디바이스 목업 감지:** 이미지 내 스마트폰 베젤이나 목업 형태가 보입니다. 제거 후 원본 이미지만 사용하세요.")
        
        # 3. 텍스트 및 명칭 체크 [cite: 66, 73, 185, 192]
        reader = easyocr.Reader(['ko','en'])
        ocr_result = reader.readtext(img_np, detail=0)
        full_text = " ".join(ocr_result)
        
        if any(bad in full_text for bad in ['포인트', '캐시', '리워드']):
            errors.append("🚨 **명칭 위반:** '포인트/캐시' 명칭이 발견되었습니다. 반드시 **'쿠키'**로 수정하세요.")
            
        if any(ban in full_text for ban in BAN_WORDS):
            errors.append("🚨 **금지 문구:** '설치/다운로드' 등의 문구는 사용 불가합니다. **'접속하기'**로 수정하세요.")

        if not errors:
            st.success("✅ 모든 정밀 검수(색상, 목업, 문구)를 통과했습니다!")
            st.balloons()
        else:
            for err in errors:
                st.error(err)

    with st.expander("📝 검수 가이드 확인 (Gitbook)"):
        st.write("- **배경 금지:** #fefefe, #f6f6f6, #000000, #f7f7f7 ")
        st.write("- **리워드:** 무조건 '쿠키' 표기 [cite: 73, 192]")
        st.write("- **기기:** 디바이스 목업 사용 불가 [cite: 69, 188]")