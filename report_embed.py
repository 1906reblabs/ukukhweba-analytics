# report_embed.py
import streamlit as st

def render_weekly_report():
    st.subheader("🧠 Simphiwe's Weekly JSE Intelligence")
    st.caption("Proprietary analysis — updated every Monday")
    
    # Option A: Paste your report content here directly
    # Option B: Pull from Substack RSS (free)
    import feedparser
    feed = feedparser.parse("https://YOUR_SUBSTACK.substack.com/feed")
    
    latest = feed.entries[0]
    st.markdown(f"### {latest.title}")
    st.markdown(f"*Published: {latest.published}*")
    
    # Strip HTML from summary
    from html.parser import HTMLParser
    class MLStripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.fed = []
        def handle_data(self, d): self.fed.append(d)
        def get_data(self): return ''.join(self.fed)
    
    s = MLStripper()
    s.feed(latest.summary)
    clean_text = s.get_data()
    
    st.write(clean_text[:800] + "...")
    st.link_button("Read Full Report →", latest.link)