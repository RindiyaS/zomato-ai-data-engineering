import os
import re
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import snowflake.connector

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()


# ============================================================
# CONFIG
# ============================================================

MODEL = "gemini-3.5-flash-lite"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("❌ GEMINI_API_KEY is missing in .env file.")
    st.stop()


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Zomato AI Analytics",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# THEME-FRIENDLY CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    h1 {
        font-size: 42px !important;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }

    h2 {
        font-weight: 700 !important;
    }

    h3 {
        font-weight: 700 !important;
    }

    .section-title {
        font-size: 22px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 12px;
    }

    div[data-testid="stMetric"] {
        padding: 18px;
        border-radius: 16px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.10);
    }

    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 800;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 12px;
    }

    div[data-testid="stDownloadButton"] button {
        border-radius: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "query_result" not in st.session_state:
    st.session_state.query_result = None

if "generated_sql" not in st.session_state:
    st.session_state.generated_sql = None

if "last_question" not in st.session_state:
    st.session_state.last_question = ""

if "query_executed" not in st.session_state:
    st.session_state.query_executed = False

if "selected_example" not in st.session_state:
    st.session_state.selected_example = ""

if "question_input" not in st.session_state:
    st.session_state.question_input = ""


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🍽️ Zomato AI")

    st.markdown("---")

    st.subheader("📊 Analytics")

    st.write(
        "Ask natural-language questions "
        "and explore your Zomato data."
    )

    st.markdown("---")

    st.subheader("💡 Example Questions")

    st.caption(
        "Click a question to use it:"
    )


    # --------------------------------------------------------
    # EXAMPLE QUESTION 1
    # --------------------------------------------------------

    if st.button(
        "Top 10 cities by GMV",
        use_container_width=True
    ):

        st.session_state.question_input = (
            "Top 10 cities by GMV"
        )

        st.session_state.query_result = None
        st.session_state.generated_sql = None
        st.session_state.query_executed = False

        st.rerun()


    # --------------------------------------------------------
    # EXAMPLE QUESTION 2
    # --------------------------------------------------------

    if st.button(
        "Top restaurants by revenue",
        use_container_width=True
    ):

        st.session_state.question_input = (
            "Top restaurants by revenue"
        )

        st.session_state.query_result = None
        st.session_state.generated_sql = None
        st.session_state.query_executed = False

        st.rerun()


    # --------------------------------------------------------
    # EXAMPLE QUESTION 3
    # --------------------------------------------------------

    if st.button(
        "Which city has the highest AOV?",
        use_container_width=True
    ):

        st.session_state.question_input = (
            "Which city has the highest AOV?"
        )

        st.session_state.query_result = None
        st.session_state.generated_sql = None
        st.session_state.query_executed = False

        st.rerun()


    # --------------------------------------------------------
    # EXAMPLE QUESTION 4
    # --------------------------------------------------------

    if st.button(
        "Show cancellation rate by city",
        use_container_width=True
    ):

        st.session_state.question_input = (
            "Show cancellation rate by city"
        )

        st.session_state.query_result = None
        st.session_state.generated_sql = None
        st.session_state.query_executed = False

        st.rerun()


    # --------------------------------------------------------
    # EXAMPLE QUESTION 5
    # --------------------------------------------------------

    if st.button(
        "Average delivery time by city",
        use_container_width=True
    ):

        st.session_state.question_input = (
            "Average delivery time by city"
        )

        st.session_state.query_result = None
        st.session_state.generated_sql = None
        st.session_state.query_executed = False

        st.rerun()


    # --------------------------------------------------------
    # EXAMPLE QUESTION 6
    # --------------------------------------------------------

    if st.button(
        "Revenue by cuisine",
        use_container_width=True
    ):

        st.session_state.question_input = (
            "Revenue by cuisine"
        )

        st.session_state.query_result = None
        st.session_state.generated_sql = None
        st.session_state.query_executed = False

        st.rerun()


    st.markdown("---")

    st.subheader("⚙️ Technology")

    st.write("🤖 Gemini")
    st.write("❄️ Snowflake")
    st.write("📊 Streamlit")
    st.write("📈 Plotly")


# ============================================================
# SNOWFLAKE CONNECTION
# ============================================================

def get_snowflake_connection():

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="MARTS",
        role="DBT_ROLE"
    )


# ============================================================
# TABLE INFORMATION
# ============================================================

