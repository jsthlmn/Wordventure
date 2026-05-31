import pdfplumber
import pandas as pd
from google import genai
import json
import sqlite3
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic_settings import BaseSettings, SettingsConfigDict

import base64
from google.oauth2 import service_account
from langchain_google_genai import GoogleGenerativeAI
import os

from pydantic import BaseModel, Field
from typing import List, Optional


class Settings(BaseSettings):
    google_api_key: str
    gemini_model: str
    model_config = SettingsConfigDict(env_file=".env")


env = Settings()


def gemini():
    llm_gemini = GoogleGenerativeAI(
        model=env.gemini_model,
        temperature=0,
        google_api_key=env.google_api_key
    )
    return llm_gemini


llm = gemini()


# Pydantic
class VocabularyStructure(BaseModel):
    words: str = Field(description="The words of the vocabulary.")
    part_of_speech: str = Field(description="The part of speech of the vocabulary. e.g. n. (Noun), v. (Verb), adj. (Adverb), etc.")
    level: str = Field(description="The level of the words in English vocabulary. e.g. A1 (Elementary), A2 (Pre Intermediate), B1 (Intermediate), B2 (Upper Intermediate), C1 (Advanced).")


VOCABULARY_TEMPLATE = """
    You are a helpful assistant that helps people to learn English by separate a structure given vocabulary.
    Always return the output strictly in JSON format without any additional explanation or comments.

    To define words, part_of_speech, level, follow these steps:
    - Identify vocabulary input and consider which section each part belongs to based on vocabulary structure.
    - Then separate a words, part_of_speech, and level into different parts.
    - If the input have a multiple part_of_speech or level, always return result in the same part. Don't separate into multiple result.
    - Always return a valid output for these vocabulary parts.

    Final Verification:
    [] The output should always be in following format:
        {{
            "words": "<words>",
            "part_of_speech": "<part_of_speech>",
            "level": "<level>"
        }}
    
    {format_instruction}
    <example>
        INPUT 1: "wrong adj. A1, adv. B1, n. B2"
        OUTPUT 1: {{
            "words": "wrong",
            "part_of_speech": "adj. adv. n.",
            "level": "A1 B1 B2"
            }}
            
        INPUT 2: "zero number B2"
        OUTPUT 2: {{
            "words": "zero ",
            "part_of_speech": "number",
            "level": "B2"
            }}
    </example>

    INPUT: {{input}}
"""

conn = sqlite3.connect('vocabulary.db')

''' Read PDF content '''
text = ''
with pdfplumber.open('American_Oxford_5000.pdf') as pdf:
    for page in pdf.pages:
        text += page.extract_text() + '\n'

# print(text)
#
'''
Pattern for classifying words, also used to add newline after this patter, since text in the document formatted in -
multiple columns
'''
# pattern = ['A1 ', 'A2 ', 'B1 ', 'B2 ']
pattern2 = ['B2 ', 'C1 ']

# text = 'Test ini adalah tes A1 Ini juga test A2 apalagi ini B1 juga tes B2'

for i in pattern2:
    text = text.replace(i, i + '\n')
# print(text)

lines = [line.strip() for line in text.split('\n') if line.strip()]
vocab_df = pd.DataFrame({'vocabs': lines})
# print(vocab_df)

vocab_df = vocab_df.iloc[4:2010]
vocab_df = vocab_df[~vocab_df['vocabs'].str.contains('© Oxford University Press')]
print(vocab_df)

# AI Parts
# input_df = [['1', 'used to modal v. A2']]
# input_df = pd.DataFrame(input_df, columns=['id', 'vocabs'])

all_df = pd.DataFrame(columns=['input', 'words', 'part_of_speech', 'level'])

parser = JsonOutputParser(pydantic_object=VocabularyStructure)
template = VOCABULARY_TEMPLATE
prompt = PromptTemplate(
    template=template,
    input_variables=["input"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

chain = prompt | llm

for index, content in vocab_df.iloc[0:1999].iterrows():
    try:
        response = chain.invoke(content['vocabs'])
        parsed_response = parser.invoke(response)

        output_df = pd.DataFrame(parsed_response, index=[0])
        output_df['input'] = content['vocabs']
        output_df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Rearrange columns
        output_df = output_df[['input', 'words', 'part_of_speech', 'level']]

        all_df = pd.concat([all_df, output_df], ignore_index=True)

        # Insert into Sqlite database
        all_df.to_sql('vocabulary', conn, if_exists='append', index=False)
    except Exception as e:
        print(e)
        print(content['vocabs'])

# all_df = all_df.sort_values(by='input')
print(all_df)

#
# conn.close()
#
# all_df.to_excel('vocab2.xlsx', index=False)
