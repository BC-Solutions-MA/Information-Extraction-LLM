import pandas as pd
import numpy as np
import re
import streamlit as st
import os
import zipfile
from io import BytesIO
import base64
from datetime import datetime
import config
from dataclasses import dataclass
from time import sleep
import llm
import ocr

# Data reading --------------------------------------------------------------------------------------------
def read_tables_kyc(supabaseObj) -> dict[pd.DataFrame]:
    """
    Reads and returns KYC-related tables from a Supabase object.

    Parameters:
    supabaseObj (object): An instance of a Supabase object

    Returns:
    list[pd.DataFrame]: A list containing three DataFrames in the following order:
                        - DataFrame of all files
                        - DataFrame of all pipelines
                        - DataFrame of all results
    """
    df_files = pd.DataFrame(supabaseObj.get_all_files())
    if len(df_files) == 0:
        df_files = pd.DataFrame(columns=['id', 'created_at', 'name', 'ocr_json', 'ocr_text', 'storage_id', 'status'])
    df_pipelines = pd.DataFrame(supabaseObj.get_all_pipelines())
    if len(df_pipelines) == 0:
        df_pipelines = pd.DataFrame(columns=['id', 'created_at', 'name', 'config', 'prompt'])
    df_results = pd.DataFrame(supabaseObj.get_all_results())
    if len(df_results) == 0:
        df_results = pd.DataFrame(columns=['id', 'created_at', 'pipeline_id', 'llm_json', 'llm_score', 'status', 'corrected', 'corrected_score', 'file_id'])
    return {'Files': df_files, 'Pipelines': df_pipelines, 'Results': df_results}

# Langchain wrapper ---------------------------------------------------------------------------------------------
def init_chains_by_config(_generator, df_kie_config: pd.DataFrame, df_pipelines: pd.DataFrame) -> dict:
    """
    Initialize extraction chains for each unique pipeline based on the provided configuration.

    This function creates a dictionary of extraction chains, where each chain is initialized using the
    configuration specific to each pipeline. The configurations are retrieved from the `df_pipelines` DataFrame
    and applied to the generator provided.

    Args:
        _generator (ChatOpenAI): An instance of the ChatOpenAI model used for generating responses.
        df_kie_config (pd.DataFrame): A DataFrame containing the KIE configuration with a column 'pipeline'.
        df_pipelines (pd.DataFrame): A DataFrame containing pipeline configurations with columns 'name' and 'config'.

    Returns:
        dict: A dictionary where keys are unique pipeline names and values are tuples containing the initialized
              LLMChain, StructuredOutputParser, and OutputFixingParser for each pipeline.
    """
    unique_pipeline_names = df_kie_config.pipeline.unique()
    chains = {}
    for pipeline in unique_pipeline_names:
        config_pipeline = df_pipelines[df_pipelines['name'] == pipeline]['config'].iloc[0]
        chains[pipeline] = llm.get_extraction_chain(_generator, config_pipeline)
    return chains

