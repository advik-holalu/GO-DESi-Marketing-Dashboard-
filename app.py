import streamlit as st
import pandas as pd
import plotly.express as px
import re
import math

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(page_title="Brand Building Dashboard", layout="wide")
st.markdown(
    "<h1 style='text-align:left; font-weight:800;'>Brand Building Dashboard</h1>",
    unsafe_allow_html=True
)

# --------------------------------------------------
# Load and Clean Marketing Dashboard Data (Main File)
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("MarketingDashboardUpdated.xlsx")
    df.columns = df.columns.str.strip()

    # Detect core columns automatically
    month_col = next((c for c in df.columns if re.search("month", c, re.I)), None)
    region_col = next((c for c in df.columns if re.search("region", c, re.I)), None)
    category_col = next((c for c in df.columns if re.fullmatch("category", c.strip(), re.I)), None)
    platform_col = next((c for c in df.columns if re.search("platform", c, re.I)), None)
    keyword_type_col = next((c for c in df.columns if re.search("keyword type", c, re.I)), None)
    keyword_col = next((c for c in df.columns if re.fullmatch("keyword", c.strip(), re.I)), None)

    # Standardize category text formatting
    if category_col:
        df[category_col] = (
            df[category_col].astype(str).str.strip()
            .replace({"nan": pd.NA, "NaN": pd.NA, "": pd.NA, "None": pd.NA})
            .str.title()
        )

    # Normalize platform names
    if platform_col:
        df[platform_col] = (
            df[platform_col].astype(str).str.strip().str.lower().replace({
                "instagram": "instamart",
                "insta-mart": "instamart",
                "blinkit": "blinkit",
                "zepto": "zepto"
            }).map({
                "blinkit": "Blinkit",
                "instamart": "Instamart",
                "zepto": "Zepto"
            })
        )

    # Clean keyword type
    if keyword_type_col:
        df[keyword_type_col] = (
            df[keyword_type_col].astype(str).str.strip().str.lower()
            .replace({"branded": "brand"})
            .str.title()
        )

    # Detect metric columns
    metrics = {
        "Volume Share": next((c for c in df.columns if re.search("volume share", c, re.I)), None),
        "Ad SOV": next((c for c in df.columns if re.search(r"\bad", c, re.I)), None),
        "Org. SOV": next((c for c in df.columns if re.search("org", c, re.I)), None),
        "Overall SOV": next((c for c in df.columns if re.search("overall", c, re.I)), None),
        "Cat. Imp. Share": next((c for c in df.columns if re.search("cat.*imp", c, re.I)), None),
    }

    # Convert all metric percentage values to numeric
    for col in metrics.values():
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("%", "", regex=False),
                errors="coerce"
            ).fillna(0)

    # Month mapping and sorting
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    def parse_month(x):
        x = str(x).lower()
        for k, v in month_map.items():
            if k in x:
                return v
        return None

    df["MonthNum"] = df[month_col].apply(parse_month)
    df["MonthName"] = df["MonthNum"].map({v: k.title() for k, v in month_map.items()})
    df = df.dropna(subset=["MonthNum"])

    # Remove ALL keyword and restrict month to Apr onwards
    if keyword_col:
        df = df[~df[keyword_col].astype(str).str.fullmatch("all", case=False, na=False)]
    df = df[df["MonthNum"] >= 4]

    # Final platform constraint
    df = df[df[platform_col].isin(["Blinkit", "Instamart", "Zepto"])]

    return df, region_col, category_col, platform_col, keyword_type_col, keyword_col, metrics


# Load main dataset
df, region_col, category_col, platform_col, keyword_type_col, keyword_col, metrics = load_data()


# --------------------------------------------------
# Side Tabs Setup
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "Volume Share MoM",
    "Keyword Trend Analysis",
    "Brand Strength Analysis"
])

