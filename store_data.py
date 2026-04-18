# store_data.py — persist daily snapshots
from supabase import create_client
import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def store_snapshot(df):
    records = df.to_dict(orient="records")
    supabase.table("jse_daily_snapshots").insert(records).execute()
    print(f"Stored {len(records)} records")

# Run via cron (GitHub Actions free tier = 2000 min/month)
# .github/workflows/daily_fetch.yml → runs at 6PM SAST every weekday