def apply_kie_files(supabaseObj, df_kie_config: pd.DataFrame, df_files: pd.DataFrame, df_results: pd.DataFrame, chains: dict) -> pd.DataFrame:
    """
    Apply Knowledge Information Extraction (KIE) to files based on the provided configuration.

    This function processes each file in the configuration DataFrame using the corresponding extraction chain,
    generating JSON results for each file. The results are then appended to the configuration DataFrame.

    Args:
        df_kie_config (pd.DataFrame): A DataFrame containing the KIE configuration with columns 'pipeline', 'pipeline_id', and 'file_id'.
        df_results (pd.DataFrame): A DataFrame containing OCR text results for the files with columns 'file_id' and 'ocr_text'.
        chains (dict): A dictionary where keys are pipeline names and values are tuples containing the initialized
                       LLMChain, StructuredOutputParser, and OutputFixingParser for each pipeline.

    Returns:
        pd.DataFrame: The updated configuration DataFrame with an additional column 'llm_json' containing the
                      JSON extraction results for each file.
    """
    kie_results = []
    progress_bar = st.progress(0, text="Information Extraction in progress. Please wait...")
    bar_incremetor = Program()
    n_updated = 0
    for i, row in df_kie_config.iterrows():
        st.markdown(f'<b>Pipeline: </b>{row.pipeline}<br/> <b>File:</b> {row.filepath.split("/")[-1]} ', unsafe_allow_html=True)
        # Parameters
        pipeline_name = row.pipeline
        pipeline_id = row.pipeline_id
        file_id = row.file_id
        chain, parser, new_parser = chains[pipeline_name]
        ocr_text = df_files.loc[df_files['id'] == file_id, 'ocr_text'].iloc[0]
        # Generate JSON extraction
        json_result = llm.generate_response(chain, parser, new_parser, ocr_text)
        st.json(json_result)
        kie_results.append(json_result)
        supabaseObj.create_llm_result(file_id, pipeline_id, json_result)
        n_updated += 1
        bar_incremetor.increment()
        progress_perc = round(bar_incremetor.progress / len(df_kie_config) * 100)
        progress_bar.progress(progress_perc, text=f"Progress: {progress_perc}%")
    st.markdown(f'<b> {n_updated} documents have been processed!</b>', unsafe_allow_html=True)
    df_kie_config['llm_json'] = kie_results
    return df_kie_config
      

# Metrics computation -------------------------------------------------------------------------------------------
@st.cache_data
def compute_metrics_kyc(df_dict) -> dict:
    """
    Computes various KYC-related metrics from provided data.

    Parameters:
    df_dict (dict[str, pd.DataFrame]): A dictionary containing DataFrames with keys 'Files', 'Pipelines', and 'Results'.

    Returns:
    dict: A dictionary containing computed metrics with the following keys:
          - 'Files': [number_of_files, percentage_of_used_files]
          - 'OCR': [number_of_files_processed_by_OCR, percentage_of_files_processed_by_OCR]
          - 'KIE': [number_of_files_processed_by_KIE, percentage_of_files_processed_by_KIE]
          - 'Pipelines': [number_of_pipelines, percentage_of_used_pipelines]
    """
    metrics = {}
    df_files, df_pipelines, df_results = df_dict['Files'], df_dict['Pipelines'], df_dict['Results']
    
    # 1st Metric: Number of files + Percentage of used files
    n_files = len(df_files)
    metrics['Files'] = [n_files, None]
    
    # 2nd Metric: Number of files processed by OCR + their percentage
    n_files_ocr = df_files.dropna(subset=['ocr_json'])['id'].nunique()
    p_files_ocr = 0 if n_files == 0 else round(n_files_ocr / n_files * 100)
    metrics['OCR'] = [n_files_ocr, p_files_ocr]
    
    # 3rd Metric: Number of files processed by KIE + their percentage
    n_files_kie = df_results.dropna(subset=['llm_json'])['file_id'].nunique()
    p_files_kie = 0 if n_files == 0 else round(n_files_kie / n_files * 100)
    metrics['KIE'] = [n_files_kie, p_files_kie]
    
    # 4th Metric: Number of pipelines + Percentage of used pipelines
    n_pipelines = len(df_pipelines)
    n_used_pipelines = len(df_pipelines[df_pipelines['id'].map(lambda x: x in df_results['pipeline_id'])])
    metrics['Pipelines'] = [n_pipelines, None]
    
    return metrics


# Supabase layer ------------------------------------------------------------------------------------------
@st.cache_data
def upload_files(_supabaseObj, files: list, filenames: list, df_files: pd.DataFrame):
    """
    Upload files to Supabase if they are not already present in the files table.

    Args:
    _supabaseObj: The Supabase object for interacting with the Supabase service.
    files (list): List of files to be uploaded.
    filenames (list): List of filenames corresponding to the files.
    df_files (pd.DataFrame): The DataFrame containing the files metadata.

    Returns:
    None
    """
    uploaded = []
    for filename, file in zip(filenames, files):
        if f'kyc-files/{filename}' not in df_files['name'].tolist():
            _supabaseObj.new_file(file.read(), filename)
            uploaded.append(filename)
    if len(uploaded) != 0:
        st.session_state.uploader_key += 1
        st.experimental_rerun()

