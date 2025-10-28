import streamlit as st
import pandas as pd
import plotly.express as px
import re
import math

# --------------------------------------------------
# 🎨 Page Configuration
# --------------------------------------------------
st.set_page_config(page_title="Marketing Keyword Dashboard", layout="wide")
st.markdown(
    "<h1 style='text-align:left; color:#ffffff; font-weight:800;'>📊 Marketing Keyword Dashboard</h1>",
    unsafe_allow_html=True
)

# --------------------------------------------------
# 🧩 Load & Clean Main Data  (MarketingDashboardUpdated.xlsx)
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("MarketingDashboardUpdated.xlsx")
    df.columns = df.columns.str.strip()

    # --- Detect columns dynamically
    month_col = next((c for c in df.columns if re.search("month", c, re.I)), None)
    region_col = next((c for c in df.columns if re.search("region", c, re.I)), None)
    category_col = next((c for c in df.columns if re.fullmatch("category", c.strip(), re.I)), None)
    platform_col = next((c for c in df.columns if re.search("platform", c, re.I)), None)
    keyword_type_col = next((c for c in df.columns if re.search("keyword type", c, re.I)), None)
    keyword_col = next((c for c in df.columns if re.fullmatch("keyword", c.strip(), re.I)), None)

    # --- Clean category
    if category_col:
        df[category_col] = (
            df[category_col].astype(str).str.strip()
            .replace({"nan": pd.NA, "NaN": pd.NA, "": pd.NA, "None": pd.NA})
            .str.title()
        )

    # --- Normalize platform names
    if platform_col:
        df[platform_col] = (
            df[platform_col].astype(str).str.strip().str.lower().replace({
                "instagram": "instamart", "insta-mart": "instamart",
                "blinkit": "blinkit", "zepto": "zepto"
            }).map({"blinkit": "Blinkit", "instamart": "Instamart", "zepto": "Zepto"})
        )

    # --- Normalize keyword type
    if keyword_type_col:
        df[keyword_type_col] = (
            df[keyword_type_col].astype(str).str.strip().str.lower()
            .replace({"branded": "brand"}).str.title()
        )

    # --- Detect metrics
    metrics = {
        "Volume Share": next((c for c in df.columns if re.search("volume share", c, re.I)), None),
        "Ad SOV": next((c for c in df.columns if re.search(r"\bad", c, re.I)), None),
        "Org. SOV": next((c for c in df.columns if re.search("org", c, re.I)), None),
        "Overall SOV": next((c for c in df.columns if re.search("overall", c, re.I)), None),
        "Cat. Imp. Share": next((c for c in df.columns if re.search("cat.*imp", c, re.I)), None),
    }

    # --- Convert to numeric
    for col in metrics.values():
        if col and col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("%", "", regex=False).replace("", 0),
                errors="coerce"
            ).fillna(0)

    # --- Month mapping
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    def parse_month(x):
        for k, v in month_map.items():
            if re.search(k, str(x).lower()):
                return v
        return None

    df["MonthNum"] = df[month_col].apply(parse_month)
    df["MonthName"] = df["MonthNum"].map({v: k.title() for k, v in month_map.items()})
    df = df.dropna(subset=["MonthNum"])

    # --- Remove "ALL" keyword and keep only Apr–Sep
    if keyword_col:
        df = df[~df[keyword_col].astype(str).str.fullmatch("all", case=False, na=False)]
    df = df[df["MonthNum"] >= 4]

    # --- Valid platforms only
    valid_platforms = ["Blinkit", "Instamart", "Zepto"]
    df = df[df[platform_col].isin(valid_platforms)]

    return df, region_col, category_col, platform_col, keyword_type_col, keyword_col, metrics


df, region_col, category_col, platform_col, keyword_type_col, keyword_col, metrics = load_data()

# --------------------------------------------------
# 📂 Tabs
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "📈 Volume Share MoM",
    "🔍 Keyword Trend Analysis",
    "💪 Brand Strength Analysis"
])

