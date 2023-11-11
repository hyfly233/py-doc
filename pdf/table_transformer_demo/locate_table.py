import os

import torch
from PIL import Image
from dotenv import load_dotenv
from torch import Tensor
from transformers import TableTransformerForObjectDetection, DetrImageProcessor

from pdf.table_transformer_demo.utils import plot_results

# 加载 .env 文件
load_dotenv()

model = TableTransformerForObjectDetection.from_pretrained(
    "microsoft/table-transformer-detection"
)


def main():
    # file_path = hf_hub_download(repo_id="nielsr/example-pdf", repo_type="dataset", filename="example_pdf.png")
    file_path = os.getenv("IMAGE_PATH")

    image = Image.open(file_path).convert("RGB")
    width, height = image.size
    image.resize((int(width * 0.5), int(height * 0.5)))

    detr_image_processor = DetrImageProcessor()
    encoding = detr_image_processor(image, return_tensors="pt")
    encoding.keys()

    print(encoding["pixel_values"].shape)

    with torch.no_grad():
        outputs = model(**encoding)

    width, height = image.size
    print(f"图片大小: {width} x {height}")
    results = detr_image_processor.post_process_object_detection(
        outputs, threshold=0.7, target_sizes=[(height, width)]
    )[0]

    scores = results["scores"]
    labels = results["labels"]
    boxes: Tensor = results["boxes"]

    for i, box in enumerate(boxes):
        (xmin, ymin, xmax, ymax) = box.tolist()
        print(f"表格 {i} - xmin: {xmin}, ymin: {ymin}, xmax: {xmax}, ymax: {ymax}")

    plot_results(model, image, scores, labels, boxes)


if __name__ == "__main__":
    main()
