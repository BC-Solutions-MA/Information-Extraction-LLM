import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import datetime
import backend, frontend, llm, ocr, config
import time

# Menu -------------------------------------------------------------------------------------------------------------------------------- M
def display_menu() -> str:
    """
    Displays the sidebar menu with options and styles defined in the config module.

    Returns:
        str: The chosen page from the menu options.
    """
    with st.sidebar:
        chosen_page = option_menu(
            menu_title=config.MENU_TITLE, 
            options=config.MENU_OPTIONS,
            menu_icon=config.ICON_MENU,
            icons=config.MENU_OPTION_ICONS,
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "rgba(0,0,0,0)"},
                "icon": {"color": "white", "font-size": "17px"},
                "container-xxl": {"line-height": "1em", 'padding': '0', 'margin': 0},
                "nav-link": {"font-size": "13px", "text-align": "left", "margin":"0px", "--hover-color": "#3b3b3b"},
                "nav-link-selected": {"background-color": "#3b3b3b", "font-size": "12px"},
            }
        )
    return chosen_page

# Menu redirection
def page_redirection(chosen_page: str, supabaseObj):
    """
    Redirects to different pages based on the chosen page.

    Args:
        chosen_page (str): The page chosen from the menu options.
        chain (LLMChain): The language model chain used for generating responses.
        output_parser (StructuredOutputParser): The parser for structuring the output.
        new_parser (OutputFixingParser): The parser for fixing and refining the output.
        supabaseObj (object): The Supabase client object.
    """
    if chosen_page == config.MENU_OPTIONS[0]:
        pipeline_manager(supabaseObj)
    elif chosen_page == config.MENU_OPTIONS[1]:
        ocr_page(supabaseObj)
    elif chosen_page == config.MENU_OPTIONS[2]:
        information_extraction(supabaseObj)

# Page 1: Pipeline manager ---------------------------------------------------------------------------------------------------------------- P1
def pipeline_manager(supabaseObj):
    """
    Manages the pipeline page

    Args:
        supabaseObj (object): The Supabase client object.
    """
    chosen_sub_page = display_menu_1()
    page_redirection_1(chosen_sub_page, supabaseObj)

# Sub Menu 1
def display_menu_1() -> str:
    """
    Displays the sub-menu for the pipeline manager with options and styles defined in the config module.

    Returns:
        str: The chosen sub-page from the sub-menu options.
    """
    chosen_page = option_menu(
        menu_title=config.MENU1_TITLE, 
        options=config.MENU1_OPTIONS,
        menu_icon=config.ICON_MENU1,
        icons=config.MENU1_OPTION_ICONS,
        default_index=0, 
        orientation='horizontal',
        styles={
            "container": {"padding": "0!important", "background-color": "rgba(0,0,0,0)"},
            "icon": {"color": "white", "font-size": "17px"},
            "container-xxl": {"line-height": "1em", 'padding': '0', 'margin': 0},
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "#3b3b3b"},
            "nav-link-selected": {"background-color": "#3b3b3b", "font-size": "14px"},
        }
    )
    return chosen_page

# Sub Menu 1 redirection
def page_redirection_1(chosen_page: str, supabaseObj):
    """
    Redirects to different sub-pages based on the chosen sub-page.

    Args:
        chosen_page (str): The sub-page chosen from the sub-menu options.
        supabaseObj (object): The Supabase client object.
    """
    if chosen_page == config.MENU1_OPTIONS[0]:
        file_storage_manager(supabaseObj)
    elif chosen_page == config.MENU1_OPTIONS[1]:
        extraction_pipeline(supabaseObj)
    elif chosen_page == config.MENU1_OPTIONS[2]:
        process_runner(supabaseObj)

