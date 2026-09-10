import hashlib
import hmac
import html
import os
from datetime import datetime

import streamlit as st

from app_core import (
    BEIJING_TZ,
    load_history,
    load_settings,
    next_scheduled_run,
    run_accounts,
    save_settings,
    settings_health,
    split_values,
)


st.set_page_config(page_title="mimotion 控制台", page_icon=None, layout="wide")

THEME = """
<style>
:root {
  --ink: #f4f6ef;
  --muted: #9aa69c;
  --panel: rgba(25, 31, 27, .86);
  --line: rgba(228, 241, 226, .12);
  --acid: #d8ff57;
  --blue: #68b5ff;
  --mint: #62d995;
  --red: #ff7368;
  --focus: #b9efff;
  --acid-ink: #10140d;
}
.stApp {
  background:
    radial-gradient(circle at 82% 2%, rgba(104,181,255,.10), transparent 28rem),
    linear-gradient(145deg, #0b0e0c 0%, #121713 46%, #0b0d0c 100%);
  color: var(--ink);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #0d110e; border-right: 1px solid var(--line); }
.block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 5rem; }
h1, h2, h3 { font-family: "Arial Narrow", "Roboto Condensed", "Inter Tight", "Segoe UI", sans-serif; letter-spacing: -.035em; }
p, label, .stMarkdown, [data-testid="stWidgetLabel"] { font-family: "Segoe UI", sans-serif; }
.masthead { display:flex; align-items:flex-end; justify-content:space-between; gap:2rem; margin-bottom:1.15rem; }
.eyebrow { color:var(--acid); font: 700 .76rem/1.2 Consolas, monospace; letter-spacing:.18em; text-transform:uppercase; }
.title { font: 750 clamp(2.8rem,11vw,6.2rem)/.9 "Arial Narrow", "Roboto Condensed", "Inter Tight", "Segoe UI", sans-serif; letter-spacing:-.075em; margin:.35rem 0 0; }
.clock { color:var(--muted); font: 500 .78rem/1.6 Consolas, monospace; text-align:right; }
.pace-rail { height:12px; display:grid; grid-template-columns:1.4fr .65fr 1fr .35fr; gap:4px; margin:1.2rem 0 2rem; }
.pace-rail span { display:block; background:#283029; }
.pace-rail span:nth-child(1) { background:var(--acid); }
.pace-rail span:nth-child(2) { background:var(--blue); }
.pace-rail span:nth-child(3) { background:#344038; }
.pace-rail span:nth-child(4) { background:var(--mint); }
.rail-legend { display:flex; gap:1.2rem; margin:-1.4rem 0 1.8rem; color:var(--muted); font:600 .68rem/1.2 Consolas,monospace; letter-spacing:.08em; }
.rail-legend b { color:var(--ink); font-weight:600; }
.metric-card { min-height:126px; background:var(--panel); border:1px solid var(--line); border-top:2px solid rgba(216,255,87,.35); padding:1.15rem 1.2rem; }
.metric-label { color:var(--muted); font:600 .75rem/1.4 Consolas,monospace; letter-spacing:.08em; text-transform:uppercase; }
.metric-value { margin-top:1.25rem; font:700 clamp(1.45rem,3vw,2.7rem)/1 "Arial Narrow","Segoe UI",sans-serif; letter-spacing:-.045em; }
.metric-detail { margin-top:.65rem; color:var(--muted); font-size:.875rem; }
.section-copy { max-width:54rem; color:var(--muted); margin-bottom:1.2rem; }
.account-chip { display:inline-block; max-width:100%; overflow-wrap:anywhere; margin:.2rem .35rem .2rem 0; padding:.42rem .65rem; border:1px solid var(--line); background:#141a16; color:#d8dfd8; font:600 .74rem/1 Consolas,monospace; }
.command-deck { min-height:120px; display:flex; flex-direction:column; justify-content:center; padding:1rem 0; }
.command-title { font:700 clamp(1.45rem,3vw,2.3rem)/1.05 "Arial Narrow","Segoe UI",sans-serif; letter-spacing:-.035em; }
.command-meta { margin-top:.65rem; color:var(--muted); font-size:.9rem; }
.result-line { padding:.75rem 0; border-bottom:1px solid var(--line); }
.status-good { color:var(--mint); }
.status-bad { color:var(--red); }
.locked { max-width:620px; margin:12vh auto; border:1px solid var(--line); background:var(--panel); padding:2rem; }
.locked h1 { margin-top:0; }
div[data-testid="stForm"], div[data-testid="stExpander"] { border-color:var(--line); background:rgba(20,25,22,.68); }
.stButton > button, .stFormSubmitButton > button { border-radius:0; min-height:2.8rem; font-weight:700; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background:var(--acid); color:var(--acid-ink); border-color:var(--acid); }
.stTabs [data-baseweb="tab-list"] { gap:1.5rem; border-bottom:1px solid var(--line); }
.stTabs [data-baseweb="tab"] { background:transparent; padding:.9rem 0; }
.stTabs [aria-selected="true"] { color:var(--acid); box-shadow:inset 0 -3px 0 var(--acid); }
input, textarea { border-radius:0 !important; }
:where(button, input, textarea, [role="tab"], [role="checkbox"], [role="switch"], [role="option"]):focus-visible {
  outline:3px solid var(--focus) !important;
  outline-offset:3px !important;
  box-shadow:0 0 0 5px rgba(185,239,255,.16) !important;
}
@media (max-width: 760px) {
  .block-container { padding:1.1rem .9rem 3rem; }
  .masthead { align-items:flex-start; flex-direction:column; }
  .clock { text-align:left; }
  .pace-rail { height:8px; margin:1rem 0 1.35rem; }
  .rail-legend { margin:-.8rem 0 1.25rem; gap:.7rem; flex-wrap:wrap; }
  .metric-card { min-height:96px; padding:.9rem; }
  .metric-value { margin-top:.7rem; font-size:clamp(1.3rem,7vw,2rem); }
  .stTabs [data-baseweb="tab-list"] { overflow-x:auto; scrollbar-width:none; gap:1.1rem; white-space:nowrap; }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
  .stButton > button, .stFormSubmitButton > button, input, textarea, [role="combobox"] { min-height:44px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration:.001ms !important;
    animation-iteration-count:1 !important;
    transition-duration:.001ms !important;
    scroll-behavior:auto !important;
  }
}
@media (prefers-reduced-motion: no-preference) {
  .pace-rail span { animation: rail-in .65s cubic-bezier(.2,.8,.2,1) both; transform-origin:left; }
  .pace-rail span:nth-child(2) { animation-delay:.08s; }
  .pace-rail span:nth-child(3) { animation-delay:.16s; }
  .pace-rail span:nth-child(4) { animation-delay:.24s; }
  @keyframes rail-in { from { transform:scaleX(0); opacity:0; } to { transform:scaleX(1); opacity:1; } }
}
</style>
"""
st.markdown(THEME, unsafe_allow_html=True)


