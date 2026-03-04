"""
Gradio UI for the Business Intelligence Agent Pipeline — Corporate Dark / Bloomberg Redesign

This app demonstrates Google ADK's SequentialAgent pattern:
1. Text-to-SQL Agent (standalone)
2. SQL execution via BIService
3. Insight Pipeline (SequentialAgent: Visualization → Explanation)
"""

import gradio as gr
import asyncio
import os
import pandas as pd
import altair as alt
from dotenv import load_dotenv
from google.genai import types
import tempfile
from datetime import datetime
from bi_agent import root_runner
from bi_agent.tools import generate_report_pdf

current_df_storage = None
load_dotenv(dotenv_path='bi_agent/.env')

# ============================================================================
# Corporate Dark JS — Bloomberg-style ticker header + loading
# ============================================================================
js_code = """
function createGradioAnimation() {

    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@400;500;600;700&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    const style = document.createElement('style');
    style.innerHTML = `
        * { font-family: 'DM Mono', monospace !important; }

        @keyframes tickerScroll {
            0%   { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }
        @keyframes fadeDown {
            from { opacity: 0; transform: translateY(-10px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50%       { opacity: 0.4; }
        }
        @keyframes shimmer {
            0%   { background-position: -400px 0; }
            100% { background-position: 400px 0; }
        }

        /* ── Loading overlay ── */
        #corp-loading {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(10,14,22,0.93);
            z-index: 10000;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 16px;
        }
        #corp-loading.visible { display: flex; }
        .corp-spinner {
            width: 36px; height: 36px;
            border: 2px solid #1e2d45;
            border-top-color: #f5a623;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .corp-load-label {
            font-size: 0.65rem;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: #4a6080;
        }
        .corp-load-status {
            font-size: 0.75rem;
            color: #f5a623;
            letter-spacing: 2px;
            animation: pulse 1.4s ease infinite;
        }

        /* ── Ticker bar ── */
        .ticker-wrap {
            overflow: hidden;
            background: #0d1117;
            border-bottom: 1px solid #1e2d45;
            padding: 6px 0;
            white-space: nowrap;
        }
        .ticker-inner {
            display: inline-block;
            animation: tickerScroll 28s linear infinite;
        }
        .ticker-item {
            display: inline-block;
            margin: 0 32px;
            font-size: 0.65rem;
            letter-spacing: 1px;
            color: #4a6080;
        }
        .ticker-item .t-name  { color: #7a9cc0; margin-right: 6px; }
        .ticker-item .t-val   { color: #e2e8f0; margin-right: 4px; }
        .ticker-item .t-up    { color: #34d399; }
        .ticker-item .t-down  { color: #f87171; }
    `;
    document.head.appendChild(style);

    /* Loading overlay */
    const overlay = document.createElement('div');
    overlay.id = 'corp-loading';
    overlay.innerHTML = `
        <div class="corp-spinner"></div>
        <div class="corp-load-status">PROCESSING</div>
        <div class="corp-load-label">Running Agent Pipeline</div>
    `;
    document.body.appendChild(overlay);

    const showOverlay = () => overlay.classList.add('visible');
    const hideOverlay = () => overlay.classList.remove('visible');
    const obs = new MutationObserver(() => {
        const badge = document.querySelector('.progress-level-inner, .generating');
        if (badge) showOverlay(); else hideOverlay();
    });
    obs.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => {
        const btn = document.querySelector('button.primary');
        if (btn) btn.addEventListener('click', () => { showOverlay(); setTimeout(hideOverlay, 500); });
    }, 2000);

    /* ── Ticker bar ── */
    const items = [
        { name:'TEXT-TO-SQL',  val:'ACTIVE',  chg:'+OK',  up:true  },
        { name:'SQL EXECUTOR', val:'READY',   chg:'+OK',  up:true  },
        { name:'TREND AGENT',  val:'STANDBY', chg:'——',   up:null  },
        { name:'VIZ AGENT',    val:'STANDBY', chg:'——',   up:null  },
        { name:'EXPLAIN AGENT',val:'STANDBY', chg:'——',   up:null  },
        { name:'GOOGLE ADK',   val:'v1.0',    chg:'+RUN', up:true  },
        { name:'DATABASE',     val:'CONN',    chg:'+LIVE',up:true  },
    ];
    const buildTicker = () => items.map(i => {
        const cls = i.up === true ? 't-up' : i.up === false ? 't-down' : 't-val';
        return `<span class="ticker-item">
            <span class="t-name">${i.name}</span>
            <span class="t-val">${i.val}</span>
            <span class="${cls}">${i.chg}</span>
        </span>`;
    }).join('');

    const ticker = document.createElement('div');
    ticker.className = 'ticker-wrap';
    ticker.innerHTML = `<div class="ticker-inner">${buildTicker()}${buildTicker()}</div>`;

    /* ── Main Header ── */
    const banner = document.createElement('div');
    banner.id = 'corp-banner';
    banner.style.cssText = `
        background: linear-gradient(180deg, #0d1117 0%, #111827 100%);
        padding: 28px 40px 22px;
        border-bottom: 2px solid #1e2d45;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 24px;
        animation: fadeDown 0.5s ease both;
    `;
    banner.innerHTML = `
        <div>
            <div style="font-size:0.58rem;letter-spacing:5px;text-transform:uppercase;color:#4a6080;margin-bottom:8px;">
                Bloomberg · Google ADK · Sequential Agent
            </div>
            <div style="display:flex;align-items:baseline;gap:14px;">
                <span style="font-family:'DM Sans',sans-serif !important;font-size:clamp(1.4rem,2.8vw,2rem);font-weight:700;color:#e2e8f0;letter-spacing:-0.5px;">
                    BI Agent
                </span>
                <span style="font-size:0.65rem;letter-spacing:3px;color:#4a6080;text-transform:uppercase;">
                    Intelligence Terminal
                </span>
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.6rem;letter-spacing:2px;color:#4a6080;text-transform:uppercase;margin-bottom:4px;">Pipeline Status</div>
            <div style="display:flex;gap:8px;justify-content:flex-end;">
                <span style="background:#0f2718;border:1px solid #34d39944;color:#34d399;font-size:0.6rem;padding:3px 8px;letter-spacing:1px;">● ONLINE</span>
                <span style="background:#1a1200;border:1px solid #f5a62344;color:#f5a623;font-size:0.6rem;padding:3px 8px;letter-spacing:1px;" id="corp-time"></span>
            </div>
        </div>
    `;

    const gradioContainer = document.querySelector('.gradio-container');
    if (gradioContainer) {
        gradioContainer.insertBefore(ticker, gradioContainer.firstChild);
        gradioContainer.insertBefore(banner, ticker);
    }

    /* Clock */
    const timeEl = document.getElementById('corp-time');
    const tick = () => {
        if (timeEl) timeEl.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
    };
    tick(); setInterval(tick, 1000);

    return 'Corporate Dark Init Complete';
}
"""

