import os

from docx import Document
from dotenv import load_dotenv

load_dotenv()


def add_comment(file_path):
    if file_path.endswith('.docx'):
        doc = Document(file_path)
        doc.add_page_break()
        paragraph = doc.add_paragraph("这是一个新的段落。")
        doc.add_comment(
            runs=paragraph.runs,
            text="这是一个评论。",
            author="作者名",
            initials="作者缩写",
        )
        doc.save(file_path)


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    add_comment(word_path)