def request_headers() -> dict:
    try:
        return {str(key).lower(): str(value) for key, value in st.context.headers.items()}
    except Exception:
        return {}


def authorized_identity() -> str | None:
    if os.environ.get("MIMOTION_DEV_AUTH_BYPASS") == "1":
        return "local preview"
    headers = request_headers()
    identity = headers.get("cf-access-authenticated-user-email")
    if identity:
        allowed = {
            item.strip().lower()
            for item in os.environ.get("MIMOTION_ALLOWED_EMAILS", "").split(",")
            if item.strip()
        }
        if not allowed or identity.lower() in allowed:
            return identity
    expected_hash = os.environ.get("MIMOTION_ADMIN_PASSWORD_SHA256", "")
    if expected_hash:
        if st.session_state.get("password_ok"):
            return "password access"
        with st.form("password_gate"):
            password = st.text_input("访问密码", type="password")
            submitted = st.form_submit_button("进入控制台", type="primary")
        if submitted:
            actual = hashlib.sha256(password.encode("utf-8")).hexdigest()
            if hmac.compare_digest(actual, expected_hash.lower()):
                st.session_state.password_ok = True
                st.rerun()
            st.error("访问密码不正确。")
    return None


identity = authorized_identity()
if not identity:
    st.markdown(
        """
        <div class="locked">
          <div class="eyebrow">Protected workspace</div>
          <h1>mimotion 已锁定</h1>
          <p>请通过已授权的 Cloudflare Access 入口访问。账号与通知凭据不会通过未认证页面暴露。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

try:
    settings = load_settings()
except Exception:
    st.error("配置暂时不可用，请检查服务器密钥与存储权限。")
    st.stop()

health = settings_health(settings)
history = load_history(60)
next_run = next_scheduled_run(settings)
now = datetime.now(BEIJING_TZ)

st.markdown(
    f"""
    <div class="masthead">
      <div>
        <div class="eyebrow">Zepp Life operations</div>
        <div class="title">mimotion</div>
      </div>
      <div class="clock">{now:%Y-%m-%d}<br>{now:%H:%M:%S} 北京时间<br>{html.escape(identity)}</div>
    </div>
    <div class="pace-rail" role="img" aria-label="mimotion 夜跑控制台状态轨道"><span></span><span></span><span></span><span></span></div>
    <div class="rail-legend"><b>READY</b><span>SCHEDULE</span><span>RUN</span><span>NOTIFY</span></div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(4)
schedule_status = "已启用" if settings["SCHEDULE_ENABLED"] and health["configured"] else "等待账号" if settings["SCHEDULE_ENABLED"] else "未启用"
if next_run:
    next_run_label = ("今天" if next_run.date() == now.date() else "明天") + next_run.strftime(" %H:%M")
else:
    next_run_label = "未启用"
metric_values = [
    ("系统状态", "可执行" if health["configured"] else "待配置", "凭据已加密保存" if health["configured"] else "先保存至少一个账号"),
    ("账号数量", f"{health['account_count']} 个", html.escape(" / ".join(health["accounts"][:2]) or "暂无账号")),
    ("步数策略", f"{settings['MIN_STEP']:,}–{settings['MAX_STEP']:,}", "定时执行按当天时间线性增长" if settings["TIME_SCALE"] else "每次使用完整范围"),
    ("下一次执行", next_run_label, f"计划{schedule_status} · 北京时间随机分钟"),
]
for column, (label, value, detail) in zip(metric_cols, metric_values):
    column.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-detail">{detail}</div></div>',
        unsafe_allow_html=True,
    )

