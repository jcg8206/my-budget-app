import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import io
import os

# 1. Page Configuration & Custom CSS
st.set_page_config(
    page_title="공모과제 예산 & 지출 통합관리 시스템",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
        margin-bottom: 20px;
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
        height: 42px;
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

# 2. Safe Data Loading & Persistence
def load_data():
    if os.path.exists("budget_projects.csv"):
        p_df = pd.read_csv("budget_projects.csv")
    else:
        p_df = pd.DataFrame(columns=["과제코드", "과제/사업단명", "책임자", "배정예산액", "비고"])
    p_df["배정예산액"] = pd.to_numeric(p_df["배정예산액"], errors="coerce").fillna(0).astype(int)

    if os.path.exists("categories.csv"):
        c_df = pd.read_csv("categories.csv")
    else:
        c_df = pd.DataFrame(columns=["비목", "보조비목", "보조세목", "설명"])

    if os.path.exists("expenses.csv"):
        e_df = pd.read_csv("expenses.csv")
    else:
        e_df = pd.DataFrame(columns=["No", "지출일자", "과제/사업단명", "비목", "보조비목", "보조세목", "지출액", "지출처/적요", "지급상태", "비고"])
    
    e_df["지출액"] = pd.to_numeric(e_df["지출액"], errors="coerce").fillna(0).astype(int)
    if "No" in e_df.columns:
        e_df["No"] = pd.to_numeric(e_df["No"], errors="coerce").fillna(1).astype(int)
    
    return p_df, c_df, e_df

if "budget_projects" not in st.session_state or "expenses" not in st.session_state or "categories" not in st.session_state:
    p, c, e = load_data()
    st.session_state["budget_projects"] = p
    st.session_state["categories"] = c
    st.session_state["expenses"] = e

def save_data_to_csv():
    try:
        st.session_state["budget_projects"].to_csv("budget_projects.csv", index=False, encoding="utf-8-sig")
        st.session_state["categories"].to_csv("categories.csv", index=False, encoding="utf-8-sig")
        st.session_state["expenses"].to_csv("expenses.csv", index=False, encoding="utf-8-sig")
    except Exception:
        pass

# 3. Helper Functions for Cascading Category Dropdowns
def get_bimok_list():
    c_df = st.session_state["categories"]
    if not c_df.empty and "비목" in c_df.columns:
        return c_df["비목"].dropna().unique().tolist()
    return ["운영비", "인건비", "여비"]

def get_bojo_bimok_list(selected_bimok):
    c_df = st.session_state["categories"]
    if not c_df.empty and "보조비목" in c_df.columns:
        filtered = c_df[c_df["비목"] == selected_bimok]
        if not filtered.empty:
            return filtered["보조비목"].dropna().unique().tolist()
    return ["일반수용비"]

def get_bojo_semok_list(selected_bimok, selected_bojo_bimok):
    c_df = st.session_state["categories"]
    if not c_df.empty and "보조세목" in c_df.columns:
        filtered = c_df[(c_df["비목"] == selected_bimok) & (c_df["보조비목"] == selected_bojo_bimok)]
        if not filtered.empty:
            return filtered["보조세목"].dropna().unique().tolist()
    return ["일반수용비(3)"]

# 4. Sidebar Navigation & Global Summary
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/analytics.png", width=50)
    st.markdown("## 🏛️ 예산 & 지출 관리")
    st.caption("공모과제 실시간 통합 관리 시스템")
    st.divider()
    
    menu = st.radio(
        "📌 메뉴 선택",
        [
            "📊 통합 대시보드",
            "🔍 과제별 상세 관리",
            "💰 예산 편성 및 사업단 관리",
            "📝 지출 내역 입력 및 수정",
            "🏷️ 예산 세목 기준표 설정",
            "📁 엑셀 내보내기 & 백업"
        ]
    )
    st.divider()
    
    t_budget = st.session_state["budget_projects"]["배정예산액"].sum() if not st.session_state["budget_projects"].empty else 0
    t_expense = st.session_state["expenses"]["지출액"].sum() if not st.session_state["expenses"].empty else 0
    t_balance = t_budget - t_expense
    t_rate = (t_expense / t_budget * 100) if t_budget > 0 else 0.0
    
    st.markdown("### 📈 전체 현황 요약")
    st.caption(f"**총 배정 예산:** ₩{t_budget:,.0f}")
    st.caption(f"**총 지출 금액:** ₩{t_expense:,.0f}")
    st.caption(f"**총 잔액:** ₩{t_balance:,.0f}")
    st.progress(min(int(t_rate), 100))
    st.caption(f"**종합 집행률:** {t_rate:.1f}%")

st.markdown('<div class="main-title">공모과제 예산 & 지출 통합 관리 웹 시스템</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">모든 담당자가 웹에서 실시간으로 예산, 과제별 내역, 세목, 지출을 자유롭게 조회하고 수정할 수 있습니다.</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE 1: 📊 통합 대시보드 (과제 추가/삭제 및 수정 기능 내장)
# ----------------------------------------------------
if menu == "📊 통합 대시보드":
    st.subheader("📊 전체 예산 및 과제별 집행 현황")
    
    # Key Summary Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("총 배정 예산액", f"₩{t_budget:,.0f}")
    with c2:
        st.metric("총 지출 집행액", f"₩{t_expense:,.0f}")
    with c3:
        st.metric("총 예산 잔액", f"₩{t_balance:,.0f}")
    with c4:
        st.metric("종합 집행률", f"{t_rate:.1f}%")
        
    st.divider()
    
    p_df = st.session_state["budget_projects"].copy()
    e_df = st.session_state["expenses"].copy()
    
    exp_summary = e_df.groupby("과제/사업단명")["지출액"].sum().reset_index() if not e_df.empty else pd.DataFrame(columns=["과제/사업단명", "지출액"])
    dash_df = pd.merge(p_df, exp_summary, on="과제/사업단명", how="left").fillna({"지출액": 0})
    dash_df["지출액"] = dash_df["지출액"].astype(int)
    dash_df["잔액"] = dash_df["배정예산액"] - dash_df["지출액"]
    dash_df["집행률(%)"] = np.where(dash_df["배정예산액"] > 0, (dash_df["지출액"] / dash_df["배정예산액"] * 100).round(1), 0.0)
    
    def calc_status(r):
        if r > 100:
            return "🔴 초과집행"
        elif r >= 85:
            return "🟡 집행임박"
        else:
            return "🟢 정상"
            
    dash_df["상태"] = dash_df["집행률(%)"].apply(calc_status)
    
    col_l, col_r = st.columns([1.1, 0.9])
    
    with col_l:
        st.markdown("#### 🏢 과제/사업단별 집행 현황")
        st.dataframe(
            dash_df[["과제코드", "과제/사업단명", "책임자", "배정예산액", "지출액", "잔액", "집행률(%)", "상태"]],
            use_container_width=True,
            column_config={
                "배정예산액": st.column_config.NumberColumn("배정예산", format="₩%,d"),
                "지출액": st.column_config.NumberColumn("지출액", format="₩%,d"),
                "잔액": st.column_config.NumberColumn("잔액", format="₩%,d"),
                "집행률(%)": st.column_config.NumberColumn("집행률", format="%.1f%%")
            },
            hide_index=True
        )
        
    with col_r:
        st.markdown("#### 📈 과제별 예산 vs 지출 비교")
        if not dash_df.empty:
            fig = px.bar(
                dash_df,
                x="과제코드",
                y=["배정예산액", "지출액"],
                barmode="group",
                labels={"value": "금액(원)", "variable": "구분", "과제코드": "과제코드"},
                color_discrete_map={"배정예산액": "#1B365D", "지출액": "#008080"}
            )
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    # Dashboard Management Expander (Add, Delete, Edit Projects directly on Dashboard)
    with st.expander("⚡ 대시보드에서 과제 직접 추가 / 삭제 / 예산 수정하기", expanded=False):
        d_tab1, d_tab2, d_tab3 = st.tabs(["➕ 과제 신규 추가", "🗑️ 과제 삭제", "✏️ 예산 실시간 수정"])
        
        with d_tab1:
            st.markdown("##### 📌 대시보드에서 바로 과제 추가")
            with st.form("dash_add_proj_form", clear_on_submit=True):
                ca, cb, cc = st.columns(3)
                with ca:
                    d_code = st.text_input("과제 코드 (예: 4-3-12)")
                    d_name = st.text_input("과제 / 사업단명")
                with cb:
                    d_leader = st.text_input("과제 책임자")
                    d_budget = st.number_input("배정 예산액 (원)", min_value=0, step=1000000, value=10000000)
                with cc:
                    d_note = st.text_area("비고 메모", height=108)
                    
                sub_d_proj = st.form_submit_button("🚀 과제 등록 완료")
                if sub_d_proj:
                    if not d_name or not d_code:
                        st.error("과제 코드와 과제/사업단명은 필수입니다.")
                    else:
                        new_p = {
                            "과제코드": d_code,
                            "과제/사업단명": d_name,
                            "책임자": d_leader,
                            "배정예산액": int(d_budget),
                            "비고": d_note
                        }
                        st.session_state["budget_projects"] = pd.concat([st.session_state["budget_projects"], pd.DataFrame([new_p])], ignore_index=True)
                        save_data_to_csv()
                        st.success(f"'{d_name}' 과제가 성공적으로 추가되었습니다!")
                        st.rerun()

        with d_tab2:
            st.markdown("##### 🗑️ 등록된 과제 삭제")
            p_options = st.session_state["budget_projects"]["과제/사업단명"].tolist() if not st.session_state["budget_projects"].empty else []
            if not p_options:
                st.info("삭제할 수 있는 과제가 없습니다.")
            else:
                del_p_name = st.selectbox("삭제할 과제/사업단 선택", p_options, key="dash_del_select")
                del_exp_too = st.checkbox("해당 과제에 등록된 지출 내역도 함께 삭제하기", value=True)
                
                if st.button("🔴 선택한 과제 삭제하기", key="dash_btn_del_proj"):
                    main_p = st.session_state["budget_projects"]
                    st.session_state["budget_projects"] = main_p[main_p["과제/사업단명"] != del_p_name].reset_index(drop=True)
                    
                    if del_exp_too:
                        main_e = st.session_state["expenses"]
                        st.session_state["expenses"] = main_e[main_e["과제/사업단명"] != del_p_name].reset_index(drop=True)
                        
                    save_data_to_csv()
                    st.success(f"'{del_p_name}' 과제가 성공적으로 삭제되었습니다!")
                    st.rerun()

        with d_tab3:
            st.markdown("##### ✏️ 예산 편성표 실시간 수정")
            edited_dash_proj = st.data_editor(
                st.session_state["budget_projects"],
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "배정예산액": st.column_config.NumberColumn("배정예산액(원)", format="₩%,d", step=100000)
                },
                key="dash_proj_editor"
            )
            if st.button("💾 대시보드 예산 수정사항 저장", key="dash_save_proj_btn"):
                st.session_state["budget_projects"] = edited_dash_proj
                save_data_to_csv()
                st.success("예산 편성 정보가 반영되었습니다!")
                st.rerun()

    st.divider()
    st.markdown("#### 🏷️ 비목별 지출 비율")
    if not e_df.empty and "비목" in e_df.columns:
        cat_agg = e_df.groupby("비목")["지출액"].sum().reset_index()
        fig_pie = px.pie(
            cat_agg,
            values="지출액",
            names="비목",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_pie.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

# ----------------------------------------------------
# PAGE 2: 🔍 과제별 상세 관리
# ----------------------------------------------------
elif menu == "🔍 과제별 상세 관리":
    st.subheader("🔍 과제별 예산 & 지출 상세 관리")
    st.info("💡 관리하고자 하는 과제/사업단을 선택하면, 해당 과제의 예산, 잔액, 상세 지출내역을 독립적으로 조회하고 수정할 수 있습니다.")
    
    p_df = st.session_state["budget_projects"].copy()
    e_df = st.session_state["expenses"].copy()
    
    proj_names = p_df["과제/사업단명"].tolist() if not p_df.empty else ["등록된 과제 없음"]
    selected_proj = st.selectbox("🎯 상세 관리할 과제/사업단 선택", proj_names, index=0)
    
    if selected_proj and selected_proj != "등록된 과제 없음":
        proj_info = p_df[p_df["과제/사업단명"] == selected_proj].iloc[0]
        proj_code = proj_info.get("과제코드", "")
        proj_leader = proj_info.get("책임자", "")
        proj_budget = int(proj_info.get("배정예산액", 0))
        proj_note = proj_info.get("비고", "")
        
        proj_exp = e_df[e_df["과제/사업단명"] == selected_proj].copy() if not e_df.empty else pd.DataFrame()
        spent_total = int(proj_exp["지출액"].sum()) if not proj_exp.empty else 0
        balance = proj_budget - spent_total
        rate = (spent_total / proj_budget * 100) if proj_budget > 0 else 0.0
        
        st.markdown(f"### 📌 [{proj_code}] {selected_proj}")
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("배정 예산액", f"₩{proj_budget:,.0f}")
        with m2:
            st.metric("총 지출액", f"₩{spent_total:,.0f}")
        with m3:
            st.metric("예산 잔액", f"₩{balance:,.0f}")
        with m4:
            st.metric("과제 집행률", f"{rate:.1f}%")
            
        st.progress(min(int(rate), 100))
        
        p_tab1, p_tab2, p_tab3 = st.tabs(["📝 이 과제의 지출 내역 관리", "➕ 이 과제에 지출 추가", "⚙️ 이 과제 예산 정보 수정"])
        
        with p_tab1:
            st.markdown(f"##### 📝 '{selected_proj}' 지출 내역 (실시간 수정 가능)")
            st.caption("아래 표에서 직접 금액, 적요, 지급상태 등을 수정할 수 있습니다.")
            
            if proj_exp.empty:
                st.info("현재 등록된 지출 내역이 없습니다. '이 과제에 지출 추가' 탭에서 새 내역을 등록해보세요.")
            else:
                bimoks = get_bimok_list()
                edited_proj_exp = st.data_editor(
                    proj_exp,
                    num_rows="dynamic",
                    use_container_width=True,
                    column_config={
                        "지출액": st.column_config.NumberColumn("지출액(원)", min_value=0, step=1000, format="₩%,d"),
                        "비목": st.column_config.SelectboxColumn("비목", options=bimoks),
                        "지급상태": st.column_config.SelectboxColumn("지급상태", options=["지급완료", "결재대기", "보완요청", "지급취소"])
                    },
                    key=f"editor_{selected_proj}"
                )
                
                if st.button("💾 이 과제 지출 내역 저장", key="btn_save_proj_exp"):
                    main_e = st.session_state["expenses"].copy()
                    main_e = main_e[main_e["과제/사업단명"] != selected_proj]
                    main_e = pd.concat([main_e, edited_proj_exp], ignore_index=True)
                    st.session_state["expenses"] = main_e
                    save_data_to_csv()
                    st.success("해당 과제의 지출 내역이 성공적으로 저장되었습니다!")
                    st.rerun()

        with p_tab2:
            st.markdown(f"##### ➕ '{selected_proj}' 전용 지출 등록 (예산세목기준 연동)")
            
            c_col1, c_col2, c_col3 = st.columns(3)
            with c_col1:
                p_bimok = st.selectbox("비목 (대분류)", options=get_bimok_list(), key=f"p_bimok_{selected_proj}")
            with c_col2:
                p_bojo_bimok_opts = get_bojo_bimok_list(p_bimok)
                p_bojo_bimok = st.selectbox("보조비목 (중분류)", options=p_bojo_bimok_opts, key=f"p_bojo_{selected_proj}")
            with c_col3:
                p_bojo_semok_opts = get_bojo_semok_list(p_bimok, p_bojo_bimok)
                p_bojo_semok = st.selectbox("보조세목 (소분류)", options=p_bojo_semok_opts, key=f"p_semok_{selected_proj}")
                
            with st.form(key=f"form_add_{selected_proj}"):
                fc1, fc2 = st.columns(2)
                with fc1:
                    ins_date = st.date_input("지출일자", datetime.now())
                    ins_amount = st.number_input("지출 금액 (원)", min_value=0, step=10000, value=50000)
                    ins_status = st.selectbox("지급 상태", ["지급완료", "결재대기", "보완요청", "지급취소"])
                with fc2:
                    ins_desc = st.text_input("지출처 / 적요 내용", placeholder="예: 사업 관련 연구자문료 지급")
                    ins_note = st.text_input("비고", placeholder="예: 계좌이체 증빙")
                    
                sub_btn = st.form_submit_button("🚀 이 과제에 지출 등록")
                
                if sub_btn:
                    main_e = st.session_state["expenses"].copy()
                    max_no = main_e["No"].max() if not main_e.empty else 0
                    new_row = {
                        "No": int(max_no) + 1,
                        "지출일자": str(ins_date),
                        "과제/사업단명": selected_proj,
                        "비목": p_bimok,
                        "보조비목": p_bojo_bimok,
                        "보조세목": p_bojo_semok,
                        "지출액": int(ins_amount),
                        "지출처/적요": ins_desc,
                        "지급상태": ins_status,
                        "비고": ins_note
                    }
                    st.session_state["expenses"] = pd.concat([main_e, pd.DataFrame([new_row])], ignore_index=True)
                    save_data_to_csv()
                    st.success(f"'{selected_proj}' 과제에 ₩{ins_amount:,.0f} 지출이 등록되었습니다!")
                    st.rerun()

        with p_tab3:
            st.markdown(f"##### ⚙️ '{selected_proj}' 예산 및 과제 정보 변경")
            with st.form(key=f"form_edit_proj_info"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_code = st.text_input("과제 코드", value=proj_code)
                    new_leader = st.text_input("과제 책임자", value=str(proj_leader))
                with ec2:
                    new_budget = st.number_input("배정 예산액 (원)", min_value=0, step=1000000, value=proj_budget)
                    new_note = st.text_input("비고 메모", value=str(proj_note))
                    
                btn_upd_p = st.form_submit_button("💾 과제 정보 수정 저장")
                
                if btn_upd_p:
                    main_p = st.session_state["budget_projects"].copy()
                    idx = main_p[main_p["과제/사업단명"] == selected_proj].index
                    if not idx.empty:
                        main_p.loc[idx[0], "과제코드"] = new_code
                        main_p.loc[idx[0], "책임자"] = new_leader
                        main_p.loc[idx[0], "배정예산액"] = new_budget
                        main_p.loc[idx[0], "비고"] = new_note
                        st.session_state["budget_projects"] = main_p
                        save_data_to_csv()
                        st.success("과제 예산 및 기본 정보가 수정되었습니다!")
                        st.rerun()

# ----------------------------------------------------
# PAGE 3: 💰 예산 편성 및 사업단 관리
# ----------------------------------------------------
elif menu == "💰 예산 편성 및 사업단 관리":
    st.subheader("💰 과제/사업단 등록 및 예산 배정 관리")
    st.info("💡 새로운 세부과제/사업단을 등록하거나 전체 사업단의 예산액, 책임자, 과제명을 종합 수정 및 삭제할 수 있습니다.")
    
    tab1, tab2, tab3 = st.tabs(["➕ 신규 과제/사업단 추가", "✏️ 전체 예산 편성표 종합 수정", "🗑️ 과제 삭제"])
    
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
                        "배정예산액": int(p_budget),
                        "비고": p_note
                    }
                    st.session_state["budget_projects"] = pd.concat([st.session_state["budget_projects"], pd.DataFrame([new_proj])], ignore_index=True)
                    save_data_to_csv()
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
                "배정예산액": st.column_config.NumberColumn("배정예산액(원)", format="₩%,d", step=100000)
            },
            key="proj_editor_all"
        )
        
        if st.button("💾 예산 편성 변경사항 저장"):
            st.session_state["budget_projects"] = edited_proj_df
            save_data_to_csv()
            st.success("예산 편성 정보가 업데이트되었습니다!")
            st.rerun()

    with tab3:
        st.markdown("##### 🗑️ 과제/사업단 삭제")
        p_opts = st.session_state["budget_projects"]["과제/사업단명"].tolist() if not st.session_state["budget_projects"].empty else []
        if not p_opts:
            st.info("삭제할 수 있는 과제가 없습니다.")
        else:
            del_target = st.selectbox("삭제할 과제/사업단 선택", p_opts, key="del_tab_select")
            del_exp_flag = st.checkbox("해당 과제의 지출 내역도 함께 삭제하기", value=True, key="del_tab_check")
            if st.button("🔴 과제 삭제 실행", key="btn_del_tab"):
                main_p = st.session_state["budget_projects"]
                st.session_state["budget_projects"] = main_p[main_p["과제/사업단명"] != del_target].reset_index(drop=True)
                if del_exp_flag:
                    main_e = st.session_state["expenses"]
                    st.session_state["expenses"] = main_e[main_e["과제/사업단명"] != del_target].reset_index(drop=True)
                save_data_to_csv()
                st.success(f"'{del_target}' 과제가 정상적으로 삭제되었습니다.")
                st.rerun()

