import os

from docx import Document
from dotenv import load_dotenv

load_dotenv()


def parse_document(file_path):
    if file_path.endswith('.docx'):
        doc = Document(file_path)
        text_blocks = []
        for i, para in enumerate(doc.paragraphs):
            for run in para.runs:
                text_blocks.append({
                    "paragraph_index": i,
                    "text": run.text,
                    "font": {
                        "name": run.font.name,
                        "size": run.font.size
                    }
                })
        return text_blocks, doc


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    text_blocks, doc = parse_document(word_path)
    print("text_blocks:", text_blocks)
