"""
Gradio UI for the Business Intelligence Agent Pipeline.

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
import random
from datetime import datetime
# Import root agent runner
from bi_agent import root_runner
from bi_agent.tools import generate_report_pdf

# Global variable to store current dataframe for download
current_df_storage = None

# Load environment variables from bi_agent/.env
load_dotenv(dotenv_path='bi_agent/.env')

js_code = """
function createGradioAnimation() {
    // Add font from Google Fonts
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600;700&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
    
    // Add global CSS style
    const style = document.createElement('style');
    style.innerHTML = '* { font-family: "Source Code Pro", monospace !important; }';
    document.head.appendChild(style);
    
    var container = document.createElement('div');
    container.id = 'gradio-animation';
    container.style.fontSize = '2em';
    container.style.fontWeight = 'bold';
    container.style.textAlign = 'center';
    container.style.marginTop = '30px';
    container.style.marginBottom = '20px';
    container.style.color = '#FFFFFF';
    container.style.fontFamily = "'Source Code Pro', monospace";

    var text = 'Welcome to Business Intelligence Agent (Google ADK)'; 
        for (var i = 0; i < text.length; i++) {
            (function(i){
                setTimeout(function(){
                    var letter = document.createElement('span');
                    letter.style.opacity = '0';
                    letter.style.transition = 'opacity 0.5s ease-in-out';
                    letter.style.display = 'inline-block';
                    
                    if (text[i] === ' ') {
                        letter.innerHTML = '&nbsp;'; 
                    } else {
                        letter.innerText = text[i];
                    }
                    container.appendChild(letter);
                    setTimeout(function() { letter.style.opacity = '1'; }, 50);
                }, i * 100);
            })(i);
        }

        var gradioContainer = document.querySelector('.gradio-container');
        if (gradioContainer) {
            gradioContainer.insertBefore(container, gradioContainer.firstChild);
        }
        return 'Animation Created';
    }
    """
css = """
@import url('https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600;700&display=swap');

* { font-family: ''Source Code Pro'', sans-serif !important; }

