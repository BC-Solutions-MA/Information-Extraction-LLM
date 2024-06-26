import pandas as pd
import streamlit as st
from streamlit_image_zoom import image_zoom
from PIL import Image, ImageDraw, ImageFont
import config
import backend
import io

# Pipeline explorer viz --------------------------------------------------------------------------------------------------------------
def display_form_updater(supabaseObj, pipelines, df_pipelines):
    """
    Displays a form for updating selected pipeline details including name and configuration.

    Args:
        supabaseObj: Supabase object for interacting with Supabase service.
        pipelines (DataFrame): DataFrame indicating selected pipelines.
        df_pipelines (DataFrame): DataFrame containing the pipelines data.
    """
    df_selected = df_pipelines[pipelines['Select']]
    for i, row in df_selected.iterrows():
        container = st.container()
        display_pipeline_form(container, row, supabaseObj)
        st.write('---------------------')

def display_pipeline_form(container, row, supabaseObj):
    """
    Displays the form for a specific pipeline, including its current configuration.

    Args:
        container: The Streamlit container to place the form elements in.
        row (Series): The row of the DataFrame representing the pipeline.
        supabaseObj: Supabase object for interacting with Supabase service.
    """
    container.markdown(f"<h4>{row['name']}</h4>", unsafe_allow_html=True)
    container.json(row['config'])
    name = container.text_input("Update pipeline Name", key=f'pipeline {row["name"]}', value=row['name'])
    container.markdown("###### Update features")
    config_pipe = backend.str_to_dict(row['config']) if isinstance(row['config'], str) else row['config']
    pipeline_name = row['name']
    if name not in st.session_state:
        st.session_state[name] = {"fields": {i: key for i, key in enumerate(list(config_pipe.keys()))}, "descriptions": {i: value for i, value in enumerate(list(config_pipe.values()))}}
    display_fields(container, pipeline_name)
    add_buttons(container, row, supabaseObj, name)

def display_fields(container, pipeline_name):
    """
    Displays the fields and descriptions for a specific pipeline.

    Args:
        container: The Streamlit container to place the form elements in.
        pipeline_name (str): The name of the pipeline.
    """
    keys = st.session_state[pipeline_name]['fields'].keys()
    for j in keys:
        c1, c2, c3 = container.columns([4, 16, 1])
        with c1:
            st.session_state[pipeline_name]['fields'][j] = st.text_input(f"Field {j+1}", key=f"textC2{pipeline_name}{j}", value=st.session_state[pipeline_name]['fields'][j])
        with c2:
            st.session_state[pipeline_name]['descriptions'][j] = st.text_input(f"Field {j+1} description", key=f"textDescC2{pipeline_name}{j}", value=st.session_state[pipeline_name]['descriptions'][j])
        with c3:
            st.markdown('<br/>', unsafe_allow_html=True)
            st.button("❌", key=f'delete2C{pipeline_name}{j}', on_click=backend.delete_field_pipeline, args=(j, pipeline_name))

def add_buttons(container, row, supabaseObj, name):
    """
    Adds buttons for adding fields, updating, and deleting the pipeline.

    Args:
        container: The Streamlit container to place the buttons in.
        row (Series): The row of the DataFrame representing the pipeline.
        supabaseObj: Supabase object for interacting with Supabase service.
        name (str): The name of the pipeline.
    """
    cols = container.columns([6, 3, 4, 4, 6])
    cols[1].button("➕ Add field", on_click=backend.add_field_pipeline, key=f'button{row["name"]}', args=(row['name'],))
    submit_button = cols[2].button("💾 Update Pipeline", key=f'update {row["name"]}', on_click=update_pipeline, args = (supabaseObj, row['id'], name,))
    delete_button = cols[3].button("❌ Delete Pipeline", key=f'delete {row["name"]}')
    if delete_button:
        delete_pipeline(supabaseObj, row['id'])