deck_copy, deck_action = st.columns([2.1, 1])
with deck_copy:
    st.markdown(
        f'<div class="command-deck"><div class="eyebrow">Manual command</div><div class="command-title">向 {health["account_count"]} 个账号提交步数</div><div class="command-meta">当前范围 {settings["MIN_STEP"]:,}–{settings["MAX_STEP"]:,} · 使用服务器加密配置与令牌缓存</div></div>',
        unsafe_allow_html=True,
    )
with deck_action:
    st.write("")
    confirm = st.checkbox("我确认按当前范围提交到已保存账号", disabled=not health["configured"])
    run_now = st.button("立即运行", type="primary", disabled=not confirm or not health["configured"], use_container_width=True)

if run_now:
    progress = st.progress(0)
    status = st.status("正在连接 Zepp Life", expanded=True)

    def update_progress(index: int, total: int, result: dict) -> None:
        progress.progress(index / total)
        css = "status-good" if result["success"] else "status-bad"
        label = "成功" if result["success"] else "失败"
        status.markdown(f'<div class="result-line {css}">{label} · {html.escape(result["user"])} · {html.escape(result["msg"])}</div>', unsafe_allow_html=True)

    try:
        record = run_accounts(settings, source="manual", on_progress=update_progress)
        if record["failed"] and record["success"]:
            status.update(label=f"部分完成：成功 {record['success']}，失败 {record['failed']}", state="complete", expanded=True)
            st.warning("部分账号执行失败，请在下方结果中查看原因。")
        elif record["failed"]:
            status.update(label=f"执行失败：{record['failed']} 个账号未完成", state="error", expanded=True)
        else:
            status.update(label=f"全部 {record['success']} 个账号执行成功", state="complete", expanded=True)
    except Exception:
        status.update(label="执行未开始。请检查服务器连接与配置后重试。", state="error", expanded=True)

plan_tab, accounts_tab, notify_tab, history_tab = st.tabs(
    ["定时计划", "账号保险箱", "通知", "执行记录"]
)

with plan_tab:
    st.subheader("服务器定时计划")
    st.markdown('<p class="section-copy">服务器每分钟检查一次计划，在选定小时内生成随机分钟执行。它会替代 GitHub Actions 的 Random Cron，避免通过提交代码来更新时间。</p>', unsafe_allow_html=True)
    with st.form("schedule_form"):
        schedule_enabled = st.toggle("启用服务器定时任务", value=settings["SCHEDULE_ENABLED"])
        schedule_hours = st.multiselect(
            "北京时间执行小时",
            options=list(range(24)),
            default=settings["SCHEDULE_HOURS"],
            format_func=lambda hour: f"{hour:02d}:00–{hour:02d}:59",
        )
        time_scale = st.toggle("按当天时间线性增长步数", value=settings["TIME_SCALE"])
        sleep_gap = st.number_input("多账号间隔（秒）", min_value=0.0, max_value=120.0, value=float(settings["SLEEP_GAP"]), step=1.0)
        if st.form_submit_button("保存计划", type="primary", use_container_width=True):
            updated = dict(settings)
            updated.update(SCHEDULE_ENABLED=schedule_enabled, SCHEDULE_HOURS=schedule_hours, TIME_SCALE=time_scale, SLEEP_GAP=sleep_gap)
            save_settings(updated)
            st.success("计划已保存。")
            st.rerun()

