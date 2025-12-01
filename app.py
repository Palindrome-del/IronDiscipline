# app.py (V19 - Final Integration: Review + Manual Price + Doctor)
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config.settings import Config
from utils.data_loader import DataLoader
from agents.tech_agent import TechAgent
from agents.screener import MarketScanner
from agents.macro_agent import MacroAgent
from agents.warrant_agent import WarrantAgent
from agents.portfolio_agent import PortfolioAgent
from agents.hunter import HunterAgent
from agents.strategy_agent import StrategyAgent
from agents.alpha_tactician import AlphaTactician
from agents.position_monitor import PositionMonitor
from agents.review_agent import ReviewAgent
from utils.watchlist_mgr import WatchlistManager
from utils.history_mgr import HistoryManager
import colorama
import time

# --- 1. 頁面設定 ---
st.set_page_config(page_title="Iron Discipline AI 戰情室", layout="wide", page_icon="🛡️")

# --- 2. CSS 美化 ---
st.markdown("""
<style>
    .metric-card {background-color: #f0f2f6; border: 1px solid #d0d2d6; padding: 15px; border-radius: 10px; color: black;}
    .stButton>button {width: 100%; border-radius: 5px; font-weight: bold;}
    /* 戰術看板樣式 */
    .action-box {background-color: #d1e7dd; border-left: 5px solid #198754; padding: 20px; border-radius: 5px; color: #0f5132;}
    .wait-box {background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 20px; border-radius: 5px; color: #664d03;}
    /* 狀態框 */
    .alert-box {background-color: #f8d7da; border-left: 5px solid #dc3545; padding: 10px; color: #721c24; margin-bottom: 10px;}
    .safe-box {background-color: #d1e7dd; border-left: 5px solid #198754; padding: 10px; color: #0f5132; margin-bottom: 10px;}
    /* 權證與投資長樣式 */
    .cio-box {background-color: #e2e3e5; border-left: 5px solid #383d41; padding: 20px; border-radius: 5px; color: #383d41;}
    .warrant-box {background-color: #cfe2ff; border-left: 5px solid #0d6efd; padding: 20px; border-radius: 5px; color: #084298;}
</style>
""", unsafe_allow_html=True)

# --- 3. 系統初始化 ---
@st.cache_resource(ttl=3600) 
def load_system():
    print(">>> 正在啟動 Iron Discipline AI 全系統 (V19)...")
    loader = DataLoader()
    
    tech_agent = TechAgent() 
    scanner = MarketScanner(tech_agent=tech_agent)
    macro = MacroAgent()
    warrant_agent = WarrantAgent()
    portfolio_agent = PortfolioAgent()
    hunter = HunterAgent()
    strategy_agent = StrategyAgent()
    
    tactician = AlphaTactician(hunter, scanner, tech_agent, strategy_agent, macro, portfolio_agent)
    monitor = PositionMonitor(loader, portfolio_agent)
    watchlist_mgr = WatchlistManager()
    history_mgr = HistoryManager()
    
    # 注入 ReviewAgent
    reviewer = ReviewAgent(loader, scanner, strategy_agent, history_mgr)
    
    return tech_agent, scanner, macro, warrant_agent, portfolio_agent, hunter, strategy_agent, tactician, monitor, watchlist_mgr, history_mgr, reviewer

try:
    tech, scan, macro, warrant, portfolio, hunt, strat, tactician, monitor, wl_mgr, hist_mgr, reviewer = load_system()
except Exception as e:
    st.error(f"🔥 系統核心啟動失敗: {e}")
    st.stop()