def update_pipeline(supabaseObj, pipeline_id, pipeline_name):
    """
    Updates the pipeline name and configuration in the database.

    Args:
        supabaseObj: Supabase object for interacting with Supabase service.
        pipeline_id (str): The ID of the pipeline to update.
        pipeline_name (str): The new name of the pipeline.
    """
    config_pipe = {st.session_state[pipeline_name]["fields"][i]: st.session_state[pipeline_name]["descriptions"][i] for i in st.session_state[pipeline_name]["fields"].keys()}
    supabaseObj.update_pipeline_name_by_id(pipeline_id, pipeline_name)
    supabaseObj.update_config_by_id(pipeline_id, config_pipe)

def delete_pipeline(supabaseObj, pipeline_id):
    """
    Deletes a pipeline from the database.

    Args:
        supabaseObj: Supabase object for interacting with Supabase service.
        pipeline_id (str): The ID of the pipeline to delete.
    """
    supabaseObj.delete_pipeline(pipeline_id)
    st.experimental_rerun()

## Pipelines (Add new) -------------------------------------------------------------------------------------------------
def display_fields_for_new_pipeline(pipeline_name):
    """
    Displays the input fields for the new pipeline's configuration.

    Args:
        pipeline_name (str): Name of the pipeline.
    """
    for i, key in enumerate(st.session_state.new_pipeline['fields'].keys()):
        field_key = f'field_{key}'
        description_key = f'description_{key}'
        
        c1, c2, c3 = st.columns([4, 16, 1])
        with c1:
            st.session_state.new_pipeline['fields'][key] = st.text_input(f"Field {i + 1}", key=f"text{field_key}", value = st.session_state.new_pipeline['fields'][key])
        with c2:
           st.session_state.new_pipeline['descriptions'][key] = st.text_input(f"Field {i + 1} description", key=f"textDesc{description_key}", value = st.session_state.new_pipeline['descriptions'][key])
        with c3:
            st.markdown('<br/>', unsafe_allow_html=True)
            st.session_state.new_pipeline[f'delete{field_key}'] = st.button("❌", key=f"delete{field_key}", on_click=backend.delete_field, args=(key,))

def add_buttons_for_new_pipeline(pipeline_name, supabaseObj):
    """
    Displays add and submit buttons for the new pipeline form.

    Args:
        pipeline_name (str): Name of the pipeline.
        supabaseObj: Supabase object for interacting with Supabase service.
    """
    cols = st.columns([6, 2.5, 3, 2.5, 6])
    cols[1].button("➕ Add field", on_click=backend.add_field, key=f'add_f_new_pipe')
    # Submit button for the form
    submit_button =  cols[2].button("💾 Save Pipeline", key='save', on_click=backend.save_pipeline, args = (supabaseObj, pipeline_name,))
    # Clear button
    clear_button = cols[3].button(":leftwards_arrow_with_hook: Reset", key='reset', on_click=backend.reset_form)


## Tables --------------------------------------------------------------------------------------------------------------
def display_selectable_table(df: pd.DataFrame, column_configuration: dict) -> pd.DataFrame:
    """
    Displays a DataFrame as an editable table with a selectable column and custom column configurations.

    Args:
        df (pd.DataFrame): The DataFrame to be displayed.
        column_configuration (dict): Dictionary defining the configuration for each column in the DataFrame.

    Returns:
        pd.DataFrame: The DataFrame with an added 'Select' column indicating selected rows.
    """
    df.insert(0, "Select", False)
    # Update selection from session state
    if 'config' in df.columns and len(df) == len(st.session_state.pipeline_selection):
        for _id in df['id'].unique():
            df.loc[df['id']==_id, "Select"] = st.session_state.pipeline_selection[_id]
    df = df.sort_values('created_at', ascending=False)
    # Display table
    df_editor = st.data_editor(
        df[['Select', 'name', 'created_at'] + (['config'] if 'config' in df.columns else ['status'])],
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True,
    )
    if 'id' in df.columns:
        df_editor['id'] = df['id']
    # Save selection in session_state
    if 'config' in df.columns:
        st.session_state.pipeline_selection = df_editor.set_index('id')['Select'].to_dict()
    return df_editor

