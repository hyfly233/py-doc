import os
import uuid

import fitz
import pymupdf
from dotenv import load_dotenv

from common.document_chunk import BaseDocument
from common.utils import calculate_md5_file

load_dotenv()


def parse_document(doc: BaseDocument) -> BaseDocument | None:
    if doc.file_extension_name == "pdf":
        pdf = pymupdf.open(file_path)

        for page_num in range(pdf.page_count):
            page: fitz.Document = pdf[page_num]

            text = page.get_text("text")

            print(text)

    return None


if __name__ == "__main__":
    doc_id = str(uuid.uuid4())
    file_path = os.getenv("PDF_PATH")

    document = BaseDocument(
        doc_id=doc_id,
        file_name=os.path.basename(file_path),
        file_path=file_path,
        file_checksum=calculate_md5_file(file_path),
        total_size=None,
        file_extension_name="pdf",
        content=None,
        chunk_size=2000,
        chunk_overlap=200,
    )

    processed_doc = parse_document(document)

    # 处理后的文档
    if processed_doc is not None:
        print("Processed Document ID:", processed_doc.doc_id)
