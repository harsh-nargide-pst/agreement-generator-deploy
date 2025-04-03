import fitz
import os
import re
from collections import Counter
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from PIL import Image as PILImage
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from typing import List, Tuple, Optional, Dict, Union
from reportlab.lib.colors import Color

PAGE_WIDTH, PAGE_HEIGHT = A4

def add_watermark(c, doc) -> None:
    """Adds a large semi-transparent 'DRAFT' watermark at the center of each page."""
    c.saveState()

    c.setFillColor(Color(0.85, 0.85, 0.85, alpha=0.3))

    text = "DRAFT"
    font_name = "Helvetica-Bold"
    font_size = 80
    c.setFont(font_name, font_size)

    c.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()

def extract_text_from_pdf(pdf_path: str, chunk_size: int = 1000) -> List[str]:
    """Extracts text from a PDF file and returns it in manageable chunks."""
    doc = fitz.open(pdf_path)
    full_text = "\n".join([page.get_text("text") for page in doc])
    chunks = [full_text[i: i + chunk_size] for i in range(0, len(full_text), chunk_size)]
    return chunks

def find_font_file(font_name: str, fonts_dir: str = "fonts") -> Optional[str]:
    """Searches for a font file in the project-specific fonts directory."""
    font_extensions = (".ttf", ".otf")
    for root, _, files in os.walk(fonts_dir):
        for file in files:
            if file.lower().startswith(font_name.lower()) and file.lower().endswith(font_extensions):
                return os.path.join(root, file)
    return None

def extract_fonts(pdf_path: str) -> Tuple[str, Optional[str]]:
    """Extracts the most common font from a PDF."""
    doc = fitz.open(pdf_path)
    font_counter = Counter()
    for page in doc:
        text_instances = page.get_text("dict")["blocks"]
        for block in text_instances:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_name = span["font"]
                        font_counter[font_name] += 1
    if not font_counter:
        return "Helvetica", None
    font_name, _ = font_counter.most_common(1)[0]
    font_file = find_font_file(font_name)
    return font_name, font_file

def resize_image(image_path: str, max_width: int = 80, max_height: int = 50) -> Optional[str]:
    """Resizes an image to fit within max dimensions while maintaining aspect ratio."""
    try:
        img = PILImage.open(image_path)
        img.thumbnail((max_width, max_height))
        resized_img_path = f"temp_resized_{os.path.basename(image_path)}"
        img.save(resized_img_path)
        return resized_img_path
    except Exception as e:
        return None

def doc_template(output_pdf_path: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

def get_styles(font_name: str, font_file: Optional[str]) -> Dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    custom_styles = {
        "heading1": ParagraphStyle(name='CustomHeading1', parent=styles['Heading1'], fontName=font_name if font_file else "Helvetica", fontSize=16, spaceAfter=2),
        "heading2": ParagraphStyle(name='CustomHeading2', parent=styles['Heading2'], fontName=font_name if font_file else "Helvetica", fontSize=14, spaceAfter=2),
        "heading3": ParagraphStyle(name='CustomHeading3', parent=styles['Heading3'], fontName=font_name if font_file else "Helvetica", fontSize=12, spaceAfter=2),
        "bullet": ParagraphStyle(name='CustomBullet', parent=styles['Normal'], fontName=font_name if font_file else "Helvetica", leftIndent=12, spaceAfter=5),
        "normal": ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontName=font_name if font_file else "Helvetica",
            fontSize=10,
            spaceAfter=2,
            alignment=4,
            leading=12
        ),
    }
    return custom_styles

def process_heading(line: str, custom_styles: Dict[str, ParagraphStyle]) -> Optional[Tuple[Paragraph, Spacer]]:
    if line.startswith('# '):
        return Paragraph(line[2:], custom_styles['heading1']), Spacer(1, 6)
    elif line.startswith('## '):
        return Paragraph(line[3:], custom_styles['heading2']), Spacer(1, 4)
    elif line.startswith('### '):
        return Paragraph(line[4:], custom_styles['heading3']), Spacer(1, 2)
    return None