# --- 4. 側邊欄導航 ---
with st.sidebar:
    st.title("🛡️ 鋼鐵紀律")
    
    # 資產摘要
    p_data = portfolio.get_summary()
    curr_cash = p_data.get('cash', 117000)
    st.metric("可用彈藥", f"${curr_cash:,.0f}")
    st.progress(min(curr_cash / 200000, 1.0))
    st.caption("目標: $200,000")
    
    st.markdown("---")
    page = st.radio("戰術面板", [
        "⚡ 今日戰術 (Dashboard)", 
        "💰 資產庫存管理", 
        "📝 盤後檢討與學習", # [V19] 檢討模組
        "🛠️ 手動分析工具",
        "📜 歷史戰報回顧"
    ])
    
    # 觀察清單 Widget
    st.markdown("---")
    with st.expander("📋 觀察清單", expanded=False):
        my_watchlist = wl_mgr.load()
        for item in my_watchlist:
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{item['id']}**")
            if c2.button("❌", key=f"del_{item['id']}"):
                wl_mgr.remove_stock(item['id'])
                st.rerun()
        
        new_stock = st.text_input("新增", max_chars=4, key="add_wl_input")
        if st.button("➕ 加入"):
            if new_stock: wl_mgr.add_stock(new_stock, "手動加入"); st.rerun()

    st.markdown("---")
    if st.button("🔄 刷新系統"):
        st.cache_resource.clear()
        st.rerun()

# =================================================
# 頁面 1: 今日戰術 (Dashboard)
# =================================================
if page == "⚡ 今日戰術 (Dashboard)":
    st.title("⚡ 即時戰術指揮中心")
    st.caption("系統將綜合總經、資金與全市場掃描，給出當下最高期望值的操作建議。")

    if st.button("🔥 生成今日最佳操作指令", type="primary"):
        with st.status("AI 戰術官正在運算中...", expanded=True) as status:
            st.write("1. 分析全球總經局勢...")
            st.write("2. 盤點資金部位...")
            st.write("3. 獵鷹出動：掃描全台股異動標的...")
            st.write("4. TFT 模型推演：計算預期 ROI...")
            st.write("5. Gemini 投資長：最終決策審核...")
            
            tactic_report = tactician.generate_daily_tactics()
            st.session_state.daily_report = tactic_report
            status.update(label="✅ 決策完成！", state="complete", expanded=False)

    if 'daily_report' in st.session_state:
        report = st.session_state.daily_report
        
        # 存檔按鈕
        col_save, col_void = st.columns([1, 4])
        with col_save:
            if st.button("💾 儲存此戰報", key="save_tactic"):
                fname = hist_mgr.save_report("Tactic", report['stock_id'], report)
                st.toast(f"戰報已儲存: {fname}")

        # 顯示邏輯
        cio_text = report.get('gemini_analysis', '無建議')
        clean_text = cio_text.replace(" ", "").replace("\n", "").replace("*", "")
        is_vetoed = any(k in clean_text for k in ["決策：觀望", "決策：賣出", "保持100%現金", "建議空手", "暫不進場"])

        if report['status'] == 'ACTION':
            if is_vetoed:
                st.markdown(f"""<div class="wait-box"><h2>🛑 投資長否決：{report['stock_id']} (風險過高)</h2><p>掃描發現潛力 (ROI {report['roi']:.2f}%)，但未通過風控。</p></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="action-box"><h2>🚀 攻擊指令：{report['stock_id']}</h2><p><b>現價：</b>{report['price']} | <b>預期漲幅：</b>{report['roi']:.2f}%</p></div>""", unsafe_allow_html=True)
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("### 🤖 投資長決策報告")
                st.markdown(cio_text)
            with c2:
                st.metric("總經評分", f"{report['macro_score']}", report['macro_msg'])
                st.metric("停損防守點", f"{report['support']:.1f}")
            
            # --- 換股對決功能 ---
            st.divider()
            p_pos = portfolio.get_summary()['positions']
            if p_pos and not is_vetoed:
                st.markdown("#### ⚖️ 換股對決 (Rebalance Duel)")
                holdings = [p['stock_id'] for p in p_pos]
                selected_old = st.selectbox("選擇要比較的持倉", holdings)
                
                if st.button(f"🥊 {report['stock_id']} vs {selected_old} (AI 裁判)"):
                    with st.spinner("正在進行雙股深度比較..."):
                        duel_result = tactician.evaluate_rebalance(report, selected_old)
                        st.session_state.duel_result = duel_result
                
                if 'duel_result' in st.session_state:
                    st.markdown(f"""<div class="cio-box"><h3>🥊 對決結果</h3>{st.session_state.duel_result.replace(chr(10), '<br>')}</div>""", unsafe_allow_html=True)
            # --------------------
            
            st.divider()
            with st.expander("⚡ 調用下單介面", expanded=not is_vetoed):
                q_type = st.selectbox("商品", ["Stock", "Warrant"], key="q_type")
                q_price = st.number_input("成交價", value=float(report['price']), key="q_price")
                q_qty = st.number_input("數量", min_value=1, step=1000, key="q_qty")
                q_stop = st.number_input("停損價", value=float(report['support']), key="q_stop")
                q_target = st.number_input("目標價", value=float(report['price'])*1.1, key="q_tar")
                default_note = f"AI 戰術: {report['stock_id']} (CIO:{'核准' if not is_vetoed else '否決'})"
                q_note = st.text_input("筆記", value=default_note, key="q_note")
                
                if st.button("📥 下單並監控"):
                    success, msg = portfolio.record_transaction("BUY", report['stock_id'], q_type, q_price, q_qty, q_note, stop_loss=q_stop, target_price=q_target)
                    if success:
                        st.success(msg)
                        time.sleep(2)
                        st.rerun()
                    else: st.error(msg)
        else:
            st.markdown(f"""<div class="wait-box"><h2>🛑 防守指令：觀望</h2><p>{report['reason']}</p></div>""", unsafe_allow_html=True)
            st.metric("總經評分", f"{report['macro_score']}", report['macro_msg'])

