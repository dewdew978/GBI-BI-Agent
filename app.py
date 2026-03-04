# """
# Gradio UI for the Business Intelligence Agent Pipeline.

# This app demonstrates Google ADK's SequentialAgent pattern:
# 1. Text-to-SQL Agent (standalone)
# 2. SQL execution via BIService
# 3. Insight Pipeline (SequentialAgent: Visualization → Explanation)
# """

# import gradio as gr
# import asyncio
# import os
# import pandas as pd
# import altair as alt
# from dotenv import load_dotenv
# from google.genai import types
# import tempfile
# import random
# from datetime import datetime
# # Import root agent runner
# from bi_agent import root_runner
# from bi_agent.tools import generate_report_pdf

# # Global variable to store current dataframe for download
# current_df_storage = None

# # Load environment variables from bi_agent/.env
# load_dotenv(dotenv_path='bi_agent/.env')

# js_code = """
# function createGradioAnimation() {
#     // Add font from Google Fonts
#     const link = document.createElement('link');
#     link.href = 'https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600;700&display=swap';
#     link.rel = 'stylesheet';
#     document.head.appendChild(link);
    
#     // Add global CSS style
#     const style = document.createElement('style');
#     style.innerHTML = '* { font-family: "Source Code Pro", monospace !important; }';
#     document.head.appendChild(style);
    
#     var container = document.createElement('div');
#     container.id = 'gradio-animation';
#     container.style.fontSize = '2em';
#     container.style.fontWeight = 'bold';
#     container.style.textAlign = 'center';
#     container.style.marginTop = '30px';
#     container.style.marginBottom = '20px';
#     container.style.color = '#FFFFFF';
#     container.style.fontFamily = "'Source Code Pro', monospace";

#     var text = 'Welcome to Business Intelligence Agent (Google ADK)'; 
#         for (var i = 0; i < text.length; i++) {
#             (function(i){
#                 setTimeout(function(){
#                     var letter = document.createElement('span');
#                     letter.style.opacity = '0';
#                     letter.style.transition = 'opacity 0.5s ease-in-out';
#                     letter.style.display = 'inline-block';
                    
#                     if (text[i] === ' ') {
#                         letter.innerHTML = '&nbsp;'; 
#                     } else {
#                         letter.innerText = text[i];
#                     }
#                     container.appendChild(letter);
#                     setTimeout(function() { letter.style.opacity = '1'; }, 50);
#                 }, i * 100);
#             })(i);
#         }

#         var gradioContainer = document.querySelector('.gradio-container');
#         if (gradioContainer) {
#             gradioContainer.insertBefore(container, gradioContainer.firstChild);
#         }
#         return 'Animation Created';
#     }
#     """
# css = """
# @import url('https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600;700&display=swap');

# * { font-family: ''Source Code Pro'', sans-serif !important; }

# .result-card {
#     background: #1a1a1a !important;
#     border-radius: 12px !important;
#     padding: 15px !important;
#     border: 1px solid #333 !important;
# }
# """
# async def run_bi_pipeline_async(user_question: str):
#     """
#     Run the complete BI pipeline using root_runner.

#     This function executes the entire BI pipeline:
#     1. Text-to-SQL: Generate SQL from question
#     2. SQL Execution: Execute query against database
#     3. Data Formatting: Prepare results
#     4. Visualization: Generate Altair chart
#     5. Explanation: Provide plain-language insights

#     Args:
#         user_question: Natural language question from the user

#     Returns:
#         Dictionary with keys: sql_query, query_results, chart_spec, explanation_text
#     """
#     # Create session
#     session = await root_runner.session_service.create_session(
#         user_id='user',
#         app_name='bi_agent'
#     )

#     # Create user message
#     content = types.Content(
#         role='user',
#         parts=[types.Part(text=user_question)]
#     )

#     # Run the complete pipeline
#     events_async = root_runner.run_async(
#         user_id='user',
#         session_id=session.id,
#         new_message=content
#     )

#     # Extract results from state
#     results = {}
#     async for event in events_async:
#         if event.actions and event.actions.state_delta:
#             for key, value in event.actions.state_delta.items():
#                 results[key] = value

#     return results


# async def process_request_async(message: str):
#     """
#     Process user request through the BI pipeline using root_runner.

#     The root_agent handles the complete pipeline:
#     1. Text-to-SQL Agent → Generates SQL from question
#     2. SQL Executor Agent → Executes SQL against database
#     3. Data Formatter Agent → Formats results
#     4. Insight Pipeline → Visualization + Explanation

#     Args:
#         message: User's natural language question

#     Returns:
#         Tuple of (sql_query, df, chart, explanation_text)
#     """
    
#     try:
#         # Validate input
#         if not message.strip():
#             return "Error: Please enter a question", None, None, "Error: No question provided"

#         # Run the complete BI pipeline
#         results = await run_bi_pipeline_async(message)

#         # Extract SQL query
#         sql_query = results.get('sql_query', '')

#         # --- เพิ่ม Logic เพื่อตัด Thinking Process ออกจาก SQL ---
#         if '</thinking_process>' in sql_query:
#             sql_query = sql_query.split('</thinking_process>')[-1].strip()
#         # Clean up SQL query (remove markdown if present)
#         sql_query = sql_query.strip()
#         if sql_query.startswith("```sql"):
#             sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
#         elif sql_query.startswith("```"):
#             sql_query = sql_query.replace("```", "").strip()

#         # Extract query results
#         query_results_str = results.get('query_results', '{}')
#         print(f"DEBUG: query_results_str = {repr(query_results_str)}")

#         query_results = {'success': False, 'data': [], 'error': 'Uninitialized'} 

#         try:
#             import json
#             import re
            
