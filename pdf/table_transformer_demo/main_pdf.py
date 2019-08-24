import os

import fitz  # PyMuPDF
import torch
from PIL import Image
from dotenv import load_dotenv
from transformers import TableTransformerForObjectDetection, DetrImageProcessor

from pdf.table_transformer_demo.utils import plot_results

load_dotenv()

model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-detection")


def process_pdf(pdf_path):
    doc = fitz.open(pdf_path)

    detr_image_processor = DetrImageProcessor()
    for page_number in range(len(doc)):
        page = doc[page_number]
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        encoding = detr_image_processor(img, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**encoding)

        width, height = img.size

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

            # 可选：可视化
            plot_results(model, img, scores, labels, boxes)


if __name__ == '__main__':
    file_path = os.getenv('PDF_PATH')
    process_pdf(file_path)