# =================================================
# 頁面 2: 資產庫存管理 (含手動報價 & 診斷)
# =================================================
elif page == "💰 資產庫存管理":
    st.subheader("💼 資產監控室")
    
    # 1. 監控功能
    if st.button("🔄 掃描庫存狀態 (即時價)"):
        with st.spinner("正在巡視持倉..."):
            st.session_state.monitor_report = monitor.review_portfolio()
    
    if 'monitor_report' in st.session_state and st.session_state.monitor_report:
        st.markdown("### 🚨 庫存健康度")
        for item in st.session_state.monitor_report:
            cls = "alert-box" if item['status'] in ['STOP_LOSS', 'DANGER'] else "safe-box"
            emoji = "🚨" if item['status'] == 'STOP_LOSS' else ("💰" if item['status']=='TAKE_PROFIT' else "✅")
            st.markdown(f"""
            <div class="{cls}">
                <b>{emoji} {item['stock_id']} ({item['type']})</b> | 現價: {item['current_price']} | 損益: ${item['unrealized_pl']:,.0f} ({item['roi_pct']:.2f}%)<br>
                <b>狀態：{item['action_msg']}</b> (停損: {item['stop_loss']})
            </div>
            """, unsafe_allow_html=True)

    p_data = portfolio.get_summary()
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        new_cash = st.number_input("目前現金", value=float(p_data['cash']), step=1000.0)
        if st.button("💾 更新現金"):
            portfolio.update_cash(new_cash); st.toast("已更新"); st.rerun()
    with col_b:
        mkt_value = sum([p['avg_cost'] * p['qty'] for p in p_data['positions']])
        st.metric("持倉成本市值", f"${mkt_value:,.0f}")
    with col_c:
        total = p_data['cash'] + mkt_value
        gap = 200000 - total
        st.metric("總資產", f"${total:,.0f}", f"-${gap:,.0f}" if gap>0 else "達標!", delta_color="off")
    
    st.divider()
    st.markdown("### 📜 持倉操作 (含手動報價)")
    
    if p_data['positions']:
        for i, pos in enumerate(p_data['positions']):
            # --- [V17] 手動報價欄位 ---
            c1, c2, c3, c4 = st.columns([1.2, 1.5, 1.5, 1])
            
            c1.write(f"**{pos['stock_id']}**\n({pos['type']})")
            c2.caption(f"均價: {pos['avg_cost']:.2f}\n量: {pos['qty']}")
            
            # 手動輸入區
            manual_price = c3.number_input("手動現價", value=0.0, key=f"mp_{i}", help="若自動抓不到，請輸入目前第一檔買價")
            
            # 即時損益試算 (若有輸入)
            if manual_price > 0:
                cost = pos['avg_cost']
                val = manual_price * pos['qty']
                fee_rate = 0.004425 if pos['type'] == 'Stock' else 0.002425
                net_val = val * (1 - fee_rate)
                pl = net_val - (cost * pos['qty'])
                roi = (pl / (cost * pos['qty'])) * 100
                
                color = "red" if roi < 0 else "green"
                c3.markdown(f":{color}[損益: ${pl:,.0f} ({roi:.2f}%)]")

            # 診斷按鈕
            if c4.button(f"🩺 診斷", key=f"diag_{i}"):
                loader_inst = DataLoader() 
                with st.spinner(f"正在為 {pos['stock_id']} 進行深度健檢..."):
                    # 優先使用手動價格，否則抓即時
                    df = loader_inst.fetch_data(pos['stock_id'], force_update=True)
                    
                    # --- [V17] 強制注入手動價格 ---
                    if manual_price > 0 and df is not None:
                        df.iloc[-1, df.columns.get_loc('Close')] = manual_price
                        print(f"手動注入價格: {manual_price}")
                    
                    if df is not None:
                        sc, msg, tech_data = tech.analyze(df)
                        if 'macro_data' not in st.session_state: st.session_state.macro_data = macro.analyze()
                        
                        advice = strat.review_holding(pos['stock_id'], pos, tech_data, st.session_state.macro_data)
                        st.session_state[f"diag_res_{i}"] = advice
                    else:
                        st.error("數據不足")

            if f"diag_res_{i}" in st.session_state:
                st.markdown(f"""<div class="cio-box"><h3>🤖 診斷報告</h3>{st.session_state[f"diag_res_{i}"].replace(chr(10), '<br>')}</div>""", unsafe_allow_html=True)
            st.markdown("---")

    with st.expander("⚡ 新增/調整交易紀錄"):
        c1, c2 = st.columns([1, 4])
        with c1:
            action = st.radio("動作", ["買進", "賣出"], key="act_p")
            act_code = "BUY" if "買" in action else "SELL"
        with c2:
            tc1, tc2, tc3 = st.columns(3)
            t_stock = tc1.text_input("代號", key="ts_p")
            t_type = tc2.selectbox("類型", ["Stock", "Warrant"], key="tt_p")
            t_code = "Stock" if "Stock" in t_type else "Warrant"
            tc4, tc5 = st.columns(2)
            t_price = tc4.number_input("價", min_value=0.0, step=0.01, key="tp_p")
            t_qty = tc5.number_input("量", min_value=1, step=1000, key="tq_p")
            
            if act_code == "BUY":
                tc6, tc7 = st.columns(2)
                t_stop = tc6.number_input("停損價", min_value=0.0, step=0.1)
                t_target = tc7.number_input("目標價", min_value=0.0, step=0.1)
            else: t_stop, t_target = 0.0, 0.0

            t_note = st.text_input("筆記", key="tn_p")
            
            if t_price > 0 and t_qty > 0:
                raw = t_price * t_qty
                disc = 0.6 if t_code == "Stock" else 1.0
                fee = max(20, int(raw * 0.001425 * disc))
                tax = int(raw * (0.003 if t_code=="Stock" else 0.001)) if act_code == "SELL" else 0
                final = raw + fee if act_code == "BUY" else raw - fee - tax
                st.caption(f"預估結算: ${final:,.0f} (含費{fee}, 稅{tax})")

            if st.button("執行交易", type="primary" if act_code=="BUY" else "secondary"):
                if t_stock:
                    s, m = portfolio.record_transaction(act_code, t_stock, t_code, t_price, t_qty, t_note, stop_loss=t_stop, target_price=t_target)
                    if s: st.success(m); time.sleep(1); st.rerun()
                    else: st.error(m)

    st.markdown("### 持倉與紀錄")
    tab1, tab2 = st.tabs(["📜 持倉", "lL 歷史"])
    with tab1:
        if p_data['positions']:
            df_pos = pd.DataFrame(p_data['positions'])
            cols = ['id', 'stock_id', 'type', 'avg_cost', 'qty', 'stop_loss', 'target_price', 'note']
            for c in cols: 
                if c not in df_pos.columns: df_pos[c] = 0
            st.dataframe(df_pos[cols], use_container_width=True)
            if st.button("❌ 刪除選定ID (修正用)"):
                st.info("請使用上方的賣出功能來平倉。")
        else: st.info("目前無持倉。")
    with tab2:
        if p_data['history']:
            st.dataframe(pd.DataFrame(p_data['history']), use_container_width=True)

