import logging
import os

import fitz  # PyMuPDF
import torch
from PIL import Image
from dotenv import load_dotenv
from transformers import TableTransformerForObjectDetection, DetrImageProcessor

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)
_log = logging.getLogger(__name__)

model = TableTransformerForObjectDetection.from_pretrained(
    "microsoft/table-transformer-detection"
)


def main():
    pdf_path: str = os.getenv("PDF_PATH")
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]

    # 打开PDF
    doc: fitz.Document = fitz.open(pdf_path)
    detr_image_processor = DetrImageProcessor()

    for page_number in range(len(doc)):
        page = doc[page_number]
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        encoding = detr_image_processor(img, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**encoding)

        width, height = img.size
        processed_result = detr_image_processor.post_process_object_detection(
            outputs, threshold=0.7, target_sizes=[(height, width)]
        )

        for results in processed_result:
            boxes = results["boxes"]

            print(f"第 {page_number + 1} 页检测到 {len(boxes)} 个表格/对象")
            for i, box in enumerate(boxes):
                (xmin, ymin, xmax, ymax) = box.tolist()
                print(
                    f"  表格 {i} - xmin: {xmin}, ymin: {ymin}, xmax: {xmax}, ymax: {ymax}"
                )

                png_name = f"png_{pdf_basename}_p{page_number + 1}_t{i}.png"
                cropped_img = img.crop((xmin, ymin, xmax, ymax))
                cropped_img.save(png_name)


if __name__ == "__main__":
    main()