#             raw_str = str(query_results_str).strip()
            
#             # Method 1: Try parsing as JSON
#             clean_json = re.sub(r'^```[a-z]*\s*', '', raw_str, flags=re.IGNORECASE)
#             clean_json = re.sub(r'\s*```$', '', clean_json)
            
#             parsed_json = json.loads(clean_json)
            
#             if isinstance(parsed_json, list):
#                 query_results = {'success': True, 'data': parsed_json}
#             else:
#                 query_results = parsed_json

#         except Exception as e_json:
#             print(f"⚠️ Not valid JSON, trying to parse Markdown Table...")
            
#             # Method 2: Try parsing markdown table
#             try:
#                 lines = raw_str.split('\n')
#                 table_lines = [line.strip() for line in lines if '|' in line and line.strip()]
                
#                 if len(table_lines) >= 3:  # Header, separator, at least 1 data row
#                     headers = [h.strip() for h in table_lines[0].strip('|').split('|')]
#                     headers = [h.replace('\\_', '_') for h in headers]  # Remove escaping
#                     data_list = []
                    
#                     for line in table_lines[2:]:  # Skip separator
#                         if line.startswith(':') or '---' in line:
#                             continue
#                         values = [v.strip() for v in line.strip('|').split('|')]
#                         if len(values) == len(headers) and values != headers:
#                             row_dict = {}
#                             for i, header in enumerate(headers):
#                                 val = values[i] if i < len(values) else ''
#                                 # Try to convert to numeric
#                                 try:
#                                     row_dict[header] = float(val)
#                                 except (ValueError, TypeError):
#                                     row_dict[header] = val
#                             data_list.append(row_dict)
                    
#                     if data_list:
#                         query_results = {
#                             'success': True, 
#                             'data': data_list
#                         }
#                         print(f"✅ Successfully parsed Markdown Table ({len(data_list)} rows)")
#                     else:
#                         raise ValueError("No data rows extracted from table")
#                 else:
#                     raise ValueError(f"Invalid table format: found {len(table_lines)} lines")

#             except Exception as e_table:
#                 print(f"⚠️ Markdown parsing failed: {e_table}")
#                 print(f"⚠️ Raw result: {raw_str[:200]}")
                
#                 # Method 3: If it's plain text, treat as error message
#                 query_results = {
#                     'success': False, 
#                     'data': [], 
#                     'error': f'Could not parse query results. Output: {raw_str[:100]}'
#                 }
#         # Check if query execution was successful
#         if not query_results.get('success', False):
#             error_msg = query_results.get('error', 'Unknown error')
#             sql_query = f"-- Error executing query\n{sql_query}\n\n-- Error: {error_msg}"
#             return sql_query, None, None, f"Error executing query: {error_msg}"

#         # Convert query results to DataFrame
#         data_list = query_results.get('data', [])
#         if not data_list:
#             df = pd.DataFrame()
#             return sql_query, df, None, "The query executed successfully but returned no data."

#         df = pd.DataFrame(data_list)

#         # --- ส่วนที่แก้ไข: ดึงค่าจาก Trend Analyst และ Explanation Agent ---
#         trend_text = results.get('trend_insights', '')
#         explanation_text = results.get('explanation_text', '')

#         # รวมข้อความ Insights เข้าด้วยกัน
#         final_insights = ""
#         if trend_text:
#             final_insights += f"### 📈 Strategic Trends\n{trend_text}\n\n---\n"
        
#         if explanation_text:
#             final_insights += f"### 💡 Data Summary\n{explanation_text}"
        
#         if not final_insights:
#             final_insights = "The query executed successfully but no additional insights were generated."

#         # Extract chart specification and explanation
#         chart_spec = results.get('chart_spec', '')
#         explanation_text = results.get('explanation_text', '')

#         # Execute chart specification
#         chart = None
#         if chart_spec:
#             try:
#                 chart_spec_clean = chart_spec.strip()
                
#                 # Remove thinking process blocks
#                 if '<thinking_process>' in chart_spec_clean:
#                     parts = chart_spec_clean.split('</thinking_process>')
#                     chart_spec_clean = parts[-1].strip() if len(parts) > 1 else chart_spec_clean
                
#                 # Remove markdown code blocks
#                 chart_spec_clean = chart_spec_clean.replace("```python", "").replace("```", "").strip()
                
#                 # Skip if no valid code found
#                 if not chart_spec_clean or chart_spec_clean.startswith('<') or 'import' not in chart_spec_clean.lower():
#                     print("No valid chart code found, skipping chart generation")
#                     chart = None
#                 else:
#                     namespace = {
#                         'alt': alt,
#                         'pd': pd,
#                         'df': df,
#                         'data': df.to_dict(orient='records')
#                     }
#                     exec(chart_spec_clean, namespace)
#                     chart = namespace.get('chart')
#                     if chart:
#                         print("Chart generated successfully")
#                     else:
#                         print("Chart variable not found in executed code")
                        
#             except SyntaxError as e:
#                 print(f"Chart syntax error: {e}")
#             except Exception as e:
#                 print(f"Chart generation warning: {e}")

#         # Return all four outputs
#         return sql_query, df, chart, final_insights

#     except Exception as e:
#         error_msg = f"Error: {str(e)}"
#         print(f"Full error: {e}")
#         import traceback
#         traceback.print_exc()
#         return error_msg, None, None, error_msg
# def create_no_data_chart():
#     "Create a simulated graph to inform the user that there is no data to display."
#     import altair as alt
#     import pandas as pd
    
#     # Create a fake DataFrame with a warning message.
#     data = pd.DataFrame({'message': ['No Data to Display for this Query']})
    
