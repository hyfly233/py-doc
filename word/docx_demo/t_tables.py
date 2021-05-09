import os

from docx import Document
from dotenv import load_dotenv

load_dotenv()


def parse_document_tables(file_path):
    if file_path.endswith('.docx'):
        doc = Document(file_path)

        print(f"表格个数: {len(doc.tables)}")

        for i, table in enumerate(doc.tables):
            for j, row in enumerate(table.rows):
                for k, cell in enumerate(row.cells):
                    print(f"表格 {i + 1}，行 {j + 1}，列 {k + 1}，内容: {cell.text}")

                print("----------")

            print("=====================")

        return doc


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    parse_document_tables(word_path)