with accounts_tab:
    st.subheader("账号保险箱")
    st.markdown('<p class="section-copy">账号与密码使用 AES-GCM 加密保存在服务器。密码不会从服务器回填到页面，也不会写入执行记录。建议每行一个账号；同时兼容旧配置的 # 分隔格式。</p>', unsafe_allow_html=True)
    if health["accounts"]:
        st.caption("当前已保存")
        st.markdown("".join(f'<span class="account-chip">{html.escape(item)}</span>' for item in health["accounts"]), unsafe_allow_html=True)
    with st.form("account_form"):
        users_input = st.text_area("手机号或邮箱", placeholder="每行一个账号；留空则保留当前账号")
        passwords_input = st.text_input("密码", type="password", placeholder="多个密码使用 # 分隔；留空则保留当前密码", help="输入内容仅用于替换服务器中的加密配置")
        col_a, col_b = st.columns(2)
        minimum = col_a.number_input("目标最小步数", min_value=1, max_value=99999, value=int(settings["MIN_STEP"]), step=500)
        maximum = col_b.number_input("目标最大步数", min_value=1, max_value=99999, value=int(settings["MAX_STEP"]), step=500)
        if st.form_submit_button("保存账号与策略", type="primary", use_container_width=True):
            updated = dict(settings)
            if users_input.strip() or passwords_input.strip():
                users = split_values(users_input)
                passwords = split_values(passwords_input)
                if not users or len(users) != len(passwords):
                    st.error("账号与密码数量不一致，请确保每个账号对应一个密码。")
                    st.stop()
                updated["USER"] = "#".join(users)
                updated["PWD"] = "#".join(passwords)
            updated["MIN_STEP"] = minimum
            updated["MAX_STEP"] = maximum
            if maximum < minimum:
                st.error("最大步数必须大于或等于最小步数。")
                st.stop()
            save_settings(updated)
            st.success("账号与策略已加密保存。")
            st.rerun()

with notify_tab:
    st.subheader("私有通知")
    st.markdown('<p class="section-copy">留空会保留已保存的值。执行摘要默认只包含脱敏账号，不包含密码或完整手机号。</p>', unsafe_allow_html=True)
    with st.form("notification_form"):
        push_plus = st.text_input("PushPlus Token", type="password", placeholder="留空保留")
        wechat = st.text_input("企业微信 Webhook Key", type="password", placeholder="留空保留")
        telegram_bot = st.text_input("Telegram Bot Token", type="password", placeholder="留空保留")
        telegram_chat = st.text_input("Telegram Chat ID", placeholder="留空保留")
        if st.form_submit_button("保存通知设置", type="primary", use_container_width=True):
            updated = dict(settings)
            replacements = {
                "PUSH_PLUS_TOKEN": push_plus,
                "PUSH_WECHAT_WEBHOOK_KEY": wechat,
                "TELEGRAM_BOT_TOKEN": telegram_bot,
                "TELEGRAM_CHAT_ID": telegram_chat,
            }
            for key, value in replacements.items():
                if value.strip():
                    updated[key] = value.strip()
            save_settings(updated)
            st.success("通知设置已加密保存。")
            st.rerun()

with history_tab:
    st.subheader("最近执行")
    st.markdown('<p class="section-copy">记录只保存时间、来源、脱敏账号、结果、耗时和步数范围。</p>', unsafe_allow_html=True)
    if not history:
        st.info("还没有执行记录。完成一次手动或定时运行后会显示在这里。")
    else:
        for record in history[:20]:
            label = f"{record['time'].replace('T', ' ')} · {'手动' if record['source'] == 'manual' else '定时'} · 成功 {record['success']} / 失败 {record['failed']}"
            with st.expander(label):
                st.caption(f"步数范围 {record['range'][0]:,}–{record['range'][1]:,} · 耗时 {record['duration_seconds']} 秒")
                for result in record.get("results", []):
                    status_class = "status-good" if result["success"] else "status-bad"
                    st.markdown(f'<div class="result-line {status_class}">{html.escape(result["user"])} · {html.escape(result["msg"])}</div>', unsafe_allow_html=True)
