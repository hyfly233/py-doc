import logging
import os

import fitz  # PyMuPDF
from PIL import Image
from dotenv import load_dotenv
from ultralytics import YOLO

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)
_log = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH")


def main():
    pdf_path: str = os.getenv("PDF_PATH")

    # 打开PDF
    doc: fitz.Document = fitz.open(pdf_path)

    model = YOLO(MODEL_PATH)  # pretrained YOLO11n model

    for page_number in range(len(doc)):
        page = doc[page_number]
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        processed_result = model(img, imgsz=960)

        for result in processed_result:
            boxes = result.boxes  # Boxes object for bounding box outputs
            result.show()  # display to screen
            result.save(filename="result.jpg")  # save to disk

            print(boxes.xyxy)

            print(f"第 {page_number + 1} 页检测到 {len(boxes.xyxy)} 个表格/对象")

            for i, box in enumerate(boxes.xyxy):
                (xmin, ymin, xmax, ymax) = box.tolist()
                print(
                    f"  表格 {i} - xmin: {xmin}, ymin: {ymin}, xmax: {xmax}, ymax: {ymax}"
                )

                png_name = f"p{page_number + 1}_t{i}.png"
                cropped_img = img.crop((xmin, ymin, xmax, ymax))
                cropped_img.save(png_name)


if __name__ == "__main__":
    main()