#     # Create a text graph in the center.
#     chart = alt.Chart(data).mark_text(
#         size=18, 
#         color='#718096',
#         fontWeight=500,
#         font='Source Code Pro'
#     ).encode(
#         text='message:N'
#     ).properties(
#         width=500,
#         height=300,
#         title="Visual Insight Summary"
#     ).configure_view(
#         strokeWidth=0 
#     )
#     return chart

# def process_request(message: str):
#     """
#     Synchronous wrapper for Gradio.

#     Database credentials are read from environment variables in bi_agent/.env
#     """
#     global current_df_storage
#     try:
#         sql_query, df, chart, explanation = asyncio.run(
#             process_request_async(message)
#         )
#         # Managing Empty Data
#         if df is None or df.empty:
#             # If no data is available, submit a Placeholder graph instead. (None)
#             no_data_chart = create_no_data_chart()
#             current_df_storage = None
#             return sql_query, df, no_data_chart, explanation
#         # Store dataframe for download
#         current_df_storage = df
#         print(f"DEBUG: Stored dataframe with {len(df) if df is not None else 0} rows")
#         return sql_query, df, chart, explanation
#     except Exception as e:
#         error_msg = f"Error: {str(e)}"
#         return error_msg, None, None, error_msg


# def download_query_results() -> str:
#     """
#     Download query results as CSV file.

#     Returns:
#         File path to the CSV file
#     """
#     global current_df_storage
    
#     print(f"DEBUG: download_query_results called")
#     print(f"DEBUG: current_df_storage is None: {current_df_storage is None}")
    
#     if current_df_storage is None or current_df_storage.empty:
#         error_msg = "No data to download. Please run a query first."
#         print(f"DEBUG: {error_msg}")
#         return error_msg
    
#     try:
#         # Create temp CSV file
#         temp_dir = tempfile.gettempdir()
#         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         csv_filename = f"query_results_{timestamp}.csv"
#         csv_path = os.path.join(temp_dir, csv_filename)
        
#         # Save dataframe to CSV
#         current_df_storage.to_csv(csv_path, index=False, encoding='utf-8')
        
#         print(f"DEBUG: CSV file created at {csv_path}")
#         print(f"DEBUG: File size: {os.path.getsize(csv_path)} bytes")
#         return csv_path
#     except Exception as e:
#         error_msg = f"Error downloading file: {str(e)}"
#         print(f"DEBUG: {error_msg}")
#         return error_msg
    


# # ============================================================================
# # Gradio UI
# # ============================================================================

# with gr.Blocks(css=css, theme=gr.themes.Monochrome()) as demo:
#     gr.Markdown("""

#     This demo uses **Google ADK's root_agent SequentialAgent**:

#     1. **Text-to-SQL Agent** → Generates SQL from natural language
#     2. **SQL Executor Agent** → Executes SQL against database
#     3. **Trend Analyst Agent** → Analyze what "significant" aspects of the data have in a business context.
#     4. **Insight Pipeline** (**SequentialAgent**) → Visualization Agent → Explanation Agent

#     Database credentials are configured in `bi_agent/.env`

#     Enter your question below and click "Analyze Data".
#     """)
#     demo.load(None, js=js_code)
#     with gr.Row():
#         user_input = gr.Textbox(
#             label="Your Question",
#             placeholder="e.g., 'What are the top 10 products by price?'",
#             lines=3
#         )

#     with gr.Row():
#         submit_btn = gr.Button("Analyze Data", variant="primary")
#         clear_btn = gr.Button("Clear")
#     gr.Markdown("---")
#     gr.Markdown("## Results")

#     # Four output panels
#     with gr.Row():
#         with gr.Column(elem_classes="result-card"):
#             gr.Markdown("### Generated SQL")
#             sql_output = gr.Code(
#                 label="SQL Query",
#                 language="sql",
#                 value="-- Waiting for input..."
#             )

#         with gr.Column(elem_classes="result-card"):
#             gr.Markdown("### Query Results")
#             data_output = gr.DataFrame(
#                 label="Data Table",
#                 wrap=True
#             )
#             # Download button and file output for CSV
#             download_btn = gr.Button(" Download as CSV", variant="secondary", size="sm")
#             download_file = gr.File(label="Download CSV", interactive=False)

#     with gr.Row():
#         with gr.Column(elem_classes="result-card"):
#             gr.Markdown("### Visualization")
#             chart_output = gr.Plot(label="Chart")

#         with gr.Column(elem_classes="result-card"):
#             gr.Markdown("### Insights")
#             explanation_output = gr.Markdown(
#                 value="*Waiting for input...*"
#             )
#     with gr.Row():
#         export_btn = gr.Button("Export to PDF Report")
#         file_output = gr.File(label="Download Report")

#     # เชื่อมต่อฟังก์ชัน (ตัวอย่างการเรียกใช้)
#     export_btn.click(
#         fn=generate_report_pdf,
#         inputs=[user_input, sql_output, data_output, explanation_output],
#         outputs=file_output
#     )
    
#     # Examples
#     gr.Examples(
#         examples=[
#             ["What are the top 10 products by transfer price?"],
#             ["Show me the product categories and their average prices"],
#             ["List all products in the Bikes category"],
#             ["How many products are there in each category?"],
#             ["What is the most expensive product?"],
#         ],
#         inputs=user_input
#     )

#     # Button actions
#     submit_btn.click(
#         fn=process_request,
#         inputs=[user_input],
#         outputs=[sql_output, data_output, chart_output, explanation_output]
#     )

#     clear_btn.click(
#         fn=lambda: (
#             "",
#             "-- Waiting for input...",
#             None,
#             None,
#             "*Waiting for input...*"
#         ),
#         inputs=None,
#         outputs=[user_input, sql_output, data_output, chart_output, explanation_output]
#     )

