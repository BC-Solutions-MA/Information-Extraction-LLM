import requests
import config
import streamlit as st
import json
import pandas as pd
import backend

@st.cache_data
def perform_ocr_with_base64(file):
    """
    Perform OCR on a file using an API that accepts a base64 encoded string.

    Args:
    file (BytesIO): The file uploaded via Streamlit.

²    Returns:
    dict: The OCR result from the API containing recognized text and other details.
    """
    base64_file = backend.file_to_base64(file)
    data = {"base64_str": base64_file}
    url = "{}ocr/predict-by-base64".format(config.OCR_API_ENDPOINT)
    response = requests.post(url, json=data)
    if response.status_code == 200:
        ocr_result = response.json()
        return ocr_result['data']
    else:
        st.error(f"OCR API request failed with status code: {response.status_code}")
        return None

@st.cache_data
def reconstruct_text(ocr_results: dict) -> str:
    """
    Reconstruct text from OCR results by organizing recognized text based on their positions.

    Args:
    ocr_results (dict): The OCR results containing bounding boxes and recognized text.

    Returns:
    str: The reconstructed text in the correct reading order.
    """
    boxes = [ocr_results[0][i][0] for i in range(len(ocr_results[0]))]
    data = [ocr_results[0][i][0] + ocr_results[0][i][1] for i in range(len(ocr_results[0]))]
    df = pd.DataFrame(data, columns=['p1', 'p2', 'p3', 'p4', 'text', 'score']) 
    for i in [1, 2, 3, 4]:
        df[f'x{i}'] = [x[0] for x in df[f'p{i}']]
        df[f'y{i}'] = [x[1] for x in df[f'p{i}']]
    line_threshold = 15  # Adjust this threshold based on the expected line height
    df['line'] = (df['y1'].diff().abs() > line_threshold).cumsum()
    df = df.sort_values(by=['line', 'x1']).reset_index(drop=True)
    reconstructed_text = ""
    for i, row in df.iterrows():
        if i == 0:
            reconstructed_text += row.text
        elif row.line == df.iloc[i-1].line:
            if abs(row.x1 - df.iloc[i-1].x1) < 40:
                reconstructed_text += f' {row.text}'
            else:
                reconstructed_text += f' | {row.text}'
        else:
            reconstructed_text += f'\n{row.text}'
    return reconstructed_text

