import os
import tempfile
# import pytesseract
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image
from docx import Document
from docx2pdf import convert
from dotenv import load_dotenv

load_dotenv()


def main(inputs):
    file_data = inputs["contract_file"]
    file_name = inputs.get("file_name", "document")

    # 获取文件扩展名
    file_ext = os.path.splitext(file_name.lower())[1]

    # 根据文件类型进行处理
    if file_ext == '.pdf':
        pdf_data, text_content, page_info = process_pdf(file_data)
    elif file_ext in ['.doc', '.docx']:
        pdf_data, text_content, page_info = process_word_to_pdf(file_data)
    elif file_ext in ['.png', '.jpg', '.jpeg']:
        pdf_data, text_content, page_info = process_image_to_pdf(file_data)
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")

    return {
        "pdf_document": pdf_data,
        "extracted_text": text_content,
        "page_structure": page_info,
        "original_format": file_ext
    }


def process_pdf(file_data):
    """处理PDF文件"""
    doc = fitz.open(stream=file_data, filetype="pdf")

    text_content = ""
    page_info = []

    for page_num in range(doc.page_count):
        page = doc[page_num]
        page_text = page.get_text()
        text_content += f"\n--- 第{page_num + 1}页 ---\n{page_text}"

        # 获取文本块位置信息
        blocks = page.get_text("dict")
        page_info.append({
            "page_num": page_num,
            "blocks": blocks
        })

    # 保存PDF到字节流
    pdf_bytes = BytesIO()
    doc.save(pdf_bytes)
    doc.close()

    return pdf_bytes.getvalue(), text_content, page_info


# ??????

def process_word_to_pdf(file_data):
    """将Word转换为PDF并处理"""
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as word_file:
        word_file.write(file_data)
        word_file_path = word_file.name

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
        pdf_file_path = pdf_file.name

    try:
        # 使用python-docx提取文本
        doc = Document(word_file_path)
        text_content = ""
        page_info = []

        for i, paragraph in enumerate(doc.paragraphs):
            text_content += paragraph.text + "\n"

        # 转换为PDF
        convert(word_file_path, pdf_file_path)

        # 读取转换后的PDF
        with open(pdf_file_path, 'rb') as f:
            pdf_data = f.read()

        # 获取PDF的结构信息
        pdf_doc = fitz.open(pdf_file_path)
        for page_num in range(pdf_doc.page_count):
            page = pdf_doc[page_num]
            blocks = page.get_text("dict")
            page_info.append({
                "page_num": page_num,
                "blocks": blocks
            })
        pdf_doc.close()

        return pdf_data, text_content, page_info

    finally:
        # 清理临时文件
        os.unlink(word_file_path)
        os.unlink(pdf_file_path)


def process_image_to_pdf(file_data):
    """将图像转换为PDF并OCR识别"""
    # 打开图像
    image = Image.open(BytesIO(file_data))

    return

    # OCR识别文本
    # text_content = pytesseract.image_to_string(image, lang='chi_sim+eng')
    #
    # # 创建包含图像的PDF
    # pdf_doc = fitz.open()
    # page = pdf_doc.new_page(width=image.width, height=image.height)
    #
    # # 插入图像
    # img_bytes = BytesIO()
    # image.save(img_bytes, format='PNG')
    # img_bytes.seek(0)
    #
    # page.insert_image(page.rect, stream=img_bytes.getvalue())
    #
    # # 保存PDF
    # pdf_bytes = BytesIO()
    # pdf_doc.save(pdf_bytes)
    # pdf_doc.close()
    #
    # page_info = [{
    #     "page_num": 0,
    #     "ocr_text": text_content,
    #     "is_image": True
    # }]
    #
    # return pdf_bytes.getvalue(), text_content, page_info


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    res = main({
        "contract_file": open(word_path, "rb").read(),
        "file_name": "example.docx",
        "file_type": ".docx"
    })

    # pdf_path: str = os.getenv('PDF_PATH')
    # res = main({
    #     "contract_file": open(pdf_path, "rb").read(),
    #     "file_name": "example.pdf",
    #     "file_type": ".pdf"
    # })

    print(f"res: {res}")
