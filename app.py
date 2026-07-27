import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import io
import os
import urllib.request
import urllib.parse
import json
import base64

# 1. Page Configuration & Custom CSS
st.set_page_config(
    page_title="공모과제 예산 & 지출 통합관리 시스템",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Professional Styling
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
    .kpi-card-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Key-Error Proof Helper Functions & Data Cleaners
def safe_get_columns(df, required_cols, default_values=None):
    """Guarantees that a DataFrame contains all required columns with proper default values."""
    if df is None or not isinstance(df, pd.DataFrame):
        df = pd.DataFrame()
    df = df.copy()
    if default_values is None:
        default_values = {}
    for col in required_cols:
        if col not in df.columns:
            def_val = default_values.get(col, "" if col not in ["배정예산액", "지출액", "잔액", "No"] else 0)
            df[col] = def_val
    return df[required_cols]

def clean_budget_projects(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["과제코드", "과제/사업단명", "책임자", "배정예산액", "비고"])
    
    df = df.copy()
    expected_cols = ["과제코드", "과제/사업단명", "책임자", "배정예산액", "비고"]
    df = safe_get_columns(df, expected_cols)
            
    df["과제코드"] = df["과제코드"].fillna("").astype(str).str.strip()
    df["과제/사업단명"] = df["과제/사업단명"].fillna("").astype(str).str.strip()
    df["책임자"] = df["책임자"].fillna("").astype(str).str.strip()
    df["배정예산액"] = pd.to_numeric(df["배정예산액"], errors="coerce").fillna(0).astype(int)
    df["비고"] = df["비고"].fillna("").astype(str).str.strip()
    
    has_content = (
        (df["과제코드"] != "") | 
        (df["과제/사업단명"] != "") | 
        (df["책임자"] != "") | 
        (df["배정예산액"] > 0) | 
        (df["비고"] != "")
    )
    df = df[has_content].reset_index(drop=True)
    return df[expected_cols]

def clean_categories(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["비목", "보조비목", "보조세목", "설명"])
    df = df.copy()
    expected_cols = ["비목", "보조비목", "보조세목", "설명"]
    df = safe_get_columns(df, expected_cols)
    
    df["비목"] = df["비목"].fillna("").astype(str).str.strip()
    df["보조비목"] = df["보조비목"].fillna("").astype(str).str.strip()
    df["보조세목"] = df["보조세목"].fillna("").astype(str).str.strip()
    df["설명"] = df["설명"].fillna("").astype(str).str.strip()
    df = df[(df["비목"] != "") | (df["보조비목"] != "") | (df["보조세목"] != "")].reset_index(drop=True)
    return df[expected_cols]

def clean_expenses(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["No", "지출일자", "과제/사업단명", "비목", "보조비목", "보조세목", "지출액", "지출처/적요", "지급상태", "비고"])
    df = df.copy()
    expected_cols = ["No", "지출일자", "과제/사업단명", "비목", "보조비목", "보조세목", "지출액", "지출처/적요", "지급상태", "비고"]
    df = safe_get_columns(df, expected_cols)
    
    df["No"] = pd.to_numeric(df["No"], errors="coerce").fillna(0).astype(int)
    max_existing_no = df["No"].max() if not df.empty else 0
    if max_existing_no <= 0:
        max_existing_no = 0
    for idx, row in df.iterrows():
        if row["No"] <= 0:
            max_existing_no += 1
            df.loc[idx, "No"] = max_existing_no

    df["지출일자"] = df["지출일자"].fillna(str(datetime.now().date())).astype(str).str.strip()
    df["과제/사업단명"] = df["과제/사업단명"].fillna("").astype(str).str.strip()
    df["비목"] = df["비목"].fillna("").astype(str).str.strip()
    df["보조비목"] = df["보조비목"].fillna("").astype(str).str.strip()
    df["보조세목"] = df["보조세목"].fillna("").astype(str).str.strip()
    df["지출액"] = pd.to_numeric(df["지출액"], errors="coerce").fillna(0).astype(int)
    df["지출처/적요"] = df["지출처/적요"].fillna("").astype(str).str.strip()
    df["지급상태"] = df["지급상태"].fillna("지급완료").astype(str).str.strip()
    df["비고"] = df["비고"].fillna("").astype(str).str.strip()
    df = df[df["과제/사업단명"] != ""].reset_index(drop=True)
    return df[expected_cols]

def clean_budget_details(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["과제/사업단명", "비목", "보조비목", "보조세목", "배정예산액", "비고"])
    
    df = df.copy()
    expected_cols = ["과제/사업단명", "비목", "보조비목", "보조세목", "배정예산액", "비고"]
    df = safe_get_columns(df, expected_cols)
            
    df["과제/사업단명"] = df["과제/사업단명"].fillna("").astype(str).str.strip()
    df["비목"] = df["비목"].fillna("").astype(str).str.strip()
    df["보조비목"] = df["보조비목"].fillna("").astype(str).str.strip()
    df["보조세목"] = df["보조세목"].fillna("").astype(str).str.strip()
    df["배정예산액"] = pd.to_numeric(df["배정예산액"], errors="coerce").fillna(0).astype(int)
    df["비고"] = df["비고"].fillna("").astype(str).str.strip()
    
    has_content = (
        (df["과제/사업단명"] != "") |
        (df["비목"] != "") |
        (df["배정예산액"] > 0)
    )
    df = df[has_content].reset_index(drop=True)
    return df[expected_cols]

def sync_project_budgets_from_details(p_df, bd_df):
    p_df = p_df.copy()
    if bd_df is None or bd_df.empty:
        return p_df
    
    bd_clean = clean_budget_details(bd_df)
    if bd_clean.empty:
        return p_df
        
    cat_sums = bd_clean.groupby("과제/사업단명")["배정예산액"].sum().reset_index()
    
    for idx, row in cat_sums.iterrows():
        p_name = row["과제/사업단명"]
        c_sum = row["배정예산액"]
        p_idx = p_df[p_df["과제/사업단명"] == p_name].index
        if not p_idx.empty and c_sum > 0:
            p_df.loc[p_idx[0], "배정예산액"] = int(c_sum)
            
    return p_df

# --- Budget Limit Validation Functions ---
def check_single_expense_budget_limit(proj_name, amount, current_exp_df, current_p_df, current_bd_df, bimok=None, bojo_bimok=None, bojo_semok=None):
    p_match = current_p_df[current_p_df["과제/사업단명"] == proj_name]
    if p_match.empty:
        return False, f"'{proj_name}' 과제를 찾을 수 없습니다."
        
    p_budget = int(p_match.iloc[0]["배정예산액"])
    p_exp = current_exp_df[current_exp_df["과제/사업단명"] == proj_name] if not current_exp_df.empty else pd.DataFrame()
    p_spent = int(p_exp["지출액"].sum()) if (not p_exp.empty and "지출액" in p_exp.columns) else 0
    p_balance = p_budget - p_spent
    
    if amount > p_balance:
        return False, f"🚫 **[과제 예산 초과]** 입력한 지출액(**₩{amount:,.0f}**)이 해당 과제의 **총 예산 잔액(₩{p_balance:,.0f})**을 초과합니다! (배정예산: ₩{p_budget:,.0f}, 현재지출: ₩{p_spent:,.0f})"
        
    if bimok and bojo_bimok and bojo_semok and not current_bd_df.empty:
        cat_match = current_bd_df[
            (current_bd_df["과제/사업단명"] == proj_name) &
            (current_bd_df["비목"] == bimok) &
            (current_bd_df["보조비목"] == bojo_bimok) &
            (current_bd_df["보조세목"] == bojo_semok)
        ]
        if not cat_match.empty:
            cat_budget = int(cat_match.iloc[0]["배정예산액"])
            if cat_budget > 0:
                cat_exp = p_exp[
                    (p_exp["비목"] == bimok) &
                    (p_exp["보조비목"] == bojo_bimok) &
                    (p_exp["보조세목"] == bojo_semok)
                ] if not p_exp.empty else pd.DataFrame()
                cat_spent = int(cat_exp["지출액"].sum()) if (not cat_exp.empty and "지출액" in cat_exp.columns) else 0
                cat_balance = cat_budget - cat_spent
                
                if amount > cat_balance:
                    return False, f"🚫 **[세목 예산 초과]** 입력한 지출액(**₩{amount:,.0f}**)이 선택한 세목 [{bimok} > {bojo_bimok} > {bojo_semok}]의 **세목 잔액(₩{cat_balance:,.0f})**을 초과합니다! (세목예산: ₩{cat_budget:,.0f}, 현재지출: ₩{cat_spent:,.0f})"
                    
    return True, ""

def validate_all_expenses_against_budgets(cand_expenses_df, current_p_df, current_bd_df):
    errors = []
    if cand_expenses_df is None or cand_expenses_df.empty:
        return True, []
        
    cand_df = cand_expenses_df.copy()
    cand_df["지출액"] = pd.to_numeric(cand_df["지출액"], errors="coerce").fillna(0).astype(int)
    
    proj_spent = cand_df.groupby("과제/사업단명")["지출액"].sum().reset_index() if "과제/사업단명" in cand_df.columns else pd.DataFrame()
    
    for idx, row in proj_spent.iterrows():
        p_name = row["과제/사업단명"]
        t_spent = row["지출액"]
        p_match = current_p_df[current_p_df["과제/사업단명"] == p_name]
        if not p_match.empty:
            p_budget = int(p_match.iloc[0]["배정예산액"])
            if t_spent > p_budget:
                excess = t_spent - p_budget
                errors.append(f"• **{p_name}**: 총 배정예산 ₩{p_budget:,.0f} < 총지출 ₩{t_spent:,.0f} (**₩{excess:,.0f} 초과**)")
                
    if not current_bd_df.empty and all(c in cand_df.columns for c in ["과제/사업단명", "비목", "보조비목", "보조세목", "지출액"]):
        cat_spent = cand_df.groupby(["과제/사업단명", "비목", "보조비목", "보조세목"])["지출액"].sum().reset_index()
        for idx, row in cat_spent.iterrows():
            p_name = row["과제/사업단명"]
            b_name = row["비목"]
            bb_name = row["보조비목"]
            bs_name = row["보조세목"]
            c_spent = row["지출액"]
            
            bd_match = current_bd_df[
                (current_bd_df["과제/사업단명"] == p_name) &
                (current_bd_df["비목"] == b_name) &
                (current_bd_df["보조비목"] == bb_name) &
                (current_bd_df["보조세목"] == bs_name)
            ]
            if not bd_match.empty:
                c_budget = int(bd_match.iloc[0]["배정예산액"])
                if c_budget > 0 and c_spent > c_budget:
                    excess = c_spent - c_budget
                    errors.append(f"• **{p_name}** [{b_name} > {bb_name} > {bs_name}]: 세목예산 ₩{c_budget:,.0f} < 세목지출 ₩{c_spent:,.0f} (**₩{excess:,.0f} 초과**)")
                    
    if errors:
        return False, errors
    return True, []

# --- GitHub REST API Auto-Commit Engine ---
def push_file_to_github_api(token, repo, path, content_str, commit_message="Auto-sync budget data"):
    if not token or not repo:
        return False, "GitHub Token or Repo name is empty."
        
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Streamlit-Budget-App"
    }
    
    sha = None
    req_get = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req_get) as response:
            if response.status == 200:
                res_data = json.loads(response.read().decode("utf-8"))
                sha = res_data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return False, f"HTTP Error {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)
        
    content_b64 = base64.b64encode(content_str.encode("utf-8-sig")).decode("utf-8")
    
    payload = {
        "message": commit_message,
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha
        
    data_bytes = json.dumps(payload).encode("utf-8")
    req_put = urllib.request.Request(url, data=data_bytes, headers=headers, method="PUT")
    
    try:
        with urllib.request.urlopen(req_put) as response:
            if response.status in [200, 201]:
                return True, "Successfully committed to GitHub!"
            else:
                return False, f"Unexpected status: {response.status}"
    except urllib.error.HTTPError as e:
        return False, f"GitHub Error {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)

def sync_all_to_github():
    gh_token = None
    gh_repo = None
    
    try:
        gh_token = st.secrets.get("GITHUB_TOKEN") or st.secrets.get("github", {}).get("TOKEN")
        gh_repo = st.secrets.get("GITHUB_REPO") or st.secrets.get("github", {}).get("REPO")
    except Exception:
        pass
        
    if not gh_token or not gh_repo:
        return False, "깃허브 토큰(GITHUB_TOKEN) 또는 저장소 이름(GITHUB_REPO)이 st.secrets에 설정되지 않았습니다."
        
    files_to_sync = {
        "budget_projects.csv": st.session_state["budget_projects"].to_csv(index=False, encoding="utf-8-sig"),
        "categories.csv": st.session_state["categories"].to_csv(index=False, encoding="utf-8-sig"),
        "expenses.csv": st.session_state["expenses"].to_csv(index=False, encoding="utf-8-sig"),
        "budget_details.csv": st.session_state["budget_details"].to_csv(index=False, encoding="utf-8-sig")
    }
    
    failed_files = []
    for filename, csv_str in files_to_sync.items():
        ok, msg = push_file_to_github_api(
            gh_token, gh_repo, filename, csv_str,
            commit_message=f"Auto-update {filename} [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
        )
        if not ok:
            failed_files.append(f"{filename}: {msg}")
            
    if failed_files:
        return False, "\n".join(failed_files)
    return True, "모든 CSV 데이터가 깃허브 저장소로 성공적으로 동기화되었습니다!"

# Safe Data Loader
def load_data():
    if os.path.exists("budget_projects.csv"):
        p_df = pd.read_csv("budget_projects.csv")
    else:
        p_df = pd.DataFrame(columns=["과제코드", "과제/사업단명", "책임자", "배정예산액", "비고"])

    if os.path.exists("categories.csv"):
        c_df = pd.read_csv("categories.csv")
    else:
        c_df = pd.DataFrame(columns=["비목", "보조비목", "보조세목", "설명"])

    if os.path.exists("expenses.csv"):
        e_df = pd.read_csv("expenses.csv")
    else:
        e_df = pd.DataFrame(columns=["No", "지출일자", "과제/사업단명", "비목", "보조비목", "보조세목", "지출액", "지출처/적요", "지급상태", "비고"])

    if os.path.exists("budget_details.csv"):
        bd_df = pd.read_csv("budget_details.csv")
    else:
        bd_df = pd.DataFrame(columns=["과제/사업단명", "비목", "보조비목", "보조세목", "배정예산액", "비고"])

    p_clean = clean_budget_projects(p_df)
    c_clean = clean_categories(c_df)
    e_clean = clean_expenses(e_df)
    bd_clean = clean_budget_details(bd_df)
    p_synced = sync_project_budgets_from_details(p_clean, bd_clean)

    return p_synced, c_clean, e_clean, bd_clean

if "budget_projects" not in st.session_state or "expenses" not in st.session_state or "categories" not in st.session_state or "budget_details" not in st.session_state:
    p, c, e, bd = load_data()
    st.session_state["budget_projects"] = p
    st.session_state["categories"] = c
    st.session_state["expenses"] = e
    st.session_state["budget_details"] = bd

if "menu_selection" not in st.session_state:
    st.session_state["menu_selection"] = "📊 통합 대시보드"

if "selected_project_nav" not in st.session_state:
    p_names = st.session_state["budget_projects"]["과제/사업단명"].tolist() if not st.session_state["budget_projects"].empty else []
    st.session_state["selected_project_nav"] = p_names[0] if p_names else "선택 가능 과제 없음"

def save_and_sync_all():
    st.session_state["budget_projects"] = clean_budget_projects(st.session_state["budget_projects"])
    st.session_state["categories"] = clean_categories(st.session_state["categories"])
    st.session_state["expenses"] = clean_expenses(st.session_state["expenses"])
    st.session_state["budget_details"] = clean_budget_details(st.session_state["budget_details"])
    
    st.session_state["budget_projects"] = sync_project_budgets_from_details(
        st.session_state["budget_projects"],
        st.session_state["budget_details"]
    )
    
    try:
        st.session_state["budget_projects"].to_csv("budget_projects.csv", index=False, encoding="utf-8-sig")
        st.session_state["categories"].to_csv("categories.csv", index=False, encoding="utf-8-sig")
        st.session_state["expenses"].to_csv("expenses.csv", index=False, encoding="utf-8-sig")
        st.session_state["budget_details"].to_csv("budget_details.csv", index=False, encoding="utf-8-sig")
    except Exception:
        pass
        
    sync_all_to_github()

# Category Dropdown Generators from Master Table
def get_bimok_list():
    c_df = st.session_state["categories"]
    if not c_df.empty and "비목" in c_df.columns:
        opts = [x for x in c_df["비목"].dropna().unique().tolist() if str(x).strip() != ""]
        if opts:
            return opts
    return ["운영비", "인건비", "여비"]

def get_bojo_bimok_list(selected_bimok):
    c_df = st.session_state["categories"]
    if not c_df.empty and all(c in c_df.columns for c in ["비목", "보조비목"]):
        filtered = c_df[c_df["비목"] == selected_bimok]
        if not filtered.empty:
            opts = [x for x in filtered["보조비목"].dropna().unique().tolist() if str(x).strip() != ""]
            if opts:
                return opts
    return ["일반수용비"]

def get_bojo_semok_list(selected_bimok, selected_bojo_bimok):
    c_df = st.session_state["categories"]
    if not c_df.empty and all(c in c_df.columns for c in ["비목", "보조비목", "보조세목"]):
        filtered = c_df[(c_df["비목"] == selected_bimok) & (c_df["보조비목"] == selected_bojo_bimok)]
        if not filtered.empty:
            opts = [x for x in filtered["보조세목"].dropna().unique().tolist() if str(x).strip() != ""]
            if opts:
                return opts
    return ["일반수용비(3)"]

proj_column_config = {
    "과제코드": st.column_config.TextColumn("과제코드", help="예: 4-3-12", disabled=False),
    "과제/사업단명": st.column_config.TextColumn("과제/사업단명", help="과제 또는 사업단 명칭", disabled=False),
    "책임자": st.column_config.TextColumn("책임자", help="과제 책임자 성명", disabled=False),
    "배정예산액": st.column_config.NumberColumn("배정예산액(원)", format="₩%,d", min_value=0, step=100000, default=0, disabled=False),
    "비고": st.column_config.TextColumn("비고", help="메모 및 비고 사항", disabled=False)
}

# 3. Sidebar Navigation & Global Summary
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/analytics.png", width=50)
    st.markdown("## 🏛️ 예산 & 지출 관리")
    st.caption("공모과제 실시간 통합 관리 시스템")
    st.divider()
    
    nav_options = [
        "📊 통합 대시보드",
        "🔍 과제별 상세 관리",
        "💰 예산 편성 및 사업단 관리",
        "📝 지출 내역 입력 및 수정",
        "🏷️ 예산 세목 기준표 설정",
        "📁 엑셀 내보내기 & 백업"
    ]
    
    current_idx = nav_options.index(st.session_state["menu_selection"]) if st.session_state["menu_selection"] in nav_options else 0
    menu = st.radio("📌 메뉴 선택", nav_options, index=current_idx, key="menu_radio_input")
    st.session_state["menu_selection"] = menu
    
    st.divider()
    
    t_budget = st.session_state["budget_projects"]["배정예산액"].sum() if not st.session_state["budget_projects"].empty else 0
    t_expense = st.session_state["expenses"]["지출액"].sum() if not st.session_state["expenses"].empty else 0
    t_balance = t_budget - t_expense
    t_rate = (t_expense / t_budget * 100) if t_budget > 0 else 0.0
    
    st.markdown("### 📈 전체 현황 요약 (실시간 연동)")
    st.caption(f"**총 배정 예산:** ₩{t_budget:,.0f}")
    st.caption(f"**총 지출 금액:** ₩{t_expense:,.0f}")
    st.caption(f"**총 예산 잔액:** ₩{t_balance:,.0f}")
    st.progress(min(int(t_rate), 100))
    st.caption(f"**종합 집행률:** {t_rate:.1f}%")

    st.divider()
    
    # GitHub Sync Status Badge
    has_token = False
    try:
        has_token = bool(st.secrets.get("GITHUB_TOKEN") or st.secrets.get("github", {}).get("TOKEN"))
    except Exception:
        pass
        
    if has_token:
        st.success("🟢 **깃허브 자동 저장 연동됨**\n수면 모드 후에도 데이터가 100% 영구 보존됩니다.")
    else:
        st.warning("⚠️ **깃허브 영구 저장 미설정**\n아래 '깃허브 연동 안내'를 참고해 토큰을 입력하세요.")
        
    with st.expander("❓ 깃허브 영구 저장 연동 방법", expanded=False):
        st.markdown("""
        **서버 수면 후에도 데이터를 100% 보존하는 방법:**
        1. [GitHub] Settings ➔ Developer Settings ➔ Personal Access Tokens (Classic) 이동
        2. `repo` 권한 선택 후 토큰 생성 및 복사
        3. [Streamlit Cloud] 앱 설정 ➔ **Secrets** 선택 후 입력:
        ```toml
        GITHUB_TOKEN = "ghp_xxxx..."
        GITHUB_REPO = "본인아이디/저장소이름"
        ```
        """)

st.markdown('<div class="main-title">공모과제 예산 & 지출 통합 관리 웹 시스템</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">모든 담당자가 웹에서 실시간으로 예산, 세목별 편성액, 과제별 상세 내역, 지출을 자유롭게 조회하고 수정할 수 있습니다.</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE 1: 📊 통합 대시보드
# ----------------------------------------------------
if st.session_state["menu_selection"] == "📊 통합 대시보드":
    st.subheader("📊 전체 예산 및 과제/세목별 집행 현황")
    
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
    bd_df = st.session_state["budget_details"].copy()
    
    exp_summary = e_df.groupby("과제/사업단명")["지출액"].sum().reset_index() if (not e_df.empty and "과제/사업단명" in e_df.columns and "지출액" in e_df.columns) else pd.DataFrame(columns=["과제/사업단명", "지출액"])
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
        view_dash = safe_get_columns(dash_df, ["과제코드", "과제/사업단명", "책임자", "배정예산액", "지출액", "잔액", "집행률(%)", "상태"])
        st.dataframe(
            view_dash,
            use_container_width=True,
            column_config={
                "배정예산액": st.column_config.NumberColumn("배정예산", format="₩%,d"),
                "지출액": st.column_config.NumberColumn("지출액", format="₩%,d"),
                "잔액": st.column_config.NumberColumn("잔액", format="₩%,d"),
                "집행률(%)": st.column_config.NumberColumn("집행률", format="%.1f%%")
            },
            hide_index=True
        )
        
        st.markdown("##### 🔍 선택한 과제 상세페이지로 즉시 이동")
        p_list_dash = dash_df["과제/사업단명"].tolist() if not dash_df.empty else []
        if p_list_dash:
            c_select_p, c_btn_jump = st.columns([2.5, 1])
            with c_select_p:
                jump_p_name = st.selectbox("상세 관리할 과제를 선택하세요", options=p_list_dash, key="dash_jump_selectbox")
            with c_btn_jump:
                st.write("") 
                if st.button("🚀 상세 관리로 이동", key="btn_jump_to_detail"):
                    st.session_state["selected_project_nav"] = jump_p_name
                    st.session_state["menu_selection"] = "🔍 과제별 상세 관리"
                    st.rerun()

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
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("#### 🏷️ 전체 비목/보조비목/보조세목별 예산 편성 vs 지출 집행 통합 현황")
    
    if not bd_df.empty and all(c in bd_df.columns for c in ["비목", "보조비목", "보조세목", "배정예산액"]):
        global_bd_sum = bd_df.groupby(["비목", "보조비목", "보조세목"])["배정예산액"].sum().reset_index()
    else:
        global_bd_sum = pd.DataFrame(columns=["비목", "보조비목", "보조세목", "배정예산액"])
        
    if not e_df.empty and all(c in e_df.columns for c in ["비목", "보조비목", "보조세목", "지출액"]):
        global_exp_sum = e_df.groupby(["비목", "보조비목", "보조세목"])["지출액"].sum().reset_index()
    else:
        global_exp_sum = pd.DataFrame(columns=["비목", "보조비목", "보조세목", "지출액"])
    
    global_cat_merged = pd.merge(
        global_bd_sum,
        global_exp_sum,
        on=["비목", "보조비목", "보조세목"],
        how="outer"
    ).fillna({"배정예산액": 0, "지출액": 0})
    
    global_cat_merged["배정예산액"] = pd.to_numeric(global_cat_merged["배정예산액"], errors="coerce").fillna(0).astype(int)
    global_cat_merged["지출액"] = pd.to_numeric(global_cat_merged["지출액"], errors="coerce").fillna(0).astype(int)
    global_cat_merged["잔액"] = global_cat_merged["배정예산액"] - global_cat_merged["지출액"]
    global_cat_merged["집행률(%)"] = np.where(global_cat_merged["배정예산액"] > 0, (global_cat_merged["지출액"] / global_cat_merged["배정예산액"] * 100).round(1), 0.0)
    
    col_cat_t, col_cat_c = st.columns([1.1, 0.9])
    
    with col_cat_t:
        view_global_cat = safe_get_columns(global_cat_merged, ["비목", "보조비목", "보조세목", "배정예산액", "지출액", "잔액", "집행률(%)"])
        st.dataframe(
            view_global_cat,
            use_container_width=True,
            column_config={
                "배정예산액": st.column_config.NumberColumn("총 편성예산", format="₩%,d"),
                "지출액": st.column_config.NumberColumn("총 지출액", format="₩%,d"),
                "잔액": st.column_config.NumberColumn("잔액", format="₩%,d"),
                "집행률(%)": st.column_config.NumberColumn("집행률", format="%.1f%%")
            },
            hide_index=True
        )
        
    with col_cat_c:
        if not global_cat_merged.empty and global_cat_merged["지출액"].sum() > 0:
            fig_pie = px.pie(
                global_cat_merged,
                values="지출액",
                names="비목",
                hole=0.4,
                title="전체 비목별 지출 비율",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_pie.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

    with st.expander("⚡ 대시보드에서 과제 직접 추가 / 삭제 / 예산·책임자 수정하기", expanded=False):
        d_tab1, d_tab2, d_tab3 = st.tabs(["➕ 과제 신규 추가", "🗑️ 과제 삭제", "✏️ 예산 편성표 실시간 수정"])
        
        with d_tab1:
            st.markdown("##### 📌 대시보드에서 바로 과제 추가 (입력 폼)")
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
                    if not d_name and not d_code:
                        st.error("과제 코드 또는 과제/사업단명을 입력해주세요.")
                    else:
                        new_p = {
                            "과제코드": d_code,
                            "과제/사업단명": d_name,
                            "책임자": d_leader,
                            "배정예산액": int(d_budget),
                            "비고": d_note
                        }
                        st.session_state["budget_projects"] = pd.concat([st.session_state["budget_projects"], pd.DataFrame([new_p])], ignore_index=True)
                        save_and_sync_all()
                        st.success(f"'{d_name}' 과제가 성공적으로 추가되었습니다!")
                        st.rerun()

        with d_tab2:
            st.markdown("##### 🗑️ 등록된 과제 삭제")
            p_options = st.session_state["budget_projects"]["과제/사업단명"].tolist() if not st.session_state["budget_projects"].empty else []
            if not p_options:
                st.info("삭제할 수 있는 과제가 없습니다.")
            else:
                del_p_name = st.selectbox("삭제할 과제/사업단 선택", p_options, key="dash_del_select")
                del_exp_too = st.checkbox("해당 과제에 등록된 세목 예산 및 지출 내역도 함께 삭제하기", value=True)
                
                if st.button("🔴 선택한 과제 삭제하기", key="dash_btn_del_proj"):
                    main_p = st.session_state["budget_projects"]
                    st.session_state["budget_projects"] = main_p[main_p["과제/사업단명"] != del_p_name]
                    
                    if del_exp_too:
                        main_e = st.session_state["expenses"]
                        st.session_state["expenses"] = main_e[main_e["과제/사업단명"] != del_p_name]
                        main_bd = st.session_state["budget_details"]
                        st.session_state["budget_details"] = main_bd[main_bd["과제/사업단명"] != del_p_name]
                        
                    save_and_sync_all()
                    st.success(f"'{del_p_name}' 과제가 성공적으로 삭제되었습니다!")
                    st.rerun()

        with d_tab3:
            st.markdown("##### ✏️ 예산 편성표 실시간 수정")
            edited_dash_proj = st.data_editor(
                st.session_state["budget_projects"],
                num_rows="dynamic",
                use_container_width=True,
                column_config=proj_column_config,
                disabled=False,
                key="dash_proj_editor"
            )
            if st.button("💾 대시보드 예산 수정사항 저장", key="dash_save_proj_btn"):
                st.session_state["budget_projects"] = edited_dash_proj
                save_and_sync_all()
                st.success("예산 편성 정보가 저장 및 반영되었습니다!")
                st.rerun()

# ----------------------------------------------------
# PAGE 2: 🔍 과제별 상세 관리 (100% Data-Loss Proof via Unique 'No' Indexing)
# ----------------------------------------------------
elif st.session_state["menu_selection"] == "🔍 과제별 상세 관리":
    st.subheader("🔍 과제별 예산 & 지출 상세 관리")
    st.info("💡 선택한 과제의 배정 예산, 세목별 예산 편성, 집행 내역을 한눈에 조회하고 비목/세목별 예산 및 지출 내역을 각각 입력·수정할 수 있습니다.")
    
    p_df = st.session_state["budget_projects"].copy()
    e_df = st.session_state["expenses"].copy()
    bd_df = st.session_state["budget_details"].copy()
    
    proj_names = p_df["과제/사업단명"].tolist() if not p_df.empty else ["등록된 과제 없음"]
    
    default_index = 0
    if st.session_state["selected_project_nav"] in proj_names:
        default_index = proj_names.index(st.session_state["selected_project_nav"])
        
    selected_proj = st.selectbox("🎯 상세 관리할 과제/사업단 선택", proj_names, index=default_index, key="detail_proj_selectbox")
    st.session_state["selected_project_nav"] = selected_proj
    
    if selected_proj and selected_proj != "등록된 과제 없음":
        proj_info = p_df[p_df["과제/사업단명"] == selected_proj].iloc[0]
        proj_code = str(proj_info.get("과제코드", ""))
        proj_leader = str(proj_info.get("책임자", ""))
        proj_budget = int(proj_info.get("배정예산액", 0))
        proj_note = str(proj_info.get("비고", ""))
        
        proj_exp = e_df[e_df["과제/사업단명"] == selected_proj].copy() if not e_df.empty else pd.DataFrame()
        spent_total = int(proj_exp["지출액"].sum()) if (not proj_exp.empty and "지출액" in proj_exp.columns) else 0
        balance = proj_budget - spent_total
        rate = (spent_total / proj_budget * 100) if proj_budget > 0 else 0.0
        
        st.markdown(f"### 📌 [{proj_code}] {selected_proj}")
        st.caption(f"**과제 책임자:** {proj_leader if proj_leader else '미지정'} | **비고/메모:** {proj_note if proj_note else '없음'}")
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("총 배정 예산액", f"₩{proj_budget:,.0f}")
        with m2:
            st.metric("총 지출 집행액", f"₩{spent_total:,.0f}")
        with m3:
            st.metric("예산 잔액", f"₩{balance:,.0f}")
        with m4:
            st.metric("과제 집행률", f"{rate:.1f}%")
            
        st.progress(min(int(rate), 100))
        
        p_tab1, p_tab2, p_tab3, p_tab4 = st.tabs([
            "📊 비목/세목별 예산 편성 관리",
            "📝 이 과제의 지출 내역 관리",
            "➕ 이 과제에 지출 추가",
            "⚙️ 이 과제 기본정보 수정"
        ])
        
        # TAB 1: Category Level Budget Allocation for this project
        with p_tab1:
            st.markdown(f"##### 📊 '{selected_proj}' 비목 · 보조비목 · 보조세목별 예산 편성 & 집행 현황")
            st.caption("비목/세목별로 예산 배정액을 설정하세요. 세목 예산의 총합이 과제의 전체 예산으로 자동 합산 반영됩니다.")
            
            proj_bd = bd_df[bd_df["과제/사업단명"] == selected_proj].copy() if not bd_df.empty else pd.DataFrame()
            
            if not proj_exp.empty and all(c in proj_exp.columns for c in ["비목", "보조비목", "보조세목", "지출액"]):
                proj_exp_cat_sum = proj_exp.groupby(["비목", "보조비목", "보조세목"])["지출액"].sum().reset_index()
            else:
                proj_exp_cat_sum = pd.DataFrame(columns=["비목", "보조비목", "보조세목", "지출액"])
            
            proj_bd_sub = safe_get_columns(proj_bd, ["비목", "보조비목", "보조세목", "배정예산액", "비고"])
            
            merged_cat_proj = pd.merge(
                proj_bd_sub,
                proj_exp_cat_sum,
                on=["비목", "보조비목", "보조세목"],
                how="outer"
            ).fillna({"배정예산액": 0, "지출액": 0, "비고": ""})
            
            merged_cat_proj["배정예산액"] = pd.to_numeric(merged_cat_proj["배정예산액"], errors="coerce").fillna(0).astype(int)
            merged_cat_proj["지출액"] = pd.to_numeric(merged_cat_proj["지출액"], errors="coerce").fillna(0).astype(int)
            merged_cat_proj["잔액"] = merged_cat_proj["배정예산액"] - merged_cat_proj["지출액"]
            merged_cat_proj["집행률(%)"] = np.where(merged_cat_proj["배정예산액"] > 0, (merged_cat_proj["지출액"] / merged_cat_proj["배정예산액"] * 100).round(1), 0.0)
            
            st.markdown("###### 🔍 [조회] 세목별 예산 대비 지출 현황")
            view_summary_cat = safe_get_columns(merged_cat_proj, ["비목", "보조비목", "보조세목", "배정예산액", "지출액", "잔액", "집행률(%)", "비고"])
            st.dataframe(
                view_summary_cat,
                use_container_width=True,
                column_config={
                    "배정예산액": st.column_config.NumberColumn("배정예산액", format="₩%,d"),
                    "지출액": st.column_config.NumberColumn("지출액", format="₩%,d"),
                    "잔액": st.column_config.NumberColumn("잔액", format="₩%,d"),
                    "집행률(%)": st.column_config.NumberColumn("집행률", format="%.1f%%")
                },
                hide_index=True
            )
            
            st.divider()
            st.markdown("###### ✏️ [수정] 비목/세목별 예산 배정액 편집 표")
            st.caption("아래 표에서 비목, 보조비목, 보조세목, 배정예산액, 비고를 직접 수정하거나 행을 추가/삭제할 수 있습니다.")
            
            bimok_opts = get_bimok_list()
            c_df = st.session_state["categories"]
            all_bojo_bimoks = c_df["보조비목"].dropna().unique().tolist() if not c_df.empty and "보조비목" in c_df.columns else ["일반수용비"]
            all_bojo_semoks = c_df["보조세목"].dropna().unique().tolist() if not c_df.empty and "보조세목" in c_df.columns else ["일반수용비(3)"]
            
            editable_bd = safe_get_columns(proj_bd, ["비목", "보조비목", "보조세목", "배정예산액", "비고"])
            
            edited_bd_proj = st.data_editor(
                editable_bd,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "비목": st.column_config.SelectboxColumn("비목", options=bimok_opts),
                    "보조비목": st.column_config.SelectboxColumn("보조비목", options=all_bojo_bimoks),
                    "보조세목": st.column_config.SelectboxColumn("보조세목", options=all_bojo_semoks),
                    "배정예산액": st.column_config.NumberColumn("배정예산액(원)", format="₩%,d", min_value=0, step=100000, default=0),
                    "비고": st.column_config.TextColumn("비고 메모")
                },
                key=f"editor_cat_bd_{selected_proj}"
            )
            
            if not editable_bd.equals(edited_bd_proj) or st.button("💾 이 과제의 세목별 예산 편성 저장", key="btn_save_proj_bd"):
                edited_clean = clean_budget_details(edited_bd_proj)
                edited_clean["과제/사업단명"] = selected_proj
                
                main_bd = st.session_state["budget_details"].copy()
                if not main_bd.empty and "과제/사업단명" in main_bd.columns:
                    main_bd = main_bd[main_bd["과제/사업단명"] != selected_proj]
                else:
                    main_bd = pd.DataFrame(columns=["과제/사업단명", "비목", "보조비목", "보조세목", "배정예산액", "비고"])
                    
                main_bd = pd.concat([main_bd, edited_clean], ignore_index=True)
                
                st.session_state["budget_details"] = main_bd
                save_and_sync_all()
                st.success(f"'{selected_proj}' 과제의 세목별 예산 편성이 저장 및 실시간 동기화되었습니다!")
                st.rerun()

            st.divider()
            st.markdown("###### ➕ 신규 세목 예산 배정 추가 (입력 폼)")
            cat_c1, cat_c2, cat_c3 = st.columns(3)
            with cat_c1:
                add_bd_bimok = st.selectbox("비목 (대분류)", options=get_bimok_list(), key=f"add_bd_b_{selected_proj}")
            with cat_c2:
                bojo_b_opts = get_bojo_bimok_list(add_bd_bimok)
                add_bd_bojo_b = st.selectbox("보조비목 (중분류)", options=bojo_b_opts, key=f"add_bd_bb_{selected_proj}")
            with cat_c3:
                bojo_s_opts = get_bojo_semok_list(add_bd_bimok, add_bd_bojo_b)
                add_bd_semok = st.selectbox("보조세목 (소분류)", options=bojo_s_opts, key=f"add_bd_bs_{selected_proj}")
                
            with st.form(key=f"form_add_bd_cat_{selected_proj}"):
                fc1, fc2 = st.columns(2)
                with fc1:
                    add_bd_amount = st.number_input("세목 배정 예산액 (원)", min_value=0, step=1000000, value=5000000)
                with fc2:
                    add_bd_note = st.text_input("세목 비고 메모", placeholder="예: 연구원 보수 배정")
                    
                sub_bd_btn = st.form_submit_button("🚀 이 세목 예산 추가")
                if sub_bd_btn:
                    main_bd = st.session_state["budget_details"].copy()
                    new_bd_row = {
                        "과제/사업단명": selected_proj,
                        "비목": add_bd_bimok,
                        "보조비목": add_bd_bojo_b,
                        "보조세목": add_bd_semok,
                        "배정예산액": int(add_bd_amount),
                        "비고": add_bd_note
                    }
                    st.session_state["budget_details"] = pd.concat([main_bd, pd.DataFrame([new_bd_row])], ignore_index=True)
                    save_and_sync_all()
                    st.success(f"'{selected_proj}' 과제 [{add_bd_bimok} > {add_bd_bojo_b}] 에 ₩{add_bd_amount:,.0f} 예산이 추가되었습니다!")
                    st.rerun()

        # TAB 2: Expenses Editor for this project (FIXED: Uses 'No' index tracking to prevent any data loss when editing amounts)
        with p_tab2:
            st.markdown(f"##### 📝 '{selected_proj}' 지출 내역 (실시간 수정 & 삭제 가능)")
            st.caption("아래 표에서 직접 금액, 비목, 적요, 지급상태 등을 수정하거나 행을 추가/삭제할 수 있습니다. 수정한 후 '💾 저장' 버튼을 누르면 즉시 전체 시스템에 반영됩니다.")
            
            view_proj_exp = safe_get_columns(proj_exp, ["No", "지출일자", "비목", "보조비목", "보조세목", "지출액", "지출처/적요", "지급상태", "비고"])
            
            if not view_proj_exp.empty and "No" in view_proj_exp.columns:
                view_proj_exp_indexed = view_proj_exp.set_index("No")
            else:
                view_proj_exp_indexed = view_proj_exp
                
            bimoks = get_bimok_list()
            c_df = st.session_state["categories"]
            all_bojo_bimoks = c_df["보조비목"].dropna().unique().tolist() if not c_df.empty and "보조비목" in c_df.columns else ["일반수용비"]
            all_bojo_semoks = c_df["보조세목"].dropna().unique().tolist() if not c_df.empty and "보조세목" in c_df.columns else ["일반수용비(3)"]
            
            edited_indexed = st.data_editor(
                view_proj_exp_indexed,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "지출액": st.column_config.NumberColumn("지출액(원)", min_value=0, step=1000, format="₩%,d"),
                    "비목": st.column_config.SelectboxColumn("비목", options=bimoks),
                    "보조비목": st.column_config.SelectboxColumn("보조비목", options=all_bojo_bimoks),
                    "보조세목": st.column_config.SelectboxColumn("보조세목", options=all_bojo_semoks),
                    "지급상태": st.column_config.SelectboxColumn("지급상태", options=["지급완료", "결재대기", "보완요청", "지급취소"])
                },
                key=f"editor_{selected_proj}"
            )
            
            if st.button("💾 이 과제 지출 내역 저장", key="btn_save_proj_exp"):
                edited_reset = edited_indexed.reset_index()
                edited_clean_exp = clean_expenses(edited_reset)
                edited_clean_exp["과제/사업단명"] = selected_proj
                
                main_e = st.session_state["expenses"].copy()
                max_no = main_e["No"].max() if (not main_e.empty and "No" in main_e.columns) else 0
                if max_no <= 0:
                    max_no = 0
                    
                for idx, row in edited_clean_exp.iterrows():
                    if row["No"] <= 0 or row["No"] in main_e["No"].values and not (proj_exp["No"] == row["No"]).any():
                        max_no += 1
                        edited_clean_exp.loc[idx, "No"] = max_no
                
                if not main_e.empty and "과제/사업단명" in main_e.columns:
                    cand_main_e = main_e[main_e["과제/사업단명"] != selected_proj]
                else:
                    cand_main_e = pd.DataFrame(columns=["No", "지출일자", "과제/사업단명", "비목", "보조비목", "보조세목", "지출액", "지출처/적요", "지급상태", "비고"])
                    
                cand_main_e = pd.concat([cand_main_e, edited_clean_exp], ignore_index=True)
                
                is_valid, errs = validate_all_expenses_against_budgets(
                    cand_main_e,
                    st.session_state["budget_projects"],
                    st.session_state["budget_details"]
                )
                
                if not is_valid:
                    st.error("🚫 **[지출 초과 오류]** 수정하신 지출 내역이 배정 예산을 초과하여 저장할 수 없습니다!\n\n" + "\n".join(errs))
                else:
                    st.session_state["expenses"] = clean_expenses(cand_main_e)
                    save_and_sync_all()
                    st.success("해당 과제의 지출 내역이 성공적으로 저장 및 자동 연동되었습니다!")
                    st.rerun()

        # TAB 3: Add New Expense for this project
        with p_tab3:
            st.markdown(f"##### ➕ '{selected_proj}' 전용 지출 등록 (예산 잔액 초과 입력 방지 & 기준표 완벽 연동)")
            
            cat_c1, cat_c2, cat_c3 = st.columns(3)
            with cat_c1:
                p_bimok = st.selectbox("비목 (대분류)", options=get_bimok_list(), key=f"p_bimok_{selected_proj}")
            with cat_c2:
                p_bojo_bimok_opts = get_bojo_bimok_list(p_bimok)
                p_bojo_bimok = st.selectbox("보조비목 (중분류)", options=p_bojo_bimok_opts, key=f"p_bojo_{selected_proj}")
            with cat_c3:
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
                    is_valid, err_msg = check_single_expense_budget_limit(
                        selected_proj,
                        int(ins_amount),
                        st.session_state["expenses"],
                        st.session_state["budget_projects"],
                        st.session_state["budget_details"],
                        bimok=p_bimok,
                        bojo_bimok=p_bojo_bimok,
                        bojo_semok=p_bojo_semok
                    )
                    
                    if not is_valid:
                        st.error(err_msg)
                    else:
                        main_e = st.session_state["expenses"].copy()
                        max_no = main_e["No"].max() if (not main_e.empty and "No" in main_e.columns) else 0
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
                        save_and_sync_all()
                        st.success(f"'{selected_proj}' 과제에 ₩{ins_amount:,.0f} 지출이 등록되었습니다!")
                        st.rerun()

        # TAB 4: Modify Budget & Basic Info for this project
        with p_tab4:
            st.markdown(f"##### ⚙️ '{selected_proj}' 과제 기본 정보 및 총 예산액 직접 수정")
            with st.form(key=f"form_edit_proj_info"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_code = st.text_input("과제 코드", value=proj_code)
                    new_name = st.text_input("과제 / 사업단명", value=selected_proj)
                    new_leader = st.text_input("과제 책임자", value=proj_leader)
                with ec2:
                    new_budget = st.number_input("배정 예산액 (원)", min_value=0, step=1000000, value=proj_budget)
                    new_note = st.text_area("비고 메모", value=proj_note, height=108)
                    
                btn_upd_p = st.form_submit_button("💾 과제 정보 수정 저장")
                
                if btn_upd_p:
                    main_p = st.session_state["budget_projects"].copy()
                    idx = main_p[main_p["과제/사업단명"] == selected_proj].index
                    if not idx.empty:
                        main_p.loc[idx[0], "과제코드"] = new_code
                        main_p.loc[idx[0], "과제/사업단명"] = new_name
                        main_p.loc[idx[0], "책임자"] = new_leader
                        main_p.loc[idx[0], "배정예산액"] = new_budget
                        main_p.loc[idx[0], "비고"] = new_note
                        
                        if new_name != selected_proj:
                            main_e = st.session_state["expenses"].copy()
                            if not main_e.empty and "과제/사업단명" in main_e.columns:
                                main_e.loc[main_e["과제/사업단명"] == selected_proj, "과제/사업단명"] = new_name
                                st.session_state["expenses"] = main_e
                            
                            main_bd = st.session_state["budget_details"].copy()
                            if not main_bd.empty and "과제/사업단명" in main_bd.columns:
                                main_bd.loc[main_bd["과제/사업단명"] == selected_proj, "과제/사업단명"] = new_name
                                st.session_state["budget_details"] = main_bd
                            
                            st.session_state["selected_project_nav"] = new_name
                            
                        st.session_state["budget_projects"] = main_p
                        save_and_sync_all()
                        st.success("과제 예산 및 기본 정보가 성공적으로 수정되었습니다!")
                        st.rerun()

# ----------------------------------------------------
# PAGE 3: 💰 예산 편성 및 사업단 관리
# ----------------------------------------------------
elif st.session_state["menu_selection"] == "💰 예산 편성 및 사업단 관리":
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
                if not p_name and not p_code:
                    st.error("과제 코드 또는 과제/사업단명을 입력해주세요.")
                else:
                    new_proj = {
                        "과제코드": p_code,
                        "과제/사업단명": p_name,
                        "책임자": p_leader,
                        "배정예산액": int(p_budget),
                        "비고": p_note
                    }
                    st.session_state["budget_projects"] = pd.concat([st.session_state["budget_projects"], pd.DataFrame([new_proj])], ignore_index=True)
                    save_and_sync_all()
                    st.success(f"'{p_name}' 과제가 성공적으로 등록되었습니다!")
                    st.rerun()

    with tab2:
        st.markdown("##### ✏️ 전체 예산 편성표 종합 수정")
        st.caption("표에서 직접 칸을 클릭하여 과제명, 예산, 책임자, 비고 등을 수정하거나 신규 행을 추가/삭제할 수 있습니다.")
        
        edited_proj_df = st.data_editor(
            st.session_state["budget_projects"],
            num_rows="dynamic",
            use_container_width=True,
            column_config=proj_column_config,
            disabled=False,
            key="proj_editor_all"
        )
        
        if st.button("💾 예산 편성 변경사항 저장"):
            st.session_state["budget_projects"] = edited_proj_df
            save_and_sync_all()
            st.success("예산 편성 정보가 업데이트되었습니다!")
            st.rerun()

    with tab3:
        st.markdown("##### 🗑️ 과제/사업단 삭제")
        p_opts = st.session_state["budget_projects"]["과제/사업단명"].tolist() if not st.session_state["budget_projects"].empty else []
        if not p_opts:
            st.info("삭제할 수 있는 과제가 없습니다.")
        else:
            del_target = st.selectbox("삭제할 과제/사업단 선택", p_opts, key="del_tab_select")
            del_exp_flag = st.checkbox("해당 과제의 세목 예산 및 지출 내역도 함께 삭제하기", value=True, key="del_tab_check")
            if st.button("🔴 과제 삭제 실행", key="btn_del_tab"):
                main_p = st.session_state["budget_projects"]
                st.session_state["budget_projects"] = main_p[main_p["과제/사업단명"] != del_target]
                if del_exp_flag:
                    main_e = st.session_state["expenses"]
                    st.session_state["expenses"] = main_e[main_e["과제/사업단명"] != del_target]
                    main_bd = st.session_state["budget_details"]
                    st.session_state["budget_details"] = main_bd[main_bd["과제/사업단명"] != del_target]
                save_and_sync_all()
                st.success(f"'{del_target}' 과제가 정상적으로 삭제되었습니다.")
                st.rerun()

# ----------------------------------------------------
# PAGE 4: 📝 지출 내역 입력 및 수정 (Real-time Budget & Category KPIs)
# ----------------------------------------------------
elif st.session_state["menu_selection"] == "📝 지출 내역 입력 및 수정":
    st.subheader("📝 전체 지출 내역 입력 및 통합 관리")
    
    tab_exp1, tab_exp2 = st.tabs(["➕ 신규 지출 등록 (예산 & 세목 연동)", "✏️ 전체 지출 내역 실시간 에디터"])
    
    proj_list = st.session_state["budget_projects"]["과제/사업단명"].tolist() if not st.session_state["budget_projects"].empty else ["선택가능 과제없음"]
    
    with tab_exp1:
        st.markdown("##### 📥 신규 지출 등록 (실시간 배정액 · 현재 잔액 표시)")
        
        # 1. Project Selection FIRST
        c_proj_select, c_space = st.columns([2, 1])
        with c_proj_select:
            e_proj = st.selectbox("🎯 관련 과제/사업단 선택", proj_list, key="main_input_eproj")
            
        p_df = st.session_state["budget_projects"]
        e_df = st.session_state["expenses"]
        bd_df = st.session_state["budget_details"]
        
        p_match = p_df[p_df["과제/사업단명"] == e_proj] if not p_df.empty else pd.DataFrame()
        p_budget = int(p_match.iloc[0]["배정예산액"]) if not p_match.empty else 0
        p_exp = e_df[e_df["과제/사업단명"] == e_proj] if not e_df.empty else pd.DataFrame()
        p_spent = int(p_exp["지출액"].sum()) if (not p_exp.empty and "지출액" in p_exp.columns) else 0
        p_balance = p_budget - p_spent
        p_rate = (p_spent / p_budget * 100) if p_budget > 0 else 0.0
        
        st.markdown("###### 💳 선택 과제 총 예산 현황")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("과제 총 배정 예산", f"₩{p_budget:,.0f}")
        with m2:
            st.metric("현재 총 지출액", f"₩{p_spent:,.0f}")
        with m3:
            st.metric("현재 과제 잔액", f"₩{p_balance:,.0f}")
        with m4:
            st.metric("과제 집행률", f"{p_rate:.1f}%")
            
        st.progress(min(int(p_rate), 100))
        st.divider()
        
        # 2. Cascading Category Selection
        st.markdown("###### 🏷️ 예산 세목 선택 (비목 ➔ 보조비목 ➔ 보조세목 연동)")
        cat_c1, cat_c2, cat_c3 = st.columns(3)
        with cat_c1:
            sel_bimok = st.selectbox("비목 (대분류)", options=get_bimok_list(), key="main_sel_bimok")
        with cat_c2:
            bojo_bimok_opts = get_bojo_bimok_list(sel_bimok)
            sel_bojo_bimok = st.selectbox("보조비목 (중분류)", options=bojo_bimok_opts, key="main_sel_bojo_bimok")
        with cat_c3:
            bojo_semok_opts = get_bojo_semok_list(sel_bimok, sel_bojo_bimok)
            sel_bojo_semok = st.selectbox("보조세목 (소분류)", options=bojo_semok_opts, key="main_sel_bojo_semok")
            
        cat_match = bd_df[
            (bd_df["과제/사업단명"] == e_proj) &
            (bd_df["비목"] == sel_bimok) &
            (bd_df["보조비목"] == sel_bojo_bimok) &
            (bd_df["보조세목"] == sel_bojo_semok)
        ] if not bd_df.empty else pd.DataFrame()
        
        c_budget = int(cat_match.iloc[0]["배정예산액"]) if not cat_match.empty else 0
        cat_exp = p_exp[
            (p_exp["비목"] == sel_bimok) &
            (p_exp["보조비목"] == sel_bojo_bimok) &
            (p_exp["보조세목"] == sel_bojo_semok)
        ] if not p_exp.empty else pd.DataFrame()
        c_spent = int(cat_exp["지출액"].sum()) if (not cat_exp.empty and "지출액" in cat_exp.columns) else 0
        c_balance = c_budget - c_spent if c_budget > 0 else p_balance
        
        if c_budget > 0:
            st.info(f"📌 **[{sel_bimok} > {sel_bojo_bimok} > {sel_bojo_semok}] 세목 예산**: 배정액 **₩{c_budget:,.0f}** | 지출액 **₩{c_spent:,.0f}** | **현재 세목 잔액 ₩{c_balance:,.0f}**")
        else:
            st.caption(f"ℹ️ 선택 세목의 별도 세목 예산 편성이 없는 경우, 과제 잔액(**₩{p_balance:,.0f}**) 한도 내에서 지출할 수 있습니다.")

        st.divider()
        
        # 3. Form for Expense Input Details
        st.markdown("###### 📝 지출 상세 정보 입력")
        with st.form("add_expense_form_main", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                e_date = st.date_input("지출 일자", datetime.now())
                e_amount = st.number_input("지출 금액 (원)", min_value=0, step=10000, value=50000)
            with col2:
                e_status = st.selectbox("지급 상태", ["지급완료", "결재대기", "보완요청", "지급취소"])
                e_details = st.text_input("지출처 / 적요 내용", placeholder="예: 5월 실무협의회 회의비 결제")
            with col3:
                e_notes = st.text_input("비고 (증빙 구분 등)", placeholder="예: 법인카드 / E나라도움")
                st.write("") # spacer
                
            submit_exp = st.form_submit_button("🚀 지출 내역 추가")
            
            if submit_exp:
                is_valid, err_msg = check_single_expense_budget_limit(
                    e_proj,
                    int(e_amount),
                    st.session_state["expenses"],
                    st.session_state["budget_projects"],
                    st.session_state["budget_details"],
                    bimok=sel_bimok,
                    bojo_bimok=sel_bojo_bimok,
                    bojo_semok=sel_bojo_semok
                )
                
                if not is_valid:
                    st.error(err_msg)
                else:
                    main_e = st.session_state["expenses"].copy()
                    max_no = main_e["No"].max() if (not main_e.empty and "No" in main_e.columns) else 0
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
                    save_and_sync_all()
                    st.success("지출 내역이 성공적으로 입력되었습니다! (예산 및 대시보드 자동 연동 완료)")
                    st.rerun()

    with tab_exp2:
        st.markdown("##### ✏️ 전체 지출 내역 에디터 (실시간 수정 · 삭제 · 자동연동)")
        st.caption("표 안의 원하는 칸을 더블클릭하여 수정하거나 행을 추가/삭제하세요. 수정한 후 '💾 저장' 버튼을 누르면 즉시 전체 시스템에 반영됩니다.")
        
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
            
        view_exp_df = safe_get_columns(view_exp_df, ["No", "지출일자", "과제/사업단명", "비목", "보조비목", "보조세목", "지출액", "지출처/적요", "지급상태", "비고"])
            
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
        
        save_clicked_main = st.button("💾 지출 내역 변경사항 저장", key="btn_save_all_exp")
        
        if save_clicked_main:
            if not filter_proj and not filter_status:
                cand_main_e = edited_exp_df
            else:
                main_e = st.session_state["expenses"].copy()
                mask = pd.Series(True, index=main_e.index)
                if filter_proj:
                    mask &= main_e["과제/사업단명"].isin(filter_proj)
                if filter_status:
                    mask &= main_e["지급상태"].isin(filter_status)
                
                main_e = main_e[~mask]
                cand_main_e = pd.concat([main_e, edited_exp_df], ignore_index=True)
                
            is_valid, errs = validate_all_expenses_against_budgets(
                cand_main_e,
                st.session_state["budget_projects"],
                st.session_state["budget_details"]
            )
            
            if not is_valid:
                st.error("🚫 **[지출 초과 오류]** 수정하신 지출 내역이 배정 예산을 초과하여 저장할 수 없습니다!\n\n" + "\n".join(errs))
            else:
                st.session_state["expenses"] = clean_expenses(cand_main_e)
                save_and_sync_all()
                st.success("전체 지출 내역이 성공적으로 업데이트되어 전체 대시보드에 100% 연동되었습니다!")
                st.rerun()

# ----------------------------------------------------
# PAGE 5: 🏷️ 예산 세목 기준표 설정
# ----------------------------------------------------
elif st.session_state["menu_selection"] == "🏷️ 예산 세목 기준표 설정":
    st.subheader("🏷️ 비목 / 보조비목 / 보조세목 표준 관리")
    st.info("💡 조직 내에서 사용할 예산 항목 체계를 설정합니다. 여기서 설정/수정된 비목, 보조비목, 보조세목은 지출 입력 선택목록에 100% 즉시 반영됩니다.")
    
    view_cat_df = safe_get_columns(st.session_state["categories"], ["비목", "보조비목", "보조세목", "설명"])
    
    edited_cat_df = st.data_editor(
        view_cat_df,
        num_rows="dynamic",
        use_container_width=True,
        key="cat_editor_main"
    )
    
    if st.button("💾 비목 체계 저장", key="btn_save_categories"):
        st.session_state["categories"] = clean_categories(edited_cat_df)
        save_and_sync_all()
        st.success("비목 표준 기준표가 성공적으로 업데이트되었습니다! 이제 지출 입력 시 반영됩니다.")
        st.rerun()

# ----------------------------------------------------
# PAGE 6: 📁 엑셀 내보내기 & 백업
# ----------------------------------------------------
elif st.session_state["menu_selection"] == "📁 엑셀 내보내기 & 백업":
    st.subheader("📁 데이터 내보내기 및 복원")
    st.markdown("웹에 작성된 모든 예산 및 지출 내역을 **엑셀 파일(.xlsx)** 형태로 다운로드하거나, 이전 데이터를 복원할 수 있습니다.")
    
    col_exp, col_imp = st.columns(2)
    
    with col_exp:
        st.markdown("#### 📥 엑셀 내보내기")
        st.write("현재 작성된 통합 예산/지출 데이터를 멀티 탭 엑셀 파일로 다운로드합니다.")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            st.session_state["budget_projects"].to_excel(writer, sheet_name="과제별_총예산", index=False)
            st.session_state["budget_details"].to_excel(writer, sheet_name="세목별_예산편성", index=False)
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
                    st.session_state["expenses"] = clean_expenses(up_df)
                    save_and_sync_all()
                    st.success("지출 내역이 성공적으로 복원되었습니다!")
                    st.rerun()
            except Exception as e:
                st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
