import streamlit as st
from PIL import Image
import numpy as np

# --- 5개 PDF 가이드라인 기반 통합 데이터 세팅 ---
FULL_GUIDE = {
    "광고 목록화면": {"size": (720, 360), "limit_kb": 200, "desc": "가이드 4~5p 참조"},
    "광고 상세화면": {"size": (720, 780), "limit_kb": 400, "desc": "가이드 9~10p 참조"},
    "영상형 띠배너": {"size": (720, 210), "limit_kb": 200, "desc": "가이드 2p 참조"},
    "2차 팝업": {"size": (720, 360), "limit_kb": 200, "desc": "가이드 25p 참조 (텍스트 150자 이내)"},
    "상세 이벤트 이미지": {"size": (720, "variable"), "limit_kb": 1000, "desc": "가이드 5~6p 참조, 세로 길이는 가변"},
    "참여중 영역": {"size": (144, 144), "limit_kb": 100, "desc": "가이드 19p 참조"},
    "아이콘형 소재": {"size": (120, 120), "limit_kb": 50, "desc": "가이드 21p 참조"}
}

# 검수 로직 함수 보강
def check_dimensions(w, h):
    for name, spec in FULL_GUIDE.items():
        target_w = spec['size'][0]
        target_h = spec['size'][1]
        
        # 가변 세로형 처리 (상세 이벤트 등)
        if target_h == "variable":
            if w == target_w: return name
        # 일반 정규 규격 처리
        elif (w, h) == (target_w, target_h):
            return name
    return "미분류/규격외 소재"

# --- Streamlit UI 부분 ---
st.title("🍪 쿠키오븐 통합 소재 검수 (v1.1)")
st.caption("5개의 PDF 가이드라인(멀티미션, 상세이벤트, 팝업 등)이 모두 통합된 버전입니다.")

uploaded_file = st.file_uploader("이미지 업로드", type=['png', 'jpg'])

if uploaded_file:
    img = Image.open(uploaded_file)
    w, h = img.size
    kb = len(uploaded_file.getvalue()) / 1024
    
    res_type = check_dimensions(w, h)
    
    st.subheader(f"📊 판별 결과: {res_type}")
    
    # 1. 규격/용량 검사
    if res_type in FULL_GUIDE:
        spec = FULL_GUIDE[res_type]
        st.write(f"📍 **참조 가이드:** {spec['desc']}")
        
        if kb > spec['limit_kb']:
            st.error(f"❌ 용량 초과: {kb:.1f}KB (기준: {spec['limit_kb']}KB)")
        else:
            st.success(f"✅ 용량 통과: {kb:.1f}KB")
    else:
        st.warning("⚠️ 규격 불일치: 쿠키오븐 표준 규격이 아닙니다. PDF 가이드를 다시 확인하세요.")

    # [중요] 상세 이벤트 이미지 전용 안내
    if "상세 이벤트" in res_type:
        st.info("💡 상세 이벤트 이미지는 가로 720px 고정, 세로는 가변입니다. 디자인 요소 중복 여부를 수동 확인하세요.")

    # 2. 텍스트/안전영역 검수 (이전 OCR 로직과 결합)
    # ... (OCR 관련 코드는 이전 답변과 동일하게 유지)