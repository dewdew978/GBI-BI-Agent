"""
Tools for the Business Intelligence agents.

This module defines tools that agents can call to interact with the database,
execute queries, and process results.
"""

import os
import json
import re
import tempfile
import datetime
import pandas as pd
from typing import Dict, Any
from dotenv import load_dotenv
from .db_config import create_db_engine, get_schema_info
from .sql_executor import execute_query, validate_sql

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, Table, TableStyle, KeepTogether, Flowable,
)

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



# ============================================================================
# PDF Report — Formal White  (reportlab)
# ============================================================================

# ── Colour palette ─────────────────────────────────────────────────────────
_C_NAVY   = colors.HexColor('#0a2342')
_C_GOLD   = colors.HexColor('#c8a951')
_C_BLACK  = colors.HexColor('#1a1a1a')
_C_GRAY   = colors.HexColor('#555555')
_C_LGRAY  = colors.HexColor('#888888')
_C_BORDER = colors.HexColor('#dde1e7')
_C_CODEBG = colors.HexColor('#f4f4f4')
_C_TBLALT = colors.HexColor('#f5f7fa')
_C_WHITE  = colors.white

_W, _H = A4


# ── Custom Flowables ───────────────────────────────────────────────────────

class _GoldRule(Flowable):
    """2pt gold divider rule under the report title."""
    def __init__(self, width=165*mm, height=2):
        super().__init__()
        self._w, self._h = width, height

    def draw(self):
        self.canv.setFillColor(_C_GOLD)
        self.canv.rect(0, 0, self._w, self._h, stroke=0, fill=1)

    def wrap(self, *_):
        return self._w, self._h + 6


class _ThinRule(Flowable):
    """0.5pt light-grey rule used under section headings."""
    def __init__(self, width=165*mm):
        super().__init__()
        self._w = width

    def draw(self):
        self.canv.setStrokeColor(_C_BORDER)
        self.canv.setLineWidth(0.5)
        self.canv.line(0, 0, self._w, 0)

    def wrap(self, *_):
        return self._w, 7


# ── Style sheet ────────────────────────────────────────────────────────────

def _pdf_styles() -> dict:
    return {
        'org': ParagraphStyle('org',
            fontName='Helvetica', fontSize=7.5, textColor=_C_LGRAY,
            leading=10, tracking=3, spaceAfter=2),

        'title': ParagraphStyle('title',
            fontName='Helvetica-Bold', fontSize=20, textColor=_C_NAVY,
            leading=26, spaceAfter=2),

        'subtitle': ParagraphStyle('subtitle',
            fontName='Helvetica', fontSize=9, textColor=_C_GRAY,
            leading=13, spaceAfter=0),

        'meta': ParagraphStyle('meta',
            fontName='Helvetica', fontSize=8, textColor=_C_LGRAY,
            leading=12, alignment=TA_RIGHT),

        'section': ParagraphStyle('section',
            fontName='Helvetica-Bold', fontSize=9, textColor=_C_NAVY,
            leading=12, spaceBefore=18, spaceAfter=6, tracking=2),

        'body': ParagraphStyle('body',
            fontName='Helvetica', fontSize=9.5, textColor=_C_BLACK,
            leading=16, spaceAfter=4, alignment=TA_JUSTIFY),

        'bullet': ParagraphStyle('bullet',
            fontName='Helvetica', fontSize=9.5, textColor=_C_BLACK,
            leading=15, leftIndent=14, firstLineIndent=-10, spaceAfter=5),

        'code': ParagraphStyle('code',
            fontName='Courier', fontSize=8,
            textColor=colors.HexColor('#1a1a2e'),
            leading=13, leftIndent=0),

        'footer': ParagraphStyle('footer',
            fontName='Helvetica', fontSize=6.5,
            textColor=colors.HexColor('#8899aa'),
            leading=10, alignment=TA_CENTER),
    }


# ── Helpers ────────────────────────────────────────────────────────────────

def _clean_text(text) -> str:
    if isinstance(text, pd.DataFrame):
        text = text.to_string()
    if text is None:
        return 'N/A'
    s = str(text).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^\x20-\x7E\n]', '', s).strip()


def _strip_md(text: str) -> str:
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    return text


def _header_block(S: dict) -> Table:
    ts  = datetime.datetime.now().strftime('%d %B %Y, %H:%M')
    ref = datetime.datetime.now().strftime('RPT-%Y%m%d-%H%M')
    left = [
        Paragraph('BUSINESS INTELLIGENCE UNIT', S['org']),
        Paragraph('Intelligence Report', S['title']),
        Paragraph('Automated Analysis  ·  Google ADK  ·  Sequential Agent Pipeline',
                  S['subtitle']),
    ]
    right = [
        Paragraph(f'Date: {ts}',              S['meta']),
        Paragraph(f'Ref:  {ref}',             S['meta']),
        Paragraph('Classification: Internal', S['meta']),
    ]
    tbl = Table([[left, right]], colWidths=[110*mm, 55*mm])
    tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'BOTTOM'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _sql_card(sql_text: str, S: dict) -> Table:
    """SQL rendered in a light-grey card with navy left border."""
    lines = _clean_text(sql_text).split('\n')
    rows  = [[Paragraph(ln if ln.strip() else '\u00a0', S['code'])]
             for ln in lines[:80]]
    tbl = Table(rows, colWidths=[165*mm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), _C_CODEBG),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BOX',           (0, 0), (-1, -1), 0.75, _C_BORDER),
        ('LINEBEFORE',    (0, 0), (0, -1),  3,    _C_NAVY),
    ]))
    return tbl