def process_bullet(line: str, custom_styles: Dict[str, ParagraphStyle]) -> Paragraph:
    content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line[2:])
    return Paragraph('• ' + content, custom_styles['bullet'])

def process_table(
    lines: List[str],
    index: int,
    custom_styles: Dict[str, ParagraphStyle],
    doc: SimpleDocTemplate,
    temp_files: List[str]
) -> Tuple[Table, Spacer, int]:
    table_data = []
    header_row = [cell.strip() for cell in lines[index].split('|')[1:-1]]
    table_data.append([Paragraph(f"<b>{h}</b>", custom_styles['normal']) for h in header_row])
    index += 2

    while index < len(lines) and lines[index].startswith('|'):
        row_cells = []
        cells = [cell.strip() for cell in lines[index].split('|')[1:-1]]

        for cell in cells:
            img_match = re.search(r'!\[.*?\]\((.*?)\)', cell)
            if img_match:
                img_path = img_match.group(1)
                resized_img = resize_image(img_path)
                if resized_img:
                    row_cells.append(Image(resized_img, width=80, height=50))
                    temp_files.append(resized_img)
            else:
                formatted_cell = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', cell)
                row_cells.append(Paragraph(formatted_cell, custom_styles['normal']))

        table_data.append(row_cells)
        index += 1

    col_width = doc.width / len(header_row)
    table = Table(table_data, colWidths=[col_width] * len(header_row))
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    return table, Spacer(1, 12), index - 1

