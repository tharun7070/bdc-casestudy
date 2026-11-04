"""
Optional Spark extension for the same real Retailrocket events.csv.
Install Java compatible with your PySpark version and:
    pip install pyspark
    python spark_analysis.py
This is Spark local mode, not a multi-node cluster.
"""
from pathlib import Path
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

spark = (SparkSession.builder.appName("ShopTraceRetailrocket")
         .master("local[*]").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

raw = (spark.read.option("header", True).option("inferSchema", True)
       .csv("data/events.csv"))
events = (raw.select(
    F.col("timestamp").cast("long").alias("event_ts"),
    F.col("visitorid").cast("long").alias("visitor_id"),
    F.lower(F.trim(F.col("event"))).alias("event_type"),
    F.col("itemid").cast("long").alias("item_id")
).dropna().filter(F.col("event_type").isin("view", "addtocart", "transaction")))

w = Window.partitionBy("visitor_id").orderBy("event_ts")
events = events.withColumn("previous_ts", F.lag("event_ts").over(w))
w_running = w.rowsBetween(Window.unboundedPreceding, Window.currentRow)
events = events.withColumn(
    "session_number",
    F.sum(F.when(
        F.col("previous_ts").isNull() |
        ((F.col("event_ts") - F.col("previous_ts")) > 30 * 60 * 1000), 1
    ).otherwise(0)).over(w_running)
).withColumn(
    "session_id",
    F.concat_ws("_", F.col("visitor_id").cast("string"),
                F.col("session_number").cast("string"))
)

sessions = events.groupBy("session_id").agg(
    F.count("*").alias("event_count"),
    F.count(F.when(F.col("event_type") == "view", True)).alias("views"),
    F.count(F.when(F.col("event_type") == "addtocart", True)).alias("carts"),
    F.count(F.when(F.col("event_type") == "transaction", True)).alias("transactions")
)

print("Events:", events.count())
print("Visitors:", events.select("visitor_id").distinct().count())
print("Sessions:", sessions.count())
print("Single-event sessions:", sessions.filter("event_count = 1").count())

print("Top viewed products:")
events.filter("event_type = 'view'").groupBy("item_id").count().orderBy(F.desc("count")).show(10)

print("Session funnel:")
sessions.agg(
    F.count("*").alias("sessions"),
    F.sum(F.when(F.col("views") > 0, 1).otherwise(0)).alias("sessions_with_views"),
    F.sum(F.when(F.col("carts") > 0, 1).otherwise(0)).alias("sessions_with_cart"),
    F.sum(F.when(F.col("transactions") > 0, 1).otherwise(0)).alias("sessions_with_transaction")
).show()

Path("outputs").mkdir(exist_ok=True)
spark.stop()
