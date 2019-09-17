import os

import fitz
from dotenv import load_dotenv

load_dotenv()


def parse_document(file_path):
    if file_path.endswith('.pdf'):
        doc = fitz.open(file_path)
        text_blocks = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            blocks = page.get_text("dict")
            for block in blocks["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_blocks.append({
                                "text": span["text"],
                                "bbox": span["bbox"],  # 位置坐标
                                "page": page_num,
                                "font": span["font"],
                                "size": span["size"]
                            })
        return text_blocks, doc


if __name__ == '__main__':
    pdf_path: str = os.getenv('PDF_PATH')
    text_blocks, doc = parse_document(pdf_path)
    # print("text_blocks:", text_blocks)
    print("doc:", doc)
