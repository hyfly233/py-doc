import os

from dotenv import load_dotenv

load_dotenv()

def parse_document(file_path):
    if file_path.endswith('.docx'):
        pass