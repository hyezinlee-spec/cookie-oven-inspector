import streamlit as st
from PIL import Image
import numpy as np
import easyocr
import google.generativeai as genai

# --- [1. Google AI API 설정] ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-2.5-flash')
    else:
        st.error("❌ API 키가 설정되지 않았습니다. Streamlit Cloud의 Secrets 설정을 확인하세요.")
        st.stop()
except Exception as e:
    st.error(f"❌ API 연결 오류: {str(e)}")
    st.stop()

# --- [2. 가이드 데이터 세팅] ---
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

# --- [3. 검수 함수] ---
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

def check_visual_ai(image, res_type):
    # 소재 유형에 따른 맞춤형 AI 지시문
    mockup_instruction = "단, '참여중 영역' 소재는 기기 목업이 포함되어도 괜찮아." if res_type == "참여중 영역" else "스마트폰 베젤, 홈버튼, 노치 등 기기 형태가 포함되면 무조건 YES로 보고해."
    
    prompt = f"""
    너는 네이버웹툰 광고 검수 전문가야. 다음 사항을 엄격히 체크해줘:
    1. 디바이스 목업: {mockup_instruction}
    2. 플랫폼 명칭: '웹툰 쿠키'나 '시리즈 쿠키' 명칭이 보이면 '쿠키'로 통일하도록 지시해.
    3. 가독성: 배경색 때문에 로고나 텍스트가 묻히는 곳이 있는가?
    4. 저작권: 판매 상품 이미지나 인물 실사가 포함되어 저작권 확인이 필요한가?

    응답 형식:
    [목업여부: YES/NO] 
    [명칭여부: PASS/FAIL]
    [상세 의견]: 
    """
    response = model.generate_content([prompt, image])
    return response.text

# --- [4. UI 및 메인 로직] ---
st.set_page_config(page_title="쿠키오븐 통합 검수 v5.4", layout="wide")
st.title("🍪 쿠키오븐 제작가이드 통합 검수 (v5.4)")
st.caption("디바이스 목업 사용 금지 및 소재별 체크리스트가 보강된 최종 버전입니다.")

file = st.file_uploader("검수할 이미지 업로드", type=['png', 'jpg', 'jpeg'])

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
            res_type = name; break

    col1, col2 = st.columns(2)
    with col1:
        st.image(img, use_container_width=True, caption=f"분석 대상: {res_type}")

    with col2:
        st.subheader(f"📊 검수 리포트: {res_type}")
        errors, passes, special_notices = [], [], []

        # --- A. 규격 및 용량 ---
        if res_type in ASSET_GUIDE:
            st.write(f"✔️ **이미지 규격 일치** ({w}x{h}px)")
            limit_kb = ASSET_GUIDE[res_type]['kb']
            if kb <= limit_kb:
                st.write(f"✔️ **용량 준수** ({kb:.1f}KB / 기준 {limit_kb}KB 이하)")
                passes.append(f"용량 준수: {kb:.1f}KB")
            else:
                errors.append(f"용량 초과: 현재 {kb:.1f}KB (기준 {limit_kb}KB 이하)")
        else:
            errors.append(f"규격 위반: {w}x{h}px은 표준 규격이 아닙니다.")

        # --- B. 배경색 규정 ---
        bad_bg = check_bg_color(img)
        if bad_bg:
            errors.append(f"배경색 위반: 금지된 단색 배경({bad_bg}) 감지")
        else:
            passes.append("배경색 규정 준수")

        # --- C. AI 및 OCR 분석 ---
        with st.spinner("AI가 시각 요소 및 텍스트를 분석 중입니다..."):
            ai_opinion = check_visual_ai(img, res_type)
            reader = easyocr.Reader(['ko','en'])
            ocr_res = reader.readtext(img_np, detail=0)
            full_txt = "".join(ocr_res).replace(" ", "")

        if "[목업여부: YES]" in ai_opinion and res_type != "참여중 영역":
            errors.append("🚨 **디바이스 목업 감지:** 기기 외곽선(베젤, 노치 등)이 발견되었습니다.")
        
        if "[명칭여부: FAIL]" in ai_opinion or "웹툰쿠키" in full_txt or "시리즈쿠키" in full_txt:
            special_notices.append("⚠️ **명칭 통일 권장:** '웹툰/시리즈 쿠키' 대신 **'쿠키'**로 통일하세요.")

        if any(ban in full_txt for ban in BAN_WORDS):
            errors.append("🚨 **금지 문구:** '설치/실행' 등 문구 사용 불가")

        # --- 결과 출력 ---
        st.divider()
        if not errors:
            st.success("🎉 기본 수치 및 정책 검사 통과!")
            st.balloons()
        else:
            for err in errors: st.error(err)
        
        if special_notices:
            for notice in special_notices: st.info(notice)
        
        st.info(f"💡 **AI 분석 의견:**\n{ai_opinion}")

    # --- [5. 소재별 동적 사이드바] ---
    with st.sidebar:
        st.header("📝 소재별 체크리스트")
        
        # 공통 항목 (3, 4, 8, 9, 10번 반영)
        st.write("📍 **[공통]** 심의필 위치 및 여백 확인 (우하단)")
        st.write("📍 **[공통]** 원본 **PSD 파일** 제출 필수")
        st.write("📍 **[공통]** 배경색 대비 로고/텍스트 가독성 확인")
        st.write("📍 **[공통]** 저작권/초상권 확보 이미지 사용 여부")
        
        # 1번: 목업 사용 금지 (참여중 영역 제외 모든 상품)
        if res_type != "참여중 영역" and res_type != "미분류":
            st.warning("🚫 **디바이스 목업 사용 금지:** 스마트폰 베젤, 홈버튼 등이 포함되지 않았나요?")
        
        # 2번: 광고 목록화면 전용
        if res_type == "광고 목록화면":
            st.info("🍪 **쿠키 아이콘 여백:** 하단 22px, 우측 30px 준수")

        # 5번: 참여중 영역 전용
        if res_type == "참여중 영역":
            st.success("📱 **참여중 영역:** 앱 마켓 로고 사용 권장")
            st.write("✔️ 이 유형은 기기 목업 사용이 허용됩니다.")

        # 6번: 상세 화면 설명 전용
        if res_type == "상세 화면 설명":
            st.markdown("---")
            st.subheader("🔍 상세 설명 이미지 전용")
            st.write("- 나눔고딕 폰트 / PNG 형식 준수")
            st.write("- 라이트/다크모드 2종 필수 제작")