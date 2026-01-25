import streamlit as st
from PIL import Image
import numpy as np
import easyocr

# --- [1. 깃북 기반 통합 가이드 데이터] ---
ASSET_GUIDE = {
    "광고 목록화면": {"size": (720, 360), "kb": 200},
    "광고 상세화면": {"size": (720, 780), "kb": 400},
    "참여중 영역": {"size": (144, 144), "kb": 100},
    "퀴즈 상세화면": {"size": (720, 780), "kb": 400},
    "영상형 띠배너": {"size": (720, 200), "kb": 200},
    "2차 팝업": {"size": (720, 360), "kb": 200},
    "상세 화면 설명": {"size": (720, -1), "kb": 400} 
}

FORBIDDEN_COLORS = ["#fefefe", "#f6f6f6", "#000000", "#f7f7f7"]
BAN_WORDS = ['설치', '실행', '다운', '다운로드']

# --- [2. 색상 검수 함수] ---
def hex_to_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

def check_bg_color(img):
    img_rgb = img.convert('RGB')
    w, h = img_rgb.size
    pixels = [img_rgb.getpixel((0,0)), img_rgb.getpixel((w-1, 0)), 
              img_rgb.getpixel((0, h-1)), img_rgb.getpixel((w-1, h-1))]
    avg_color = np.mean(pixels, axis=0)
    for f_hex in FORBIDDEN_COLORS:
        if np.all(np.abs(avg_color - hex_to_rgb(f_hex)) < 15):
            return f_hex
    return None

# --- [3. Streamlit UI 구성] ---
st.set_page_config(page_title="쿠키오븐 통합 검수 v4.2", layout="wide")
st.title("🍪 쿠키오븐 제작가이드 통합 검수 (v4.2)")
st.caption("네이버쇼핑 CPS, 라이브방송 등 모든 특수 가이드 수치가 반영되었습니다.")

file = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'])

if file:
    img = Image.open(file)
    img_np = np.array(img.convert('RGB'))
    w, h = img.size
    kb = len(file.getvalue()) / 1024
    
    # 유형 판별
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
        special_notices = []

        # --- A. 규격 및 용량 검수 ---
        if res_type in ASSET_GUIDE:
            st.write(f"✔️ **이미지 규격 일치** ({w}x{h}px)")
            limit_kb = ASSET_GUIDE[res_type]['kb']
            if kb <= limit_kb:
                st.write(f"✔️ **용량 준수** ({kb:.1f}KB / 기준 {limit_kb}KB 이하)")
                passes.append(f"용량 준수: {kb:.1f}KB")
            else:
                errors.append(f"용량 초과: 현재 {kb:.1f}KB (기준 {limit_kb}KB 이하)")
        else:
            errors.append(f"규격 위반: {w}x{h}px은 표준 가이드 규격이 아닙니다.")

        # --- B. 배경색 검수 ---
        bad_bg = check_bg_color(img)
        if bad_bg:
            errors.append(f"배경색 위반: 금지된 단색 배경({bad_bg}) 감지")
        else:
            passes.append("배경색 규정 준수")

        # --- C. OCR 분석 및 특수 가이드 체크 ---
        with st.spinner("텍스트 및 특수 가이드 분석 중..."):
            reader = easyocr.Reader(['ko','en'])
            ocr_res = reader.readtext(img_np, detail=0)
            full_txt = "".join(ocr_res).replace(" ", "")

        # 명칭 및 금지문구
        if any(bad in full_txt for bad in ['포인트', '캐시', '리워드', '혜택']):
            errors.append("🚨 명칭 위반: 반드시 '쿠키'로 기재 (포인트/캐시 등 감지)")
        if any(ban in full_txt for ban in BAN_WORDS):
            errors.append("🚨 금지 문구: '설치/실행' 등 사용 불가. '접속하기' 권장")

        # 특수 가이드 감지 (네이버쇼핑, 라이브방송 등)
        if "쇼핑" in full_txt or "N쇼핑" in full_txt:
            special_notices.append("🛒 **네이버쇼핑 CPS 감지:** 이미지 여백(상하 40/42px, 좌우 44px)과 텍스트 높이 가이드를 준수했는지 수동 확인이 필요합니다.")
        
        if "LIVE" in full_txt or "라이브" in full_txt:
            special_notices.append("📺 **라이브 방송 감지:** 상단 38px, 하단 32px, 양측 36px 여백을 유지하고 'LIVE' 영역과 겹치지 않는지 확인하세요.")
            
        if res_type == "영상형 띠배너":
            special_notices.append("🎞️ **영상형 띠배너 유의사항:** 영상 내 여백이 없을 경우 상단에 10px의 흰색 여백을 추가해야 합니다.")

        # --- 결과 출력 ---
        st.divider()
        if not errors:
            st.success("🎉 기본 수치 검사 통과! 아래 특수 가이드 및 체크리스트를 최종 확인하세요.")
            st.balloons()
        else:
            st.error("🚨 수정이 필요한 항목이 있습니다.")
            for err in errors:
                st.write(f"- {err}")
        
        if special_notices:
            st.info("💡 **유형별 특수 가이드 안내**")
            for notice in special_notices:
                st.write(notice)
        
        with st.expander("✅ 합격 항목 확인"):
            for p in passes: st.write(f"✔️ {p}")

    with st.sidebar:
        st.markdown("### 📝 수동 확인 필수 리스트")
        st.write("1. **기기 목업 사용 금지:** 스마트폰 베젤, 홈버튼 등이 포함되었는지 확인하세요.")
        st.write("2. **쿠키 아이콘 여백:** 하단 22px, 우측 30px 여백 준수 여부.")
        st.write("3. **심의필 위치:** 우하단 배치 및 여백(하단 22px, 우측 36px).")
        st.write("4. **에셋 제출:** PNG/JPG와 함께 **PSD 파일** 동봉 필수.")