# Sub Page 1 --------
def file_storage_manager(supabaseObj):
    """
    Manages the file storage page, displaying file explorer and upload components.

    Args:
        supabaseObj (object): The Supabase client object.
    """
    # Read Files table
    df_files = pd.DataFrame(supabaseObj.get_all_files())
    # Preprocess Files table
    df_files = backend.preprocess_files_table(df_files)
    # Display File Storage explorer
    with st.expander('File explorer', expanded=True):
        file_storage_explorer(supabaseObj, df_files)
    with st.expander('Upload files', expanded=True):
        files = frontend.display_file_reader()
        if len(files) != 0:
            backend.upload_files(supabaseObj, files, [file.name.split('/')[-1] for file in files], df_files)

# Sub² page 1_1
def file_storage_explorer(supabaseObj, df_files):
    """
    Displays the file storage explorer with options to select, download, and delete files.

    Args:
        supabaseObj (object): The Supabase client object.
        df_files (pd.DataFrame): The DataFrame containing file information.
    """
    # Display table editor
    df_files_editor = frontend.display_selectable_table(df_files[['name', 'created_at', 'status']], config.FILES_COLUMN_CONFIGURATION)
    # Filter on selected rows (files)
    df_files_filtered = df_files[df_files_editor['Select']]
    cols = st.columns([4, 8, 2, 2])
    # Download files
    if cols[0].toggle("Enable download"):
        files = []
        # Download from Bucket
        for i, row in df_files_filtered.iterrows():
            file_content = supabaseObj.download_file(row['name'])
            files.append({"name": row['name'], "content": file_content})
        # Zip files
        zip_buffer = backend.create_zip(files)
        # Enable client to download Zip through button
        cols[2].download_button(label="Download ZIP", data=zip_buffer, file_name="all_files.zip", mime="application/zip")
    # Delete files
    if cols[3].button('Delete files'):
        for i, row in df_files_filtered.iterrows():
            supabaseObj.delete_file(row['id'])
        st.experimental_rerun()

# Sub Page 2 ----------
def extraction_pipeline(supabaseObj):
    """
    Manages the extraction pipeline page, displaying pipeline explorer and components to add a new pipeline.

    Args:
        supabaseObj (object): The Supabase client object.
    """
    with st.expander('Pipeline explorer', expanded=True):
        pipeline_explorer(supabaseObj)
    with st.expander('Add a new pipeline', expanded=True):
        add_new_pipeline(supabaseObj)

# Sub² Page2_1
def pipeline_explorer(supabaseObj):
    """
    Displays the pipeline explorer page with selectable pipelines and their update forms.

    Args:
        supabaseObj (object): Supabase object for interacting with Supabase service.
        
    Retrieves all pipelines from the database using the Supabase object, preprocesses the data
    for display, and then presents a selectable table of pipelines. Users can choose a pipeline
    to update its name and configuration. Changes are saved back to the database upon submission.
    """
    # Read pipelines table
    df_pipelines = pd.DataFrame(supabaseObj.get_all_pipelines())
    # Preprocess pipelines table
    df_pipelines = backend.preprocess_pipelines_table(df_pipelines)
    # Display available pipelines in a selectable table
    df_pipelines_editor = frontend.display_selectable_table(df_pipelines[['id', 'name', 'created_at', 'config']], config.PIPELINES_COLUMN_CONFIGURATION)
    # Display form for updating selected pipeline details
    frontend.display_form_updater(supabaseObj, df_pipelines_editor, df_pipelines)


# Sub² Page2_2
def add_new_pipeline(supabaseObj):
    """
    Displays a form for adding a new pipeline with a name and configuration.

    Args:
        supabaseObj: Supabase object for interacting with Supabase service.
    """
    # Name input
    name = st.text_input("Pipeline Name", key='new_pipeline_name')
    # Configuration JSON input
    st.markdown("##### Features Configuration")
    frontend.display_fields_for_new_pipeline(name)
    frontend.add_buttons_for_new_pipeline(name, supabaseObj)
        
