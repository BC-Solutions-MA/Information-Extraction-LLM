import streamlit as st

# LLM ---------------------------------------------------------------------------------
GENERATOR_API_URI = "https://93a5-34-72-211-144.ngrok-free.app/v1"
MAX_TOKENS = 200
TEMPLATE_PROMPT = ("You are an advanced information extraction algorithm. "
"Extract information from the provided text only if it is explicitly mentioned. "
"If an attribute is not found in the text, return the attribute name as key in the final json with a empty string value affected to it `\"\"` "
"Here is the text for information extraction: {text} "
"{format_instructions}"
)

# Supabase ------------------------------------------------------------------------------
URL: str = "https://hxshejoduhitvgdqhxto.supabase.co"
SERVICE_KEY :str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh4c2hlam9kdWhpdHZnZHFoeHRvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcxNTc3NjkxOCwiZXhwIjoyMDMxMzUyOTE4fQ.nan7NUHTngr_0cazDms5dy3mGFOF2hIjtEkxDOIIolA"

# Unstructured --------------------------------------------------------------------------
UNSTRUCTURED_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbmdlc3Rpb24iLCJyb2xlcyI6WyJzZXJ2aWNlIl19.aHsCJxGWiq3c5XUJ7SWGbAVqmBTMs-WtUPw--wZttv4"
UNSTRUCTURED_API_ENDPOINT = "https://866e-35-203-189-209.ngrok-free.app/ingest"
FONT_PATH = "data/font/BioRhyme-Bold.otf"

# Streamlit ------------------------------------------------------------------------------
PAGE_TITLE = 'KYC'
## Menu main
MENU_TITLE = "KYC"
ICON_MENU = 'bi bi-person-check'
MENU_OPTION_ICONS = ['sliders2-vertical', 'bi bi-file-earmark-text', 'bi bi-diagram-3']
MENU_OPTIONS = ['Document processing', 'OCR', 'Information extraction']
## Menu page 1
MENU1_TITLE = 'Document processing'
ICON_MENU1 = 'sliders2-vertical'
MENU1_OPTION_ICONS = ['bi bi-folder2', 'bi bi-ui-checks', 'bi bi-cpu']
MENU1_OPTIONS = ['File storage', 'Pipeline manager', 'Process runner']
## Data editor config (Table: Files)
FILES_COLUMN_CONFIGURATION = {
    "Select": st.column_config.CheckboxColumn(required=True, width="small"),
    "name": st.column_config.TextColumn(
        "File name", help="The name of the file", max_chars=100, width="large"
    ),
    "created_at": st.column_config.DatetimeColumn(
        "Date of creation", width="large"
    ),
    "status": st.column_config.TextColumn(
        "Extraction status", width="medium"
    ),
}
## Data editor config (Table: Pipelines)
PIPELINES_COLUMN_CONFIGURATION = {
    "Select": st.column_config.CheckboxColumn(required=True, width="small"),
    "name": st.column_config.TextColumn(
        "Pipeline name", help="The name of the pipeline", max_chars=100, width="medium"
    ),
    "created_at": st.column_config.DatetimeColumn(
        "Date of creation", width="medium"
    ),
    "config": st.column_config.TextColumn(
        "Configuration", width="large"
    ),
}