TABLE_INFO = """

Available Snowflake tables:

1. FCT_ORDERS

Columns:
- order_id
- order_date
- customer_id
- restaurant_id
- city
- cuisine
- payment_method
- order_status
- is_delivered
- sales_amount
- discount
- delivery_fee
- gst
- customer_rating
- delivery_time_min


2. DIM_RESTAURANTS

Columns:
- restaurant_id
- restaurant_name
- city
- cuisine
- rating
- cost_for_two


3. DIM_CUSTOMER

Columns:
- customer_id
- customer_name
- age
- age_segment
- gender
- city


4. MART_DAILY_CITY_REVENUE

Columns:
- order_date
- city
- orders
- cancel_rate
- gmv
- aov


5. MART_RESTAURANT_PERFORMANCE

Columns:
- restaurant_id
- restaurant_name
- city
- cuisine
- orders
- revenue
- avg_customer_rating
- cancel_rate


6. MART_DELIVERY_SLA

Columns:
- city
- order_hour
- delivered_orders
- p50_delivery_min
- late_rate

"""


# ============================================================
# GEMINI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = f"""

You are a Snowflake SQL generator for a Zomato analytics application.

{TABLE_INFO}

Rules:

1. Return ONLY valid JSON.

Exact format:

{{
  "sql": "SELECT ..."
}}

2. Generate ONLY SELECT queries or WITH ... SELECT queries.

3. Never generate:

DROP
DELETE
TRUNCATE
ALTER
UPDATE
INSERT
CREATE
REPLACE
GRANT
REVOKE

4. Use only the tables and columns provided above.

5. Prefer MART tables when they can answer the question directly.

6. Do not invent table names.

7. Use bare table names.

8. Do not add database/schema prefixes.

9. Always make the SQL executable in Snowflake.

10. Maximum 100 rows unless the user explicitly asks for an aggregation.

11. For ranking questions such as:

"Top 10 cities by GMV"

Use:

SELECT
    city,
    SUM(gmv) AS total_gmv
FROM MART_DAILY_CITY_REVENUE
GROUP BY city
ORDER BY total_gmv DESC
LIMIT 10

12. For city-wise GMV, use MART_DAILY_CITY_REVENUE.

13. For restaurant performance, use MART_RESTAURANT_PERFORMANCE.

14. For delivery SLA questions, use MART_DELIVERY_SLA.

15. For customer questions, use DIM_CUSTOMER.

16. For raw order-level questions, use FCT_ORDERS.

17. SQL must not contain markdown code fences.