#     # Download CSV button action
#     download_btn.click(
#         fn=download_query_results,
#         inputs=None,
#         outputs=download_file
#     )
#     if __name__ == "__main__":
#         demo.launch(theme=gr.themes.Monochrome())

# """
# Gradio UI for the Business Intelligence Agent Pipeline — Cyberpunk/Neon Redesign

# This app demonstrates Google ADK's SequentialAgent pattern:
# 1. Text-to-SQL Agent (standalone)
# 2. SQL execution via BIService
# 3. Insight Pipeline (SequentialAgent: Visualization → Explanation)
# """

# import gradio as gr
# import asyncio
# import os
# import pandas as pd
# import altair as alt
# from dotenv import load_dotenv
# from google.genai import types
# import tempfile
# import random
# from datetime import datetime
# # Import root agent runner
# from bi_agent import root_runner
# from bi_agent.tools import generate_report_pdf

# # Global variable to store current dataframe for download
# current_df_storage = None

# # Load environment variables from bi_agent/.env
# load_dotenv(dotenv_path='bi_agent/.env')

# # ============================================================================
# # Cyberpunk / Neon JS — Animated Header + Scanline Overlay + Loading
# # ============================================================================
# js_code = """
# function createGradioAnimation() {
#     // ── Fonts ──────────────────────────────────────────────────────────────
#     const link = document.createElement('link');
#     link.href = 'https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700;900&display=swap';
#     link.rel = 'stylesheet';
#     document.head.appendChild(link);

#     // ── Global style override ──────────────────────────────────────────────
#     const style = document.createElement('style');
#     style.innerHTML = `
#         * { font-family: 'Share Tech Mono', monospace !important; }

#         /* scanline overlay */
#         body::before {
#             content: '';
#             position: fixed;
#             inset: 0;
#             background: repeating-linear-gradient(
#                 0deg,
#                 transparent,
#                 transparent 2px,
#                 rgba(0,255,255,0.03) 2px,
#                 rgba(0,255,255,0.03) 4px
#             );
#             pointer-events: none;
#             z-index: 9999;
#         }

#         /* neon cursor */
#         * { cursor: crosshair !important; }

#         /* glitch keyframes */
#         @keyframes glitch {
#             0%   { text-shadow: 2px 0 #ff00ff, -2px 0 #00ffff; }
#             20%  { text-shadow: -3px 0 #ff00ff,  3px 0 #00ffff; clip-path: inset(10% 0 80% 0); }
#             40%  { text-shadow:  3px 2px #ff00ff, -3px -2px #00ffff; }
#             60%  { text-shadow: -2px 0 #ff00ff,  2px 0 #00ffff; clip-path: inset(50% 0 30% 0); }
#             80%  { text-shadow:  1px 0 #ff00ff, -1px 0 #00ffff; }
#             100% { text-shadow:  2px 0 #ff00ff, -2px 0 #00ffff; clip-path: none; }
#         }

#         @keyframes neonPulse {
#             0%, 100% { opacity: 1; }
#             50%       { opacity: 0.7; }
#         }

#         @keyframes borderFlow {
#             0%   { border-color: #00ffff; box-shadow: 0 0 8px #00ffff, inset 0 0 8px rgba(0,255,255,0.05); }
#             33%  { border-color: #ff00ff; box-shadow: 0 0 8px #ff00ff, inset 0 0 8px rgba(255,0,255,0.05); }
#             66%  { border-color: #00ff88; box-shadow: 0 0 8px #00ff88, inset 0 0 8px rgba(0,255,136,0.05); }
#             100% { border-color: #00ffff; box-shadow: 0 0 8px #00ffff, inset 0 0 8px rgba(0,255,255,0.05); }
#         }

#         @keyframes typeCaret {
#             0%, 100% { opacity: 1; }
#             50%       { opacity: 0; }
#         }

#         /* spinner used by loading overlay */
#         @keyframes spinNeon {
#             to { transform: rotate(360deg); }
#         }

#         /* loading overlay */
#         #bi-loading-overlay {
#             display: none;
#             position: fixed;
#             inset: 0;
#             background: rgba(0,0,0,0.82);
#             z-index: 10000;
#             flex-direction: column;
#             align-items: center;
#             justify-content: center;
#             gap: 24px;
#         }
#         #bi-loading-overlay.visible { display: flex; }

#         #bi-loading-overlay .spinner {
#             width: 72px; height: 72px;
#             border: 4px solid #111;
#             border-top-color: #00ffff;
#             border-right-color: #ff00ff;
#             border-radius: 50%;
#             animation: spinNeon 0.8s linear infinite;
#             box-shadow: 0 0 24px #00ffff;
#         }
#         #bi-loading-overlay .load-text {
#             font-family: 'Orbitron', monospace !important;
#             color: #00ffff;
#             font-size: 1rem;
#             letter-spacing: 4px;
#             text-transform: uppercase;
#             animation: neonPulse 1.2s ease-in-out infinite;
#             text-shadow: 0 0 12px #00ffff;
#         }
#         #bi-loading-overlay .load-sub {
#             color: #ff00ff88;
#             font-size: 0.72rem;
#             letter-spacing: 2px;
#         }
#     `;
#     document.head.appendChild(style);

#     // ── Loading overlay ───────────────────────────────────────────────────
#     const overlay = document.createElement('div');
#     overlay.id = 'bi-loading-overlay';
#     overlay.innerHTML = `
#         <div class="spinner"></div>
#         <div class="load-text">PROCESSING QUERY</div>
#         <div class="load-sub">[ NEURAL NET ACTIVE... ]</div>
#     `;
#     document.body.appendChild(overlay);