# ============================================================================
# Corporate Dark CSS
# ============================================================================
css = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@400;500;600;700&display=swap');

*, *::before, *::after { font-family: 'DM Mono', monospace !important; box-sizing: border-box; }

body, .gradio-container {
    background: #0d1117 !important;
    color: #c9d6e3 !important;
}

/* Dividers */
.gradio-container hr { border: none !important; border-top: 1px solid #1e2d45 !important; margin: 24px 0 !important; }

/* ── Result Cards ── */
.result-card {
    background: #111827 !important;
    border-radius: 2px !important;
    padding: 20px 22px !important;
    border: 1px solid #1e2d45 !important;
    border-left: 3px solid #f5a623 !important;
    transition: border-color 0.2s !important;
}
.result-card:hover { border-left-color: #fbbf47 !important; }

/* ── Card inner headings ── */
.result-card h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    color: #4a6080 !important;
    text-transform: uppercase !important;
    letter-spacing: 3px !important;
    margin-bottom: 14px !important;
    border-bottom: 1px solid #1e2d45 !important;
    padding-bottom: 8px !important;
    text-shadow: none !important;
}

/* ── Input ── */
textarea, input[type="text"] {
    background: #0d1117 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 2px !important;
    color: #e2e8f0 !important;
    padding: 12px 16px !important;
    font-size: 0.82rem !important;
    line-height: 1.6 !important;
    transition: border-color 0.2s !important;
    caret-color: #f5a623 !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: #f5a623 !important;
    box-shadow: 0 0 0 1px #f5a62322 !important;
    outline: none !important;
}
textarea::placeholder, input::placeholder { color: #2a3f58 !important; font-style: normal !important; }

/* ── Primary button ── */
button.primary, button[variant="primary"] {
    background: #f5a623 !important;
    border: none !important;
    color: #0d1117 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 12px 28px !important;
    border-radius: 2px !important;
    transition: background 0.15s, transform 0.1s !important;
}
button.primary:hover, button[variant="primary"]:hover { background: #fbbf47 !important; }
button.primary:active, button[variant="primary"]:active { transform: scale(0.98) !important; background: #d4891a !important; }

/* ── Secondary button ── */
button.secondary, button[variant="secondary"] {
    background: transparent !important;
    border: 1px solid #1e2d45 !important;
    color: #4a6080 !important;
    font-size: 0.68rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border-radius: 2px !important;
    padding: 10px 20px !important;
    transition: border-color 0.2s, color 0.2s !important;
}
button.secondary:hover, button[variant="secondary"]:hover {
    border-color: #f5a623 !important;
    color: #f5a623 !important;
}

/* ── Other buttons ── */
button:not(.primary):not(.secondary) {
    background: transparent !important;
    border: 1px solid #1e2d45 !important;
    color: #4a6080 !important;
    border-radius: 2px !important;
    font-size: 0.68rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    transition: all 0.2s !important;
}
button:not(.primary):not(.secondary):hover {
    border-color: #7a9cc0 !important;
    color: #c9d6e3 !important;
}

/* ── Code block ── */
.code-wrap, .codemirror-wrapper, code, pre {
    background: #080c12 !important;
    border: 1px solid #1e2d45 !important;
    color: #7dd3fc !important;
    border-radius: 2px !important;
    font-size: 0.77rem !important;
}

/* ── DataFrame table ── */
table { border-collapse: collapse !important; width: 100% !important; }
thead tr { background: #0d1117 !important; }
thead th {
    color: #f5a623 !important;
    border-bottom: 1px solid #1e2d45 !important;
    padding: 9px 14px !important;
    font-size: 0.62rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    font-weight: 500 !important;
}
tbody tr { background: #111827 !important; border-bottom: 1px solid #161f2e !important; transition: background 0.1s !important; }
tbody tr:nth-child(even) { background: #0f1620 !important; }
tbody tr:hover { background: #162032 !important; }
tbody td { color: #c9d6e3 !important; padding: 8px 14px !important; font-size: 0.77rem !important; }

/* ── Insights markdown ── */
.result-card h1, .result-card h2 {
    font-family: 'DM Sans', sans-serif !important;
    color: #ffffff !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    font-style: normal !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid #2a3f58 !important;
    padding-bottom: 6px !important;
    margin-top: 18px !important;
    text-shadow: none !important;
}
/* h3 inside markdown prose (### headings) */
.result-card .prose h3,
.result-card [data-testid="markdown"] h3,
.result-card .markdown-body h3 {
    font-family: 'DM Sans', sans-serif !important;
    color: #f5a623 !important;
    font-size: 0.80rem !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid #2a3f58 !important;
    padding-bottom: 5px !important;
    margin-top: 16px !important;
}
.result-card p, .result-card li {
    color: #d4e4f5 !important;
    line-height: 1.85 !important;
    font-size: 0.81rem !important;
}
.result-card ul { padding-left: 1.2em !important; }
.result-card li { margin-bottom: 6px !important; }
.result-card li::marker { color: #f5a623 !important; }
.result-card strong {
    color: #ffffff !important;
    font-weight: 700 !important;
    text-shadow: none !important;
}
.result-card em { color: #f5a623 !important; font-style: normal !important; }
.result-card hr { border-top: 1px solid #1e2d45 !important; margin: 14px 0 !important; }

/* ── App-level markdown ── */
.gradio-container h2 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: #4a6080 !important;
    text-transform: uppercase !important;
    letter-spacing: 4px !important;
    text-shadow: none !important;
    font-style: normal !important;
}
.gradio-container p { color: #4a6080 !important; font-size: 0.78rem !important; }
.gr-prose, .prose { color: #4a6080 !important; font-size: 0.75rem !important; line-height: 1.7 !important; }

/* ── Labels ── */
label span { color: #2a3f58 !important; font-size: 0.62rem !important; letter-spacing: 2px !important; text-transform: uppercase !important; }

/* ── File ── */
.file-preview { background: #0d1117 !important; border-color: #1e2d45 !important; }

/* ── Examples ── */
.examples-holder button {
    background: #111827 !important;
    border: 1px solid #1e2d45 !important;
    color: #4a6080 !important;
    font-size: 0.68rem !important;
    border-radius: 2px !important;
    transition: all 0.15s !important;
}
.examples-holder button:hover {
    border-color: #f5a623 !important;
    color: #f5a623 !important;
    background: #1a1200 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #1e2d45; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #2a3f58; }
"""

# ============================================================================
# Pipeline logic (unchanged)
# ============================================================================

async def run_bi_pipeline_async(user_question: str):
    session = await root_runner.session_service.create_session(
        user_id='user', app_name='bi_agent'
    )
    content = types.Content(role='user', parts=[types.Part(text=user_question)])
    events_async = root_runner.run_async(
        user_id='user', session_id=session.id, new_message=content
    )
    results = {}
    async for event in events_async:
        if event.actions and event.actions.state_delta:
            for key, value in event.actions.state_delta.items():
                results[key] = value
    return results


async def process_request_async(message: str):
    try:
        if not message.strip():
            return "Error: Please enter a question", None, None, "Error: No question provided"

        results = await run_bi_pipeline_async(message)
        sql_query = results.get('sql_query', '')

        if '</thinking_process>' in sql_query:
            sql_query = sql_query.split('</thinking_process>')[-1].strip()
        sql_query = sql_query.strip()
        if sql_query.startswith("```sql"):
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        elif sql_query.startswith("```"):
            sql_query = sql_query.replace("```", "").strip()

        query_results_str = results.get('query_results', '{}')
        print(f"DEBUG: query_results_str = {repr(query_results_str)}")
        query_results = {'success': False, 'data': [], 'error': 'Uninitialized'}

        try:
            import json, re
            raw_str = str(query_results_str).strip()
            clean_json = re.sub(r'^```[a-z]*\s*', '', raw_str, flags=re.IGNORECASE)
            clean_json = re.sub(r'\s*```$', '', clean_json)
            parsed_json = json.loads(clean_json)
            if isinstance(parsed_json, list):
                query_results = {'success': True, 'data': parsed_json}
            else:
                query_results = parsed_json
        except Exception:
            try:
                lines = raw_str.split('\n')
                table_lines = [l.strip() for l in lines if '|' in l and l.strip()]
                if len(table_lines) >= 3:
                    headers = [h.strip().replace('\\_', '_') for h in table_lines[0].strip('|').split('|')]
                    data_list = []
                    for line in table_lines[2:]:
                        if line.startswith(':') or '---' in line:
                            continue
                        values = [v.strip() for v in line.strip('|').split('|')]
                        if len(values) == len(headers) and values != headers:
                            row_dict = {}
                            for i, h in enumerate(headers):
                                val = values[i] if i < len(values) else ''
                                try:
                                    row_dict[h] = float(val)
                                except (ValueError, TypeError):
                                    row_dict[h] = val
                            data_list.append(row_dict)
                    if data_list:
                        query_results = {'success': True, 'data': data_list}
                    else:
                        raise ValueError("No rows")
                else:
                    raise ValueError("Invalid table")
            except Exception:
                query_results = {
                    'success': False, 'data': [],
                    'error': f'Could not parse results. Output: {raw_str[:100]}'
                }

        if not query_results.get('success', False):
            error_msg = query_results.get('error', 'Unknown error')
            sql_query = f"-- Error executing query\n{sql_query}\n\n-- Error: {error_msg}"
            return sql_query, None, None, f"Error executing query: {error_msg}"

        data_list = query_results.get('data', [])
        if not data_list:
            return sql_query, pd.DataFrame(), None, "Query executed successfully but returned no data."

        df = pd.DataFrame(data_list)

        trend_text = results.get('trend_insights', '')
        explanation_text = results.get('explanation_text', '')
        final_insights = ""
        if trend_text:
            final_insights += f"### Strategic Trends\n{trend_text}\n\n---\n"
        if explanation_text:
            final_insights += f"### Data Summary\n{explanation_text}"
        if not final_insights:
            final_insights = "Query executed. No additional insights generated."

        chart_spec = results.get('chart_spec', '')
        chart = None
        if chart_spec:
            try:
                cs = chart_spec.strip()
                if '<thinking_process>' in cs:
                    cs = cs.split('</thinking_process>')[-1].strip()
                cs = cs.replace("```python", "").replace("```", "").strip()
                if cs and not cs.startswith('<') and 'import' in cs.lower():
                    ns = {'alt': alt, 'pd': pd, 'df': df, 'data': df.to_dict(orient='records')}
                    exec(cs, ns)
                    chart = ns.get('chart')
            except Exception as e:
                print(f"Chart warning: {e}")

        return sql_query, df, chart, final_insights

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        import traceback; traceback.print_exc()
        return error_msg, None, None, error_msg


def create_no_data_chart():
    data = pd.DataFrame({'message': ['No data returned for this query']})
    return (
        alt.Chart(data)
        .mark_text(size=13, color='#2a3f58', font='DM Mono')
        .encode(text='message:N')
        .properties(width=500, height=300, title="VISUAL OUTPUT")
        .configure_view(strokeWidth=0, fill='#111827')
        .configure_title(font='DM Mono', fontSize=10, color='#2a3f58', anchor='start')
    )


def process_request(message: str):
    global current_df_storage
    try:
        sql_query, df, chart, explanation = asyncio.run(process_request_async(message))
        if df is None or df.empty:
            current_df_storage = None
            return sql_query, df, create_no_data_chart(), explanation
        current_df_storage = df
        return sql_query, df, chart, explanation
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        return error_msg, None, None, error_msg


def download_query_results() -> str:
    global current_df_storage
    if current_df_storage is None or current_df_storage.empty:
        return "No data available. Run a query first."
    try:
        temp_dir = tempfile.gettempdir()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(temp_dir, f"query_results_{ts}.csv")
        current_df_storage.to_csv(path, index=False, encoding='utf-8')
        return path
    except Exception as e:
        return f"Export error: {str(e)}"


# ============================================================================
# Gradio UI — Corporate Dark Layout
# ============================================================================

PIPELINE_DESC = """
`01` Text-to-SQL &nbsp;|&nbsp; `02` SQL Executor &nbsp;|&nbsp; `03` Trend Analyst &nbsp;|&nbsp; `04` Visualization &nbsp;|&nbsp; `05` Explanation

*Credentials configured in* `bi_agent/.env`
"""

with gr.Blocks(css=css, theme=gr.themes.Base()) as demo:

    demo.load(None, js=js_code)

    gr.Markdown(PIPELINE_DESC)
    gr.Markdown("---")

    # ── Input ──────────────────────────────────────────────────────────────
    with gr.Row():
        user_input = gr.Textbox(
            label="Query Input",
            placeholder="Enter a natural language question about your data...",
            lines=3
        )

    with gr.Row():
        submit_btn = gr.Button("▶  Run Analysis", variant="primary")
        clear_btn  = gr.Button("✕  Clear",         variant="secondary")

    gr.Markdown("---")
    gr.Markdown("## Output")

    # ── Row 1: SQL + Table ─────────────────────────────────────────────────
    with gr.Row():
        with gr.Column(elem_classes="result-card"):
            gr.Markdown("### Generated SQL")
            sql_output = gr.Code(
                label="SQL Query", language="sql",
                value="-- Awaiting query..."
            )
        with gr.Column(elem_classes="result-card"):
            gr.Markdown("### Query Results")
            data_output   = gr.DataFrame(label="Data Table", wrap=True)
            download_btn  = gr.Button("↓  Export CSV", variant="secondary", size="sm")
            download_file = gr.File(label="CSV Export", interactive=False)

    # ── Row 2: Chart + Insights ────────────────────────────────────────────
    with gr.Row():
        with gr.Column(elem_classes="result-card"):
            gr.Markdown("### Visualization")
            chart_output = gr.Plot(label="Chart")
        with gr.Column(elem_classes="result-card"):
            gr.Markdown("### Intelligence Report")
            explanation_output = gr.Markdown(value="*Awaiting analysis output...*")

    # ── Export ─────────────────────────────────────────────────────────────
    gr.Markdown("---")
    with gr.Row():
        export_btn  = gr.Button("⬡  Generate PDF Report")
        file_output = gr.File(label="PDF Report")

    export_btn.click(
        fn=generate_report_pdf,
        inputs=[user_input, sql_output, data_output, explanation_output],
        outputs=file_output
    )

    # ── Examples ───────────────────────────────────────────────────────────
    gr.Examples(
        examples=[
            ["What are the top 10 products by transfer price?"],
            ["Show me the product categories and their average prices"],
            ["List all products in the Bikes category"],
            ["How many products are there in each category?"],
            ["What is the most expensive product?"],
        ],
        inputs=user_input
    )

    # ── Wiring ─────────────────────────────────────────────────────────────
    submit_btn.click(
        fn=process_request,
        inputs=[user_input],
        outputs=[sql_output, data_output, chart_output, explanation_output]
    )
    clear_btn.click(
        fn=lambda: ("", "-- Awaiting query...", None, None, "*Awaiting analysis output...*"),
        inputs=None,
        outputs=[user_input, sql_output, data_output, chart_output, explanation_output]
    )
    download_btn.click(
        fn=download_query_results,
        inputs=None,
        outputs=download_file
    )


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Base())