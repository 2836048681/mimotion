import streamlit as st
import json
import os
import time
import random
from main import MiMotionRunner
from util import push_util

# 设置页面配置
st.set_page_config(page_title="小米运动刷步助手", page_icon="Oc", layout="centered")

st.title("🏃 小米运动(Zepp Life) 刷步助手")
st.markdown("基于 `mimotion` 项目的可视化操作界面")

# --- 侧边栏：配置区域 ---
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    # 账号设置
    st.subheader("1. 账号信息")
    st.info("支持多账号，使用 # 分隔")
    user_input = st.text_input("手机号/邮箱 (USER)", placeholder="13800000000")
    pwd_input = st.text_input("密码 (PWD)", type="password", placeholder="password123")
    
    # 步数设置
    st.subheader("2. 步数范围")
    col1, col2 = st.columns(2)
    with col1:
        min_step = st.number_input("最小步数", value=18000, step=1000)
    with col2:
        max_step = st.number_input("最大步数", value=25000, step=1000)
        
    # 推送设置
    st.subheader("3. 推送通知 (选填)")
    push_plus_token = st.text_input("PushPlus Token")
    wechat_key = st.text_input("企业微信 Webhook Key")
    tg_bot_token = st.text_input("Telegram Bot Token")
    tg_chat_id = st.text_input("Telegram Chat ID")

# --- 主界面：功能区域 ---

# 选项卡
tab1, tab2 = st.tabs(["🚀 立即运行", "📋 生成 GitHub Config"])

# TAB 1: 立即运行逻辑
with tab1:
    st.write("### 在线执行")
    st.caption("点击下方按钮将直接调用接口刷步数，日志将显示在下方。")
    
    if st.button("开始刷步数", type="primary"):
        if not user_input or not pwd_input:
            st.error("请先在左侧侧边栏填写账号和密码！")
        else:
            # 准备数据
            users = user_input.split('#')
            pwds = pwd_input.split('#')
            
            if len(users) != len(pwds):
                st.error(f"账号数量({len(users)})与密码数量({len(pwds)})不匹配，请检查！")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_area = st.empty()
                logs = []
                exec_results = []
                
                total = len(users)
                for idx, (u, p) in enumerate(zip(users, pwds)):
                    status_text.text(f"正在处理第 {idx+1}/{total} 个账号: {u}...")
                    
                    try:
                        # 调用 main.py 中的核心类 MiMotionRunner
                        runner = MiMotionRunner(u, p)
                        # 执行登录和刷步逻辑
                        msg, success = runner.login_and_post_step(min_step, max_step)
                        
                        # 记录结果
                        result_data = {
                            "user": u,
                            "success": success,
                            "msg": msg
                        }
                        exec_results.append(result_data)
                        
                        # 显示日志
                        icon = "✅" if success else "❌"
                        logs.append(f"{icon} 账号 **{u}**: {msg}")
                        log_area.markdown("\n".join(logs))
                        
                    except Exception as e:
                        st.error(f"账号 {u} 执行出错: {str(e)}")
                        exec_results.append({"user": u, "success": False, "msg": str(e)})
                    
                    # 更新进度条
                    progress_bar.progress((idx + 1) / total)
                    time.sleep(1) # 避免请求过快
                
                status_text.text("执行完成！")
                
                # 处理推送
                success_count = sum(1 for r in exec_results if r['success'])
                summary = f"执行账号总数{total}，成功：{success_count}，失败：{total - success_count}"
                st.success(summary)
                
                # 如果配置了推送，尝试推送
                if push_plus_token or wechat_key or (tg_bot_token and tg_chat_id):
                    with st.spinner("正在发送推送通知..."):
                        push_config = push_util.PushConfig(
                            push_plus_token=push_plus_token,
                            push_wechat_webhook_key=wechat_key,
                            telegram_bot_token=tg_bot_token,
                            telegram_chat_id=tg_chat_id,
                            push_plus_max=30
                        )
                        push_util.push_results(exec_results, summary, push_config)
                    st.info("推送任务已处理")

# TAB 2: 生成 JSON 配置
with tab2:
    st.write("### 生成 GitHub Actions 配置")
    st.caption("如果你仍想使用 GitHub Actions 自动运行，可以在这里生成配置 JSON，然后复制到 Secrets 的 `CONFIG` 中。")
    
    if user_input and pwd_input:
        config_dict = {
            "USER": user_input,
            "PWD": pwd_input,
            "MIN_STEP": str(min_step),
            "MAX_STEP": str(max_step),
            "PUSH_PLUS_TOKEN": push_plus_token,
            "PUSH_WECHAT_WEBHOOK_KEY": wechat_key,
            "TELEGRAM_BOT_TOKEN": tg_bot_token,
            "TELEGRAM_CHAT_ID": tg_chat_id,
            "SLEEP_GAP": "5",
            "USE_CONCURRENT": "False"
        }
        
        # 移除空值
        config_dict = {k: v for k, v in config_dict.items() if v}
        
        json_str = json.dumps(config_dict, ensure_ascii=False, indent=2)
        st.code(json_str, language="json")
        st.caption("复制上方代码，填入 GitHub 仓库 Settings -> Secrets -> Actions -> CONFIG 中。")
    else:
        st.warning("请先在左侧侧边栏填写账号和密码。")