#     // hook into Gradio's queue activity via MutationObserver on status badge
#     const showOverlay  = () => overlay.classList.add('visible');
#     const hideOverlay  = () => overlay.classList.remove('visible');

#     const statusObs = new MutationObserver(() => {
#         const badge = document.querySelector('.progress-level-inner, .generating');
#         if (badge) showOverlay(); else hideOverlay();
#     });
#     statusObs.observe(document.body, { childList: true, subtree: true });

#     // also hook submit button directly
#     setTimeout(() => {
#         const btn = document.querySelector('button.primary');
#         if (btn) {
#             btn.addEventListener('click', () => {
#                 showOverlay();
#                 setTimeout(hideOverlay, 500); // fallback
#             });
#         }
#     }, 2000);

#     // ── Animated Hero Banner ──────────────────────────────────────────────
#     const banner = document.createElement('div');
#     banner.id = 'cyber-banner';
#     banner.style.cssText = `
#         background: linear-gradient(135deg, #0a0a0f 0%, #0d0620 50%, #080d1a 100%);
#         border-bottom: 1px solid #00ffff44;
#         padding: 36px 24px 28px;
#         text-align: center;
#         position: relative;
#         overflow: hidden;
#     `;

#     // grid bg inside banner
#     banner.innerHTML = `
#         <div style="
#             position:absolute;inset:0;
#             background-image:
#                 linear-gradient(rgba(0,255,255,0.07) 1px, transparent 1px),
#                 linear-gradient(90deg, rgba(0,255,255,0.07) 1px, transparent 1px);
#             background-size: 40px 40px;
#             pointer-events:none;
#         "></div>

#         <div style="position:relative;z-index:2;">
#             <div id="banner-tag" style="
#                 display:inline-block;
#                 color:#ff00ff;
#                 font-size:0.65rem;
#                 letter-spacing:5px;
#                 text-transform:uppercase;
#                 margin-bottom:10px;
#                 opacity:0.8;
#             ">// GOOGLE ADK — SEQUENTIAL AGENT PIPELINE //</div>

#             <h1 id="banner-title" style="
#                 font-family:'Orbitron',monospace !important;
#                 font-size:clamp(1.4rem,3.5vw,2.6rem);
#                 font-weight:900;
#                 color:#00ffff;
#                 letter-spacing:3px;
#                 text-transform:uppercase;
#                 margin:0 0 8px;
#                 animation: glitch 6s infinite, neonPulse 3s ease-in-out infinite;
#                 text-shadow: 0 0 20px #00ffff, 0 0 40px #00ffff88;
#             ">Business Intelligence Agent</h1>

#             <div id="banner-sub" style="
#                 color:#00ff8899;
#                 font-size:0.78rem;
#                 letter-spacing:3px;
#                 margin-top:4px;
#             ">TEXT-TO-SQL &nbsp;▸&nbsp; EXECUTE &nbsp;▸&nbsp; TREND ANALYSIS &nbsp;▸&nbsp; VISUALIZE &nbsp;▸&nbsp; EXPLAIN</div>
#         </div>
#     `;

#     const gradioContainer = document.querySelector('.gradio-container');
#     if (gradioContainer) {
#         gradioContainer.insertBefore(banner, gradioContainer.firstChild);
#     }

#     return 'Cyberpunk Init Complete';
# }
# """

# # ============================================================================
# # Cyberpunk / Neon CSS
# # ============================================================================
# css = """
# @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700;900&display=swap');

# /* ── Base ──────────────────────────────────────────────────────────────── */
# *, *::before, *::after {
#     font-family: 'Share Tech Mono', monospace !important;
#     box-sizing: border-box;
# }

# body, .gradio-container {
#     background: #07070f !important;
#     color: #c0f0ff !important;
# }

# /* ── Cards ─────────────────────────────────────────────────────────────── */
# .result-card {
#     background: #0c0c1a !important;
#     border-radius: 6px !important;
#     padding: 18px !important;
#     border: 1px solid #00ffff55 !important;
#     animation: borderFlow 5s linear infinite !important;
#     position: relative;
#     overflow: hidden;
# }
# .result-card::before {
#     content: '';
#     position: absolute;
#     inset: 0;
#     background: linear-gradient(135deg, rgba(0,255,255,0.03) 0%, transparent 60%);
#     pointer-events: none;
# }

# /* ── Inputs ─────────────────────────────────────────────────────────────── */
# textarea, input[type="text"] {
#     background: #0a0a18 !important;
#     border: 1px solid #00ffff66 !important;
#     color: #00ffff !important;
#     border-radius: 4px !important;
#     padding: 10px 14px !important;
#     caret-color: #ff00ff !important;
#     transition: border-color 0.3s, box-shadow 0.3s !important;
# }
# textarea:focus, input[type="text"]:focus {
#     border-color: #ff00ff !important;
#     box-shadow: 0 0 14px rgba(255,0,255,0.35) !important;
#     outline: none !important;
# }
# textarea::placeholder, input::placeholder { color: #00ffff55 !important; }