def save_pipeline(supabaseObj, pipeline_name):
    """
    Save a new pipeline configuration to the database using the provided Supabase object.

    This function constructs a configuration JSON object from the current session state, then uses the Supabase
    object to save this configuration under the specified pipeline name. After saving, the function resets the form.

    Args:
        supabaseObj: An instance of a Supabase client or similar object with a method `create_pipeline` for saving the pipeline.
        pipeline_name (str): The name to be assigned to the new pipeline.

    Returns:
        None
    """
    config_json = {
        st.session_state.new_pipeline['fields'][key]: st.session_state.new_pipeline['descriptions'][key]
        for key in st.session_state.new_pipeline['fields']
        if (len(st.session_state.new_pipeline['fields'][key]) != 0 and len(st.session_state.new_pipeline['descriptions'][key]) != 0)
    }
    supabaseObj.create_pipeline(pipeline_name, config_json, None)
    reset_form()

    
# Transformations ----------------------------------------------------------------------------------
@st.cache_data
def preprocess_pipelines_table(df_pipelines):
    """
    Preprocess the pipelines table. If the table is empty, create a DataFrame with the required columns.
    Convert 'config' column to dictionary and 'created_at' column to datetime.

    Args:
    df_pipelines (pd.DataFrame): The DataFrame containing pipeline data.

    Returns:
    pd.DataFrame: The preprocessed DataFrame.
    """
    if len(df_pipelines) == 0:
        df_pipelines = pd.DataFrame(columns=["id", "created_at", "name", "config", "prompt"])
    else:
        df_pipelines['config'] = df_pipelines['config'].map(lambda x: str_to_dict(x) if type(x)==str else x)
        df_pipelines['created_at'] = pd.to_datetime(df_pipelines['created_at'])
    return df_pipelines

@st.cache_data
def preprocess_files_table(df_files):
    """
    Preprocess the files table. If the table is empty, create a DataFrame with the required columns.
    Convert 'created_at' column to datetime.

    Args:
    df_files (pd.DataFrame): The DataFrame containing files data.

    Returns:
    pd.DataFrame: The preprocessed DataFrame.
    """
    if len(df_files) == 0:
        df_files = pd.DataFrame(columns=["id", "name", "created_at", "status"])
    else:
        df_files['created_at'] = pd.to_datetime(df_files['created_at'])
    return df_files

