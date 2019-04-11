import os

import fitz  # PyMuPDF
import pymupdf.table
from PIL import (Image)
from dotenv import load_dotenv


load_dotenv()

os.environ["TESSDATA_PREFIX"] = os.getenv("TESSDATA_PREFIX")


def main():
    pdf_path: str = os.getenv('PDF_PATH')

    doc: fitz.Document = fitz.open(pdf_path)
    page = doc[0]  # 第1页

    # 对整页进行 OCR，返回识别到的文本
    pix: fitz.Pixmap = page.get_pixmap(dpi=300)
    pix.pdfocr_save("./test.pdf")


if __name__ == '__main__':
    main()