# /* ── Primary Button (Analyze Data) ─────────────────────────────────────── */
# button.primary, button[variant="primary"] {
#     background: transparent !important;
#     border: 2px solid #00ffff !important;
#     color: #00ffff !important;
#     font-family: 'Orbitron', monospace !important;
#     font-size: 0.78rem !important;
#     letter-spacing: 3px !important;
#     text-transform: uppercase !important;
#     padding: 12px 28px !important;
#     border-radius: 4px !important;
#     position: relative;
#     overflow: hidden;
#     transition: all 0.25s ease !important;
#     cursor: crosshair !important;
#     box-shadow: 0 0 12px rgba(0,255,255,0.3), inset 0 0 12px rgba(0,255,255,0.05) !important;
# }
# button.primary::before, button[variant="primary"]::before {
#     content: '';
#     position: absolute;
#     inset: 0;
#     background: linear-gradient(90deg, transparent, rgba(0,255,255,0.12), transparent);
#     transform: translateX(-100%);
#     transition: transform 0.4s ease;
# }
# button.primary:hover::before, button[variant="primary"]:hover::before {
#     transform: translateX(100%);
# }
# button.primary:hover, button[variant="primary"]:hover {
#     background: rgba(0,255,255,0.08) !important;
#     box-shadow: 0 0 24px rgba(0,255,255,0.6), inset 0 0 20px rgba(0,255,255,0.1) !important;
#     color: #fff !important;
# }
# button.primary:active, button[variant="primary"]:active {
#     transform: scale(0.97) !important;
# }

# /* ── Secondary Buttons (Clear, Download, Export) ───────────────────────── */
# button.secondary, button[variant="secondary"] {
#     background: transparent !important;
#     border: 1px solid #ff00ff88 !important;
#     color: #ff00ff !important;
#     font-size: 0.72rem !important;
#     letter-spacing: 2px !important;
#     text-transform: uppercase !important;
#     border-radius: 4px !important;
#     padding: 9px 18px !important;
#     transition: all 0.25s ease !important;
#     box-shadow: 0 0 8px rgba(255,0,255,0.2) !important;
#     cursor: crosshair !important;
# }
# button.secondary:hover, button[variant="secondary"]:hover {
#     background: rgba(255,0,255,0.1) !important;
#     box-shadow: 0 0 18px rgba(255,0,255,0.5) !important;
#     border-color: #ff00ff !important;
#     color: #fff !important;
# }

# /* ── Export PDF Button ──────────────────────────────────────────────────── */
# button:not(.primary):not(.secondary) {
#     background: transparent !important;
#     border: 1px solid #00ff8866 !important;
#     color: #00ff88 !important;
#     border-radius: 4px !important;
#     letter-spacing: 2px !important;
#     transition: all 0.25s !important;
#     box-shadow: 0 0 8px rgba(0,255,136,0.15) !important;
# }
# button:not(.primary):not(.secondary):hover {
#     background: rgba(0,255,136,0.1) !important;
#     box-shadow: 0 0 18px rgba(0,255,136,0.4) !important;
#     border-color: #00ff88 !important;
#     color: #fff !important;
# }

# /* ── Code block (SQL output) ────────────────────────────────────────────── */
# .code-wrap, .codemirror-wrapper, code, pre {
#     background: #060610 !important;
#     border: 1px solid #00ffff33 !important;
#     color: #00ff88 !important;
#     border-radius: 4px !important;
# }

# /* ── DataFrame table ────────────────────────────────────────────────────── */
# table { border-collapse: collapse !important; width: 100% !important; }
# thead tr { background: #0d0d22 !important; }
# thead th {
#     color: #ff00ff !important;
#     border-bottom: 1px solid #ff00ff55 !important;
#     padding: 8px 12px !important;
#     font-size: 0.75rem !important;
#     letter-spacing: 1px !important;
#     text-transform: uppercase !important;
# }
# tbody tr { background: #09091a !important; transition: background 0.15s !important; }
# tbody tr:hover { background: rgba(0,255,255,0.06) !important; }
# tbody td {
#     border-bottom: 1px solid #ffffff10 !important;
#     color: #aaddff !important;
#     padding: 7px 12px !important;
#     font-size: 0.78rem !important;
# }

# /* ── Markdown headings in Insights ─────────────────────────────────────── */
# .result-card h1, .result-card h2, .result-card h3 {
#     font-family: 'Orbitron', monospace !important;
#     color: #00ffff !important;
#     text-shadow: 0 0 10px #00ffff88 !important;
#     border-bottom: 1px solid #00ffff33 !important;
#     padding-bottom: 6px !important;
#     margin-top: 14px !important;
# }
# .result-card p, .result-card li {
#     color: #b0d8f0 !important;
#     line-height: 1.7 !important;
# }
# .result-card strong {
#     color: #ff00ff !important;
#     text-shadow: 0 0 8px #ff00ff66 !important;
# }
# .result-card hr {
#     border-color: #00ffff22 !important;
#     margin: 14px 0 !important;
# }
# .result-card em { color: #00ff88 !important; font-style: normal !important; }

# /* ── Section headers inside app ─────────────────────────────────────────── */
# .gradio-container h3 {
#     font-family: 'Orbitron', monospace !important;
#     color: #00ffff !important;
#     font-size: 0.82rem !important;
#     letter-spacing: 3px !important;
#     text-transform: uppercase !important;
#     text-shadow: 0 0 10px rgba(0,255,255,0.5) !important;
# }

# /* ── Gradio description block ───────────────────────────────────────────── */
# .gr-prose, .prose { color: #00ffff88 !important; font-size: 0.78rem !important; }

# /* ── Labels ─────────────────────────────────────────────────────────────── */
# label span { color: #00ffff99 !important; font-size: 0.72rem !important; letter-spacing: 1px !important; }

# /* ── File component ─────────────────────────────────────────────────────── */
# .file-preview { background: #0a0a18 !important; border-color: #00ff8855 !important; }

# /* ── Tabs (if any) ──────────────────────────────────────────────────────── */
# .tab-nav button {
#     border-bottom: 2px solid transparent !important;
#     color: #00ffff88 !important;
# }
# .tab-nav button.selected {
#     border-bottom-color: #00ffff !important;
#     color: #00ffff !important;
# }