def kie_preprocess_config(df_files: pd.DataFrame, df_pipelines: pd.DataFrame, df_results: pd.DataFrame, kie_config: dict) -> pd.DataFrame:
    """
    Preprocess the KIE (Knowledge Information Extraction) configuration to create a DataFrame ready for processing.

    This function takes in dataframes containing file information, pipeline information, and results of previous
    processing, along with a configuration dictionary. It processes these inputs to produce a DataFrame that
    associates files with pipelines, excluding any file-pipeline pairs that have already been processed.

    Args:
        df_files (pd.DataFrame): A DataFrame containing file information with columns 'name' and 'id'.
        df_pipelines (pd.DataFrame): A DataFrame containing pipeline information with columns 'name' and 'id'.
        df_results (pd.DataFrame): A DataFrame containing results of previously processed file-pipeline pairs 
                                    with columns 'file_id' and 'pipeline_id'.
        kie_config (dict): A dictionary containing configuration data with keys 'filepaths' and 'pipelines'.

    Returns:
        pd.DataFrame: A DataFrame containing file and pipeline associations ready for processing. The DataFrame
                      will have columns 'filepath', 'pipeline', 'file_id', and 'pipeline_id', with any
                      previously processed pairs removed.
    """
    df = pd.DataFrame(kie_config)
    df = df.explode('pipelines')
    df = df.explode('filepaths')
    df = df.rename({'pipelines': 'pipeline', 'filepaths': 'filepath'}, axis=1)
    df = df.drop_duplicates()
    df = df.merge(df_files[['name', 'id']], how='left', left_on='filepath', right_on='name').rename({'id': 'file_id'}, axis=1).drop(['name'], axis=1)
    df = df.merge(df_pipelines[['name', 'id']], how='left', left_on='pipeline', right_on='name').rename({'id': 'pipeline_id'}, axis=1).drop(['name'], axis=1)
    df = df.merge(df_results[['id', 'file_id']], how='left', on='file_id').rename({'id': 'result_id'}, axis=1)
    
    # Remove already processed (file, pipeline)
    index_to_remove = []
    for i, row in df.iterrows():
        if row.pipeline_id in df_results[df_results.file_id == row.file_id].pipeline_id.tolist():
            index_to_remove.append(i)
            st.info(f'{row.filepath} has already been processed with pipeline {row.pipeline}.')
    
    df = df.drop(index_to_remove)
    return df

@st.cache_data
def filter_bboxes_kie(ocr_json, llm_json):
    """
    Filters bounding boxes from OCR results based on text extracted from LLM.

    This function takes in OCR-detected text blocks and key information extracted 
    from a large language model (LLM) and filters the OCR text blocks that match 
    the LLM key information. It returns the filtered OCR text blocks and a 
    dictionary mapping the text blocks to their corresponding titles from the LLM.

    Parameters:
    ocr_json (list): A list of OCR-detected text blocks. Each text block is represented 
                     as a list where the first element is an identifier and the second 
                     element is a tuple containing the text and other information.
    llm_json (dict): A dictionary where keys are titles and values are the corresponding 
                     text extracted by the LLM.

    Returns:
    list: A list containing a single list of filtered OCR text blocks.
    dict: A dictionary mapping the filtered OCR text blocks to their corresponding titles 
          from the LLM.

    """
    reference = ' || '.join(list(llm_json.values()))
    final_result = {}
    titles_dict = {}
    paddle_results = ocr.get_individual_boxes(ocr_json)
    for page_number, paddle_result in paddle_results.items():
        blocks = []
        for block in paddle_result:
            for title, text in llm_json.items():
                if (block[1].lower() in text.lower() and (len(block[1]) > 2 or block[1].lower()==text.lower())) or (('date' in title.lower() or 'tax' in title.lower()) and text.lower() in block[1].lower() and len(text)>2) or (len(text)>3 and len(text)>0.45*len(block[1]) and text.lower() in block[1].lower()):
                    blocks.append(block)
                    titles_dict[block[1]] = title
                    continue
        final_result[page_number] = blocks
    return final_result, titles_dict
        
# Utilities -----------------------------------------------------------------------------------------
@st.cache_data
def remove_text_between_delimiters(text):
    """
    This function removes text that starts with '//' and continues to the end of the line.
    It also removes excessive whitespace and newline characters.

    Args:
    text (str): The input string containing text with delimiters.

    Returns:
    str: The cleaned text with the specified patterns removed.
    """
    # Use regex to find text from // to the end of the line
    pattern = r'//.*$'
    # Replace the found text with an empty string
    cleaned_text = re.sub(pattern, '', text, flags=re.MULTILINE)
    # Remove excessive whitespace and newlines
    cleaned_text = re.sub(r'[\n\t]+| +', ' ', cleaned_text)
    return cleaned_text

@st.cache_data
def file_to_base64(file_content):
    """
    Convert a file uploaded via Streamlit into a base64 encoded string.

    Args:
    file_content: The file read from supabase

    Returns:
    str: Base64 encoded string representation of the file.
    """
    base64_bytes = base64.b64encode(file_content)
    base64_string = base64_bytes.decode('utf-8')
    return base64_string
    
