import streamlit as st
from PIL import Image
import numpy as np
import easyocr
import google.generativeai as genai

# --- [준비단계] Google AI API 키 설정 (Secrets 활용) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("API 키가 설정되지 않았습니다. Streamlit Cloud의 Secrets 설정을 확인하세요.")
    st.stop()

# --- [1. 깃북 기반 통합 가이드 데이터 세팅] ---
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

# --- [2. 핵심 검수 함수] ---
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

def check_visual_elements(image):
    """Gemini API를 사용하여 시각적 목업 및 저작권 요소를 판단"""
    prompt = """
    너는 '네이버웹툰 쿠키오븐' 광고 소재 검수 전문가야. 업로드된 이미지에서 다음 위반 사항을 엄격히 확인해줘.
    
    1. 디바이스 목업: 스마트폰의 베젤, 홈버튼, 노치 등 기기 외곽 형태가 조금이라도 포함되어 있는가? (가장 중요)
    2. 플랫폼 명칭: '웹툰 쿠키'나 '시리즈 쿠키'라고 썼는가? (그냥 '쿠키'로 통일 권장)
    3. 저작권/초상권: 연예인 실사나 특정 상품 브랜드 컷이 포함되어 저작권 확인이 필요한가?
    4. 가독성: 배경색 때문에 로고나 글자가 잘 안 보이는가?

    형식:
    [목업여부: YES/NO] 
    [플랫폼명칭: PASS/FAIL]
    분석 의견: 
    """
    response = model.generate_content([prompt, image])
    return response.text

# --- [3. Streamlit UI 및 메인 로직] ---
st.set_page_config(page_title="쿠키오븐 통합 검수 v5.0", layout="wide")
st.title("🍪 쿠키오븐 제작가이드 통합 검수 (v5.0)")
st.caption("Gemini AI 시각 검수와 수치 검증이 통합된 최종 버전입니다.")

file = st.file_uploader("검수할 이미지 파일을 업로드하세요", type=['png', 'jpg', 'jpeg'])

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
        st.image(img, use_container_width=True, caption=f"분석 대상: {res_type} ({w}x{h}px)")

    with col2:
        st.subheader(f"📊 검수 리포트: {res_type}")
        errors = []
        passes = []
        special_notices = []

        # --- A. 규격 및 용량 검수 (즉시 노출) ---
        if res_type in ASSET_GUIDE:
            st.write(f"✔️ **이미지 규격 일치** ({w}x{h}px)")
            limit_kb = ASSET_GUIDE[res_type]['kb']
            if kb <= limit_kb:
                st.write(f"✔️ **용량 준수** ({kb:.1f}KB / 기준 {limit_kb}KB 이하)")
                passes.append(f"용량 준수: {kb:.1f}KB")
            else:
                errors.append(f"용량 초과: 현재 {kb:.1f}KB (기준 {limit_kb}KB 이하)")
        else:
            errors.append(f"규격 위반: {w}x{h}px은 가이드에 정의된 표준 규격이 아닙니다.")

        # --- B. 배경색 검수 ---
        bad_bg = check_bg_color(img)
        if bad_bg:
            errors.append(f"배경색 위반: 금지된 단색 배경({bad_bg}) 감지")
        else:
            passes.append("배경색 규정 준수")

        # --- C. 지능형 시각 및 텍스트 검수 ---
        with st.spinner("AI가 이미지를 정밀 분석 중입니다..."):
            # 1. Gemini AI 시각 분석
            ai_opinion = check_visual_elements(img)
            
            # 2. 전통적 OCR 분석 (금지 단어)
            reader = easyocr.Reader(['ko','en'])
            ocr_res = reader.readtext(img_np, detail=0)
            full_txt = "".join(ocr_res).replace(" ", "")

        # AI 분석 결과 기반 에러 추가
        if "[목업여부: YES]" in ai_opinion:
            errors.append(f"🚨 **디바이스 목업 감지:** {ai_opinion}")
        if "[플랫폼명칭: FAIL]" in ai_opinion:
            special_notices.append("⚠️ **명칭 통일 권장:** '웹툰/시리즈 쿠키' 대신 **'쿠키'**로 표기하세요.")

        # 금지문구 및 명칭 (수치적 체크)
        if any(bad in full_txt for bad in ['포인트', '캐시', '리워드', '혜택']):
            errors.append("🚨 명칭 위반: 반드시 '쿠키'로 기재 (포인트/캐시 등 감지)")
        if any(ban in full_txt for ban in BAN_WORDS):
            errors.append("🚨 금지 문구: '설치/실행' 등 사용 불가. '접속하기' 권장")

        # 유형별 특수 알림
        if "쇼핑" in full_txt or "N쇼핑" in full_txt:
            special_notices.append("🛒 **네이버쇼핑 CPS 감지:** 이미지 여백(상하 40/42px, 좌우 44px) 수동 확인 필요")
        if "LIVE" in full_txt or "라이브" in full_txt:
            special_notices.append("📺 **라이브 방송 감지:** 상단 38px, 하단 32px, 양측 36px 여백 준수 확인")

        # --- 결과 출력 ---
        st.divider()
        if not errors:
            st.success("🎉 모든 가이드를 통과했습니다! 아래 특이사항만 최종 확인하세요.")
            st.balloons()
        else:
            st.error("🚨 수정이 필요한 항목이 있습니다.")
            for err in errors: st.write(f"- {err}")
        
        if special_notices:
            st.info("💡 **알림 및 권장 사항**")
            for notice in special_notices: st.write(notice)
        
        with st.expander("✅ 합격 항목 상세 확인"):
            for p in passes: st.write(f"✔️ {p}")

    # --- [4. 소재별 가변형 사이드바] ---
    with st.sidebar:
        st.markdown("### 📝 소재별 수동 확인 리스트")
        st.write("📍 **[공통]** 심의필 위치 및 여백 (하단 22px, 우측 36px)")
        st.write("📍 **[공통]** 원본 **PSD 파일** 동봉 여부")
        st.write("📍 **[공통]** 배경색 대비 로고/텍스트 가독성")
        
        if res_type == "광고 목록화면":
            st.info("🍪 **쿠키 아이콘 여백:** 하단 22px, 우측 30px 준수")
        if res_type == "참여중 영역":
            st.success("📱 **참여중 영역 전용:** 앱 마켓 로고 사용 권장")
        if res_type == "상세 화면 설명":
            st.markdown("---")
            st.write("🔍 **상세화면 전용 체크**")
            st.write("- 나눔고딕 폰트 / PNG 형식 준수")
            st.write("- 라이트/다크모드 2종 제작 여부")