# /* ── Scrollbar ──────────────────────────────────────────────────────────── */
# ::-webkit-scrollbar { width: 6px; height: 6px; }
# ::-webkit-scrollbar-track { background: #0a0a18; }
# ::-webkit-scrollbar-thumb { background: #00ffff55; border-radius: 3px; }
# ::-webkit-scrollbar-thumb:hover { background: #00ffff; }

# /* ── Examples ───────────────────────────────────────────────────────────── */
# .examples-holder button {
#     background: #0d0d20 !important;
#     border: 1px solid #00ffff33 !important;
#     color: #00ffff99 !important;
#     font-size: 0.72rem !important;
#     transition: all 0.2s !important;
# }
# .examples-holder button:hover {
#     border-color: #00ffff !important;
#     color: #00ffff !important;
#     box-shadow: 0 0 10px rgba(0,255,255,0.3) !important;
# }
# """

# # ============================================================================
# # Pipeline logic (unchanged)
# # ============================================================================

# async def run_bi_pipeline_async(user_question: str):
#     session = await root_runner.session_service.create_session(
#         user_id='user',
#         app_name='bi_agent'
#     )
#     content = types.Content(
#         role='user',
#         parts=[types.Part(text=user_question)]
#     )
#     events_async = root_runner.run_async(
#         user_id='user',
#         session_id=session.id,
#         new_message=content
#     )
#     results = {}
#     async for event in events_async:
#         if event.actions and event.actions.state_delta:
#             for key, value in event.actions.state_delta.items():
#                 results[key] = value
#     return results


# async def process_request_async(message: str):
#     try:
#         if not message.strip():
#             return "Error: Please enter a question", None, None, "Error: No question provided"

#         results = await run_bi_pipeline_async(message)
#         sql_query = results.get('sql_query', '')

#         if '</thinking_process>' in sql_query:
#             sql_query = sql_query.split('</thinking_process>')[-1].strip()
#         sql_query = sql_query.strip()
#         if sql_query.startswith("```sql"):
#             sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
#         elif sql_query.startswith("```"):
#             sql_query = sql_query.replace("```", "").strip()

#         query_results_str = results.get('query_results', '{}')
#         print(f"DEBUG: query_results_str = {repr(query_results_str)}")

#         query_results = {'success': False, 'data': [], 'error': 'Uninitialized'}

#         try:
#             import json
#             import re

#             raw_str = str(query_results_str).strip()
#             clean_json = re.sub(r'^```[a-z]*\s*', '', raw_str, flags=re.IGNORECASE)
#             clean_json = re.sub(r'\s*```$', '', clean_json)
#             parsed_json = json.loads(clean_json)

#             if isinstance(parsed_json, list):
#                 query_results = {'success': True, 'data': parsed_json}
#             else:
#                 query_results = parsed_json

#         except Exception:
#             try:
#                 lines = raw_str.split('\n')
#                 table_lines = [line.strip() for line in lines if '|' in line and line.strip()]

#                 if len(table_lines) >= 3:
#                     headers = [h.strip() for h in table_lines[0].strip('|').split('|')]
#                     headers = [h.replace('\\_', '_') for h in headers]
#                     data_list = []

#                     for line in table_lines[2:]:
#                         if line.startswith(':') or '---' in line:
#                             continue
#                         values = [v.strip() for v in line.strip('|').split('|')]
#                         if len(values) == len(headers) and values != headers:
#                             row_dict = {}
#                             for i, header in enumerate(headers):
#                                 val = values[i] if i < len(values) else ''
#                                 try:
#                                     row_dict[header] = float(val)
#                                 except (ValueError, TypeError):
#                                     row_dict[header] = val
#                             data_list.append(row_dict)

#                     if data_list:
#                         query_results = {'success': True, 'data': data_list}
#                     else:
#                         raise ValueError("No data rows extracted")
#                 else:
#                     raise ValueError("Invalid table format")

#             except Exception as e_table:
#                 query_results = {
#                     'success': False,
#                     'data': [],
#                     'error': f'Could not parse query results. Output: {raw_str[:100]}'
#                 }

#         if not query_results.get('success', False):
#             error_msg = query_results.get('error', 'Unknown error')
#             sql_query = f"-- Error executing query\n{sql_query}\n\n-- Error: {error_msg}"
#             return sql_query, None, None, f"Error executing query: {error_msg}"

#         data_list = query_results.get('data', [])
#         if not data_list:
#             df = pd.DataFrame()
#             return sql_query, df, None, "The query executed successfully but returned no data."

#         df = pd.DataFrame(data_list)

#         trend_text = results.get('trend_insights', '')
#         explanation_text = results.get('explanation_text', '')

#         final_insights = ""
#         if trend_text:
#             final_insights += f"### 📈 Strategic Trends\n{trend_text}\n\n---\n"
#         if explanation_text:
#             final_insights += f"### 💡 Data Summary\n{explanation_text}"
#         if not final_insights:
#             final_insights = "The query executed successfully but no additional insights were generated."

#         chart_spec = results.get('chart_spec', '')
#         chart = None

#         if chart_spec:
#             try:
#                 chart_spec_clean = chart_spec.strip()
#                 if '<thinking_process>' in chart_spec_clean:
#                     parts = chart_spec_clean.split('</thinking_process>')
#                     chart_spec_clean = parts[-1].strip() if len(parts) > 1 else chart_spec_clean
#                 chart_spec_clean = chart_spec_clean.replace("```python", "").replace("```", "").strip()

#                 if chart_spec_clean and not chart_spec_clean.startswith('<') and 'import' in chart_spec_clean.lower():
#                     namespace = {
#                         'alt': alt,
#                         'pd': pd,
#                         'df': df,
#                         'data': df.to_dict(orient='records')
#                     }
#                     exec(chart_spec_clean, namespace)
#                     chart = namespace.get('chart')

