import os

import fitz  # PyMuPDF
import pymupdf.table
from PIL import (Image)
from dotenv import load_dotenv

load_dotenv()


def main():
    pdf_path: str = os.getenv('PDF_PATH')
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]





if __name__ == '__main__':
    main()