.result-card {
    background: #1a1a1a !important;
    border-radius: 12px !important;
    padding: 15px !important;
    border: 1px solid #333 !important;
}
"""
async def run_bi_pipeline_async(user_question: str):
    """
    Run the complete BI pipeline using root_runner.

    This function executes the entire BI pipeline:
    1. Text-to-SQL: Generate SQL from question
    2. SQL Execution: Execute query against database
    3. Data Formatting: Prepare results
    4. Visualization: Generate Altair chart
    5. Explanation: Provide plain-language insights

    Args:
        user_question: Natural language question from the user

    Returns:
        Dictionary with keys: sql_query, query_results, chart_spec, explanation_text
    """
    # Create session
    session = await root_runner.session_service.create_session(
        user_id='user',
        app_name='bi_agent'
    )

    # Create user message
    content = types.Content(
        role='user',
        parts=[types.Part(text=user_question)]
    )

    # Run the complete pipeline
    events_async = root_runner.run_async(
        user_id='user',
        session_id=session.id,
        new_message=content
    )

    # Extract results from state
    results = {}
    async for event in events_async:
        if event.actions and event.actions.state_delta:
            for key, value in event.actions.state_delta.items():
                results[key] = value

    return results


async def process_request_async(message: str):
    """
    Process user request through the BI pipeline using root_runner.

    The root_agent handles the complete pipeline:
    1. Text-to-SQL Agent → Generates SQL from question
    2. SQL Executor Agent → Executes SQL against database
    3. Data Formatter Agent → Formats results
    4. Insight Pipeline → Visualization + Explanation

    Args:
        message: User's natural language question

    Returns:
        Tuple of (sql_query, df, chart, explanation_text)
    """
    
    try:
        # Validate input
        if not message.strip():
            return "Error: Please enter a question", None, None, "Error: No question provided"

        # Run the complete BI pipeline
        results = await run_bi_pipeline_async(message)

        # Extract SQL query
        sql_query = results.get('sql_query', '')

        # --- เพิ่ม Logic เพื่อตัด Thinking Process ออกจาก SQL ---
        if '</thinking_process>' in sql_query:
            sql_query = sql_query.split('</thinking_process>')[-1].strip()
        # Clean up SQL query (remove markdown if present)
        sql_query = sql_query.strip()
        if sql_query.startswith("```sql"):
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        elif sql_query.startswith("```"):
            sql_query = sql_query.replace("```", "").strip()

        # Extract query results
        query_results_str = results.get('query_results', '{}')
        print(f"DEBUG: query_results_str = {repr(query_results_str)}")

        query_results = {'success': False, 'data': [], 'error': 'Uninitialized'} 

        try:
            import json
            import re
            
            raw_str = str(query_results_str).strip()
            
            # Method 1: Try parsing as JSON
            clean_json = re.sub(r'^```[a-z]*\s*', '', raw_str, flags=re.IGNORECASE)
            clean_json = re.sub(r'\s*```$', '', clean_json)
            
            parsed_json = json.loads(clean_json)
            
            if isinstance(parsed_json, list):
                query_results = {'success': True, 'data': parsed_json}
            else:
                query_results = parsed_json

        except Exception as e_json:
            print(f"⚠️ Not valid JSON, trying to parse Markdown Table...")
            
            # Method 2: Try parsing markdown table
            try:
                lines = raw_str.split('\n')
                table_lines = [line.strip() for line in lines if '|' in line and line.strip()]
                
                if len(table_lines) >= 3:  # Header, separator, at least 1 data row
                    headers = [h.strip() for h in table_lines[0].strip('|').split('|')]
                    headers = [h.replace('\\_', '_') for h in headers]  # Remove escaping
                    data_list = []
                    
                    for line in table_lines[2:]:  # Skip separator
                        if line.startswith(':') or '---' in line:
                            continue
                        values = [v.strip() for v in line.strip('|').split('|')]
                        if len(values) == len(headers) and values != headers:
                            row_dict = {}
                            for i, header in enumerate(headers):
                                val = values[i] if i < len(values) else ''
                                # Try to convert to numeric
                                try:
                                    row_dict[header] = float(val)
                                except (ValueError, TypeError):
                                    row_dict[header] = val
                            data_list.append(row_dict)
                    
                    if data_list:
                        query_results = {
                            'success': True, 
                            'data': data_list
                        }
                        print(f"✅ Successfully parsed Markdown Table ({len(data_list)} rows)")
                    else:
                        raise ValueError("No data rows extracted from table")
                else:
                    raise ValueError(f"Invalid table format: found {len(table_lines)} lines")

            except Exception as e_table:
                print(f"⚠️ Markdown parsing failed: {e_table}")
                print(f"⚠️ Raw result: {raw_str[:200]}")
                
                # Method 3: If it's plain text, treat as error message
                query_results = {
                    'success': False, 
                    'data': [], 
                    'error': f'Could not parse query results. Output: {raw_str[:100]}'
                }
        # Check if query execution was successful
        if not query_results.get('success', False):
            error_msg = query_results.get('error', 'Unknown error')
            sql_query = f"-- Error executing query\n{sql_query}\n\n-- Error: {error_msg}"
            return sql_query, None, None, f"Error executing query: {error_msg}"

        # Convert query results to DataFrame
        data_list = query_results.get('data', [])
        if not data_list:
            df = pd.DataFrame()
            return sql_query, df, None, "The query executed successfully but returned no data."

        df = pd.DataFrame(data_list)

        # --- ส่วนที่แก้ไข: ดึงค่าจาก Trend Analyst และ Explanation Agent ---
        trend_text = results.get('trend_insights', '')
        explanation_text = results.get('explanation_text', '')

        # รวมข้อความ Insights เข้าด้วยกัน
        final_insights = ""
        if trend_text:
            final_insights += f"### 📈 Strategic Trends\n{trend_text}\n\n---\n"
        
        if explanation_text:
            final_insights += f"### 💡 Data Summary\n{explanation_text}"
        
        if not final_insights:
            final_insights = "The query executed successfully but no additional insights were generated."

        # Extract chart specification and explanation
        chart_spec = results.get('chart_spec', '')
        explanation_text = results.get('explanation_text', '')

        # Execute chart specification
        chart = None
        if chart_spec:
            try:
                chart_spec_clean = chart_spec.strip()
                
                # Remove thinking process blocks
                if '<thinking_process>' in chart_spec_clean:
                    parts = chart_spec_clean.split('</thinking_process>')
                    chart_spec_clean = parts[-1].strip() if len(parts) > 1 else chart_spec_clean
                
                # Remove markdown code blocks
                chart_spec_clean = chart_spec_clean.replace("```python", "").replace("```", "").strip()
                
                # Skip if no valid code found
                if not chart_spec_clean or chart_spec_clean.startswith('<') or 'import' not in chart_spec_clean.lower():
                    print("No valid chart code found, skipping chart generation")
                    chart = None
                else:
                    namespace = {
                        'alt': alt,
                        'pd': pd,
                        'df': df,
                        'data': df.to_dict(orient='records')
                    }
                    exec(chart_spec_clean, namespace)
                    chart = namespace.get('chart')
                    if chart:
                        print("Chart generated successfully")
                    else:
                        print("Chart variable not found in executed code")
                        
            except SyntaxError as e:
                print(f"Chart syntax error: {e}")
            except Exception as e:
                print(f"Chart generation warning: {e}")

        # Return all four outputs
        return sql_query, df, chart, final_insights

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Full error: {e}")
        import traceback
        traceback.print_exc()
        return error_msg, None, None, error_msg
def create_no_data_chart():
    "Create a simulated graph to inform the user that there is no data to display."
    import altair as alt
    import pandas as pd
    
    # Create a fake DataFrame with a warning message.
    data = pd.DataFrame({'message': ['No Data to Display for this Query']})
    
    # Create a text graph in the center.
    chart = alt.Chart(data).mark_text(
        size=18, 
        color='#718096',
        fontWeight=500,
        font='Source Code Pro'
    ).encode(
        text='message:N'
    ).properties(
        width=500,
        height=300,
        title="Visual Insight Summary"
    ).configure_view(
        strokeWidth=0 
    )
    return chart

def process_request(message: str):
    """
    Synchronous wrapper for Gradio.

    Database credentials are read from environment variables in bi_agent/.env
    """
    global current_df_storage
    try:
        sql_query, df, chart, explanation = asyncio.run(
            process_request_async(message)
        )
        # Managing Empty Data
        if df is None or df.empty:
            # If no data is available, submit a Placeholder graph instead. (None)
            no_data_chart = create_no_data_chart()
            current_df_storage = None
            return sql_query, df, no_data_chart, explanation
        # Store dataframe for download
        current_df_storage = df
        print(f"DEBUG: Stored dataframe with {len(df) if df is not None else 0} rows")
        return sql_query, df, chart, explanation
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        return error_msg, None, None, error_msg


def download_query_results() -> str:
    """
    Download query results as CSV file.

    Returns:
        File path to the CSV file
    """
    global current_df_storage
    
    print(f"DEBUG: download_query_results called")
    print(f"DEBUG: current_df_storage is None: {current_df_storage is None}")
    
    if current_df_storage is None or current_df_storage.empty:
        error_msg = "No data to download. Please run a query first."
        print(f"DEBUG: {error_msg}")
        return error_msg
    
    try:
        # Create temp CSV file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"query_results_{timestamp}.csv"
        csv_path = os.path.join(temp_dir, csv_filename)
        
        # Save dataframe to CSV
        current_df_storage.to_csv(csv_path, index=False, encoding='utf-8')
        
        print(f"DEBUG: CSV file created at {csv_path}")
        print(f"DEBUG: File size: {os.path.getsize(csv_path)} bytes")
        return csv_path
    except Exception as e:
        error_msg = f"Error downloading file: {str(e)}"
        print(f"DEBUG: {error_msg}")
        return error_msg
    


# ============================================================================
# Gradio UI
# ============================================================================

with gr.Blocks(css=css, theme=gr.themes.Monochrome()) as demo:
    gr.Markdown("""

    This demo uses **Google ADK's root_agent SequentialAgent**:

    1. **Text-to-SQL Agent** → Generates SQL from natural language
    2. **SQL Executor Agent** → Executes SQL against database
    3. **Trend Analyst Agent** → Analyze what "significant" aspects of the data have in a business context.
    4. **Data Formatter Agent** → Prepares results for visualization
    5. **Insight Pipeline** (**SequentialAgent**) → Visualization Agent → Explanation Agent

    Database credentials are configured in `bi_agent/.env`

    Enter your question below and click "Analyze Data".
    """)
    demo.load(None, js=js_code)
    with gr.Row():
        user_input = gr.Textbox(
            label="Your Question",
            placeholder="e.g., 'What are the top 10 products by price?'",
            lines=3
        )

    with gr.Row():
        submit_btn = gr.Button("Analyze Data", variant="primary")
        clear_btn = gr.Button("Clear")
    gr.Markdown("---")
    gr.Markdown("## Results")

    # Four output panels
    with gr.Row():
        with gr.Column(elem_classes="result-card"):
            gr.Markdown("### Generated SQL")
            sql_output = gr.Code(
                label="SQL Query",
                language="sql",
                value="-- Waiting for input..."
            )

        with gr.Column(elem_classes="result-card"):
            gr.Markdown("### Query Results")
            data_output = gr.DataFrame(
                label="Data Table",
                wrap=True
            )
            # Download button and file output for CSV
            download_btn = gr.Button(" Download as CSV", variant="secondary", size="sm")
            download_file = gr.File(label="Download CSV", interactive=False)

    with gr.Row():
        with gr.Column(elem_classes="result-card"):
            gr.Markdown("### Visualization")
            chart_output = gr.Plot(label="Chart")

        with gr.Column(elem_classes="result-card"):
            gr.Markdown("### Insights")
            explanation_output = gr.Markdown(
                value="*Waiting for input...*"
            )
    with gr.Row():
        export_btn = gr.Button("Export to PDF Report")
        file_output = gr.File(label="Download Report")

    # เชื่อมต่อฟังก์ชัน (ตัวอย่างการเรียกใช้)
    export_btn.click(
        fn=generate_report_pdf,
        inputs=[user_input, sql_output, data_output, explanation_output],
        outputs=file_output
    )
    
    # Examples
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

    # Button actions
    submit_btn.click(
        fn=process_request,
        inputs=[user_input],
        outputs=[sql_output, data_output, chart_output, explanation_output]
    )

    clear_btn.click(
        fn=lambda: (
            "",
            "-- Waiting for input...",
            None,
            None,
            "*Waiting for input...*"
        ),
        inputs=None,
        outputs=[user_input, sql_output, data_output, chart_output, explanation_output]
    )

    # Download CSV button action
    download_btn.click(
        fn=download_query_results,
        inputs=None,
        outputs=download_file
    )
    if __name__ == "__main__":
        demo.launch(theme=gr.themes.Monochrome())