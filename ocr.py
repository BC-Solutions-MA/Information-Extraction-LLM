import requests
import config
import streamlit as st
import json
import pandas as pd
import backend


def unstructured_by_url(file_url: str):
    """
    Sends a POST request to the Unstructured API with the provided file URL.

    Args:
        file_url (str): The URL of the file to be processed.

    Returns:
        response (requests.Response): The response from the Unstructured API.
    """
    headers = {"Authorization": f"Bearer {config.UNSTRUCTURED_TOKEN}"}
    response = requests.post(config.UNSTRUCTURED_API_ENDPOINT, headers=headers, json={"language": "en", "file_url": file_url})
    if response.status_code==200:
        ocr_json = response.json()
        return ocr_json
    else:
        st.error(f'Request failed {response.status_code}')
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
    layout_data = get_layout_boxes(ocr_results)
    text = ""
    for layout in layout_data:
        text+=layout['text']+'\n'
    return text

# Utilities --------------------------------------------------------------------------------------------------------------------------------------
@st.cache_data
def get_individual_boxes(response: dict):
    """
    Extracts individual bounding boxes and text from the PaddleOCR results in the response.

    Args:
        response (dict): The response dictionary containing OCR results.

    Returns:
        dict: A dictionary where keys are page numbers and values are lists of tuples, 
              each containing a bounding box and the corresponding text.
    """
    paddle_bboxes = [x['metadata'] for x in response if x['type'] == 'Paddle_BBox']
    paddle_bboxes = {x['page_number']: [[el['bbox'], el['text']] for el in x['paddle_bbox']] for x in paddle_bboxes}
    return paddle_bboxes

@st.cache_data
def get_page_images(response: dict):
    """
    Extracts page images from the response.

    Args:
        response (dict): The response dictionary containing page images.

    Returns:
        dict: A dictionary where keys are page numbers and values are the corresponding base64-encoded images.
    """
    page_images = [x['metadata']['images'] for x in response if x['type'] == 'Page_Images']
    page_images = {x['page_number']: x['image'] for x in page_images[0]}
    return page_images

@st.cache_data
def get_layout_boxes(response: dict):
    """
    Extracts layout boxes from the response that are not of type 'Paddle_BBox' or 'Page_Images'.

    Args:
        response (dict): The response dictionary containing layout data.

    Returns:
        list: A list of layout data dictionaries.
    """
    layout_data = [x for x in response if x['type'] not in ['Paddle_BBox', 'Page_Images']]
    return layout_data




