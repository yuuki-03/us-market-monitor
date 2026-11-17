import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="米ハイテク・半導体 急変動モニター",
    page_icon="📊",
    layout="wide",
)

st.title("📊 ナスダック・SOX 急変動＆日経平均統計モニター")
st.caption(
    "開いた瞬間に最新データを自動取得し、翌日の日経平均の傾向を算出します"
)


@st.cache_data(ttl=3600)
def load_market_data():
  tickers = {"Nasdaq": "^IXIC", "SOX": "^SOX", "Nikkei": "^N225"}
  df_list = {}
  for name, ticker in tickers.items():
    data = yf.download(ticker, start="2010-01-01", progress=False)
    if isinstance(data.columns, pd.MultiIndex):
      close = data["Close"][ticker]
    else:
      close = data["Close"]
    df_list[name] = close.pct_change() * 100

  df = pd.DataFrame(df_list).dropna()
  df["Nikkei_Next"] = df["Nikkei"].shift(-1)
  return df


@st.cache_data(ttl=3600)
def fetch_news(query):
  url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=ja&gl=JP&ceid=JP:ja"
  try:
    res = requests.get(url, timeout=5)
    root = ET.fromstring(res.content)
    items = []
    for item in root.findall(".//item")[:4]:
      title = item.find("title").text
      link = item.find("link").text
      items.append((title, link))
    return items
  except Exception:
    return []


with st.spinner("最新マーケットデータと過去統計を計算中..."):
  df = load_market_data()

latest_date = df.index[-1].strftime("%Y-%m-%d")
nasdaq_chg = df["Nasdaq"].iloc[-1]
sox_chg = df["SOX"].iloc[-1]

st.subheader(f"🗓️ 直近の米国市場結果（{latest_date} 終値ベース）")

col1, col2 = st.columns(2)


def render_alert_card(col, name, chg):
  with col:
    if chg <= -3.0:
      st.markdown(
          f"""
                <div style="background-color:#fff3e0; border-left:8px solid #ff9800; padding:16px; border-radius:8px; color:#333;">
                    <h3 style="margin:0; color:#e65100;">🟠 【急落・警戒】{name}: {chg:+.2f}%</h3>
                    <p style="margin:8px 0 0 0;">-3.0%以上の大幅下落を検知しました。自律反発か続落か要注意です。</p>
                </div>
                """,
          unsafe_allow_html=True,
      )
    elif chg >= 5.0:
      st.markdown(
          f"""
                <div style="background-color:#ffebee; border-left:8px solid #f44336; padding:16px; border-radius:8px; color:#333;">
                    <h3 style="margin:0; color:#c62828;">🔴 【急騰・注目】{name}: {chg:+.2f}%</h3>
                    <p style="margin:8px 0 0 0;">+5.0%以上の記録的急騰を検知しました。東京市場のハイテク株にも強い追い風です。</p>
                </div>
                """,
          unsafe_allow_html=True,
      )
    else:
      st.markdown(
          f"""
                <div style="background-color:#f5f5f5; border-left:8px solid #9e9e9e; padding:16px; border-radius:8px; color:#333;">
                    <h3 style="margin:0; color:#424242;">⚪ 【通常範囲】{name}: {chg:+.2f}%</h3>
                    <p style="margin:8px 0 0 0;">急変動基準（-3%以下 / +5%以上）の範囲内です。</p>
                </div>
                """,
          unsafe_allow_html=True,
      )


render_alert_card(col1, "ナスダック総合", nasdaq_chg)
render_alert_card(col2, "SOX（半導体指数）", sox_chg)

st.divider()

st.subheader("📈 過去統計：米国ハイテク急変動の『翌日』の日経平均（2010年〜）")

hist_df = df.dropna(subset=["Nikkei_Next"])

stats = []
for idx_name, col_key in [("ナスダック総合", "Nasdaq"), ("SOX指数", "SOX")]:
  fall_df = hist_df[hist_df[col_key] <= -3.0]
  rise_df = hist_df[hist_df[col_key] >= 5.0]
  stats.append({
      "対象指数": idx_name,
      "🟠 急落(-3%以下)回数": f"{len(fall_df)}回",
      "🟠 急落翌日の日経勝率": (
          f"{(fall_df['Nikkei_Next'] > 0).mean()*100:.1f}%"
          if len(fall_df)
          else "-"
      ),
      "🟠 急落翌日の平均騰落": (
          f"{fall_df['Nikkei_Next'].mean():+.2f}%" if len(fall_df) else "-"
      ),
      "🔴 急騰(+5%以上)回数": f"{len(rise_df)}回",
      "🔴 急騰翌日の日経勝率": (
          f"{(rise_df['Nikkei_Next'] > 0).mean()*100:.1f}%"
          if len(rise_df)
          else "-"
      ),
      "🔴 急騰翌日の平均騰落": (
          f"{rise_df['Nikkei_Next'].mean():+.2f}%" if len(rise_df) else "-"
      ),
  })

st.table(pd.DataFrame(stats))

tab1, tab2 = st.tabs(["ナスダック 急変動履歴", "SOX指数 急変動履歴"])
with tab1:
  n_events = hist_df[
      (hist_df["Nasdaq"] <= -3.0) | (hist_df["Nasdaq"] >= 5.0)
  ].sort_index(ascending=False)
  st.dataframe(
      n_events[["Nasdaq", "Nikkei_Next"]].rename(
          columns={
              "Nasdaq": "ナスダック騰落(%)",
              "Nikkei_Next": "翌日日経平均(%)",
          }
      ),
      use_container_width=True,
  )

with tab2:
  s_events = hist_df[
      (hist_df["SOX"] <= -3.0) | (hist_df["SOX"] >= 5.0)
  ].sort_index(ascending=False)
  st.dataframe(
      s_events[["SOX", "Nikkei_Next"]].rename(
          columns={"SOX": "SOX騰落(%)", "Nikkei_Next": "翌日日経平均(%)"}
      ),
      use_container_width=True,
  )

st.divider()

st.subheader("📰 米国株・半導体セクター 最新ニュース要因")
news_items = fetch_news("米国株 ナスダック 半導体 株価")
if news_items:
  for title, link in news_items:
    st.markdown(f"- [{title}]({link})")
else:
  st.write("現在ニュースを取得できませんでした。")