# Sub page 3 ------------------
def process_runner(supabaseObj):
    """
    Manages the overall processing of KYC-related tasks including reading tables,
    monitoring, OCR job management, and information extraction job management.

    Args:
        supabaseObj: The Supabase client object for database interaction.
    """
    # Read KYC db tables 
    df_dict = backend.read_tables_kyc(supabaseObj)
    df_files, df_pipelines, df_results = df_dict['Files'], df_dict['Pipelines'], df_dict['Results']
    # Display metrics - monitoring
    monitoring(supabaseObj, df_dict)
    # OCR Job Manager
    ocr_job_manager(supabaseObj, df_files, df_results)
    # Information extraction job manager
    kie_job_manager(supabaseObj, df_files, df_pipelines, df_results)

# Sub² page 3_1
def monitoring(supabaseObj, df_dict: dict):
    """
    Displays monitoring metrics for the KYC process using Streamlit.

    Args:
        supabaseObj: The Supabase client object for database interaction.
        df_dict (dict): A dictionary containing dataframes for 'Files', 'Pipelines', and 'Results'.
    """
    with st.expander('Monitoring', expanded=True):    
        # Compute metrics (# Files unused/ocr/kie and # Pipelines)
        metrics = backend.compute_metrics_kyc(supabaseObj, df_dict)
        # Display metrics
        frontend.display_metrics_kyc(metrics)

# Sub² page 3_2
def ocr_job_manager(supabaseObj, df_files: pd.DataFrame, df_results: pd.DataFrame):
    """
    Manages the OCR job processing including file selection, OCR application, and result saving.

    Args:
        supabaseObj: The Supabase client object for database interaction.
        df_files (pd.DataFrame): DataFrame containing file information.
        df_results (pd.DataFrame): DataFrame containing OCR results information.
    """
    # OCR process runner
    with st.expander('OCR Job Manager', expanded=True):        
        use_all = st.toggle('Apply OCR on all unprocessed files')
        
        with st.form("my_form"):
            # Unused files paths     
            unused_filepaths = df_files[df_files.ocr_json.isna()]['name'].unique()
            selected_filepaths = frontend.display_ocr_filters(unused_filepaths, use_all)
            # Button: Apply OCR
            cols = st.columns([4, 1, 4])
            submitted = cols[1].form_submit_button("Apply OCR")
            if submitted:
                # Download files
                files = [supabaseObj.download_file(filepath) for filepath in selected_filepaths]
                # Apply OCR w/ progress bar
                progress_bar = st.progress(0, text="OCR in progress. Please wait...")
                bar_incremetor = backend.Program()
                n_updated = 0
                for i, file in enumerate(files):    
                    file_id = df_files[df_files['name'].map(lambda x: x == selected_filepaths[i])]['id'].iloc[0]
                    if selected_filepaths[i].split('.')[-1].lower() not in ['jpg', 'png', 'jpeg']:
                        st.info(f'{selected_filepaths[i]} is not an image!')
                    else:
                        # Apply OCR
                        ocr_json = ocr.perform_ocr_with_base64(file)
                        ocr_text = ocr.reconstruct_text(ocr_json)
                        # Save OCR Result
                        supabaseObj.create_ocr_result(file_id, ocr_json, ocr_text)
                        n_updated += 1
                    bar_incremetor.increment()
                    progress_perc = round(bar_incremetor.progress / len(selected_filepaths) * 100)
                    progress_bar.progress(progress_perc, text=f"Progress: {progress_perc}%")
                st.markdown(f'<b> {n_updated} images have been processed!</b>', unsafe_allow_html=True)            
                st.experimental_rerun()
                
