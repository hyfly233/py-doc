import logging
import os
import time
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from PIL import Image
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    TableStructureOptions,
    TableFormerMode,
)
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption
)
from docling_core.types import DoclingDocument
from docling_core.types.doc import (
    TableItem,
    ProvenanceItem
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
_log = logging.getLogger(__name__)


class TableLocation:
    def __init__(self, page_no: int, name: str, rect: tuple[float, float, float, float]):
        self.page_no = page_no
        self.name = name
        self.rect = rect

def main():
    pdf_path: str = os.getenv('PDF_PATH')
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]

    # docling 识别表格并获取 bbox
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=False,  # 启用单元格匹配
        mode=TableFormerMode.FAST
    )

    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=10,
        device=AcceleratorDevice.AUTO,
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            ),
        }
    )

    start_time = time.time()
    # 格式化时间
    _log.info(
        f"开始转换文档，开始时间 [{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))}] ..........")

    input_doc_path = Path(pdf_path)
    conv_result = converter.convert(input_doc_path)

    end_time = time.time()
    _log.info(f"转换文档结束，完成时间 [{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))}] ..........")
    _log.info(f"转换文档状态 {conv_result.status} 耗时 [{end_time - start_time}] s ..........")

    _log.info(f"###########################")

    _log.info(f"文档的页数 {len(conv_result.pages)} ---- ")
    for i, page in enumerate(conv_result.pages):
        _log.info(f"第 {i + 1} 页 - "
                  f"pageNo {page.page_no} - "
                  f"高度: {page.size.height} 宽度: {page.size.width} - "
                  )

    document: DoclingDocument = conv_result.document
    # 获取 table 的数量、位置
    tables: List[TableItem] = document.tables
    _log.info(f"文档的表格数量 {len(tables)} ---- ")

    table_locations: List[TableLocation] = []

    for i, table in enumerate(tables):

        prov: List[ProvenanceItem] = table.prov
        location: str = ""
        for e in prov:
            page_no = e.page_no
            bbox = e.bbox

            t_height = bbox.height
            t_width = bbox.width

            location += (
                f"第 {page_no} 页 - "
                f"表格高度: {t_height} 宽度: {t_width} - "
                f"表格位置: left {bbox.l} top {bbox.t} right {bbox.r} bottom {bbox.b} - "
            )

            # docling 的坐标与 fitz 的坐标系 y 轴是相反的
            table_locations.append(TableLocation(page_no, f"p{page_no}_t{i}", (bbox.l, bbox.t, bbox.r, bbox.b)))

    _log.info(f"###########################")

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

            # docling 的坐标与 fitz 的坐标系 y 轴是相反的
            # 坐标系转换
            new_t = page_height - t
            new_b = page_height - b

            _log.info(f"表格 {table_location.name} 位置: left {l} top {new_t} right {r} bottom {new_b} - ")

            # 限制在页面范围内
            l = max(0, min(l, page_width))
            r = max(0, min(r, page_width))
            new_t = max(0, min(new_t, page_height))
            new_b = max(0, min(new_b, page_height))

            safe_rect = (l, new_t, r, new_b)

            clip: fitz.Rect = fitz.Rect(safe_rect)
            pix: fitz.Pixmap = page.get_pixmap(clip=clip, dpi=200)
            # 保存为图片
            img: Image.Image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            png_name = f"{table_location.name}.png"
            img.save(png_name)
            _log.info(f"截图已保存为: {png_name}")


if __name__ == '__main__':
    main()