def _parse_md(raw: str, S: dict) -> list:
    """Convert markdown-ish text to ReportLab Paragraph objects."""
    result = []
    for line in _clean_text(_strip_md(raw)).split('\n'):
        line = line.rstrip()
        if not line:
            result.append(Spacer(1, 4))
        elif line.strip().startswith(('- ', '* ')):
            result.append(Paragraph(
                f'<bullet>\u2022</bullet> {line.strip()[2:]}',
                S['bullet']))
        elif '---' in line:
            result.append(_ThinRule())
        else:
            result.append(Paragraph(line, S['body']))
    return result


def _draw_page(canvas, doc):
    """Header & footer chrome drawn on every page."""
    canvas.saveState()

    # ── Top bar: navy + gold strip ──────────────────────────────────────
    canvas.setFillColor(_C_NAVY)
    canvas.rect(0, _H - 10*mm, _W, 10*mm, stroke=0, fill=1)
    canvas.setFillColor(_C_GOLD)
    canvas.rect(0, _H - 12*mm, _W, 2*mm,  stroke=0, fill=1)

    canvas.setFillColor(_C_WHITE)
    canvas.setFont('Helvetica', 7)
    canvas.drawString(24*mm, _H - 6.5*mm,
                      'BUSINESS INTELLIGENCE UNIT  //  GOOGLE ADK')
    canvas.drawRightString(_W - 24*mm, _H - 6.5*mm, f'Page {doc.page}')

    # ── Bottom bar: navy + gold strip ───────────────────────────────────
    canvas.setFillColor(_C_NAVY)
    canvas.rect(0, 0, _W, 8*mm, stroke=0, fill=1)
    canvas.setFillColor(_C_GOLD)
    canvas.rect(0, 8*mm, _W, 1*mm, stroke=0, fill=1)

    canvas.setFillColor(colors.HexColor('#8899aa'))
    canvas.setFont('Helvetica', 6.5)
    canvas.drawCentredString(_W / 2, 3*mm,
        'CONFIDENTIAL  ·  AUTO-GENERATED  ·  BI AGENT  ·  FOR INTERNAL USE ONLY')

    canvas.restoreState()


def generate_report_pdf(question, sql, trend, explanation) -> str:
    """
    Generate a formal white-background PDF report.

    Parameters
    ----------
    question    : str              — original user query
    sql         : str              — generated SQL query
    trend       : str              — strategic trends (markdown)
    explanation : str | DataFrame  — executive summary / data table

    Returns
    -------
    str — absolute path to the generated PDF file
    """
    out_path = os.path.join(
        tempfile.gettempdir(),
        f'bi_report_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
    )

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=24*mm, rightMargin=24*mm,
        topMargin=22*mm, bottomMargin=18*mm,
        title='Business Intelligence Report',
        author='BI Agent — Google ADK',
    )

    S     = _pdf_styles()
    story = []

    # ── Cover header ─────────────────────────────────────────────────────
    story.append(_header_block(S))
    story.append(Spacer(1, 6))
    story.append(_GoldRule())
    story.append(Spacer(1, 20))

    # ── 1. User Question ─────────────────────────────────────────────────
    story.append(Paragraph('1.  USER QUESTION', S['section']))
    story.append(_ThinRule())
    story.append(Spacer(1, 6))
    story.append(Paragraph(_clean_text(question) or 'N/A', S['body']))
    story.append(Spacer(1, 14))

    # ── 2. Generated SQL ─────────────────────────────────────────────────
    story.append(Paragraph('2.  GENERATED SQL QUERY', S['section']))
    story.append(_ThinRule())
    story.append(Spacer(1, 6))
    story.append(_sql_card(sql, S))
    story.append(Spacer(1, 14))

    # ── 3. Strategic Trends ──────────────────────────────────────────────
    story.append(Paragraph('3.  STRATEGIC TRENDS', S['section']))
    story.append(_ThinRule())
    story.append(Spacer(1, 6))
    story.extend(_parse_md(str(trend), S))
    story.append(Spacer(1, 14))

    # ── 4. Executive Summary ─────────────────────────────────────────────
    story.append(Paragraph('4.  EXECUTIVE SUMMARY', S['section']))
    story.append(_ThinRule())
    story.append(Spacer(1, 6))
    exp_str = (explanation.to_string()
               if isinstance(explanation, pd.DataFrame)
               else str(explanation))
    story.extend(_parse_md(exp_str, S))

    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return out_path




