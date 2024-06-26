from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser, OutputFixingParser
from langchain.chains import LLMChain
import streamlit as st
import pandas as pd
import config
from typing import Optional
from pydantic import BaseModel, Field
from typing import Dict

@st.cache_resource
def get_generator_model():
    """
    Initializes and returns the language model for generating responses.

    Returns:
        ChatOpenAI: An instance of the ChatOpenAI model with specified configurations.
    """
    llm = ChatOpenAI(
        openai_api_key="EMPTY",
        openai_api_base=config.GENERATOR_API_URI,
        max_tokens=config.MAX_TOKENS,
        temperature=0
    )
    return llm


@st.cache_resource
def get_extraction_chain(_generator, pipeline_config: dict):
    """
    Creates and returns the LLMChain and output parsers for information extraction.

    Args:
        _generator (ChatOpenAI): The language model used for generating responses.

    Returns:
        tuple: A tuple containing the LLMChain, StructuredOutputParser, and OutputFixingParser.
    """
    response_schemas = []
    for key, value in pipeline_config.items():
        # Schemas 
        response_schemas.append(ResponseSchema(name=key,
                                               description=value)
                                )
    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()
    # prompt
    prompt = ChatPromptTemplate(
    messages=[
        HumanMessagePromptTemplate.from_template(config.TEMPLATE_PROMPT)  
    ],
    input_variables=["text"],
    partial_variables={"format_instructions": format_instructions},
    output_parser=output_parser  # here we add the output parser to the Prompt template
    )
    new_parser = OutputFixingParser.from_llm(parser=output_parser, llm=_generator)
    # Create chain
    chain = LLMChain(llm=_generator, 
                     prompt=prompt)
    return chain, output_parser, new_parser

def generate_response(chain, output_parser, new_parser, text):
    """
    Generates and processes the response for a given input text using the specified chain and parsers.

    Args:
        chain (LLMChain): The language model chain used for generating responses.
        output_parser (StructuredOutputParser): The parser for structuring the output.
        new_parser (OutputFixingParser): The parser for fixing and refining the output.
        text (str): The input text for which the response is to be generated.

    Returns:
        dict: The parsed response containing extracted information.
    """
    # Reconstruct history
    response = chain.invoke({"text" : text})['text']
    try:      
        response = output_parser.parse(response)
    except:
        response = new_parser.parse(response)
    return response