@st.cache_data
def create_zip(files):
    """
    Create a zip file from a list of files.

    Args:
    files (list): A list of dictionaries where each dictionary contains 'name' and 'content' keys.

    Returns:
    BytesIO: A buffer containing the zip file.
    """
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file in files:
            zip_file.writestr(file["name"], file["content"])
    zip_buffer.seek(0)
    return zip_buffer

def str_to_dict(dict_string: str) -> dict:
    """
    Convert a string representation of a dictionary into an actual dictionary.

    Args:
    dict_string (str): The string representation of the dictionary.

    Returns:
    dict: The converted dictionary.
    """
    dict_string = dict_string.strip('{}')
    pairs = dict_string.split(', ')
    result_dict = {key.strip('"\' '): value.strip('"\' ') for key, value in (pair.split(': ') for pair in pairs)}
    return result_dict

@dataclass
class Program:
    progress: int = 0

    def increment(self):
        self.progress += 1
        sleep(0.1)
        
# Session management --------------------------------------------------------------------------
def init_sessions():
    """
    Initialize session state variables if not already set. This function is used to ensure that
    specific keys are present in Streamlit's session state to manage features and fields across
    the session.
    """
    if 'features' not in st.session_state:
        st.session_state['features'] = []
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
     # Initialize session state if not already done
    if 'new_pipeline' not in st.session_state:
        st.session_state.new_pipeline = {'fields': {0: "", 1: ""}, 'descriptions': {0: "", 1: ""}}
    if 'pipeline_selection' not in st.session_state:
        st.session_state.pipeline_selection = {}
        
def add_field():
    """
    Adds a new field to the new pipeline form.
    """
    new_index = 0 if len(st.session_state.new_pipeline['fields'])==0 else max(st.session_state.new_pipeline['fields'].keys())+1
    st.session_state.new_pipeline['fields'][new_index] = ""
    st.session_state.new_pipeline['descriptions'][new_index] = ""

def delete_field(field_index):
    """
    Deletes a field from the new pipeline form.

    Args:
        field_index (int): Index of the field to delete.
        pipeline_name (str): Name of the pipeline.
    """
    if field_index in st.session_state.new_pipeline['fields']:
        del st.session_state.new_pipeline['fields'][field_index]
    if field_index in st.session_state.new_pipeline['descriptions']:
        del st.session_state.new_pipeline['descriptions'][field_index]

def reset_form():
    """
    Resets the 'new_pipeline' session state to empty dictionaries for fields and descriptions.

    This function clears out any existing field and description data stored in the 
    'new_pipeline' session state, effectively resetting the form to its initial state 
    with no fields or descriptions added.
    """
    st.session_state.new_pipeline = {'fields': {0: "", 1: ""}, 'descriptions': {0: "", 1: ""}}
    st.session_state.new_pipeline_name = ""
    
def add_field_pipeline(pipeline_name):
    """
    Adds a new field to the session state for a specific pipeline.

    Args:
        pipeline_name (str): The name of the pipeline to add a field to.
    """
    st.session_state[pipeline_name]["fields"][0 if len(st.session_state[pipeline_name]["fields"]) == 0 else max(st.session_state[pipeline_name]["fields"].keys()) + 1] = ""
    st.session_state[pipeline_name]["descriptions"][0 if len(st.session_state[pipeline_name]["descriptions"]) == 0 else max(st.session_state[pipeline_name]["descriptions"].keys()) + 1] = ""

def delete_field_pipeline(field_index, pipeline_name):
    """
    Deletes a field from the session state for a given pipeline.

    Args:
        field_index (int): The index of the field to delete.
        pipeline_name (str): The name of the pipeline whose field is to be deleted.
    """
    if pipeline_name in st.session_state:
        del st.session_state[pipeline_name]["fields"][field_index]
        del st.session_state[pipeline_name]["descriptions"][field_index]
   