def create_pdf_file(
    content: str,
    output_pdf_path: str = "output.pdf",
    font_name: str = "Times-Roman",
    font_file: Optional[str] = "fonts/times-roman/Times-Roman.ttf",
    isDraft: bool = False,
    preserve_line_breaks: bool = True
) -> str:
    if not font_name or not font_file:
        font_name = "Times-Roman"
        font_file = "fonts/times-roman/Times-Roman.ttf"
    if font_name != "Times-Roman":
        pdfmetrics.registerFont(TTFont(font_name, font_file))

    temp_files: List[str] = []
    try:
        doc = doc_template(output_pdf_path)
        custom_styles = get_styles(font_name, font_file)

        left_aligned_style = ParagraphStyle(
            name='LeftAligned',
            parent=custom_styles['normal'],
            alignment=0
        )

        elements: List[Union[Paragraph, Spacer, Table, Image]] = []
        lines = content.split('\n')
        i = 0

        if preserve_line_breaks:
            while i < len(lines):
                line = lines[i].strip()

                if line.startswith('#'):
                    if heading := process_heading(line, custom_styles):
                        elements.extend(heading)
                elif line.startswith('- '):
                    elements.append(process_bullet(line, custom_styles))
                elif line.startswith('|') and i + 2 < len(lines) and lines[i+1].startswith('|---'):
                    table, spacer, i = process_table(lines, i, custom_styles, doc, temp_files)
                    elements.append(table)
                    elements.append(spacer)
                else:
                    img_match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
                    if img_match:
                        text_before_img = line[:img_match.start()].strip()
                        if text_before_img:
                            formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text_before_img)
                            elements.append(Paragraph(formatted_text, left_aligned_style))

                        img_path = img_match.group(2)
                        resized_img = resize_image(img_path)
                        if resized_img:
                            temp_files.append(resized_img)
                            img = Image(resized_img, width=80, height=50)
                            t = Table([[img]], colWidths=[doc.width])
                            t.setStyle(TableStyle([
                                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                ('LEFTPADDING', (0, 0), (0, 0), 0),
                                ('RIGHTPADDING', (0, 0), (0, 0), 0),
                                ('TOPPADDING', (0, 0), (0, 0), 0),
                                ('BOTTOMPADDING', (0, 0), (0, 0), 0),
                            ]))
                            elements.append(t)
                            elements.append(Spacer(1, 5))

                        text_after_img = line[img_match.end():].strip()
                        if text_after_img:
                            formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text_after_img)
                            elements.append(Paragraph(formatted_text, left_aligned_style))
                    elif line:
                        formatted_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                        elements.append(Paragraph(formatted_line, left_aligned_style))
                    else:
                        elements.append(Spacer(1, 10))

                i += 1
        else:
            text_buffer: List[str] = []

            while i < len(lines):
                line = lines[i].strip()

                is_special_format = (
                    not line or
                    line.startswith('#') or
                    line.startswith('-') or
                    (line.startswith('|') and i + 2 < len(lines) and lines[i+1].startswith('|---'))
                )

                if is_special_format:
                    if text_buffer:
                        combined_text = ' '.join(text_buffer)
                        combined_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', combined_text)

                        img_matches = list(re.finditer(r'!\[(.*?)\]\((.*?)\)', combined_text))
                        if img_matches:
                            current_pos = 0
                            for match in img_matches:
                                if match.start() > current_pos:
                                    text_segment = combined_text[current_pos:match.start()]
                                    if text_segment.strip():
                                        elements.append(Paragraph(text_segment, left_aligned_style))

                                img_path = match.group(2)
                                resized_img = resize_image(img_path)
                                if resized_img:
                                    temp_files.append(resized_img)
                                    img = Image(resized_img, width=80, height=50)
                                    t = Table([[img]], colWidths=[doc.width])
                                    t.setStyle(TableStyle([
                                        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                        ('LEFTPADDING', (0, 0), (0, 0), 0),
                                        ('RIGHTPADDING', (0, 0), (0, 0), 0),
                                        ('TOPPADDING', (0, 0), (0, 0), 0),
                                        ('BOTTOMPADDING', (0, 0), (0, 0), 0),
                                    ]))
                                    elements.append(t)
                                    elements.append(Spacer(1, 5))

                                current_pos = match.end()

                            if current_pos < len(combined_text):
                                text_segment = combined_text[current_pos:]
                                if text_segment.strip():
                                    elements.append(Paragraph(text_segment, left_aligned_style))
                        else:
                            elements.append(Paragraph(combined_text, custom_styles['normal']))

                        elements.append(Spacer(1, 6))
                        text_buffer = []

                    if heading := process_heading(line, custom_styles):
                        elements.extend(heading)
                    elif line.startswith('- '):
                        elements.append(process_bullet(line, custom_styles))
                    elif line.startswith('|') and i + 2 < len(lines) and lines[i+1].startswith('|---'):
                        table, spacer, i = process_table(lines, i, custom_styles, doc, temp_files)
                        elements.append(table)
                        elements.append(spacer)
                else:
                    text_buffer.append(line)

                i += 1

            if text_buffer:
                combined_text = ' '.join(text_buffer)
                combined_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', combined_text)

                img_matches = list(re.finditer(r'!\[(.*?)\]\((.*?)\)', combined_text))
                if img_matches:
                    current_pos = 0
                    for match in img_matches:
                        if match.start() > current_pos:
                            text_segment = combined_text[current_pos:match.start()]
                            if text_segment.strip():
                                elements.append(Paragraph(text_segment, left_aligned_style))

                        img_path = match.group(2)
                        resized_img = resize_image(img_path)
                        if resized_img:
                            temp_files.append(resized_img)
                            img = Image(resized_img, width=80, height=50)
                            t = Table([[img]], colWidths=[doc.width])
                            t.setStyle(TableStyle([
                                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                ('LEFTPADDING', (0, 0), (0, 0), 0),
                                ('RIGHTPADDING', (0, 0), (0, 0), 0),
                                ('TOPPADDING', (0, 0), (0, 0), 0),
                                ('BOTTOMPADDING', (0, 0), (0, 0), 0),
                            ]))
                            elements.append(t)
                            elements.append(Spacer(1, 5))

                        current_pos = match.end()

                    if current_pos < len(combined_text):
                        text_segment = combined_text[current_pos:]
                        if text_segment.strip():
                            elements.append(Paragraph(text_segment, left_aligned_style))
                else:
                    elements.append(Paragraph(combined_text, custom_styles['normal']))

        if isDraft:
            doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
        else:
            doc.build(elements)

        return output_pdf_path
    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
