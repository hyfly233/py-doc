import os

from dotenv import load_dotenv

load_dotenv()

def parse_document(file_path):
    if file_path.endswith('.docx'):
        pass


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    parse_document(word_path)