# --------------------------------------------------
# 🧭 TAB 1 — Volume Share MoM
# --------------------------------------------------
with tab1:
    st.markdown("<h2 style='color:#ffffff;'>Volume Share MoM Analysis by Keyword Type</h2>", unsafe_allow_html=True)

    st.sidebar.header("Filter Options (Tab 1)")
    regions = st.sidebar.multiselect("Select Region(s):", sorted(df[region_col].dropna().unique()), key="region_tab1")
    categories = st.sidebar.multiselect("Select Category(s):", sorted(df[category_col].dropna().unique()), key="category_tab1")

    filtered_df = df.copy()
    if regions:
        filtered_df = filtered_df[filtered_df[region_col].isin(regions)]
    if categories:
        filtered_df = filtered_df[filtered_df[category_col].isin(categories)]

    def format_keywords_table(keywords):
        if not keywords:
            return "<p><i>No keywords available.</i></p>"
        half = math.ceil(len(keywords) / 2)
        col1, col2 = keywords[:half], keywords[half:]
        html = """
        <div style="background-color:rgba(255,255,255,0.03);border-radius:8px;padding:8px 12px;
        border:1px solid rgba(255,255,255,0.08);font-family:'Inter',sans-serif;color:#f5f5f5;
        font-size:13px;line-height:1.2;width:100%;max-height:300px;overflow-y:auto;">
        <table style="width:100%;border-collapse:collapse;">
        <tr><td style="vertical-align:top;width:48%;padding-right:10px;">"""
        html += "".join(f"<div style='padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.06);'>{kw.title()}</div>" for kw in col1)
        html += "</td><td style='vertical-align:top;width:48%;'>"
        html += "".join(f"<div style='padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.06);'>{kw.title()}</div>" for kw in col2)
        html += "</td></tr></table></div>"
        return html

    for kw_type in df[keyword_type_col].dropna().unique():
        type_df = filtered_df[filtered_df[keyword_type_col] == kw_type]
        if type_df.empty:
            continue

        vol_col = metrics["Volume Share"]
        benchmark_df = type_df[type_df["MonthNum"].between(4, 6)]
        benchmark_value = benchmark_df[vol_col].mean() if not benchmark_df.empty else 0

        trend_data = (
            type_df.groupby(["MonthName", "MonthNum", platform_col])[vol_col]
            .mean().reset_index().sort_values("MonthNum")
        )

        st.markdown(
            f"<h3 style='color:#ffffff;margin-top:35px;'>{kw_type} Keywords — Volume Share Trend (Apr–Sep)</h3>",
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([2.5, 1])
        with col1:
            fig = px.line(
                trend_data, x="MonthName", y=vol_col, color=platform_col, markers=True,
                labels={"MonthName": "Month", vol_col: "Volume Share (%)"}
            )
            fig.update_traces(connectgaps=False)
            fig.update_yaxes(zeroline=False)
            fig.add_hline(
                y=benchmark_value, line_dash="dot",
                annotation_text=f"Benchmark (Apr–Jun Avg: {benchmark_value:.2f}%)",
                annotation_position="bottom right", line_color="white", opacity=0.6
            )
            fig.update_layout(template="plotly_dark", height=400, yaxis=dict(ticksuffix="%"))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("<h4 style='color:#f5f5f5;'>Keywords in this Type</h4>", unsafe_allow_html=True)
            keywords = sorted(type_df[keyword_col].dropna().unique().tolist())
            st.markdown(format_keywords_table(keywords), unsafe_allow_html=True)

# --------------------------------------------------
# 🔍 TAB 2 — Keyword Trend Analysis (stacked full-width charts)
# --------------------------------------------------
with tab2:
    st.markdown("<h2 style='color:#ffffff;'>Keyword Trend Analysis</h2>", unsafe_allow_html=True)

    st.sidebar.header("Filter Options (Tab 2)")
    region_filter = st.sidebar.multiselect("Select Region(s):", sorted(df[region_col].dropna().unique()), key="region_tab2")
    category_filter = st.sidebar.multiselect("Select Category(s):", sorted(df[category_col].dropna().unique()), key="category_tab2")
    kw_type_filter = st.sidebar.multiselect(
        "Select Keyword Type(s):",
        sorted(df[keyword_type_col].dropna().unique()),
        default=["Brand"],
        key="kwtype_tab2"
    )

    kw_base = df.copy()
    if region_filter:
        kw_base = kw_base[kw_base[region_col].isin(region_filter)]
    if category_filter:
        kw_base = kw_base[kw_base[category_col].isin(category_filter)]
    if kw_type_filter:
        kw_base = kw_base[kw_base[keyword_type_col].isin(kw_type_filter)]

    kw_options = sorted(kw_base[keyword_col].dropna().unique())
    selected_keywords = st.sidebar.multiselect("Select Keyword(s):", kw_options, key="keyword_tab2")
    selected_metrics = st.sidebar.multiselect("Select Metrics to Display:", list(metrics.keys()), default=["Volume Share"], key="metrics_tab2")

    filtered = df.copy()
    if region_filter:
        filtered = filtered[filtered[region_col].isin(region_filter)]
    if category_filter:
        filtered = filtered[filtered[category_col].isin(category_filter)]
    if kw_type_filter:
        filtered = filtered[filtered[keyword_type_col].isin(kw_type_filter)]
    if selected_keywords:
        filtered = filtered[filtered[keyword_col].isin(selected_keywords)]

    if filtered.empty:
        st.warning("No data available for the selected filters.")
    else:
        label_types = ", ".join(kw_type_filter) if kw_type_filter else "All Types"
        st.markdown(f"<h4 style='color:#f5f5f5;'>Trend for Selected Keywords ({label_types})</h4>", unsafe_allow_html=True)

        valid_platforms = ["Blinkit", "Instamart", "Zepto"]
        for platform in valid_platforms:
            plat_df = filtered[filtered[platform_col] == platform]
            if plat_df.empty:
                st.warning(f"No data for {platform}")
                continue

            for metric in selected_metrics:
                metric_col = metrics[metric]
                plot_df = plat_df.sort_values("MonthNum").copy()
                # IMPORTANT: do NOT drop real zeros; only avoid connecting gaps
                fig = px.line(
                    plot_df, x="MonthName", y=metric_col, color=keyword_col, markers=True,
                    title=f"{platform} — {metric}",
                    labels={"MonthName": "Month", metric_col: f"{metric} (%)"},
                )
                fig.update_traces(connectgaps=False)
                fig.update_yaxes(zeroline=False)
                fig.update_layout(
                    template="plotly_dark",
                    height=450,
                    yaxis=dict(ticksuffix="%"),
                    title_font=dict(size=18),
                    margin=dict(l=30, r=30, t=60, b=30)
                )
                st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# 💪 TAB 3 — Brand Strength Analysis  (BrandStrength.xlsx)
# --------------------------------------------------
@st.cache_data
def load_brand_strength():
    df_bs = pd.read_excel("BrandStrength.xlsx")
    df_bs.columns = df_bs.columns.str.strip()

    region_col = next((c for c in df_bs.columns if re.search("region", c, re.I)), None)
    category_col = next((c for c in df_bs.columns if re.search("category", c, re.I)), None)
    platform_col = next((c for c in df_bs.columns if re.search("platform", c, re.I)), None)
    month_col = next((c for c in df_bs.columns if re.search("month", c, re.I)), None)
    bs_col = next((c for c in df_bs.columns if re.search("brand.*strength", c, re.I)), None)

    # Normalize platforms
    if platform_col:
        df_bs[platform_col] = (
            df_bs[platform_col].astype(str).str.strip().str.lower().replace({
                "instagram": "instamart", "insta-mart": "instamart",
                "blinkit": "blinkit", "zepto": "zepto"
            }).map({"blinkit": "Blinkit", "instamart": "Instamart", "zepto": "Zepto"})
        )

    # Month parsing
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    def parse_month(x):
        for k, v in month_map.items():
            if re.search(k, str(x).lower()):
                return v
        return None

    df_bs["MonthNum"] = df_bs[month_col].apply(parse_month)
    df_bs["MonthName"] = df_bs["MonthNum"].map({v: k.title() for k, v in month_map.items()})
    df_bs = df_bs.dropna(subset=["MonthNum"])
    df_bs = df_bs[df_bs["MonthNum"] >= 4]  # Apr–Sep only

    if bs_col:
        df_bs[bs_col] = pd.to_numeric(
            df_bs[bs_col].astype(str).str.replace("%", "", regex=False),
            errors="coerce"
        ).fillna(0)

    return df_bs, region_col, category_col, platform_col, bs_col


with tab3:
    st.markdown("<h2 style='color:#ffffff;'>Brand Strength Analysis</h2>", unsafe_allow_html=True)
    bs_df, region_col_bs, category_col_bs, platform_col_bs, bs_col = load_brand_strength()

    st.sidebar.header("Filter Options (Tab 3)")
    regions_bs = st.sidebar.multiselect("Select Region(s):", sorted(bs_df[region_col_bs].dropna().unique()), key="region_bs")
    categories_bs = st.sidebar.multiselect("Select Category(s):", sorted(bs_df[category_col_bs].dropna().unique()), key="category_bs")

    filtered_bs = bs_df.copy()
    if regions_bs:
        filtered_bs = filtered_bs[filtered_bs[region_col_bs].isin(regions_bs)]
    if categories_bs:
        filtered_bs = filtered_bs[filtered_bs[category_col_bs].isin(categories_bs)]

    if filtered_bs.empty:
        st.warning("No data available for selected filters.")
    else:
        valid_platforms = ["Blinkit", "Instamart", "Zepto"]
        for platform in valid_platforms:
            plat_df = filtered_bs[filtered_bs[platform_col_bs] == platform]
            if plat_df.empty:
                st.warning(f"No data for {platform}")
                continue

            fig = px.line(
                plat_df.sort_values("MonthNum"),
                x="MonthName", y=bs_col, markers=True,
                title=f"{platform} — Brand Strength Trend (Apr–Sep)",
                labels={"MonthName": "Month", bs_col: "Brand Strength (%)"}
            )
            fig.update_traces(connectgaps=False)
            fig.update_yaxes(zeroline=False)
            fig.update_layout(template="plotly_dark", height=450, yaxis=dict(ticksuffix="%"))
            st.plotly_chart(fig, use_container_width=True)