# =================================================
# 頁面 3: 盤後檢討與學習 (V19 - 正式回歸)
# =================================================
elif page == "📝 盤後檢討與學習":
    st.title("📝 每日盤後進化 (Daily Evolution)")
    st.caption("系統將自動對比今日「戰術建議」與「市場真實表現」，找出盲點並進行強化學習。")
    
    if st.button("🚀 啟動自我檢討程序", type="primary"):
        with st.status("正在掃描全市場與回溯決策...", expanded=True) as status:
            st.write("1. 獲取今日觀察清單收盤數據...")
            st.write("2. 鎖定今日漲幅最強標的...")
            st.write("3. 投資長進行差異化分析 (Gap Analysis)...")
            
            review_report = reviewer.perform_daily_review()
            st.session_state.review_report = review_report
            status.update(label="✅ 檢討完成！", state="complete")

    if 'review_report' in st.session_state:
        st.markdown(st.session_state.review_report)
        st.divider()
        st.info("💡 學習機制：您可以根據 AI 的反思，手動調整觀察清單，或在週末重新訓練模型時，特別關注這些「錯過」的特徵。")

# =================================================
# 頁面 4: 手動分析工具 (Manual Tools)
# =================================================
elif page == "🛠️ 手動分析工具":
    tool_tab1, tool_tab2, tool_tab3 = st.tabs(["🦅 獵人模式", "📡 觀察清單掃描", "🎯 單股深入分析"])
    
    with tool_tab1:
        if st.button("啟動獵鷹掃描"):
            with st.status("獵鷹運作中...", expanded=True):
                dynamic_list = hunt.hunt(mode="aggressive")
                orig = scan.target_stocks
                scan.target_stocks = dynamic_list
                res = scan.scan(strategy="AI_Alpha")
                scan.target_stocks = orig
                st.dataframe(res)
    
    with tool_tab2:
        if st.button("啟動清單掃描"):
            mylist = wl_mgr.load()
            if not mylist: st.warning("清單為空")
            else:
                ids = [x['id'] for x in mylist]
                with st.status(f"掃描 {len(ids)} 檔...", expanded=True):
                    orig = scan.target_stocks
                    scan.target_stocks = ids
                    res = scan.scan("AI_Alpha")
                    scan.target_stocks = orig
                    st.dataframe(res)

    with tool_tab3:
        c1, c2 = st.columns([1, 3])
        with c1: target_stock = st.text_input("代號", value=Config.TARGET_STOCK, key="man_t")
        with c2: run_btn = st.button("分析", key="man_r")
        
        if run_btn:
            with st.spinner("分析中..."):
                df = DataLoader().fetch_data(target_stock, force_update=True)
                if df is not None and len(df) > 60:
                    sc, msg, (c, t, s) = tech.analyze(df)
                    plot = tech.get_plot_data(df)
                    wplan = warrant.generate_plan(c, t, s, sc)
                    if 'macro_data' not in st.session_state: st.session_state.macro_data = macro.analyze()
                    adv = strat.consult(target_stock, (c, t, s), wplan, st.session_state.macro_data, portfolio.get_summary())
                    
                    full_rep = {
                        "stock_id": target_stock, "price": c, "ai_target": t, "ai_support": s,
                        "score": sc, "gemini_analysis": adv, "plot_data": plot, "warrant_plan": wplan
                    }
                    
                    st.markdown(f"""<div class="cio-box"><h3>🤖 投資長報告</h3>{adv.replace(chr(10), '<br>')}</div>""", unsafe_allow_html=True)
                    if st.button("💾 儲存此報告"): 
                        fname = hist_mgr.save_report("Analysis", target_stock, full_rep)
                        st.toast(f"已存檔: {fname}")
                    
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    col1.metric("現價", f"{c:.1f}")
                    col2.metric("目標", f"{t:.1f}", f"{(t-c)/c*100:.2f}%")
                    col3.metric("支撐", f"{s:.1f}")
                    
                    if sc >= 1:
                        st.markdown(f"""<div class="warrant-box"><h3>⚔️ {wplan['strategy']}</h3>履約價：{wplan['filters']['價內外']}</div>""", unsafe_allow_html=True)

                    fig = go.Figure()
                    hist = df.tail(90)
                    fig.add_trace(go.Scatter(x=hist['date'], y=hist['Close'], name='歷史', line=dict(color='#1f77b4')))
                    fig.add_trace(go.Scatter(x=plot['pred_dates'], y=plot['p50'], name='預測', line=dict(color='#00cc96', dash='dot')))
                    fig.add_trace(go.Scatter(x=plot['pred_dates']+plot['pred_dates'][::-1], y=list(plot['p90'])+list(plot['p10'])[::-1], fill='toself', fillcolor='rgba(0,200,0,0.2)', line=dict(color='rgba(0,0,0,0)')))
                    st.plotly_chart(fig, use_container_width=True)
                else: st.error("數據不足")

