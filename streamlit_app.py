import os
import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

# ─────────────────────────────────────────────
# BASIC CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="VoiceAgent – Voice to Insight", page_icon="🎤", layout="wide")

API_BASE_URL      = os.getenv("API_BASE_URL", "http://localhost:8000")
POLL_INTERVAL_SEC = 2
MAX_POLL_ATTEMPTS = 40

# ─────────────────────────────────────────────
# CSS  (Bigger + Green)
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
      .block-container{max-width:1500px;padding-top:1.2rem;}
      body, p, li, code{font-size:20px; line-height:1.58; color:#e9f1fb;}
      h1{font-size:44px;margin-bottom:.6rem;color:#d0e7f3;}
      h2{font-size:32px;margin:1.3rem 0 .8rem;color:#8eb8ef;}
      h3{font-size:26px;margin:1rem 0 .55rem;color:#8eb8ef;}

      :root{
        --fg:#e4e9f1;
        --fg-muted:#a5c6d6;
        --bg:#0f1a31;
        --bg-sec:#182c47;
        --border:#2a4b69;
        --accent:#22a5c5;
        --accent-dark:#064e6e;
        --radius:18px;
      }
      html, body{background:var(--bg);}
      section[data-testid="stSidebar"] {background:var(--bg-sec) !important;}

      .va-sec{ margin:0 0 2.2rem 0; padding:0; }
      .va-head{
        font-weight:700; font-size:30px; margin:0 0 .9rem 0;
        display:flex; gap:.55rem; align-items:center; color:#d0e7f7;
      }
      .va-head::after{
        content:""; flex:1; height:2px;
        background:linear-gradient(90deg,#22a5c5,#1675a3);
        margin-left:.8rem; opacity:.35;
      }
      .va-pre{
        white-space:pre-wrap;word-wrap:break-word;
        background:var(--bg-sec); border:1px solid var(--border);
        padding:1.25rem 1.45rem; border-radius:14px;
        max-height:420px; overflow:auto; font-size:18px; line-height:1.5;
      }

      .va-metrics{ display:flex; flex-wrap:wrap; gap:1.2rem; margin:.9rem 0 0; }
      .va-m{
        padding:.85rem 1.15rem .8rem; border:1px solid var(--border);
        border-radius:12px; background:var(--accent-dark);
        min-width:160px; text-align:center;
        box-shadow:0 0 0 1px #0d5c6e inset;
      }
      .va-m span{ display:block; font-size:15px; color:var(--fg-muted); margin-bottom:.3rem; }
      .va-m strong{ font-size:20px; color:#d1eafa; }

      .va-chip{
        display:inline-block; padding:.4rem 1rem; border-radius:999px;
        background:var(--accent-dark); border:1px solid var(--border);
        font-size:15px; color:#c7e6f9; margin-right:.5rem; margin-top:.2rem;
        box-shadow:0 0 0 1px #0d5c6e inset;
      }
      .va-chip.green{background:#047891;border-color:#065f78;color:#ecf7fd;}

      .va-foot{ font-size:15px;color:var(--fg-muted);margin-top:1rem; }

      .stDataFrame{background:var(--bg-sec) !important;border-radius:12px !important;}
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SMALL HELPERS
# ─────────────────────────────────────────────
def section(title: str, icon: str, body, *, pre=False, raw_html=False):
    st.markdown('<div class="va-sec">', unsafe_allow_html=True)
    st.markdown(f'<div class="va-head">{icon} {title}</div>', unsafe_allow_html=True)
    if raw_html:
        st.markdown(body, unsafe_allow_html=True)
    elif pre:
        st.markdown(f'<div class="va-pre">{body}</div>', unsafe_allow_html=True)
    else:
        st.write(body if body else "—")
    st.markdown('</div>', unsafe_allow_html=True)

def analysis_html(i: dict) -> str:
    topic = i.get("topic","N/A")
    sent  = i.get("sentiment","N/A")
    lang  = i.get("language","N/A")
    conf  = i.get("confidence_score")
    conf_display = f"{conf*100:.1f}%" if conf is not None else "N/A"
    return f"""
    <div class="va-metrics">
      <div class="va-m"><span>Topic</span><strong>{topic}</strong></div>
      <div class="va-m"><span>Sentiment</span><strong>{sent}</strong></div>
      <div class="va-m"><span>Language</span><strong>{lang}</strong></div>
      <div class="va-m"><span>Confidence</span><strong>{conf_display}</strong></div>
    </div>
    """

def action_items_html(items: list) -> str:
    if not items:
        return "<em>No action items.</em>"
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"

def naive_summarize(text: str, max_sentences: int = 2) -> str:
    if not text:
        return ""
    # basic sentence split
    s = [t.strip() for t in re.split(r'(?<=[.!?])\s+', text.replace("\\n", " ")) if t.strip()]
    summ = " ".join(s[:max_sentences])
    return summ if summ.endswith((".", "!", "?")) else (summ + "." if summ else "")

def ensure_summary_field(insight: Dict[str, Any]) -> Dict[str, Any]:
    if insight.get("summary") in (None, "", "null"):
        insight["summary"] = naive_summarize(insight.get("transcription", ""))
    return insight

def to_dt_str(ts: Optional[str]) -> str:
    if not ts:
        return "N/A"
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts

def push_to_session(insight: Dict[str, Any]):
    st.session_state.current_insight = insight

# ─────────────────────────────────────────────
# API HELPERS (with explicit error printing)
# ─────────────────────────────────────────────
def _print_http_error(resp: requests.Response, url: str, method: str):
    """Pretty-print HTTP error payloads."""
    body = resp.text
    try:
        j = resp.json()
        body = j.get("error") or j.get("detail") or json.dumps(j, indent=2, ensure_ascii=False)
    except Exception:
        pass
    st.error(f"HTTP {resp.status_code} {method} {url}\n\n{body}")

def api_get(path: str, **kwargs) -> Optional[requests.Response]:
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.get(url, timeout=30, **kwargs)
    except Exception as e:
        st.error(f"API GET error ({url}): {e}")
        return None

    if resp.status_code >= 400:
        _print_http_error(resp, url, "GET")
    return resp

def api_post(path: str, **kwargs) -> Optional[requests.Response]:
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.post(url, timeout=90, **kwargs)
    except Exception as e:
        st.error(f"API POST error ({url}): {e}")
        return None

    if resp.status_code >= 400:
        _print_http_error(resp, url, "POST")
    return resp

def poll_insight(insight_id: int) -> Optional[Dict[str, Any]]:
    progress = st.progress(0, text="Processing...")
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        resp = api_get(f"/insights/{insight_id}")
        if resp:
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("processing_status")
                if status == "completed":
                    progress.progress(100, text="✅ Completed")
                    return data
                if status == "failed":
                    progress.progress(100, text="❌ Failed")
                    backend_err = (
                        data.get("error")
                        or data.get("nlp_error")
                        or data.get("transcription_error")
                        or data.get("transcription")  # last fallback
                        or "Unknown error"
                    )
                    st.error(f"Processing failed: {backend_err}")
                    return None
            elif resp.status_code >= 400:
                # Error already printed by helper
                progress.progress(100, text="❌ Failed")
                return None

        # not done yet
        pct = int(attempt / MAX_POLL_ATTEMPTS * 100)
        progress.progress(pct, text=f"Processing... {attempt}/{MAX_POLL_ATTEMPTS}")
        time.sleep(POLL_INTERVAL_SEC)

    st.warning("⏱️ Still processing. Check back later.")
    return None

@st.cache_data(show_spinner=False)
def load_recent_insights() -> List[Dict[str, Any]]:
    r = api_get("/insights")
    return r.json() if r and r.status_code == 200 else []

def insights_to_df(insights: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for i in insights:
        rows.append({
            "id": i.get("id"),
            "filename": i.get("filename"),
            "topic": i.get("topic"),
            "sentiment": i.get("sentiment"),
            "language": i.get("language"),
            "confidence": i.get("confidence_score"),
            "status": i.get("processing_status"),
            "created_at": to_dt_str(i.get("created_at")),
            "updated_at": to_dt_str(i.get("updated_at")),
            "summary": i.get("summary"),
            "transcription": (i.get("transcription") or "")[:200] + ("..." if i.get("transcription") and len(i["transcription"]) > 200 else "")
        })
    return pd.DataFrame(rows).sort_values("created_at", ascending=False)

# ─────────────────────────────────────────────
# UI PIECES
# ─────────────────────────────────────────────
def render_sidebar():
    st.sidebar.header("Status")
    h = api_get("/health")
    if h and h.status_code == 200:
        st.sidebar.success("API Online")
    else:
        st.sidebar.error("API Offline")
    st.sidebar.caption(f"API: {API_BASE_URL}")

def render_upload_section():
    st.header("Upload Audio")
    files = st.file_uploader(
        "Select audio file(s)",
        type=["wav", "mp3", "m4a"],
        accept_multiple_files=True,
        help="WAV / MP3 / M4A up to ~50MB each"
    )
    if files and st.button("Process", type="primary"):
        for f in files:
            with st.spinner(f"Uploading {f.name}..."):
                r = api_post("/upload_audio", files={"file": (f.name, f.getvalue(), f.type)})
            if not r:
                continue
            if r.status_code == 200:
                insight_id = r.json()["insight_id"]
                st.success(f"{f.name} uploaded. Processing…")
                data = poll_insight(insight_id)
                if data:
                    push_to_session(ensure_summary_field(data))
                    st.toast(f"Done: {f.name}", icon="✅")
                    # invalidate cache so recent list updates
                    load_recent_insights.clear()
            else:
                st.error(f"Upload failed for {f.name}. See error above.")

def render_insight_view(i: Dict[str, Any]):
    i = ensure_summary_field(i)

    st.subheader("Results")
    st.markdown(
        f'<span class="va-chip">Result</span>'
        f'<span class="va-chip green">{i.get("filename","N/A")}</span>'
        f'<span class="va-chip">{i.get("processing_status","N/A")}</span>',
        unsafe_allow_html=True
    )

    section("Summary", "🧾", i["summary"])
    section("Transcription", "📝", i.get("transcription", ""), pre=True)
    section("Analysis", "📊", analysis_html(i), raw_html=True)
    section("Action Items", "✅", action_items_html(i.get("action_items") or []), raw_html=True)

    st.markdown(
        f'<div class="va-foot">Created: {to_dt_str(i.get("created_at"))} | '
        f'Updated: {to_dt_str(i.get("updated_at"))} | Status: {i.get("processing_status","N/A")}</div>',
        unsafe_allow_html=True
    )

    with st.expander("Raw JSON"):
        js = json.dumps(i, indent=2)
        st.code(js, language="json")
        st.download_button(
            "Download JSON",
            data=js,
            file_name=f"insight_{i['id']}.json",
            mime="application/json",
            key=f"dl_json_{i['id']}"
        )

def render_recent_section():
    st.header("Recent Insights")
    data = load_recent_insights()
    if not data:
        st.info("No insights yet. Upload your first audio file!")
        return

    df = insights_to_df(data)
    query = st.text_input("Search (filename/topic/sentiment/language/summary)")
    if query:
        q = query.lower()
        df_view = df[df.apply(lambda r: q in r.to_string().lower(), axis=1)]
    else:
        df_view = df

    st.dataframe(df_view, use_container_width=True, hide_index=True)

    st.markdown("##### Open any insight")
    for _, row in df_view.head(10).iterrows():
        with st.expander(f"🎵 {row['filename']} — {row['status']} (ID {row['id']})"):
            st.write(f"**Topic:** {row['topic']}")
            st.write(f"**Sentiment:** {row['sentiment']}")
            st.write(f"**Language:** {row['language']}")
            st.write(f"**Confidence:** {row['confidence']*100:.1f}%" if row['confidence'] is not None else "N/A")
            st.write(f"**Created:** {row['created_at']}")
            st.write(f"**Updated:** {row['updated_at']}")
            st.write(f"**Summary:** {row['summary'] or '—'}")
            st.write(f"**Transcription Preview:** {row['transcription']}")
            if st.button("Load in main view", key=f"load_{row['id']}"):
                r = api_get(f"/insights/{row['id']}")
                if r and r.status_code == 200:
                    push_to_session(ensure_summary_field(r.json()))
                    st.experimental_rerun()

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    inject_css()
    if "current_insight" not in st.session_state:
        st.session_state.current_insight = None

    render_sidebar()

    st.title("🎤 VoiceAgent – Voice to Insight")
    st.caption("Upload audio → get transcription, summary, sentiment & action items.")

    render_upload_section()

    st.markdown("---")
    st.header("Output")
    if st.session_state.current_insight:
        render_insight_view(st.session_state.current_insight)
    else:
        st.info("👆 Upload an audio file to see results here.")

    st.markdown("---")
    render_recent_section()

if __name__ == "__main__":
    main()