# Metric widgets -------------------------------------------------------------------------------------------------------
def display_metrics_kyc(metrics: dict) -> None:
    """
    Displays KYC-related metrics using Streamlit widgets.
    
    Parameters:
    metrics (dict): A dictionary containing computed metrics with the following keys:
                    - 'Files': [number_of_files, percentage_of_used_files]
                    - 'Pipelines': [number_of_pipelines, percentage_of_used_pipelines]
                    - 'OCR': [number_of_files_processed_by_OCR, percentage_of_files_processed_by_OCR]
                    - 'KIE': [number_of_files_processed_by_KIE, percentage_of_files_processed_by_KIE]

    """
    # Titles 
    cols = st.columns([14, 8, 20])
    cols[0].markdown('<center><i><h><u>Data tracking</u></h5></i></center>', unsafe_allow_html=True)
    cols[2].markdown('<center><i><h6><u>Process tracking</u></h6></i></center>', unsafe_allow_html=True)
    # Metrics
    cols = st.columns([2, 8, 1, 8, 10, 8, 1, 8])
    metrics_keys = ['Files', 'Pipelines', 'OCR', 'KIE']
    metrics_titles = ['\# Files', '\# Pipelines', '\# Files OCR', '\# Files KIE']
    j = 1 
    for i in range(len(cols)//2):
        cols[i+j].metric(metrics_titles[i], metrics[metrics_keys[i]][0], f'{metrics[metrics_keys[i]][1]}%' if metrics_keys[i] in ['OCR', 'KIE'] else '')
        j += 1

def display_ocr_filters(unused_files_paths: list, use_all: bool = False) -> list:
    """
    Displays a multi-select widget for choosing files to process from a given list of file paths.
    
    Args:
        unused_files_paths (list): A list of file paths that are not yet processed.
        use_all (bool, optional): If True, disables the multi-select widget and returns all file paths. Default is False.
    
    Returns:
        list: A list of selected file paths or all file paths if use_all is True.
    """
   
    name_to_path = {filepath.split('/')[1]: filepath for filepath in unused_files_paths}
    filenames = list(name_to_path.keys())
    filepaths = list(name_to_path.values())
    selected_filenames = st.multiselect('Choose files to process', filenames, disabled=use_all)
    if len(unused_files_paths) == 0:
        return []
    if use_all:
        return filepaths
    return [name_to_path[name] for name in selected_filenames]


def display_kie_filters() -> dict:
    """
    Displays controls for configuring the number of process configurations and 
    toggles for applying the process on all unprocessed files or all files.
    
    Returns:
        dict: A dictionary containing:
            - 'use_all' (bool): Indicates whether to apply on all files.
            - 'use_all_unprocessed' (bool): Indicates whether to apply on all unprocessed files.
            - 'n_config' (int): The number of process configurations selected.
    """
    cols = st.columns([5, 2.5, 2])
    cols[1].markdown('<br/>', unsafe_allow_html=True), cols[2].write('<br/>', unsafe_allow_html=True)
    n_config = cols[0].selectbox('Number of process configurations', range(1, 5))
    use_all_unprocessed_files = cols[1].toggle('Apply on all unprocessed files')
    use_all_files = cols[2].toggle('Apply on all files')
    return {'use_all': use_all_files, 'use_all_unprocessed': use_all_unprocessed_files, 'n_config': n_config}


def display_form_kie(df_files: pd.DataFrame, df_pipelines: pd.DataFrame, df_results: pd.DataFrame, kie_filters: dict) -> dict:
    """
    Displays a form for configuring KIE (Knowledge Information Extraction) settings including file selection and pipeline selection.
    
    Args:
        df_files (pd.DataFrame): DataFrame containing information about the files.
        df_pipelines (pd.DataFrame): DataFrame containing information about the pipelines.
        df_results (pd.DataFrame): DataFrame containing the results of previous processing.
        kie_filters (dict): A dictionary with filters for configuration. Expected keys are:
            - 'use_all' (bool): If True, selects all files.
            - 'use_all_unprocessed' (bool): If True, selects only unprocessed files.
            - 'n_config' (int): Number of configurations to set up.
    
    Returns:
        dict: A dictionary containing:
            - 'filepaths' (list): A list of selected file paths for each configuration.
            - 'pipelines' (list): A list of selected pipelines for each configuration.
    """
    chosen_filepaths = []
    chosen_pipelines = []
    # Loop on number of configurations
    for i in range(kie_filters['n_config']):
        st.markdown(f'###### Configuration {i+1}')
        # File filters
        cols = st.columns(2)
        disabled = False
        kie_files = df_files.dropna(subset=['ocr_json'])['name'].tolist()
        if len(df_results)!=0: 
            kie_unprocessed_files = list(set(kie_files).intersection(df_files[df_files['id'].map(lambda x: x not in df_results.file_id.unique())]['name'].tolist()))
        else:
            kie_unprocessed_files = []
        if kie_filters['use_all']:
            chosen_filepaths.append(kie_files)
            cols[0].multiselect('Choose files', [], disabled=True, key=f'msfile1{i}')
        elif kie_filters['use_all_unprocessed']:
            chosen_filepaths.append(kie_unprocessed_files)
            cols[0].multiselect('Choose files', [], disabled=True, key=f'msfile2{i}')
        else:
            chosen_filepaths.append(cols[0].multiselect('Choose files', kie_files, key=f'msfile3{i}'))
        # Pipeline filters
        pipelines = df_pipelines['name'].tolist()
        chosen_pipelines.append(cols[1].multiselect('Choose a pipeline(s)', pipelines, key=f'mspipe{i}'))
    
    form_result = {'filepaths': [], 'pipelines': []}
    for i in range(len(chosen_filepaths)):
        if len(chosen_filepaths[i]) != 0 and len(chosen_pipelines[i]) != 0:
            form_result['filepaths'].append(chosen_filepaths[i])
            form_result['pipelines'].append(chosen_pipelines[i])
    return form_result

# File reader------------------------------------------------------------------------------------------------------------
def display_file_reader():
    """
    Displays a file uploader in the sidebar for uploading PDF files and sets the PDF reference in session state.
    
    Returns:
        UploadedFile: The uploaded PDF file.
    """
    files = st.file_uploader("Upload file", accept_multiple_files=True, key=f"uploader_{st.session_state.uploader_key}")
    return files

## Images --------------------------------------------------------------------------------------------------------------
@st.cache_data
def display_original_image(uploaded_file, ocr_results):
    """
    Displays the uploaded image with OCR results as rectangles on the image using image_zoom component.

    Args:
        uploaded_file (UploadedFile): The uploaded image file.
        ocr_results (list): List of OCR results containing bounding boxes and text.
    """
    image = Image.open(io.BytesIO(uploaded_file))
    draw = ImageDraw.Draw(image)
    for res in ocr_results:
        for line in res:
            box = [tuple(point) for point in line[0]]
            box = [(min(point[0] for point in box), min(point[1] for point in box)),
                   (max(point[0] for point in box), max(point[1] for point in box))]
            txt = line[1][0]
            draw.rectangle(box, outline="red", width=2)
    size = 450 if image.size[1] - image.size[0] < 200 else 630
    with st.expander('Original document', expanded=True):
        image_zoom(image, keep_resolution=True, size=size)

@st.cache_data
def display_reconstructed_image(uploaded_file, ocr_results):
    """
    Displays a reconstructed version of the uploaded image with OCR results using image_zoom component.

    Args:
        uploaded_file (UploadedFile): The uploaded image file.
        ocr_results (list): List of OCR results containing bounding boxes and text.
    """
    image = Image.open(io.BytesIO(uploaded_file))
    white_image = Image.new("RGB", image.size, "white").convert("RGB")
    draw = ImageDraw.Draw(white_image)
    font = ImageFont.truetype(config.FONT_PATH, size=10)
    for res in ocr_results:
        for line in res:
            box = [tuple(point) for point in line[0]]
            box = [(min(point[0] for point in box), min(point[1] for point in box)),
                   (max(point[0] for point in box), max(point[1] for point in box))]
            txt = line[1][0]
            draw.rectangle(box, outline="red", width=2)
            draw.text((box[0][0], box[0][1]), txt, fill="black", font=font)
    size = 500 if image.size[1] - image.size[0] < 200 else 680
    with st.expander('Reconstructed document', expanded=True):
        image_zoom(white_image, keep_resolution=True, size=size)
        
@st.cache_data
def display_original_image_kie(uploaded_file, filtered_ocr_results, titles_dict):
    """
    Displays the uploaded image with OCR results as rectangles on the image using image_zoom component.

    Args:
        uploaded_file (UploadedFile): The uploaded image file.
        ocr_results (list): List of OCR results containing bounding boxes and text.
    """
    image = Image.open(io.BytesIO(uploaded_file))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(config.FONT_PATH, size=10)
    for res in filtered_ocr_results:
        for line in res:
            box = [tuple(point) for point in line[0]]
            box = [(min(point[0] for point in box), min(point[1] for point in box)),
                   (max(point[0] for point in box), max(point[1] for point in box))]
            txt = line[1][0]
            title = titles_dict[txt]
            draw.rectangle(box, outline="red", width=2)
            draw.text((box[1][0]+10, box[1][1]-15), title, fill="black", font=font)
    size = 750 if image.size[1] - image.size[0] < 200 else 800
    with st.expander('Original document', expanded=True):
        image_zoom(image, keep_resolution=True, size=size)

# UI utilities ----------------------------------------------------------------------------------------------
def initUI() -> None:
    """
    Initializes the UI settings including page layout and title, 
    and reduces the white space at the top and sidebar of the page.
    """
    st.set_page_config(layout="wide", page_title=config.PAGE_TITLE)
    remove_white_space()
    style_data_editor()
    format_metrics()
    
def remove_white_space() -> None:
    """
    Reduces whitespace at the top of the page and adjusts the sidebar width.
    """
    st.markdown("""
                <style>
                       .block-container {
                            padding-top: 0.3rem;
                            padding-bottom: 0rem;
                            padding-left: 5rem;
                            padding-right: 5rem;
                        }
                       div[data-testid="stSidebarUserContent"] > div{
                           margin-top:-60px;
                        }
                       .css-1aumxhk {
                            background-color: #011839;
                            background-image: none;
                            color: #ffffff
                            }
                </style>
                """, unsafe_allow_html=True)

def style_data_editor() -> None:
    """
    Style stDataFrame for black theme suitable UI
    
    """
    st.markdown(
        """
        <style>
        .stDataFrame, .stDataFrame table {
            background-color: black;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def format_metrics():
    """
    Set metrics formatting

    """
    css = """
          <style>
          label[data-testid="stMetricLabel"] > div > div[data-testid="stMarkdownContainer"] > p {font-size: 110%;font-weight: bold;!important;}
          div[data-testid="stMetricValue"] > div  {font-size: 80%;}
          [data-testid="metric-container"] label {width: fit-content;margin: auto;}
          [data-testid="metric-container"] {width: fit-content; margin: auto;}
          [data-testid="metric-container"] > div {width: fit-content;margin: auto;}
          </style>
          """
    st.markdown(css, unsafe_allow_html=True)