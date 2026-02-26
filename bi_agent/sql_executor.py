"""
SQL execution utilities with safety validation.

This module provides safe SQL query execution with validation to prevent
dangerous operations and ensure only SELECT queries are executed.
"""

import re
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


# Dangerous SQL keywords that should be blocked
BLACKLIST_KEYWORDS = [
    'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
    'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE',
    'sp_', 'xp_'  # System stored procedures
]


def validate_sql(query: str) -> tuple[bool, str]:
    """
    Validate that SQL query is safe to execute.

    Only SELECT statements are allowed. Blocks dangerous operations.

    Args:
        query: SQL query string to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not query or not query.strip():
        return False, "Query is empty"

    # Remove comments and normalize whitespace
    query_clean = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
    query_clean = query_clean.strip().upper()

    # Check if query starts with SELECT
    if not query_clean.startswith('SELECT'):
        return False, "Only SELECT queries are allowed"

    # Check for blacklisted keywords
    for keyword in BLACKLIST_KEYWORDS:
        # Use word boundaries to avoid false positives (e.g., "DELETE" in column name)
        pattern = r'\b' + re.escape(keyword.upper()) + r'\b'
        if re.search(pattern, query_clean):
            return False, f"Dangerous keyword detected: {keyword}"

    # Check for multiple statements (semicolon-separated)
    # Allow semicolon at the end, but not in the middle
    semicolons = [i for i, char in enumerate(query.strip()) if char == ';']
    if semicolons:
        # Only allow semicolon as the last character
        if len(semicolons) > 1 or semicolons[0] != len(query.strip()) - 1:
            return False, "Multiple statements not allowed"

    return True, ""


def execute_query(engine: Engine, query: str, timeout: int = 120, max_rows: int = 1000) -> dict:
    """
    Execute SQL query safely and return results.

    Args:
        engine: SQLAlchemy Engine object
        query: SQL query to execute
        timeout: Query timeout in seconds (default: 30)
        max_rows: Maximum number of rows to return (default: 1000)

    Returns:
        Dictionary with keys:
            - success: bool
            - data: pandas DataFrame (if successful)
            - error: str (if failed)
            - row_count: int
            - columns: list of column names
    """
    # Validate query first
    is_valid, error_msg = validate_sql(query)
    if not is_valid:
        return {
            'success': False,
            'data': None,
            'error': f"SQL validation failed: {error_msg}",
            'row_count': 0,
            'columns': []
        }

    try:
        # Add row limit if not already present
        query_limited = query.strip().rstrip(';')

        # Simple check if query already has TOP or LIMIT
        query_upper = query_limited.upper()
        if 'TOP' not in query_upper and 'LIMIT' not in query_upper:
            # For SQL Server, we need to add TOP after SELECT
            # This is a simple implementation - may need refinement for complex queries
            if query_upper.startswith('SELECT DISTINCT'):
                query_limited = query_limited[:15] + f' TOP {max_rows}' + query_limited[15:]
            else:
                query_limited = query_limited[:6] + f' TOP {max_rows}' + query_limited[6:]

        # Execute query with timeout
        with engine.connect() as connection:
            # Set query timeout (SQL Server specific)
            connection = connection.execution_options(timeout=timeout)

            # Execute and fetch results
            df = pd.read_sql(text(query_limited), connection)

            return {
                'success': True,
                'data': df,
                'error': None,
                'row_count': len(df),
                'columns': df.columns.tolist()
            }

    except Exception as e:
        return {
            'success': False,
            'data': None,
            'error': str(e),
            'row_count': 0,
            'columns': []
        }


def serialize_dataframe(df: pd.DataFrame, include_sample: bool = True, sample_rows: int = 5) -> str:
    """
    Serialize DataFrame to JSON string for agent state.

    Args:
        df: pandas DataFrame to serialize
        include_sample: Whether to include sample rows (default: True)
        sample_rows: Number of sample rows to include (default: 5)

    Returns:
        JSON string representation
    """
    if df is None or df.empty:
        return "{}"

    result = {
        'row_count': len(df),
        'columns': df.columns.tolist(),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
    }

    if include_sample:
        # Include first N rows as sample
        sample_df = df.head(sample_rows)
        result['sample_data'] = sample_df.to_dict(orient='records')

    # Full data for small datasets
    if len(df) <= 100:
        result['full_data'] = df.to_dict(orient='records')
    else:
        # For large datasets, only include summary statistics
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            result['summary_stats'] = df[numeric_cols].describe().to_dict()

    return pd.Series(result).to_json()


def dataframe_to_markdown(df: pd.DataFrame, max_rows: int = 10) -> str:
    """
    Convert DataFrame to markdown table for display.

    Args:
        df: pandas DataFrame
        max_rows: Maximum rows to display (default: 10)

    Returns:
        Markdown formatted table string
    """
    if df is None or df.empty:
        return "*No data available*"

    # Limit rows for display
    display_df = df.head(max_rows)

    # Convert to markdown
    markdown = display_df.to_markdown(index=False)

    if len(df) > max_rows:
        markdown += f"\n\n*Showing {max_rows} of {len(df)} rows*"

    return markdown
