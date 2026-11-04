"""Analyze the real Retailrocket clickstream using DuckDB SQL."""
from pathlib import Path
import json
import duckdb

DATA_FILE = Path("data/events.csv")
OUT_DIR = Path("outputs")
SESSION_GAP_MS = 30 * 60 * 1000  # 30 minutes

def main():
    if not DATA_FILE.exists():
        raise SystemExit("data/events.csv is missing. First run: python download_dataset.py")

    OUT_DIR.mkdir(exist_ok=True)
    db = duckdb.connect(database=":memory:")
    print("Loading Retailrocket events.csv...")
    # DuckDB scans the CSV efficiently without loading the entire dataset into Pandas.
    db.from_csv_auto(str(DATA_FILE), header=True).create_view("raw_events")

    columns = {row[0] for row in db.execute("DESCRIBE raw_events").fetchall()}
    required = {"timestamp", "visitorid", "event", "itemid", "transactionid"}
    if not required.issubset(columns):
        raise SystemExit(f"Unexpected CSV schema. Required columns: {sorted(required)}; found: {sorted(columns)}")

    print("Cleaning records and assigning 30-minute sessions...")
    db.execute("""
        CREATE TABLE clean_events AS
        SELECT
            row_number() OVER () AS event_id,
            TRY_CAST(timestamp AS BIGINT) AS event_ts,
            TRY_CAST(visitorid AS BIGINT) AS visitor_id,
            LOWER(TRIM(CAST(event AS VARCHAR))) AS event_type,
            TRY_CAST(itemid AS BIGINT) AS item_id,
            TRY_CAST(transactionid AS BIGINT) AS transaction_id
        FROM raw_events
        WHERE TRY_CAST(timestamp AS BIGINT) IS NOT NULL
          AND TRY_CAST(visitorid AS BIGINT) IS NOT NULL
          AND TRY_CAST(itemid AS BIGINT) IS NOT NULL
          AND LOWER(TRIM(CAST(event AS VARCHAR))) IN ('view', 'addtocart', 'transaction')
    """)

    db.execute("""
        CREATE TABLE ordered_events AS
        SELECT *,
            LAG(event_ts) OVER (
                PARTITION BY visitor_id ORDER BY event_ts, event_id
            ) AS previous_ts
        FROM clean_events
    """)

    db.execute(f"""
        CREATE TABLE sessionized_events AS
        SELECT *,
            SUM(
                CASE
                    WHEN previous_ts IS NULL OR event_ts - previous_ts > {SESSION_GAP_MS}
                    THEN 1 ELSE 0
                END
            ) OVER (
                PARTITION BY visitor_id
                ORDER BY event_ts, event_id
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS session_number
        FROM ordered_events
    """)

    db.execute("""
        CREATE TABLE events_with_session AS
        SELECT *,
            CAST(visitor_id AS VARCHAR) || '_' || CAST(session_number AS VARCHAR) AS session_id,
            TO_TIMESTAMP(event_ts / 1000.0) AS event_time
        FROM sessionized_events
    """)

    print("Calculating session, funnel, product and navigation metrics...")
    db.execute("""
        CREATE TABLE session_stats AS
        SELECT
            session_id,
            visitor_id,
            COUNT(*) AS event_count,
            MIN(event_ts) AS start_ts,
            MAX(event_ts) AS end_ts,
            COUNT_IF(event_type = 'view') AS views,
            COUNT_IF(event_type = 'addtocart') AS add_to_carts,
            COUNT_IF(event_type = 'transaction') AS transactions
        FROM events_with_session
        GROUP BY session_id, visitor_id
    """)

    db.execute("""
        CREATE TABLE last_events AS
        SELECT session_id, item_id AS exit_item_id, event_type AS exit_event_type
        FROM (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY session_id ORDER BY event_ts DESC, event_id DESC
                ) AS rn
            FROM events_with_session
        )
        WHERE rn = 1
    """)

    total_events, unique_visitors, total_sessions = db.execute("""
        SELECT COUNT(*), COUNT(DISTINCT visitor_id),
               (SELECT COUNT(*) FROM session_stats)
        FROM events_with_session
    """).fetchone()

    bounce_sessions = db.execute(
        "SELECT COUNT(*) FROM session_stats WHERE event_count = 1"
    ).fetchone()[0]
    bounce_rate = (bounce_sessions / total_sessions * 100) if total_sessions else 0.0

    funnel = db.execute("""
        SELECT 'Sessions' AS stage, COUNT(*) AS session_count FROM session_stats
        UNION ALL
        SELECT 'Sessions with a product view', COUNT(DISTINCT session_id)
        FROM events_with_session WHERE event_type = 'view'
        UNION ALL
        SELECT 'Sessions with add to cart', COUNT(DISTINCT session_id)
        FROM events_with_session WHERE event_type = 'addtocart'
        UNION ALL
        SELECT 'Sessions with transaction', COUNT(DISTINCT session_id)
        FROM events_with_session WHERE event_type = 'transaction'
    """).df()
    funnel["share_of_all_sessions_pct"] = (
        funnel["session_count"] / total_sessions * 100
    ).round(2) if total_sessions else 0

    cart_sessions = db.execute(
        "SELECT COUNT(*) FROM session_stats WHERE add_to_carts > 0"
    ).fetchone()[0]
    purchasing_cart_sessions = db.execute("""
        SELECT COUNT(*) FROM session_stats
        WHERE add_to_carts > 0 AND transactions > 0
    """).fetchone()[0]
    cart_abandonment_rate = (
        (cart_sessions - purchasing_cart_sessions) / cart_sessions * 100
    ) if cart_sessions else 0.0

    summary = {
        "dataset": "Retailrocket real-world anonymized e-commerce events",
        "session_gap_minutes": 30,
        "total_events": int(total_events),
        "unique_visitors": int(unique_visitors),
        "sessions": int(total_sessions),
        "single_event_sessions": int(bounce_sessions),
        "single_event_session_rate_pct": round(float(bounce_rate), 2),
        "sessions_with_add_to_cart": int(cart_sessions),
        "sessions_with_cart_and_transaction": int(purchasing_cart_sessions),
        "cart_session_abandonment_rate_pct": round(float(cart_abandonment_rate), 2),
    }

    queries = {
        "event_types": """
            SELECT event_type, COUNT(*) AS events
            FROM events_with_session GROUP BY event_type ORDER BY events DESC
        """,
        "top_viewed_products": """
            SELECT item_id, COUNT(*) AS views,
                   COUNT(DISTINCT visitor_id) AS unique_visitors
            FROM events_with_session WHERE event_type = 'view'
            GROUP BY item_id ORDER BY views DESC LIMIT 20
        """,
        "top_carted_products": """
            SELECT item_id, COUNT(*) AS add_to_cart_events,
                   COUNT(DISTINCT visitor_id) AS unique_visitors
            FROM events_with_session WHERE event_type = 'addtocart'
            GROUP BY item_id ORDER BY add_to_cart_events DESC LIMIT 20
        """,
        "top_purchased_products": """
            SELECT item_id, COUNT(*) AS transaction_events,
                   COUNT(DISTINCT visitor_id) AS unique_visitors
            FROM events_with_session WHERE event_type = 'transaction'
            GROUP BY item_id ORDER BY transaction_events DESC LIMIT 20
        """,
        "exit_products": """
            SELECT l.exit_item_id AS item_id, COUNT(*) AS sessions_ending_on_item
            FROM last_events l GROUP BY l.exit_item_id
            ORDER BY sessions_ending_on_item DESC LIMIT 20
        """,
        "navigation_transitions": """
            WITH sequenced AS (
                SELECT session_id, item_id,
                    LEAD(item_id) OVER (
                        PARTITION BY session_id ORDER BY event_ts, event_id
                    ) AS next_item_id
                FROM events_with_session
                WHERE event_type = 'view'
            )
            SELECT item_id AS from_item_id, next_item_id AS to_item_id,
                   COUNT(*) AS transitions
            FROM sequenced
            WHERE next_item_id IS NOT NULL AND item_id <> next_item_id
            GROUP BY item_id, next_item_id
            ORDER BY transitions DESC LIMIT 30
        """,
        "hourly_activity": """
            SELECT EXTRACT(HOUR FROM event_time)::INTEGER AS hour,
                   COUNT(*) AS events
            FROM events_with_session
            GROUP BY hour ORDER BY hour
        """,
        "daily_activity": """
            SELECT CAST(event_time AS DATE) AS date,
                   COUNT(*) AS events,
                   COUNT(DISTINCT visitor_id) AS visitors
            FROM events_with_session
            GROUP BY date ORDER BY date
        """,
    }

    for name, query in queries.items():
        db.execute(query).df().to_csv(OUT_DIR / f"{name}.csv", index=False)

    funnel.to_csv(OUT_DIR / "conversion_funnel.csv", index=False)
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nANALYSIS COMPLETE")
    print(json.dumps(summary, indent=2))
    print(f"\nReports saved in: {OUT_DIR.resolve()}")
    db.close()

if __name__ == "__main__":
    main()
