"""
Business Intelligence Service Module

This module provides a clean interface for database operations,
keeping the app.py focused on UI and agent orchestration.
"""

import pandas as pd
import json
from typing import Dict, Tuple, Optional
from sqlalchemy.engine import Engine

from .db_config import create_db_engine, get_schema_info, validate_connection
from .sql_executor import execute_query


class BIService:
    """Service class for Business Intelligence operations."""

    def __init__(self, server: str, database: str, username: str, password: str):
        """
        Initialize BI Service with database credentials.

        Args:
            server: SQL Server hostname
            database: Database name
            username: Database username
            password: Database password
        """
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.engine: Optional[Engine] = None
        self.schema_info: Optional[str] = None

    def connect(self) -> Tuple[bool, str]:
        """
        Connect to the database and validate connection.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.engine = create_db_engine(
                self.server,
                self.database,
                self.username,
                self.password
            )

            is_connected, message = validate_connection(self.engine)
            return is_connected, message

        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def load_schema(self, max_tables: int = 20) -> str:
        """
        Load database schema information.

        Args:
            max_tables: Maximum number of tables to include

        Returns:
            Formatted schema string
        """
        if self.engine is None:
            raise RuntimeError("Not connected to database. Call connect() first.")

        self.schema_info = get_schema_info(self.engine, max_tables=max_tables)
        return self.schema_info

    def execute_sql(self, sql_query: str) -> Dict:
        """
        Execute a SQL query and return results.

        Args:
            sql_query: SQL query to execute

        Returns:
            Dictionary with keys: success, data (DataFrame), error, row_count, columns
        """
        if self.engine is None:
            return {
                'success': False,
                'data': None,
                'error': 'Not connected to database',
                'row_count': 0,
                'columns': []
            }

        return execute_query(self.engine, sql_query)

    def prepare_data_for_agents(self, df: pd.DataFrame, sql_query: str = "") -> str:
        """
        Prepare query results as a formatted string for agents.

        Args:
            df: Query results as DataFrame
            sql_query: Original SQL query (optional)

        Returns:
            Formatted string with data summary, sample, and statistics
        """
        if df is None or df.empty:
            return "No data available"

        data_summary = {
            'columns': df.columns.tolist(),
            'row_count': len(df),
            'sample_data': df.head(10).to_dict(orient='records'),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
        }

        # Build formatted prompt
        prompt = f"""Here are the query results:
"""

        if sql_query:
            prompt += f"\nSQL Query: {sql_query}\n"

        prompt += f"""
Results: {len(df)} rows returned

Columns: {', '.join(data_summary['columns'])}
Data Types: {json.dumps(data_summary['dtypes'])}

Sample Data (first 10 rows):
{json.dumps(data_summary['sample_data'], indent=2)}
"""

        # Add summary statistics if there are numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            prompt += f"""
Summary Statistics:
{df.describe().to_string()}
"""

        return prompt

    def get_schema_for_sql_generation(self, question: str) -> str:
        """
        Get formatted prompt for SQL generation agent.

        Args:
            question: User's natural language question

        Returns:
            Formatted prompt with schema and question
        """
        if self.schema_info is None:
            raise RuntimeError("Schema not loaded. Call load_schema() first.")

        return f"""{self.schema_info}

User Question: {question}
"""

    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
