import os
import numpy as np
import pandas as pd
import streamlit as st
import snowflake.connector
from google import genai
from google.genai import types
from dotenv import load_dotenv


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# Configuration
# --------------------------------------------------

EMBEDDING_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-3.5-flash-lite"

NEW_REVIEWS = 100
TOK_K = 5

CACHE_FILE = "review_embeddings.parquet"


# --------------------------------------------------
# Gemini client
# --------------------------------------------------

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# --------------------------------------------------
# Read reviews from Snowflake
# --------------------------------------------------

def read_reviews_from_snowflake():

    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

    query = f"""
        SELECT
            REVIEW_ID,
            CITY,
            RATING,
            COMMENT
        FROM ZOMATO.STAGING.STG_REVIEWS
        SAMPLE ({NEW_REVIEWS} ROWS)
    """

    df = conn.cursor().execute(query).fetch_pandas_all()

    conn.close()

    # Convert column names to lowercase
    df.columns = [col.lower() for col in df.columns]

    return df


# --------------------------------------------------
# Create embeddings
# --------------------------------------------------

def embed(texts):

    embeddings = []

    for text in texts:

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text
        )

        embeddings.append(
            response.embeddings[0].values
        )

    return embeddings


# --------------------------------------------------
# Load reviews
# --------------------------------------------------

@st.cache_data()
def load_reviews():

    # If embeddings already exist, use them
    if os.path.exists(CACHE_FILE):

        return pd.read_parquet(CACHE_FILE)

    # Otherwise get reviews from Snowflake
    df = read_reviews_from_snowflake()

    # Create embeddings for each review
    df["embedding"] = embed(
        df["comment"].tolist()
    )

    # Save locally
    df.to_parquet(CACHE_FILE)

    return df


# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------

st.title("Chat with your Zomato Reviews")

st.caption(
    f"Searching {NEW_REVIEWS} reviews, "
    f"answering with {CHAT_MODEL} model"
)


# --------------------------------------------------
# Cosine similarity
# --------------------------------------------------

def cosine_similarity(vec_a, vec_b):

    return np.dot(vec_a, vec_b) / (
        np.linalg.norm(vec_a) *
        np.linalg.norm(vec_b)
    )


# --------------------------------------------------
# Find similar reviews
# --------------------------------------------------

def find_similar_reviews(question, df):

    # Create embedding for user's question
    question_vector = embed([question])[0]

    scores = []

    # Compare question with every review
    for review_vector in df["embedding"]:

        scores.append(
            cosine_similarity(
                question_vector,
                review_vector
            )
        )

    df = df.copy()

    df["score"] = scores

    # Get top K most similar reviews
    return df.nlargest(
        TOK_K,
        "score"
    )


# --------------------------------------------------
# Ask Gemini
# --------------------------------------------------

def ask_llm(question, top_reviews):

    context = ""

    # Build review context
    for _, row in top_reviews.iterrows():

        context += (
            f"({row['city']}, "
            f"{row['rating']} stars) "
            f"{row['comment']}\n"
        )

    # System instruction
    system_prompt = (
        "Answer ONLY using the customer reviews provided. "
        "Be concise. "
        "If the reviews do not cover the question, "
        "say that the reviews do not provide enough information."
    )

    # User prompt
    user_prompt = (
        f"Question: {question}\n\n"
        f"Reviews:\n{context}"
    )

    # Gemini API call
    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2
        )
    )

    return response.text


# --------------------------------------------------
# Main application
# --------------------------------------------------

review_df = load_reviews()


question = st.text_input(
    "Ask a question about your reviews:",
    placeholder=(
        "e.g. What are the most common complaints "
        "about delivery?"
    )
)


if question:

    # Find relevant reviews
    top_reviews = find_similar_reviews(
        question,
        review_df
    )

    # Ask Gemini using those reviews
    answer = ask_llm(
        question,
        top_reviews
    )

    # Display answer
    st.markdown("**Answer:**")

    st.write(answer)

    # Display reviews used
    with st.expander(
        "Reviews used to build this answer"
    ):

        st.dataframe(
            top_reviews[
                ["city", "rating", "comment"]
            ],
            hide_index=True
        )