18. Return valid JSON only.
"""


# ============================================================
# GENERATE SQL
# ============================================================

def generate_sql(question):

    response = client.models.generate_content(
        model=MODEL,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0
        )
    )

    text = response.text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```",
        "",
        text
    )

    text = text.strip()

    try:

        data = json.loads(text)

        sql = data["sql"]

    except Exception:

        raise ValueError(
            "Gemini returned invalid JSON.\n\n"
            + text
        )

    return sql.strip()


# ============================================================
# SQL SAFETY
# ============================================================

FORBIDDEN_WORDS = [
    "drop",
    "delete",
    "truncate",
    "alter",
    "update",
    "insert",
    "create",
    "replace",
    "grant",
    "revoke"
]


def is_safe_sql(sql):

    sql_clean = sql.strip().lower()

    if not (
        sql_clean.startswith("select")
        or sql_clean.startswith("with")
    ):

        return False

    for word in FORBIDDEN_WORDS:

        pattern = rf"\b{word}\b"

        if re.search(
            pattern,
            sql_clean
        ):

            return False

    return True


# ============================================================
# MAKE COLUMN NAMES UNIQUE
# ============================================================

def make_unique_columns(df):

    """
    Streamlit/PyArrow requires unique DataFrame column names.

    Example:

    TOTAL_GMV
    TOTAL_GMV

    becomes:

    TOTAL_GMV
    TOTAL_GMV_2
    """

    columns = []

    column_counts = {}

    for column in df.columns:

        column = str(column)

        if column not in column_counts:

            column_counts[column] = 1

            columns.append(column)

        else:

            column_counts[column] += 1

            new_column = (
                f"{column}_{column_counts[column]}"
            )

            columns.append(new_column)

    df.columns = columns

    return df


# ============================================================
# EXECUTE SQL
# ============================================================

def execute_query(sql):

    conn = None

    try:

        conn = get_snowflake_connection()

        df = pd.read_sql(
            sql,
            conn
        )

        # IMPORTANT:
        # Prevent duplicate column names from
        # breaking Streamlit/PyArrow.
        df = make_unique_columns(df)

        return df

    finally:

        if conn:

            conn.close()


# ============================================================
# MAIN HEADER
# ============================================================

st.title("🍽️ Zomato AI Analytics")

st.caption(
    "Ask questions in natural language → "
    "Gemini generates SQL → "
    "Snowflake returns the analytics."
)


# ============================================================
# QUESTION INPUT
# ============================================================

question = st.text_input(
    "💬 Ask your analytics question",

    placeholder="Example: Top 10 cities by GMV",

    key="question_input"
)


# ============================================================
# CURRENT QUESTION
# ============================================================

current_question = question.strip()


# ============================================================
# CLEAR OLD RESULT WHEN QUESTION CHANGES
# ============================================================

if (
    st.session_state.last_question
    and current_question != st.session_state.last_question
):

    st.session_state.query_result = None

    st.session_state.generated_sql = None

    st.session_state.query_executed = False


# ============================================================
# RUN BUTTON
# ============================================================

run_button = st.button(
    "🚀 Run",
    type="primary"
)


# ============================================================
# RUN QUERY
# ============================================================

if run_button:

    if not current_question:

        st.warning(
            "Please enter a question."
        )

        st.stop()


    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    try:

        with st.spinner(
            "🤖 Gemini is generating SQL..."
        ):

            sql = generate_sql(
                current_question
            )

    except Exception as e:

        st.error(
            f"❌ Gemini error: {e}"
        )

        st.stop()


    # --------------------------------------------------------
    # SQL SAFETY CHECK
    # --------------------------------------------------------

    if not is_safe_sql(sql):

        st.error(
            "🚫 Unsafe SQL detected."
        )

        st.stop()


    # --------------------------------------------------------
    # SAVE SQL
    # --------------------------------------------------------

    st.session_state.generated_sql = sql


    # --------------------------------------------------------
    # SNOWFLAKE
    # --------------------------------------------------------

    try:

        with st.spinner(
            "❄️ Running Snowflake query..."
        ):

            df = execute_query(
                sql
            )

    except Exception as e:

        st.error(
            f"❌ Snowflake error: {e}"
        )

        st.stop()


    # --------------------------------------------------------
    # EMPTY RESULT
    # --------------------------------------------------------

    if df is None or df.empty:

        st.session_state.query_result = None

        st.session_state.query_executed = False

        st.warning(
            "No results found."
        )

        st.stop()


    # --------------------------------------------------------
    # CLEAN RESULT
    # --------------------------------------------------------

    df = df.dropna(
        axis=0,
        how="all"
    )

    df = df.dropna(
        axis=1,
        how="all"
    )

    df = df.reset_index(
        drop=True
    )

    # IMPORTANT:
    # Make sure column names are still unique
    # after cleaning.
    df = make_unique_columns(df)


    # --------------------------------------------------------
    # SAVE RESULT
    # --------------------------------------------------------

    st.session_state.query_result = df

    st.session_state.last_question = (
        current_question
    )

    st.session_state.query_executed = True


# ============================================================
# SHOW RESULT ONLY FOR CURRENT QUESTION
# ============================================================

show_result = (
    st.session_state.query_executed
    and
    st.session_state.query_result is not None
    and
    current_question == st.session_state.last_question
)


if show_result:

    df = st.session_state.query_result


    # ========================================================
    # GENERATED SQL
    # ========================================================

    with st.expander(
        "🔍 View Generated SQL",
        expanded=False
    ):

        st.code(
            st.session_state.generated_sql,
            language="sql"
        )


    # ========================================================
    # RESULT HEADER
    # ========================================================

    st.markdown(
        "### 📊 Query Results"
    )


    # ========================================================
    # SINGLE VALUE
    # ========================================================

    if (
        df.shape[0] == 1
        and
        df.shape[1] == 1
    ):

        column_name = df.columns[0]

        value = df.iloc[0, 0]

        if isinstance(
            value,
            (int, float)
        ):

            display_value = (
                f"{value:,.2f}"
            )

        else:

            display_value = str(
                value
            )

        st.metric(
            label=str(
                column_name
            )
            .replace("_", " ")
            .title(),

            value=display_value
        )


    # ========================================================
    # ONE ROW / MULTIPLE COLUMNS
    # ========================================================

    elif df.shape[0] == 1:

        columns = st.columns(
            min(
                len(df.columns),
                4
            )
        )

        for i, column_name in enumerate(
            df.columns
        ):

            value = df.iloc[0][
                column_name
            ]

            with columns[
                i % len(columns)
            ]:

                label = (
                    str(column_name)
                    .replace("_", " ")
                    .title()
                )

                if isinstance(
                    value,
                    (int, float)
                ):

                    display_value = (
                        f"{value:,.2f}"
                    )

                else:

                    display_value = str(
                        value
                    )

                st.metric(
                    label=label,
                    value=display_value
                )


    # ========================================================
    # MULTI ROW RESULT
    # ========================================================

    else:

        # ----------------------------------------------------
        # DATA TABLE
        # ----------------------------------------------------

        st.dataframe(
            df,

            width="stretch",

            hide_index=True
        )


        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        csv_data = (
            df.to_csv(
                index=False
            )
            .encode("utf-8")
        )

        st.download_button(
            "⬇️ Download CSV",

            data=csv_data,

            file_name=(
                "zomato_query_result.csv"
            ),

            mime="text/csv"
        )


        # ====================================================
        # INTERACTIVE VISUALIZATION
        # ====================================================

        st.markdown(
            "### 📈 Interactive Visualization"
        )


        numeric_columns = (
            df.select_dtypes(
                include=["number"]
            )
            .columns
            .tolist()
        )


        if not numeric_columns:

            st.info(
                "ℹ️ This result does not contain "
                "a numeric column for charting."
            )


        else:

            # =================================================
            # CHART CONTROLS
            # =================================================

            c1, c2, c3 = st.columns(3)


            with c1:

                chart_type = st.selectbox(
                    "📊 Chart Type",

                    [
                        "Bar",
                        "Line",
                        "Area"
                    ],

                    key="chart_type"
                )


            with c2:

                x_column = st.selectbox(
                    "↔️ X Axis",

                    df.columns.tolist(),

                    key="x_axis"
                )


            with c3:

                y_column = st.selectbox(
                    "↕️ Y Axis",

                    numeric_columns,

                    key="y_axis"
                )


            # =================================================
            # SECOND ROW
            # =================================================

            c1, c2, c3, c4 = st.columns(4)


            with c1:

                show_values = st.toggle(
                    "🔢 Show Values",

                    value=True,

                    key="show_values"
                )


            with c2:

                show_percentage = st.toggle(
                    "📊 Show %",

                    value=False,

                    key="show_percentage"
                )


            with c3:

                sort_order = st.selectbox(
                    "↕️ Sort",

                    [
                        "Original",
                        "Highest → Lowest",
                        "Lowest → Highest"
                    ],

                    key="sort_order"
                )


            with c4:

                # Safe slider values
                row_count = len(df)

                max_slider_value = max(
                    1,
                    min(
                        100,
                        row_count
                    )
                )

                default_slider_value = min(
                    10,
                    max_slider_value
                )

                max_rows = st.slider(
                    "🔝 Show Top N",

                    min_value=1,

                    max_value=max_slider_value,

                    value=default_slider_value,

                    key="max_rows"
                )


            # =================================================
            # PREPARE CHART DATA
            # =================================================

            chart_df = df.copy()


            if (
                sort_order
                == "Highest → Lowest"
            ):

                chart_df = (
                    chart_df
                    .sort_values(
                        by=y_column,
                        ascending=False
                    )
                )


            elif (
                sort_order
                == "Lowest → Highest"
            ):

                chart_df = (
                    chart_df
                    .sort_values(
                        by=y_column,
                        ascending=True
                    )
                )


            chart_df = (
                chart_df
                .head(max_rows)
                .copy()
            )


            # =================================================
            # PERCENTAGE
            # =================================================

            if show_percentage:

                total = (
                    pd.to_numeric(
                        chart_df[
                            y_column
                        ],
                        errors="coerce"
                    )
                    .fillna(0)
                    .sum()
                )

                if total != 0:

                    chart_df[
                        "_percentage"
                    ] = (
                        pd.to_numeric(
                            chart_df[
                                y_column
                            ],
                            errors="coerce"
                        )
                        .fillna(0)
                        / total
                        * 100
                    )

                else:

                    chart_df[
                        "_percentage"
                    ] = 0.0


            # =================================================
            # CREATE CHART
            # =================================================

            if chart_type == "Bar":

                fig = px.bar(
                    chart_df,

                    x=x_column,

                    y=y_column,

                    text=(
                        y_column
                        if show_values
                        else None
                    ),

                    title=(
                        f"{y_column} by "
                        f"{x_column}"
                    )
                )


            elif chart_type == "Line":

                fig = px.line(
                    chart_df,

                    x=x_column,

                    y=y_column,

                    markers=True,

                    text=(
                        y_column
                        if show_values
                        else None
                    ),

                    title=(
                        f"{y_column} by "
                        f"{x_column}"
                    )
                )


            else:

                fig = px.area(
                    chart_df,

                    x=x_column,

                    y=y_column,

                    title=(
                        f"{y_column} by "
                        f"{x_column}"
                    )
                )


            # =================================================
            # COLORFUL BAR CHART
            # =================================================

            if chart_type == "Bar":

                colors = [
                    "#FF4B6E",
                    "#FF8A65",
                    "#A78BFA",
                    "#22D3EE",
                    "#34D399",
                    "#FBBF24",
                    "#60A5FA",
                    "#F472B6",
                    "#818CF8",
                    "#2DD4BF"
                ]

                repeated_colors = (
                    colors
                    * (
                        len(chart_df)
                        // len(colors)
                        + 1
                    )
                )

                fig.update_traces(
                    marker=dict(
                        color=(
                            repeated_colors[
                                :len(chart_df)
                            ]
                        )
                    )
                )


            # =================================================
            # VALUE LABELS
            # =================================================

            if show_values:

                if chart_type == "Bar":

                    fig.update_traces(
                        texttemplate="%{text}",

                        textposition="outside"
                    )

                elif chart_type == "Line":

                    fig.update_traces(
                        texttemplate="%{text}",

                        textposition="top center"
                    )

                elif chart_type == "Area":

                    fig.update_traces(
                        texttemplate="%{text}",

                        textposition="top center"
                    )


            # =================================================
            # PERCENTAGE HOVER
            # =================================================

            if show_percentage:

                fig.update_traces(
                    customdata=(
                        chart_df[
                            ["_percentage"]
                        ].values
                    ),

                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        f"{y_column}: "
                        "%{y:,.2f}<br>"
                        "Percentage: "
                        "%{customdata[0]:.2f}%"
                        "<extra></extra>"
                    )
                )


            # =================================================
            # CHART LAYOUT
            # =================================================

            fig.update_layout(
                height=520,

                autosize=True,

                margin=dict(
                    l=20,
                    r=20,
                    t=70,
                    b=30
                ),

                hovermode="x unified",

                legend=dict(
                    orientation="h",

                    yanchor="bottom",

                    y=1.02,

                    xanchor="right",

                    x=1
                )
            )


            fig.update_xaxes(
                showgrid=False
            )


            fig.update_yaxes(
                showgrid=True,

                gridcolor=(
                    "rgba(128,128,128,0.18)"
                )
            )


            # =================================================
            # DISPLAY CHART
            # =================================================

            st.plotly_chart(
                fig,

                width="stretch",

                key="main_chart"
            )


            # =================================================
            # PERCENTAGE BREAKDOWN
            # =================================================

            if show_percentage:

                # IMPORTANT:
                # Build this DataFrame explicitly with
                # unique column names.
                #
                # This avoids the PyArrow error:
                # Duplicate column names found

                percentage_df = pd.DataFrame()

                percentage_df[
                    str(x_column)
                ] = chart_df[
                    x_column
                ].values

                percentage_df[
                    str(y_column)
                ] = chart_df[
                    y_column
                ].values

                percentage_df[
                    "Percentage"
                ] = chart_df[
                    "_percentage"
                ].round(2).values

                # Final safety check
                percentage_df = (
                    make_unique_columns(
                        percentage_df
                    )
                )

                with st.expander(
                    "📊 Percentage Breakdown"
                ):

                    st.dataframe(
                        percentage_df,

                        width="stretch",

                        hide_index=True
                    )


# ============================================================
# WAITING FOR RUN
# ============================================================

elif current_question:

    st.info(
        "👆 Click **🚀 Run** to generate "
        "fresh results for this question."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🍽️ Zomato AI Analytics • "
    "Gemini + Snowflake + Streamlit + Plotly"
)

