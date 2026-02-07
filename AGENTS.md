## Context

This is a project that demonstrates how to build a sequential agent pipeline using Google's Agent Development Kit (ADK) with Gradio web interface.

The project can be run with `uv run adk web .` (ADK web interface) as well as `uv run app.py` (Gradio interface). Both should be run from the project root directory.

## Project Structure

The project follows the ADK web directory structure:

```
gradio-adk-agent/
├── bi_agent/              # Agent package
│   ├── __init__.py        # Package initialization
│   ├── agent.py           # Main agent definitions
│   ├── tools.py           # Custom tool definitions
│   ├── bi_service.py      # Business Intelligence service
│   ├── db_config.py       # Database configuration
│   ├── sql_executor.py    # SQL execution utilities
│   └── .env               # API keys and credentials
├── app.py                 # Gradio web interface
├── pyproject.toml         # Project dependencies
└── README.md              # Project documentation
```

## Running the Project

### Option 1: ADK Web Interface

```bash
uv run adk web . --port 8000
```

This launches the ADK web interface at http://127.0.0.1:8000

### Option 2: Gradio Interface

```bash
uv run app.py
```

This launches the Gradio interface at http://127.0.0.1:7860

## Python management with uv

The project is managed with uv. 

To add packages, use the command:

```
uv add <package-name>
```

To run the project, use the command:

```
uv run
```