# ----------------------------------------------------
# PAGE 4: 📝 지출 내역 입력 및 수정 (예산세목기준 연동 완료)
# ----------------------------------------------------
elif menu == "📝 지출 내역 입력 및 수정":
    st.subheader("📝 전체 지출 내역 입력 및 통합 관리")
    
    tab_exp1, tab_exp2 = st.tabs(["➕ 신규 지출 등록 (예산세목기준 연동)", "✏️ 전체 지출 내역 실시간 에디터"])
    
    proj_list = st.session_state["budget_projects"]["과제/사업단명"].tolist() if not st.session_state["budget_projects"].empty else ["선택가능 과제없음"]
    
    with tab_exp1:
        st.markdown("##### 📥 신규 지출 등록 (예산세목 기준표 자동 연동)")
        st.caption("비목을 선택하면 해당 비목에 속한 보조비목과 보조세목만 드롭다운에 자동으로 표시됩니다.")
        
        cat_c1, cat_c2, cat_c3 = st.columns(3)
        with cat_c1:
            sel_bimok = st.selectbox("비목 (대분류)", options=get_bimok_list(), key="main_sel_bimok")
        with cat_c2:
            bojo_bimok_opts = get_bojo_bimok_list(sel_bimok)
            sel_bojo_bimok = st.selectbox("보조비목 (중분류)", options=bojo_bimok_opts, key="main_sel_bojo_bimok")
        with cat_c3:
            bojo_semok_opts = get_bojo_semok_list(sel_bimok, sel_bojo_bimok)
            sel_bojo_semok = st.selectbox("보조세목 (소분류)", options=bojo_semok_opts, key="main_sel_bojo_semok")
            
        with st.form("add_expense_form_main", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                e_date = st.date_input("지출 일자", datetime.now())
                e_proj = st.selectbox("관련 과제/사업단", proj_list)
            with col2:
                e_amount = st.number_input("지출 금액 (원)", min_value=0, step=10000, value=50000)
                e_status = st.selectbox("지급 상태", ["지급완료", "결재대기", "보완요청", "지급취소"])
            with col3:
                e_details = st.text_input("지출처 / 적요 내용", placeholder="예: 5월 실무협의회 회의비 결제")
                e_notes = st.text_input("비고 (증빙 구분 등)", placeholder="예: 법인카드 / E나라도움")
                
            submit_exp = st.form_submit_button("🚀 지출 내역 추가")
            
            if submit_exp:
                main_e = st.session_state["expenses"].copy()
                max_no = main_e["No"].max() if not main_e.empty else 0
                new_exp = {
                    "No": int(max_no) + 1,
                    "지출일자": str(e_date),
                    "과제/사업단명": e_proj,
                    "비목": sel_bimok,
                    "보조비목": sel_bojo_bimok,
                    "보조세목": sel_bojo_semok,
                    "지출액": int(e_amount),
                    "지출처/적요": e_details,
                    "지급상태": e_status,
                    "비고": e_notes
                }
                st.session_state["expenses"] = pd.concat([main_e, pd.DataFrame([new_exp])], ignore_index=True)
                save_data_to_csv()
                st.success("지출 내역이 성공적으로 입력되었습니다!")
                st.rerun()

    with tab_exp2:
        st.markdown("##### ✏️ 전체 지출 내역 에디터")
        st.caption("표 안의 원하는 칸을 더블클릭하여 수정할 수 있습니다. 수정을 완료한 후 '지출 내역 변경사항 저장' 버튼을 누르세요.")
        
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
            
        all_bimoks = get_bimok_list()
        c_df = st.session_state["categories"]
        all_bojo_bimoks = c_df["보조비목"].dropna().unique().tolist() if not c_df.empty and "보조비목" in c_df.columns else ["일반수용비"]
        all_bojo_semoks = c_df["보조세목"].dropna().unique().tolist() if not c_df.empty and "보조세목" in c_df.columns else ["일반수용비(3)"]
        
        edited_exp_df = st.data_editor(
            view_exp_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "지출액": st.column_config.NumberColumn("지출액(원)", format="₩%,d", min_value=0, step=1000),
                "과제/사업단명": st.column_config.SelectboxColumn("과제/사업단명", options=proj_list),
                "비목": st.column_config.SelectboxColumn("비목", options=all_bimoks),
                "보조비목": st.column_config.SelectboxColumn("보조비목", options=all_bojo_bimoks),
                "보조세목": st.column_config.SelectboxColumn("보조세목", options=all_bojo_semoks),
                "지급상태": st.column_config.SelectboxColumn("지급상태", options=["지급완료", "결재대기", "보완요청", "지급취소"])
            },
            key="exp_editor_main"
        )
        
        if st.button("💾 지출 내역 변경사항 저장", key="btn_save_all_exp"):
            if not filter_proj and not filter_status:
                st.session_state["expenses"] = edited_exp_df
            else:
                main_e = st.session_state["expenses"].copy()
                for idx_val in edited_exp_df.index:
                    if idx_val in main_e.index:
                        main_e.loc[idx_val] = edited_exp_df.loc[idx_val]
                st.session_state["expenses"] = main_e
                
            save_data_to_csv()
            st.success("전체 지출 내역이 성공적으로 업데이트되었습니다!")
            st.rerun()

