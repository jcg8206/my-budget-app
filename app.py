import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

# 1. Page Configuration & Custom CSS
st.set_page_config(
    page_title="공모과제 예산 & 지출 통합관리 웹페이지",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI Polish
st.markdown("""
<style>
    .main-title {
        font-size: 26px;
        font-weight: 800;
        color: #1B365D;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 14px;
        color: #64748B;
        margin-bottom: 25px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 22px;
        font-weight: 700;
        color: #1E293B;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: #F1F5F9;
        border-radius: 6px;
        color: #334155;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1B365D !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. Session State Initialization (Persistent Local Storage)
@st.cache_data
def load_initial_data():
    try:
        p_df = pd.read_csv("budget_projects.csv")
    except:
        p_df = pd.DataFrame(columns=["과제코드", "과제/사업단명", "책임자", "배정예산액", "비고"])
        
    try:
        c_df = pd.read_csv("categories.csv")
    except:
        c_df = pd.DataFrame(columns=["비목", "보조비목", "보조세목", "설명"])
        
    try:
        e_df = pd.read_csv("expenses.csv")
    except:
        e_df = pd.DataFrame(columns=["No", "지출일자", "과제/사업단명", "비목", "보조비목", "보조세목", "지출액", "지출처/적요", "지급상태", "비고"])
    
    return p_df, c_df, e_df

init_p, init_c, init_e = load_initial_data()

if "budget_projects" not in st.session_state:
    st.session_state["budget_projects"] = init_p
if "categories" not in st.session_state:
    st.session_state["categories"] = init_c
if "expenses" not in st.session_state:
    st.session_state["expenses"] = init_e

# 3. Sidebar Navigation & Global Info
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/analytics.png", width=60)
    st.markdown("## 🏛️ 공모과제 예산 관리")
    st.markdown("**통합 예산 편성 및 실시간 지출 시스템**")
    st.divider()
    
    menu = st.radio(
        "📌 메뉴 선택",
        [
            "📊 통합 대시보드",
            "💰 예산 편성 및 사업단 관리",
            "📝 지출 내역 입력 및 수정",
            "🏷️ 예산 세목 기준표 설정",
            "📁 엑셀 내보내기 & 백업"
        ]
    )
    st.divider()
    
    # Real-time Quick Summary in Sidebar
    total_budget_sum = st.session_state["budget_projects"]["배정예산액"].sum() if not st.session_state["budget_projects"].empty else 0
    total_expense_sum = st.session_state["expenses"]["지출액"].sum() if not st.session_state["expenses"].empty else 0
    total_balance_sum = total_budget_sum - total_expense_sum
    rate = (total_expense_sum / total_budget_sum * 100) if total_budget_sum > 0 else 0
    
    st.markdown("### 📈 전체 현황 요약")
    st.caption(f"**총 예산:** ₩{total_budget_sum:,.0f}")
    st.caption(f"**총 집행:** ₩{total_expense_sum:,.0f}")
    st.caption(f"**총 잔액:** ₩{total_balance_sum:,.0f}")
    st.progress(min(int(rate), 100))
    st.caption(f"**전체 집행률:** {rate:.1f}%")

# Main Header
st.markdown('<div class="main-header">공모과제 예산 & 지출 통합 관리 웹 애플리케이션</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">모든 담당자가 웹에서 실시간으로 예산, 항목, 세목, 지출내역을 자유롭게 입력하고 수정할 수 있습니다.</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE 1: 📊 통합 대시보드
# ----------------------------------------------------
if menu == "📊 통합 대시보드":
    st.subheader("📊 전체 예산 및 과제별 집행 현황")
    
    # Top KPI Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("총 배정 예산액", f"₩{total_budget_sum:,.0f}")
    with c2:
        st.metric("총 지출 집행액", f"₩{total_expense_sum:,.0f}")
    with c3:
        st.metric("총 예산 잔액", f"₩{total_balance_sum:,.0f}")
    with c4:
        st.metric("전체 집행률", f"{rate:.1f}%")
        
    st.divider()
    
    # Calculate Department-wise Aggregate Data
    p_df = st.session_state["budget_projects"].copy()
    e_df = st.session_state["expenses"].copy()
    
    exp_by_proj = e_df.groupby("과제/사업단명")["지출액"].sum().reset_index() if not e_df.empty else pd.DataFrame(columns=["과제/사업단명", "지출액"])
    
    merged_dash = pd.merge(p_df, exp_by_proj, on="과제/사업단명", how="left").fillna({"지출액": 0})
    merged_dash["잔액"] = merged_dash["배정예산액"] - merged_dash["지출액"]
    merged_dash["집행률(%)"] = np.where(merged_dash["배정예산액"] > 0, (merged_dash["지출액"] / merged_dash["배정예산액"] * 100).round(1), 0)
    
    def get_status(r):
        if r > 100:
            return "🔴 초과집행"
        elif r >= 85:
            return "🟡 집행임박"
        else:
            return "🟢 정상"
            
    merged_dash["상태"] = merged_dash["집행률(%)"].apply(get_status)
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("#### 🏢 과제/사업단별 집행 현황")
        st.dataframe(
            merged_dash[["과제코드", "과제/사업단명", "책임자", "배정예산액", "지출액", "잔액", "집행률(%)", "상태"]],
            use_container_width=True,
            column_config={
                "배정예산액": st.column_config.NumberColumn(format="₩%d"),
                "지출액": st.column_config.NumberColumn(format="₩%d"),
                "잔액": st.column_config.NumberColumn(format="₩%d"),
                "집행률(%)": st.column_config.NumberColumn(format="%.1f%%")
            },
            hide_index=True
        )
        
    with col_right:
        st.markdown("#### 📈 과제별 예산 vs 지출 비교")
        if not merged_dash.empty:
            fig = px.bar(
                merged_dash,
                x="과제코드",
                y=["배정예산액", "지출액"],
                barmode="group",
                title="과제별 예산 및 지출액 비교",
                labels={"value": "금액(원)", "variable": "구분"},
                color_discrete_map={"배정예산액": "#1B365D", "지출액": "#008080"}
            )
            fig.update_layout(height=380, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # Category Wise Breakdown
    st.divider()
    st.markdown("#### 🏷️ 비목별 지출 분포")
    if not e_df.empty and "비목" in e_df.columns:
        cat_exp = e_df.groupby("비목")["지출액"].sum().reset_index()
        fig_pie = px.pie(
            cat_exp,
            values="지출액",
            names="비목",
            hole=0.4,
            title="비목별 지출 비율",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

# ----------------------------------------------------
# PAGE 2: 💰 예산 편성 및 사업단 관리
# ----------------------------------------------------
elif menu == "💰 예산 편성 및 사업단 관리":
    st.subheader("💰 과제/사업단 등록 및 예산 배정 관리")
    st.info("💡 새로운 세부과제/사업단을 등록하거나 기존 사업단의 예산액, 책임자, 과제명을 수정할 수 있습니다.")
    
    tab1, tab2 = st.tabs(["➕ 신규 과제/사업단 추가", "✏️ 예산 편성 및 수정 (테이블 에디터)"])
    
    with tab1:
        st.markdown("##### 📌 신규 공모과제 등록")
        with st.form("add_project_form", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                p_code = st.text_input("과제 코드 (예: 4-3-12)")
                p_name = st.text_input("과제 / 사업단명")
            with col_b:
                p_leader = st.text_input("과제 책임자")
                p_budget = st.number_input("배정 예산액 (원)", min_value=0, step=1000000, value=10000000)
            with col_c:
                p_note = st.text_area("비고 / 메모", height=108)
                
            submit_proj = st.form_submit_button("🚀 과제 등록 완료")
            
            if submit_proj:
                if not p_name or not p_code:
                    st.error("과제 코드와 과제/사업단명은 필수 입력 사항입니다.")
                else:
                    new_proj = {
                        "과제코드": p_code,
                        "과제/사업단명": p_name,
                        "책임자": p_leader,
                        "배정예산액": p_budget,
                        "비고": p_note
                    }
                    st.session_state["budget_projects"] = pd.concat([st.session_state["budget_projects"], pd.DataFrame([new_proj])], ignore_index=True)
                    st.success(f"'{p_name}' 과제가 성공적으로 등록되었습니다!")
                    st.rerun()

    with tab2:
        st.markdown("##### ✏️ 전체 예산 편성표 수정")
        st.caption("표에서 직접 칸을 클릭하여 과제명, 예산, 책임자 등을 수정하면 즉시 전체 시스템에 반영됩니다.")
        
        edited_proj_df = st.data_editor(
            st.session_state["budget_projects"],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "배정예산액": st.column_config.NumberColumn(format="₩%d", step=100000)
            },
            key="proj_editor"
        )
        
        if st.button("💾 예산 편성 변경사항 저장"):
            st.session_state["budget_projects"] = edited_proj_df
            st.success("예산 편성 정보가 업데이트되었습니다!")
            st.rerun()

# ----------------------------------------------------
# PAGE 3: 📝 지출 내역 입력 및 수정
# ----------------------------------------------------
elif menu == "📝 지출 내역 입력 및 수정":
    st.subheader("📝 지출 내역 간편 입력 및 통합 관리")
    
    tab_exp1, tab_exp2 = st.tabs(["➕ 신규 지출 등록", "✏️ 지출 내역 종합 수정 (실시간 에디터)"])
    
    proj_list = st.session_state["budget_projects"]["과제/사업단명"].tolist() if not st.session_state["budget_projects"].empty else ["선택가능 과제없음"]
    cat_df = st.session_state["categories"]
    bimok_list = cat_df["비목"].unique().tolist() if not cat_df.empty else ["운영비", "인건비", "여비"]
    
    with tab_exp1:
        st.markdown("##### 📥 신규 지출 등록 폼")
        with st.form("add_expense_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                e_date = st.date_input("지출 일자", datetime.now())
                e_proj = st.selectbox("관련 과제/사업단", proj_list)
                e_amount = st.number_input("지출 금액 (원)", min_value=0, step=10000, value=50000)
            with col2:
                e_bimok = st.selectbox("비목 (대분류)", bimok_list)
                filtered_sub = cat_df[cat_df["비목"] == e_bimok] if not cat_df.empty else pd.DataFrame()
                sub_list = filtered_sub["보조비목"].unique().tolist() if not filtered_sub.empty else ["일반수용비"]
                e_sub_bimok = st.selectbox("보조비목 (중분류)", sub_list)
                e_semok = st.text_input("보조세목 (소분류)", value="일반수용비")
            with col3:
                e_details = st.text_input("지출처 / 적요 내용", placeholder="예: 5월 실무협의회 회의비 결제")
                e_status = st.selectbox("지급 상태", ["지급완료", "결재대기", "보완요청", "지급취소"])
                e_notes = st.text_input("비고 (증빙 구분 등)", placeholder="예: 법인카드 / E나라도움")
                
            submit_exp = st.form_submit_button("🚀 지출 내역 추가")
            
            if submit_exp:
                max_no = st.session_state["expenses"]["No"].max() if not st.session_state["expenses"].empty else 0
                new_exp = {
                    "No": max_no + 1,
                    "지출일자": str(e_date),
                    "과제/사업단명": e_proj,
                    "비목": e_bimok,
                    "보조비목": e_sub_bimok,
                    "보조세목": e_semok,
                    "지출액": e_amount,
                    "지출처/적요": e_details,
                    "지급상태": e_status,
                    "비고": e_notes
                }
                st.session_state["expenses"] = pd.concat([st.session_state["expenses"], pd.DataFrame([new_exp])], ignore_index=True)
                st.success("지출 내역이 성공적으로 입력되었습니다!")
                st.rerun()

    with tab_exp2:
        st.markdown("##### ✏️ 전체 지출 내역 실시간 테이블 수정")
        st.caption("표 안의 임의의 칸을 더블클릭하여 일자, 과제, 금액, 적요 등을 직접 수정할 수 있습니다. 행 삭제/추가도 가능합니다.")
        
        # Filter options
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_proj = st.multiselect("과제/사업단 필터", options=proj_list, default=[])
        with col_f2:
            filter_status = st.multiselect("지급상태 필터", options=["지급완료", "결재대기", "보완요청", "지급취소"], default=[])
            
        view_exp_df = st.session_state["expenses"].copy()
        if filter_proj:
            view_exp_df = view_exp_df[view_exp_df["과제/사업단명"].isin(filter_proj)]
        if filter_status:
            view_exp_df = view_exp_df[view_exp_df["지급상태"].isin(filter_status)]
            
        edited_exp_df = st.data_editor(
            view_exp_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "지출액": st.column_config.NumberColumn(format="₩%d", step=10000),
                "지출일자": st.column_config.DateColumn(format="YYYY-MM-DD"),
                "지급상태": st.column_config.SelectboxColumn(options=["지급완료", "결재대기", "보완요청", "지급취소"])
            },
            key="exp_editor"
        )
        
        if st.button("💾 지출 내역 변경사항 저장"):
            # Update main dataframe
            if not filter_proj and not filter_status:
                st.session_state["expenses"] = edited_exp_df
            else:
                # Merge updates back
                st.session_state["expenses"].update(edited_exp_df)
            st.success("지출 내역이 업데이트되었습니다!")
            st.rerun()

# ----------------------------------------------------
# PAGE 4: 🏷️ 예산 세목 기준표 설정
# ----------------------------------------------------
elif menu == "🏷️ 예산 세목 기준표 설정":
    st.subheader("🏷️ 비목 / 보조비목 / 보조세목 표준 관리")
    st.info("💡 조직 내에서 사용할 예산 항목 체계를 설정합니다. 여기서 설정된 비목은 지출 입력 시 선택목록에 반영됩니다.")
    
    edited_cat_df = st.data_editor(
        st.session_state["categories"],
        num_rows="dynamic",
        use_container_width=True,
        key="cat_editor"
    )
    
    if st.button("💾 비목 체계 저장"):
        st.session_state["categories"] = edited_cat_df
        st.success("비목 표준 기준표가 업데이트되었습니다!")
        st.rerun()

# ----------------------------------------------------
# PAGE 5: 📁 엑셀 내보내기 & 백업
# ----------------------------------------------------
elif menu == "📁 엑셀 내보내기 & 백업":
    st.subheader("📁 데이터 내보내기 및 복원")
    st.markdown("웹에 작성된 모든 예산 및 지출 내역을 **엑셀 파일(.xlsx)** 형태로 다운로드하거나, 이전에 백업해둔 엑셀을 업로드하여 데이터를 원복할 수 있습니다.")
    
    col_exp, col_imp = st.columns(2)
    
    with col_exp:
        st.markdown("#### 📥 엑셀 내보내기")
        st.write("현재 작성된 통합 예산/지출 데이터를 멀티 탭 엑셀 파일로 생성합니다.")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            st.session_state["budget_projects"].to_excel(writer, sheet_name="예산편성_사업단", index=False)
            st.session_state["expenses"].to_excel(writer, sheet_name="지출내역", index=False)
            st.session_state["categories"].to_excel(writer, sheet_name="예산비목기준표", index=False)
            
        st.download_button(
            label="⬇️ 전체 데이터 엑셀 파일 다운로드 (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"공모과제_예산_지출_통합관리_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    with col_imp:
        st.markdown("#### 📤 데이터 업로드 복원")
        st.write("백업해둔 엑셀이나 CSV 데이터를 업로드하여 웹 애플리케이션 데이터를 교체합니다.")
        uploaded_file = st.file_uploader("CSV 파일 선택", type=["csv"])
        if uploaded_file is not None:
            try:
                up_df = pd.read_csv(uploaded_file)
                st.write("업로드된 데이터 미리보기:", up_df.head(3))
                if st.button("이 데이터로 지출내역 교체하기"):
                    st.session_state["expenses"] = up_df
                    st.success("지출 내역이 성공적으로 복원되었습니다!")
                    st.rerun()
            except Exception as e:
                st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
