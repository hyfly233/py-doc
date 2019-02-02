import torch
from PIL import Image
from huggingface_hub import hf_hub_download
from transformers import TableTransformerForObjectDetection, DetrImageProcessor

from table_transformer_demo.utils import plot_results

model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-structure-recognition")


def main():
    file_path = hf_hub_download(repo_id="nielsr/example-pdf", repo_type="dataset", filename="example_pdf.png")
    image = Image.open(file_path).convert("RGB")
    width, height = image.size
    image.resize((int(width * 0.5), int(height * 0.5)))

    detr_image_processor = DetrImageProcessor()
    encoding = detr_image_processor(image, return_tensors="pt")
    encoding.keys()

    print(encoding['pixel_values'].shape)

    with torch.no_grad():
        outputs = model(**encoding)

    target_sizes = [image.size[::-1]]
    results = detr_image_processor.post_process_object_detection(outputs, threshold=0.6, target_sizes=target_sizes)[0]

    scores = results['scores']
    labels = results['labels']
    boxes = results['boxes']

    plot_results(model, image, scores, labels, boxes)

    print(model.config.id2label)


if __name__ == '__main__':
    main()
