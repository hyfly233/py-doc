import os

import fitz  # PyMuPDF
from PIL import Image
from dotenv import load_dotenv

load_dotenv()


def main():
    pdf_path: str = os.getenv('PDF_PATH')
    page_number: int = 0  # 第1页，0为起始
    rect: tuple[int, int, int, int] = (100, 100, 400, 300)  # (x0, y0, x1, y1) 左上和右下坐标

    # 打开PDF
    doc: fitz.Document = fitz.open(pdf_path)
    page: fitz.Page = doc[page_number]

    # 截图区域
    clip: fitz.Rect = fitz.Rect(rect)
    pix: fitz.Pixmap = page.get_pixmap(clip=clip, dpi=200)  # 可调整dpi提高清晰度

    # 保存为图片
    img: Image.Image = Image.frombytes("RGB", tuple[pix.width:int, pix.height:int], pix.samples)
    img.save("screenshot.png")
    print("截图已保存为 screenshot.png")


if __name__ == '__main__':
    main()