# --------------------------------------------------
# TAB 1 — Volume Share MoM (Regions as Lines)
# --------------------------------------------------
with tab1:
    st.markdown("<h2>Volume Share MoM Analysis by Keyword Type</h2>", unsafe_allow_html=True)

    # Sidebar Filters
    st.sidebar.header("Filter Options (Tab 1)")

    region_filter = st.sidebar.multiselect(
        "Select Region(s):",
        sorted(df[region_col].dropna().unique()),
        key="t1_region"
    )

    category_filter = st.sidebar.multiselect(
        "Select Category(s):",
        sorted(df[category_col].dropna().unique()),
        key="t1_category"
    )

    # NEW: Platform Filter
    platform_filter = st.sidebar.multiselect(
        "Select Platform(s):",
        sorted(df[platform_col].dropna().unique()),
        key="t1_platform"
    )

    # Apply filters
    filtered = df.copy()

    if region_filter:
        filtered = filtered[filtered[region_col].isin(region_filter)]

    if category_filter:
        filtered = filtered[filtered[category_col].isin(category_filter)]

    if platform_filter:
        filtered = filtered[filtered[platform_col].isin(platform_filter)]

    # Loop through Keyword Types (kept exactly like original)
    vol_col = metrics["Volume Share"]
    keyword_types = filtered[keyword_type_col].dropna().unique().tolist()

    for kw_type in keyword_types:

        data_kw = filtered[filtered[keyword_type_col] == kw_type]
        if data_kw.empty:
            continue

        # Q1 Benchmark (Apr-Jun average)
        q1df = data_kw[data_kw["MonthNum"].between(4, 6)]
        benchmark = q1df[vol_col].mean() if not q1df.empty else 0

        # Trend grouped by REGION instead of Platform
        trend = (
            data_kw.groupby(["MonthName", "MonthNum", region_col])[vol_col]
            .mean().reset_index().sort_values("MonthNum")
        )

        st.markdown(
            f"<h3 style='margin-top:35px;'>{kw_type} Keywords — Volume Share Trend (Apr–Sep)</h3>",
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([2.5, 1])

        # ------------------- GRAPH -------------------
        with col1:
            fig = px.line(
                trend,
                x="MonthName",
                y=vol_col,
                color=region_col,              # Region becomes the line series
                markers=True,
                labels={"MonthName": "Month", vol_col: "Volume Share"}
            )
            fig.update_traces(connectgaps=False)
            fig.update_yaxes(zeroline=False)

            # Benchmark Reference Line
            fig.add_hline(
                y=benchmark,
                line_dash="dot",
                annotation_text=f"Q1 Avg: {benchmark:.2f}",
                annotation_position="bottom right",
                opacity=0.55
            )

            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)

        # ------------------- KEYWORD TABLE -------------------
        with col2:
            st.markdown("<h4>Keywords in this Segment</h4>", unsafe_allow_html=True)
            keywords = sorted(data_kw[keyword_col].dropna().unique().tolist())

            def render_keyword_list(kw):
                half = math.ceil(len(kw) / 2)
                c1, c2 = kw[:half], kw[half:]
                html = "<div style='background:rgba(255,255,255,0.05);padding:8px 10px;border-radius:6px;'>"
                html += "<table style='width:100%;'><tr><td valign='top'>"
                html += "".join(f"<div style='margin-bottom:4px;border-bottom:1px solid rgba(255,255,255,0.08);'>{k}</div>" for k in c1)
                html += "</td><td valign='top'>"
                html += "".join(f"<div style='margin-bottom:4px;border-bottom:1px solid rgba(255,255,255,0.08);'>{k}</div>" for k in c2)
                html += "</td></tr></table></div>"
                return html

            st.markdown(render_keyword_list(keywords), unsafe_allow_html=True)

