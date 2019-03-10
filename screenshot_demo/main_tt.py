import logging
import os
from typing import List

import fitz  # PyMuPDF
import torch
from PIL import Image
from dotenv import load_dotenv
from transformers import TableTransformerForObjectDetection, DetrImageProcessor

from screenshot_demo.main_docling import TableLocation

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
_log = logging.getLogger(__name__)

model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-detection")


def main():
    """
    从 PDF 中截取表格区域并保存为图片
    例外：PDF 中有图片，图片中有表格，无法截取
    """
    pdf_path: str = os.getenv('PDF_PATH')
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]

    # 打开PDF
    doc: fitz.Document = fitz.open(pdf_path)
    table_locations: List[TableLocation] = []

    detr_image_processor = DetrImageProcessor()
    for page_number in range(len(doc)):
        page = doc[page_number]
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        encoding = detr_image_processor(img, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**encoding)

        width, height = img.size

        _log.info(f"第 {page_number + 1} 页 - 图片大小: {img.size}")

        # 计算缩放比例
        scale_x = page.rect.width / img.width
        scale_y = page.rect.height / img.height

        processed_result = detr_image_processor.post_process_object_detection(outputs,
                                                                              threshold=0.7,
                                                                              target_sizes=[(height, width)])

        for results in processed_result:
            scores = results['scores']
            labels = results['labels']
            boxes = results['boxes']

            print(f"第 {page_number + 1} 页检测到 {len(boxes)} 个表格/对象")
            for i, box in enumerate(boxes):
                (xmin, ymin, xmax, ymax) = box.tolist()
                print(f"  表格 {i} - xmin: {xmin}, ymin: {ymin}, xmax: {xmax}, ymax: {ymax}")

                # 传入给模型的图片是经过缩放的，获取到的坐标需要还原
                padding = 8  # 尝试 5~20，看实际效果

                # 还原到 PDF 页面坐标
                xmin_pdf = xmin * scale_x
                ymin_pdf = ymin * scale_y
                xmax_pdf = xmax * scale_x
                ymax_pdf = ymax * scale_y

                # 加 padding，并确保不超出页面范围
                xmin_pdf = max(0, xmin_pdf - padding)
                ymin_pdf = max(0, ymin_pdf - padding)
                xmax_pdf = min(page.rect.width, xmax_pdf + padding)
                ymax_pdf = min(page.rect.height, ymax_pdf + padding)

                table_locations.append(TableLocation((page_number + 1),
                                                     f"p{page_number + 1}_t{i}",
                                                     (xmin_pdf, ymin_pdf, xmax_pdf, ymax_pdf)))

    if len(table_locations) > 0:
        # 打开PDF
        doc: fitz.Document = fitz.open(pdf_path)
        for table_location in table_locations:
            # fitz 获取对应的 page
            page: fitz.Page = doc[table_location.page_no - 1]  # page_no 从 1 开始
            l, t, r, b = table_location.rect

            page_height = page.rect.height
            page_width = page.rect.width

            _log.info(f"fitz 打开的第 {table_location.page_no} 页 高度: {page_height} 宽度: {page_width} - ")
            _log.info(f"表格 {table_location.name} 位置: left {l} top {t} right {r} bottom {b} - ")

            safe_rect = (l, t, r, b)

            clip: fitz.Rect = fitz.Rect(safe_rect)
            pix: fitz.Pixmap = page.get_pixmap(clip=clip, dpi=200)
            # 保存为图片
            img: Image.Image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            png_name = f"{table_location.name}.png"
            img.save(png_name)
            _log.info(f"截图已保存为: {png_name}")


if __name__ == '__main__':
    main()
