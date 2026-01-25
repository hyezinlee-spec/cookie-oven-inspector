import streamlit as st
from PIL import Image
import numpy as np
import easyocr
import google.generativeai as genai

# --- [1. Google AI API 설정] ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 모델명 절대 변경 금지 유지
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
    mockup_instruction = "단, '참여중 영역' 소재는 기기 목업이 포함되어도 괜찮아." if res_type == "참여중 영역" else "스마트폰 베젤, 홈버튼, 노치 등 기기 형태가 포함되어 있는지 확인해줘."
    
    # AI가 Markdown 줄바꿈(\n)을 확실히 인식하도록 지침 강화
    prompt = f"""
    너는 네이버웹툰 광고 검수 전문가야. 이미지를 분석하여 오직 아래의 양식으로만 답변해. 
    **반드시 각 라인 끝에 줄바꿈을 한 번씩 넣어서 항목을 명확히 구분해.** 항목명은 반드시 볼드체(**)로 작성해.

    [응답 양식 예시]
    ****· 디바이스 목업사용 :** 의심되지 않습니다**
    \n
    ****· 저작권 문제 :** 문제 되지 않습니다**
    \n
    ****· 가독성 :** 문제 되지 않습니다**

    [판단 기준]
    1. 목업: {mockup_instruction} 기기 외곽선이 보이면 '의심됩니다'.
    2. 저작권: 확인이 필요한 실사/제품 이미지가 보이면 '사용된 제품 및 실사 이미지 저작권 문제 없을지 체크 바랍니다'. 아닐 경우 '문제 되지 않습니다'.
    3. 가독성: 텍스트 가독성이 떨어지거나 깨진 디자인이 있다면 '텍스트와 이미지소스가 겹쳐보이니 가독성을 위해 수정 바랍니다'. 아닐 경우 '문제 되지 않습니다'.
    """
    response = model.generate_content([prompt, image])
    return response.text

# --- [4. UI 및 메인 로직] ---
st.set_page_config(page_title="쿠키오븐 통합 검수 v5.8", layout="wide")
st.title("🍪 쿠키오븐 제작가이드 통합 검수 (v5.8)")

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

        bad_bg = check_bg_color(img)
        if bad_bg:
            errors.append(f"배경색 위반: 금지된 단색 배경({bad_bg}) 감지")
        else:
            passes.append("배경색 규정 준수")

        with st.spinner("AI가 시각 요소 및 퀄리티를 분석 중입니다..."):
            ai_opinion = check_visual_ai(img, res_type)
            reader = easyocr.Reader(['ko','en'])
            ocr_res = reader.readtext(img_np, detail=0)
            full_txt = "".join(ocr_res).replace(" ", "")

        if "의심됩니다" in ai_opinion and res_type != "참여중 영역":
            errors.append("🚨 **디바이스 목업 감지:** 기기 외곽선(베젤, 노치 등)이 발견되었습니다.")
        
        if "웹툰쿠키" in full_txt or "시리즈쿠키" in full_txt:
            special_notices.append("⚠️ **명칭 통일 권장:** 웹툰/시리즈 두 플랫폼 모두 운영할 경우 '쿠키'로 명칭을 통일해주세요.")

        if any(ban in full_txt for ban in BAN_WORDS):
            errors.append("🚨 **금지 문구:** '설치/실행' 등 문구 사용 불가")

        st.divider()
        if not errors:
            st.success("🎉 기본 수치 및 정책 검사 통과!")
            st.balloons()
        else:
            for err in errors: st.error(err)
        
        if special_notices:
            for notice in special_notices: st.info(notice)
        
        # st.markdown을 사용하여 AI가 생성한 Markdown 형식을 확실하게 렌더링
        st.info("💡 **AI 분석 의견**")
        st.markdown(ai_opinion)

    with st.sidebar:
        st.header("📝 소재별 체크리스트")
        st.write("📍 **[공통]** 원본 **PSD 파일** 제출 필수")
        st.write("📍 **[공통]** 배경색 대비 로고/텍스트 가독성 확인")
        st.write("📍 **[공통]** 심의필 위치 및 여백 확인 (우하단)")
        st.write("📍 **[공통]** 저작권/초상권 확보 이미지 사용 여부")
        
        if res_type != "참여중 영역" and res_type != "미분류":
            st.warning("🚫 **디바이스 목업 사용 금지:** 스마트폰 베젤, 홈버튼 등이 포함되지 않았나요?")
        
        if res_type == "광고 목록화면":
            st.info("🍪 **쿠키 아이콘 여백:** 하단 22px, 우측 30px 준수")

        if res_type == "참여중 영역":
            st.success("📱 **참여중 영역:** 앱 마켓 로고 사용 권장")
            st.write("✔️ 이 유형은 기기 목업 사용이 허용됩니다.")

        if res_type == "상세 화면 설명":
            st.markdown("---")
            st.subheader("🔍 상세 설명 이미지 전용")
            st.write("- 나눔고딕 폰트 / PNG 형식 준수")
            st.write("- 라이트/다크모드 2종 필수 제작")