# --------------------------------------------------
# TAB 2 — Keyword Trend Analysis
# --------------------------------------------------
with tab2:
    st.markdown("<h2>Keyword Trend Analysis</h2>", unsafe_allow_html=True)

    st.sidebar.header("Filter Options (Tab 2)")

    # Filters remain unchanged
    region_filter_t2 = st.sidebar.multiselect(
        "Select Region(s):",
        sorted(df[region_col].dropna().unique()),
        key="t2_region"
    )

    category_filter_t2 = st.sidebar.multiselect(
        "Select Category(s):",
        sorted(df[category_col].dropna().unique()),
        key="t2_category"
    )

    keyword_type_filter = st.sidebar.multiselect(
        "Select Keyword Type(s):",
        sorted(df[keyword_type_col].dropna().unique()),
        default=["Brand"],
        key="t2_kwtype"
    )

    # Filter keyword universe first
    base_kw = df.copy()
    if region_filter_t2:
        base_kw = base_kw[base_kw[region_col].isin(region_filter_t2)]
    if category_filter_t2:
        base_kw = base_kw[base_kw[category_col].isin(category_filter_t2)]
    if keyword_type_filter:
        base_kw = base_kw[base_kw[keyword_type_col].isin(keyword_type_filter)]

    kw_choices = sorted(base_kw[keyword_col].dropna().unique())
    selected_keywords = st.sidebar.multiselect(
        "Select Keywords:",
        kw_choices,
        key="t2_keywords"
    )

    # Select metrics to display
    metric_choices = list(metrics.keys())
    selected_metrics = st.sidebar.multiselect(
        "Select Metrics to Display:",
        metric_choices,
        default=["Volume Share"],
        key="t2_metrics"
    )

    # Final filter pass before plotting
    filtered_t2 = df.copy()
    if region_filter_t2:
        filtered_t2 = filtered_t2[filtered_t2[region_col].isin(region_filter_t2)]
    if category_filter_t2:
        filtered_t2 = filtered_t2[filtered_t2[category_col].isin(category_filter_t2)]
    if keyword_type_filter:
        filtered_t2 = filtered_t2[filtered_t2[keyword_type_col].isin(keyword_type_filter)]
    if selected_keywords:
        filtered_t2 = filtered_t2[filtered_t2[keyword_col].isin(selected_keywords)]

    if filtered_t2.empty:
        st.warning("No data available for the selected filters.")
    else:
        label_block = ", ".join(keyword_type_filter) if keyword_type_filter else "All Keyword Types"
        st.markdown(f"<h4>Trend for Selected Keywords ({label_block})</h4>", unsafe_allow_html=True)

        # Loop platform -> then loop metrics
        for platform in ["Blinkit", "Instamart", "Zepto"]:
            pf = filtered_t2[filtered_t2[platform_col] == platform]
            if pf.empty:
                st.warning(f"No data found for {platform}")
                continue

            for metric in selected_metrics:
                metric_col = metrics[metric]
                df_plot = pf.sort_values("MonthNum")

                fig = px.line(
                    df_plot,
                    x="MonthName",
                    y=metric_col,
                    color=keyword_col,         # Keeps keyword comparison intact
                    markers=True,
                    title=f"{platform} — {metric}",
                    labels={"MonthName": "Month", metric_col: metric}
                )

                fig.update_traces(connectgaps=False)
                fig.update_yaxes(zeroline=False)
                fig.update_layout(template="plotly_dark", height=450, margin=dict(l=30, r=30, t=60, b=30))

                st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TAB 3 — Brand Strength Analysis
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

    # Standardize platform names
    df_bs[platform_col] = (
        df_bs[platform_col].astype(str).str.strip().str.lower().replace({
            "instagram": "instamart",
            "insta-mart": "instamart",
            "blinkit": "blinkit",
            "zepto": "zepto"
        }).map({
            "blinkit": "Blinkit",
            "instamart": "Instamart",
            "zepto": "Zepto"
        })
    )

    # Month conversion
    month_map = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    df_bs["MonthNum"] = df_bs[month_col].apply(lambda x: next((v for k,v in month_map.items() if k in str(x).lower()), None))
    df_bs["MonthName"] = df_bs["MonthNum"].map({v:k.title() for k,v in month_map.items()})
    df_bs = df_bs.dropna(subset=["MonthNum"])
    df_bs = df_bs[df_bs["MonthNum"] >= 4]

    # Numeric conversion
    df_bs[bs_col] = pd.to_numeric(df_bs[bs_col].astype(str).str.replace("%",""), errors="coerce").fillna(0)

    return df_bs, region_col, category_col, platform_col, bs_col


with tab3:
    st.markdown("<h2>Brand Strength Analysis</h2>", unsafe_allow_html=True)

    bs_df, region_bs, category_bs, platform_bs, strength_col = load_brand_strength()

    st.sidebar.header("Filter Options (Tab 3)")

    region_filter_bs = st.sidebar.multiselect(
        "Select Region(s):",
        sorted(bs_df[region_bs].dropna().unique()),
        key="t3_region"
    )

    category_filter_bs = st.sidebar.multiselect(
        "Select Category(s):",
        sorted(bs_df[category_bs].dropna().unique()),
        key="t3_category"
    )

    # Apply filters
    filtered_bs = bs_df.copy()
    if region_filter_bs:
        filtered_bs = filtered_bs[filtered_bs[region_bs].isin(region_filter_bs)]
    if category_filter_bs:
        filtered_bs = filtered_bs[filtered_bs[category_bs].isin(category_filter_bs)]

    if filtered_bs.empty:
        st.warning("No data available.")
    else:
        for platform in ["Blinkit", "Instamart", "Zepto"]:

            pf = filtered_bs[filtered_bs[platform_bs] == platform]
            if pf.empty:
                continue

            # Region-based trend (main fix)
            trend_bs = (
                pf.groupby(["MonthName","MonthNum",region_bs])[strength_col]
                .mean().reset_index().sort_values("MonthNum")
            )

            fig = px.line(
                trend_bs,
                x="MonthName",
                y=strength_col,
                color=region_bs,        # now one line per region
                markers=True,
                title=f"{platform} — Brand Strength by Region",
                labels={"MonthName": "Month", strength_col: "Brand Strength"}
            )

            fig.update_traces(connectgaps=False)
            fig.update_yaxes(zeroline=False)
            fig.update_layout(template="plotly_dark", height=450)

            st.plotly_chart(fig, use_container_width=True)