# =================================================
# 頁面 5: 歷史戰報回顧 (Full Restoration)
# =================================================
elif page == "📜 歷史戰報回顧":
    st.subheader("📜 歷史分析檔案館")
    files = hist_mgr.load_history_list()
    
    if not files:
        st.info("目前沒有存檔記錄。")
    else:
        sel = st.selectbox("選擇歷史戰報", files)
        if sel:
            rec = hist_mgr.load_report(sel)
            meta = rec['meta']
            data = rec['content']
            
            st.caption(f"存檔時間: {meta['timestamp']} | ID: {meta['stock_id']} | 類型: {meta['type']}")
            st.markdown(f"## {meta['stock_id']} 回顧")
            
            if 'gemini_analysis' in data:
                 st.markdown(f"""<div class="cio-box"><h3>🤖 當時建議</h3>{data['gemini_analysis'].replace(chr(10), '<br>')}</div>""", unsafe_allow_html=True)
            
            if 'plot_data' in data:
                pdata = data['plot_data']
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=pdata['pred_dates'], y=pdata['p50'], mode='lines+markers', name='當時預測', line=dict(color='#00cc96')))
                fig.add_trace(go.Scatter(x=pdata['pred_dates']+pdata['pred_dates'][::-1], y=list(pdata['p90'])+list(pdata['p10'])[::-1], fill='toself', fillcolor='rgba(0,200,0,0.2)', line=dict(color='rgba(0,0,0,0)')))
                fig.update_layout(template="plotly_white", height=400, title="當時預測路徑")
                st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("查看詳細數據"):
                st.json(data)

            if st.button("🗑️ 刪除"):
                hist_mgr.delete_report(sel)
                st.rerun()