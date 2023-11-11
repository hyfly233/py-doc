import logging
import os

import fitz  # PyMuPDF
import pymupdf.table
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)
_log = logging.getLogger(__name__)


def main():
    """
    从 PDF 中截取表格区域并保存为图片
    例外：PDF 中有图片，图片中有表格，无法截取
    """
    pdf_path: str = os.getenv("PDF_PATH")
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]

    # 打开PDF
    doc: fitz.Document = fitz.open(pdf_path)

    if doc.page_count > 0:
        for page in doc:
            find_tables: pymupdf.table.TableFinder = fitz.find_tables(page)

            _log.info("找到 %d 个表格", len(find_tables.tables))
            for i, table in enumerate(find_tables.tables):
                (x0, y0, x1, y1) = table.bbox

                # # 截图区域
                rect: tuple[int, int, int, int] = (
                    x0,
                    y0,
                    x1,
                    y1,
                )  # (x0, y0, x1, y1) 左上和右下坐标
                clip: fitz.Rect = fitz.Rect(rect)
                pix: fitz.Pixmap = page.get_pixmap(
                    clip=clip, dpi=200
                )  # 可调整dpi提高清晰度

                # 保存为图片
                img: Image.Image = Image.frombytes(
                    "RGB", [pix.width, pix.height], pix.samples
                )

                png_name = f"png_{pdf_basename}_p{page.number}_t{i}.png"
                img.save(png_name)
                _log.info("截图已保存为:", png_name)

            images = page.get_images()
            _log.info("找到 %d 张图片", len(images))
            # for img_index, image in enumerate(images):
            #     _log.info(image)


if __name__ == "__main__":
    main()
