"""Streamlit dashboard for Retailrocket's real e-commerce event data."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="ShopTrace | Real Clickstream Analytics",
                   page_icon="🛒", layout="wide")

OUT = Path("outputs")
required = ["summary.json", "event_types.csv", "top_viewed_products.csv",
            "top_carted_products.csv", "top_purchased_products.csv",
            "exit_products.csv", "navigation_transitions.csv",
            "hourly_activity.csv", "daily_activity.csv", "conversion_funnel.csv"]

st.title("🛒 ShopTrace — Real E-Commerce Clickstream Analytics")
st.caption("Retailrocket dataset | Big Data Computing case study")

missing = [name for name in required if not (OUT / name).exists()]
if missing:
    st.warning("Analytics outputs are missing. Run `python run_analysis.py` first.")
    st.code("python download_dataset.py\npython run_analysis.py\nstreamlit run app.py")
    st.stop()

summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
def load_csv(name):
    return pd.read_csv(OUT / name)

with st.sidebar:
    st.header("Dataset information")
    st.write("Source: Retailrocket / Kaggle")
    st.write("Session rule: 30 minutes of inactivity")
    st.info("The dataset contains anonymized product interactions, not page URLs or device types.")

a, b, c, d = st.columns(4)
a.metric("Recorded events", f"{summary['total_events']:,}")
b.metric("Unique visitors", f"{summary['unique_visitors']:,}")
c.metric("Derived sessions", f"{summary['sessions']:,}")
d.metric("Single-event session rate", f"{summary['single_event_session_rate_pct']:.2f}%")

e, f = st.columns(2)
e.metric("Sessions with add-to-cart", f"{summary['sessions_with_add_to_cart']:,}")
f.metric("Cart-session abandonment rate", f"{summary['cart_session_abandonment_rate_pct']:.2f}%")

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Event type distribution")
    events = load_csv("event_types.csv")
    fig = px.pie(events, names="event_type", values="events", hole=0.45)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Conversion funnel")
    funnel = load_csv("conversion_funnel.csv")
    fig = px.bar(funnel, x="stage", y="session_count",
                 labels={"stage": "Funnel stage", "session_count": "Sessions"})
    fig.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Most viewed products")
views = load_csv("top_viewed_products.csv")
fig = px.bar(views.sort_values("views"), x="views", y="item_id",
             orientation="h", labels={"item_id": "Product ID", "views": "View events"})
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Most added-to-cart products")
    carts = load_csv("top_carted_products.csv")
    fig = px.bar(carts.sort_values("add_to_cart_events"),
                 x="add_to_cart_events", y="item_id", orientation="h")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Most purchased products")
    purchases = load_csv("top_purchased_products.csv")
    fig = px.bar(purchases.sort_values("transaction_events"),
                 x="transaction_events", y="item_id", orientation="h")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Most common product-to-product navigation")
nav = load_csv("navigation_transitions.csv")
nav["journey"] = nav["from_item_id"].astype(str) + " → " + nav["to_item_id"].astype(str)
fig = px.bar(nav.head(15).sort_values("transitions"),
             x="transitions", y="journey", orientation="h",
             labels={"transitions": "Observed transitions", "journey": "Product journey"})
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Products where sessions ended")
    exits = load_csv("exit_products.csv")
    fig = px.bar(exits.sort_values("sessions_ending_on_item"),
                 x="sessions_ending_on_item", y="item_id", orientation="h")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Activity by hour (UTC)")
    hourly = load_csv("hourly_activity.csv")
    fig = px.line(hourly, x="hour", y="events", markers=True)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Daily activity")
daily = load_csv("daily_activity.csv")
daily["date"] = pd.to_datetime(daily["date"])
fig = px.line(daily, x="date", y="events", labels={"events": "Events", "date": "Date"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Download reports")
for filename, label in [
    ("conversion_funnel.csv", "Conversion funnel"),
    ("top_viewed_products.csv", "Top viewed products"),
    ("top_carted_products.csv", "Top carted products"),
    ("top_purchased_products.csv", "Top purchased products"),
    ("exit_products.csv", "Exit products"),
    ("navigation_transitions.csv", "Navigation transitions"),
]:
    st.download_button(
        f"Download {label}",
        data=(OUT / filename).read_bytes(),
        file_name=filename,
        mime="text/csv",
        key=filename,
    )

st.caption("Research/educational use. Metrics are derived from anonymized event logs and an explicitly defined 30-minute sessionization rule.")