# ----------------------------------------------------
# PAGE 5: 🏷️ 예산 세목 기준표 설정
# ----------------------------------------------------
elif menu == "🏷️ 예산 세목 기준표 설정":
    st.subheader("🏷️ 비목 / 보조비목 / 보조세목 표준 관리")
    st.info("💡 조직 내에서 사용할 예산 항목 체계를 설정합니다. 여기서 설정/수정된 비목, 보조비목, 보조세목은 지출 입력 선택목록에 100% 즉시 반영됩니다.")
    
    edited_cat_df = st.data_editor(
        st.session_state["categories"],
        num_rows="dynamic",
        use_container_width=True,
        key="cat_editor_main"
    )
    
    if st.button("💾 비목 체계 저장"):
        st.session_state["categories"] = edited_cat_df
        save_data_to_csv()
        st.success("비목 표준 기준표가 성공적으로 업데이트되었습니다! 이제 지출 입력 시 반영됩니다.")
        st.rerun()

# ----------------------------------------------------
# PAGE 6: 📁 엑셀 내보내기 & 백업
# ----------------------------------------------------
elif menu == "📁 엑셀 내보내기 & 백업":
    st.subheader("📁 데이터 내보내기 및 복원")
    st.markdown("웹에 작성된 모든 예산 및 지출 내역을 **엑셀 파일(.xlsx)** 형태로 다운로드하거나, 이전 데이터를 복원할 수 있습니다.")
    
    col_exp, col_imp = st.columns(2)
    
    with col_exp:
        st.markdown("#### 📥 엑셀 내보내기")
        st.write("현재 작성된 통합 예산/지출 데이터를 멀티 탭 엑셀 파일로 다운로드합니다.")
        
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
        st.write("백업해둔 CSV 데이터를 업로드하여 지출 내역을 복원합니다.")
        uploaded_file = st.file_uploader("CSV 파일 선택", type=["csv"])
        if uploaded_file is not None:
            try:
                up_df = pd.read_csv(uploaded_file)
                st.write("업로드된 데이터 미리보기:", up_df.head(3))
                if st.button("이 데이터로 지출내역 교체하기"):
                    st.session_state["expenses"] = up_df
                    save_data_to_csv()
                    st.success("지출 내역이 성공적으로 복원되었습니다!")
                    st.rerun()
            except Exception as e:
                st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
