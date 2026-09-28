import os
import json
import snowflake.connector
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Gemini model
MODEL = "gemini-3.5-flash-lite"

SAMPLE_N = 50

TOPICS = [
    "food quality",
    "delivery",
    "pricing",
    "service",
    "packaging",
    "other"
]

SYSTEM_PROMPT = f"""
You classify customer reviews for a food delivery app.

For the review you are given, return:

- sentiment_label: positive, negative, or neutral
- sentiment_score: a number between -1.0 and 1.0
- topic: one of {TOPICS}
- key_issue: a short phrase of 6 words or less describing the main issue.
  If there is no issue, return null.

Return ONLY JSON in this exact format:

{{
    "sentiment_label": "positive",
    "sentiment_score": 0.8,
    "topic": "packaging",
    "key_issue": null
}}
"""


# --------------------------------------------------
# Gemini client
# --------------------------------------------------

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# --------------------------------------------------
# Snowflake connection
# --------------------------------------------------

def get_connection():

    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


# --------------------------------------------------
# Create output table
# --------------------------------------------------

def create_output_table(cursor):

    cursor.execute("""
        CREATE SCHEMA IF NOT EXISTS ZOMATO.AI
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ZOMATO.AI.REVIEW_ENRICHED (
            REVIEW_ID STRING,
            SENTIMENT_LABEL STRING,
            SENTIMENT_SCORE FLOAT,
            TOPIC STRING,
            KEY_ISSUE STRING,
            MODEL STRING,
            ENRICHED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)


# --------------------------------------------------
# Get reviews that are not already enriched
# --------------------------------------------------

def get_reviews_to_enrich(cursor):

    cursor.execute(f"""
        SELECT REVIEW_ID, COMMENT
        FROM ZOMATO.RAW.REVIEWS
        WHERE REVIEW_ID NOT IN (
            SELECT REVIEW_ID
            FROM ZOMATO.AI.REVIEW_ENRICHED
        )
        LIMIT {SAMPLE_N}
    """)

    return cursor.fetchall()


# --------------------------------------------------
# Gemini classification
# --------------------------------------------------

def classify_review(comment):

    response = client.models.generate_content(
        model=MODEL,
        contents=comment,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            response_mime_type="application/json"
        )
    )

    answer = response.text

    return json.loads(answer)


# --------------------------------------------------
# Save results
# --------------------------------------------------

def save_results(cursor, results):

    if not results:
        print("No results to save.")
        return

    print(f"Saving {len(results)} enriched reviews to Snowflake...")

    cursor.executemany(
        """
        INSERT INTO ZOMATO.AI.REVIEW_ENRICHED
        (
            REVIEW_ID,
            SENTIMENT_LABEL,
            SENTIMENT_SCORE,
            TOPIC,
            KEY_ISSUE,
            MODEL
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        results
    )


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    print("Connecting to Snowflake...")

    conn = get_connection()
    cursor = conn.cursor()

    create_output_table(cursor)

    reviews = get_reviews_to_enrich(cursor)

    if len(reviews) == 0:

        print("No new reviews to enrich.")

        cursor.close()
        conn.close()

        return

    print(
        f"Enriching {len(reviews)} reviews "
        f"using Gemini {MODEL}..."
    )

    results = []

    for review_id, comment in reviews:

        print(
            f"\nClassifying review {review_id}: {comment}"
        )

        try:

            labels = classify_review(comment)

            print(f"Labels: {labels}")

            results.append(
                (
                    review_id,
                    labels["sentiment_label"],
                    labels["sentiment_score"],
                    labels["topic"],
                    labels["key_issue"],
                    MODEL
                )
            )

        except Exception as e:

            print(
                f"Error occurred while classifying "
                f"review {review_id}: {e}"
            )

    if results:

        save_results(cursor, results)

        conn.commit()

        print(
            f"\nSuccessfully saved "
            f"{len(results)} enriched reviews to Snowflake."
        )

    else:

        print("\nNo reviews were successfully enriched.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()

