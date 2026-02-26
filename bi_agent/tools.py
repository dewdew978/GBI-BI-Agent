"""
Tools for the Business Intelligence agents.

This module defines tools that agents can call to interact with the database,
execute queries, and process results.
"""

import os
import json
import pandas as pd
from typing import Dict, Any
from dotenv import load_dotenv
from .db_config import create_db_engine, get_schema_info
from .sql_executor import execute_query, validate_sql

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))


class DatabaseTools:
    """Tools for database operations that agents can use."""

    def __init__(self, server: str, database: str, username: str, password: str):
        """
        Initialize database tools with connection credentials.

        Args:
            server: SQL Server hostname
            database: Database name
            username: Database username
            password: Database password
        """
        self.engine = create_db_engine(server, database, username, password)

    def execute_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute a SQL query and return the results.

        This tool validates and executes SQL queries against the database.
        Only SELECT queries are allowed for safety.

        Args:
            sql_query: The SQL query to execute

        Returns:
            Dictionary containing:
                - success: Boolean indicating if query succeeded
                - data: List of dictionaries with query results
                - columns: List of column names
                - row_count: Number of rows returned
                - error: Error message if query failed
        """
        # Validate and execute the query
        result = execute_query(self.engine, sql_query)

        if result['success']:
            # Convert DataFrame to list of dicts for JSON serialization
            df = result['data']
            data_list = df.to_dict(orient='records') if df is not None else []

            return {
                'success': True,
                'data': data_list,
                'columns': result['columns'],
                'row_count': result['row_count'],
                'error': None
            }
        else:
            return {
                'success': False,
                'data': [],
                'columns': [],
                'row_count': 0,
                'error': result['error']
            }


def execute_sql_and_format(sql_query: str) -> str:
    """
    Execute a SQL query against the configured database and return formatted results.

    This tool:
    1. Connects to the database using credentials from environment variables
    2. Executes the provided SQL query (SELECT only for safety)
    3. Returns results as formatted JSON string with data and metadata

    Args:
        sql_query: The SQL SELECT query to execute

    Returns:
        JSON string containing:
            - success: Whether query succeeded
            - data: Query results as list of dictionaries
            - columns: Column names
            - row_count: Number of rows
            - error: Error message if failed

    Example:
        >>> result = execute_sql_and_format("SELECT TOP 5 * FROM Products")
        >>> print(result)
        {"success": true, "data": [...], "row_count": 5}
    """
    try:
        # Get database credentials from environment
        server = os.getenv("MSSQL_SERVER")
        database = os.getenv("MSSQL_DATABASE")
        username = os.getenv("MSSQL_USERNAME")
        password = os.getenv("MSSQL_PASSWORD")

        if not all([server, database, username, password]):
            return json.dumps({
                'success': False,
                'data': [],
                'columns': [],
                'row_count': 0,
                'error': 'Database credentials not configured in environment variables'
            })

        # Create database engine
        engine = create_db_engine(server, database, username, password)

        # Execute query
        result = execute_query(engine, sql_query)

        if result['success']:
            # Convert DataFrame to list of dicts for JSON serialization
            df = result['data']
            data_list = df.to_dict(orient='records') if df is not None and not df.empty else []

            response = {
                'success': True,
                'data': data_list,
                'columns': result['columns'],
                'row_count': result['row_count'],
                'error': None
            }
        else:
            response = {
                'success': False,
                'data': [],
                'columns': [],
                'row_count': 0,
                'error': result['error']
            }

        # Close engine
        engine.dispose()

        return json.dumps(response, indent=2)

    except Exception as e:
        return json.dumps({
            'success': False,
            'data': [],
            'columns': [],
            'row_count': 0,
            'error': f'Tool error: {str(e)}'
        })


def get_database_schema() -> str:
    """
    Retrieve database schema information for SQL query generation.

    Returns formatted schema showing available tables and columns that can be
    queried. This helps the text-to-SQL agent understand the database structure.

    Returns:
        Formatted string containing database schema information

    Example:
        >>> schema = get_database_schema()
        >>> print(schema)
        Database Schema:

        Table: dbo.Products
        Columns:
          - ProductID (int, NOT NULL)
          - ProductName (nvarchar, NOT NULL)
          ...
    """
    try:
        # Get database credentials from environment
        server = os.getenv("MSSQL_SERVER")
        database = os.getenv("MSSQL_DATABASE")
        username = os.getenv("MSSQL_USERNAME")
        password = os.getenv("MSSQL_PASSWORD")

        if not all([server, database, username, password]):
            return "Error: Database credentials not configured in environment variables"

        # Create database engine
        engine = create_db_engine(server, database, username, password)

        # Get schema info
        schema_info = get_schema_info(engine, max_tables=20)

        # Close engine
        engine.dispose()

        return schema_info

    except Exception as e:
        return f"Error retrieving schema: {str(e)}"