#             except Exception as e:
#                 print(f"Chart generation warning: {e}")

#         return sql_query, df, chart, final_insights

#     except Exception as e:
#         error_msg = f"Error: {str(e)}"
#         import traceback
#         traceback.print_exc()
#         return error_msg, None, None, error_msg


# def create_no_data_chart():
#     data = pd.DataFrame({'message': ['NO DATA FOR THIS QUERY']})
#     chart = alt.Chart(data).mark_text(
#         size=16,
#         color='#00ffff',
#         fontWeight=600,
#         font='Share Tech Mono'
#     ).encode(
#         text='message:N'
#     ).properties(
#         width=500, height=300,
#         title="[ VISUAL INSIGHT MATRIX ]"
#     ).configure_view(strokeWidth=0)
#     return chart


# def process_request(message: str):
#     global current_df_storage
#     try:
#         sql_query, df, chart, explanation = asyncio.run(
#             process_request_async(message)
#         )
#         if df is None or df.empty:
#             current_df_storage = None
#             return sql_query, df, create_no_data_chart(), explanation
#         current_df_storage = df
#         return sql_query, df, chart, explanation
#     except Exception as e:
#         error_msg = f"Error: {str(e)}"
#         return error_msg, None, None, error_msg


# def download_query_results() -> str:
#     global current_df_storage
#     if current_df_storage is None or current_df_storage.empty:
#         return "No data to download. Please run a query first."
#     try:
#         temp_dir = tempfile.gettempdir()
#         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         csv_path = os.path.join(temp_dir, f"query_results_{timestamp}.csv")
#         current_df_storage.to_csv(csv_path, index=False, encoding='utf-8')
#         return csv_path
#     except Exception as e:
#         return f"Error downloading file: {str(e)}"


# # ============================================================================
# # Gradio UI — Cyberpunk Layout
# # ============================================================================

# PIPELINE_DESC = """
# > `01` **Text-to-SQL Agent** → Generates SQL from natural language  
# > `02` **SQL Executor Agent** → Executes SQL against database  
# > `03` **Trend Analyst Agent** → Business context & pattern detection  
# > `04` **Insight Pipeline** *(SequentialAgent)* → Visualization ▸ Explanation  

# Database credentials are configured in `bi_agent/.env`
# """

# with gr.Blocks(css=css, theme=gr.themes.Monochrome()) as demo:

#     demo.load(None, js=js_code)

#     # ── Pipeline description ──────────────────────────────────────────────
#     gr.Markdown(PIPELINE_DESC)

#     gr.Markdown("---")

#     # ── Input row ─────────────────────────────────────────────────────────
#     with gr.Row():
#         user_input = gr.Textbox(
#             label="// QUERY INPUT",
#             placeholder="e.g., 'What are the top 10 products by price?'",
#             lines=3
#         )

#     with gr.Row():
#         submit_btn = gr.Button("⚡  ANALYZE DATA", variant="primary")
#         clear_btn  = gr.Button("✕  CLEAR",          variant="secondary")

#     gr.Markdown("---")
#     gr.Markdown("## [ RESULTS MATRIX ]")

#     # ── Output row 1: SQL + Table ─────────────────────────────────────────
#     with gr.Row():
#         with gr.Column(elem_classes="result-card"):
#             gr.Markdown("### ⟨/⟩ Generated SQL")
#             sql_output = gr.Code(
#                 label="SQL Query",
#                 language="sql",
#                 value="-- Awaiting transmission..."
#             )

#         with gr.Column(elem_classes="result-card"):
#             gr.Markdown("### ▦  Query Results")
#             data_output = gr.DataFrame(label="Data Table", wrap=True)
#             download_btn  = gr.Button("↓  DOWNLOAD CSV", variant="secondary", size="sm")
#             download_file = gr.File(label="CSV Output", interactive=False)

#     # ── Output row 2: Chart + Insights ───────────────────────────────────
#     with gr.Row():
#         with gr.Column(elem_classes="result-card"):
#             gr.Markdown("### ▲  Visualization")
#             chart_output = gr.Plot(label="Chart")

#         with gr.Column(elem_classes="result-card"):
#             gr.Markdown("### ◈  Intelligence Report")
#             explanation_output = gr.Markdown(value="*Awaiting neural analysis...*")

#     # ── Export row ────────────────────────────────────────────────────────
#     with gr.Row():
#         export_btn  = gr.Button("⬡  EXPORT PDF REPORT")
#         file_output = gr.File(label="PDF Report")

#     export_btn.click(
#         fn=generate_report_pdf,
#         inputs=[user_input, sql_output, data_output, explanation_output],
#         outputs=file_output
#     )

#     # ── Examples ─────────────────────────────────────────────────────────
#     gr.Examples(
#         examples=[
#             ["What are the top 10 products by transfer price?"],
#             ["Show me the product categories and their average prices"],
#             ["List all products in the Bikes category"],
#             ["How many products are there in each category?"],
#             ["What is the most expensive product?"],
#         ],
#         inputs=user_input
#     )

#     # ── Button wiring ─────────────────────────────────────────────────────
#     submit_btn.click(
#         fn=process_request,
#         inputs=[user_input],
#         outputs=[sql_output, data_output, chart_output, explanation_output]
#     )

#     clear_btn.click(
#         fn=lambda: ("", "-- Awaiting transmission...", None, None, "*Awaiting neural analysis...*"),
#         inputs=None,
#         outputs=[user_input, sql_output, data_output, chart_output, explanation_output]
#     )

#     download_btn.click(
#         fn=download_query_results,
#         inputs=None,
#         outputs=download_file
#     )


# if __name__ == "__main__":
#     demo.launch(theme=gr.themes.Monochrome())

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