# Sub² Page 3_3
def kie_job_manager(supabaseObj, df_files: pd.DataFrame, df_pipelines: pd.DataFrame, df_results: pd.DataFrame):
    """
    Manages the Key Information Extraction (KIE) job by setting up the environment,
    displaying filters and forms, processing configurations, and applying the KIE 
    to the specified files.

    Args:
        supabaseObj: The Supabase object for database interaction.
        df_files (pd.DataFrame): DataFrame containing the files to be processed.
        df_pipelines (pd.DataFrame): DataFrame containing the pipeline configurations.
        df_results (pd.DataFrame): DataFrame to store the results of the KIE process.

    Returns:
        None
    """
    generator = llm.get_generator_model()
    with st.expander('Information Extraction Job Manager', expanded=True):
        kie_filters = frontend.display_kie_filters()
        with st.form('KIE'):
            kie_configs = frontend.display_form_kie(df_files, df_pipelines, df_results, kie_filters)
            submit_button = st.columns([8, 2, 8])[1].form_submit_button('Apply KIE')
            if submit_button:
                df_config = backend.kie_preprocess_config(df_files, df_pipelines, df_results, kie_configs)
                chains = backend.init_chains_by_config(generator, df_config, df_pipelines)
                df = backend.apply_kie_files(supabaseObj, df_config, df_files, df_results, chains)
                
        
# Page 2: OCR  ---------------------------------------------------------------------------------------------------------------------- P2
def ocr_page(supabaseObj):
    """
    Defines the OCR page functionality for uploading files and displaying OCR results.
    """
    # Read KYC db tables 
    df_dict = backend.read_tables_kyc(supabaseObj)
    df_files = df_dict['Files']
    # Choose file
    filepaths = df_files.dropna(subset=['ocr_json'])['name'].tolist()
    filepath = st.selectbox('Choose a processed file', filepaths)
    # Read file
    if len(filepaths):
        res_row = df_files[df_files['name']==filepath].iloc[0]
        image = supabaseObj.download_file(filepath)
        columns = st.columns([15, 1, 15])
        with columns[0]:
            frontend.display_original_image(image, res_row.ocr_json)
        with columns[2]:
            frontend.display_reconstructed_image(image, res_row.ocr_json)
            with st.expander('Text', expanded=True):
               st.markdown(res_row.ocr_text)


# Page 3: Information Extraction ---------------------------------------------------------------------------------------------------- P3
def information_extraction(supabaseObj):
    """
    Manages the information extraction process by reading KYC database tables,
    allowing the user to choose a processed file, and displaying the original
    image along with the extracted text.

    Args:
        supabaseObj: The Supabase object for database interaction.

    Returns:
        None
    """
    # Read KYC db tables 
    df_dict = backend.read_tables_kyc(supabaseObj)
    df_files, df_pipelines, df_results = df_dict['Files'], df_dict['Pipelines'], df_dict['Results']
   
    # Choose file
    cols = st.columns(2)
    pipeline_ids = df_results.dropna(subset=['llm_json']).pipeline_id.unique()
    pipeline_name = cols[0].selectbox('Choose a pipeline', df_pipelines.loc[df_pipelines['id'].map(lambda x: x in pipeline_ids), 'name'].unique())
    if pipeline_name and len(df_results.dropna(subset=['llm_json']))!=0:
        pipeline_id = df_pipelines.loc[df_pipelines['name']==pipeline_name, 'id'].iloc[0]
        # Read file
        filepaths = df_files[df_files['id'].map(lambda x: x in df_results[df_results.pipeline_id==pipeline_id].dropna(subset=['llm_json']).file_id.unique())]['name'].tolist()
        if len(filepaths)!=0:
            filepath = cols[1].selectbox('Choose a processed file', filepaths)
            res_row = df_results[df_results['file_id'] == df_files[df_files['name'] == filepath]['id'].iloc[0]].iloc[0]
            ocr_json = df_files[df_files['name']==filepath].ocr_json.iloc[0]
            image = supabaseObj.download_file(filepath)
            columns = st.columns([15, 1, 10])
            with columns[0]:
                bboxes, titles_dict = backend.filter_bboxes_kie(ocr_json, res_row.llm_json)
                frontend.display_original_image_kie(image, bboxes,titles_dict)
            with columns[2]:
                with st.expander('Text', expanded=True):
                   st.json(dict(sorted(res_row.llm_json.items())))
    else:
        filepath = cols[1].selectbox('Choose a processed file', [], disabled=True)


            