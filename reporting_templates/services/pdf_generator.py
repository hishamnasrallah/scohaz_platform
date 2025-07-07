import os
import time
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, Union

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.utils import timezone

from reportlab.lib.pagesizes import letter, A4, A3, legal
from reportlab.lib.units import inch, cm, mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import qr, code128, code39
from reportlab.lib.utils import ImageReader

import arabic_reshaper
from bidi.algorithm import get_display

from ..models import PDFTemplate, PDFTemplateElement, PDFGenerationLog, PDFTemplateVariable


class PDFGenerator:
    """
    Main PDF generation service with Arabic support
    """

    # Page size mapping
    PAGE_SIZES = {
        'A4': A4,
        'A3': A3,
        'letter': letter,
        'legal': legal,
    }

    # Text alignment mapping
    TEXT_ALIGN_MAP = {
        'left': TA_LEFT,
        'right': TA_RIGHT,
        'center': TA_CENTER,
        'justify': TA_JUSTIFY,
    }

    def __init__(self, template: PDFTemplate, language: str = None):
        self.template = template
        self.language = language or template.primary_language
        self.is_rtl = self.language == 'ar'
        self.page_width = 0
        self.page_height = 0
        self.canvas = None
        self.current_page = 1
        self.fonts_registered = False

        # Register fonts once
        self._register_fonts()

    def _register_fonts(self):
        """Register Arabic and custom fonts"""
        if self.fonts_registered:
            return

        fonts_dir = os.path.join(settings.BASE_DIR, 'fonts')
        if not os.path.exists(fonts_dir):
            os.makedirs(fonts_dir)

        # Arabic fonts
        arabic_fonts = {
            'Arabic': 'NotoSansArabic-Regular.ttf',
            'Arabic-Bold': 'NotoSansArabic-Bold.ttf',
            'Arabic-Light': 'NotoSansArabic-Light.ttf',
        }

        for font_name, font_file in arabic_fonts.items():
            font_path = os.path.join(fonts_dir, font_file)
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                except:
                    print(f"Warning: Could not register font {font_name}")

        self.fonts_registered = True

    def process_arabic_text(self, text: str) -> str:
        """Process Arabic text for proper RTL display"""
        if not text:
            return text

        # Reshape Arabic text
        reshaped_text = arabic_reshaper.reshape(text)
        # Apply bidi algorithm
        bidi_text = get_display(reshaped_text)
        return bidi_text

    def process_text(self, text: str) -> str:
        """Process text based on language"""
        if self.is_rtl and text:
            return self.process_arabic_text(text)
        return text

    def get_font_name(self, element: PDFTemplateElement) -> str:
        """Get appropriate font name based on language and style"""
        if self.is_rtl:
            if element.is_bold:
                return 'Arabic-Bold'
            return 'Arabic'

        font_base = element.font_family
        if element.is_bold and element.is_italic:
            return f"{font_base}-BoldOblique"
        elif element.is_bold:
            return f"{font_base}-Bold"
        elif element.is_italic:
            return f"{font_base}-Oblique"
        return font_base

    def calculate_position(self, x: float, y: float, width: float = 0) -> tuple:
        """Calculate position based on RTL/LTR and coordinate system"""
        # ReportLab uses bottom-left origin, we use top-left
        actual_y = self.page_height - y

        if self.is_rtl:
            # Mirror X coordinate for RTL
            actual_x = self.page_width - x - width
        else:
            actual_x = x

        return actual_x, actual_y

    def process_template_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Process Django-style template variables"""
        if not text or '{{' not in text:
            return text

        try:
            template = Template(text)
            rendered = template.render(Context(context))
            return rendered
        except Exception as e:
            print(f"Template processing error: {e}")
            return text

    def evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate element display condition"""
        if not condition:
            return True

        try:
            # Simple evaluation - can be enhanced with safer methods
            template = Template(f"{{% if {condition} %}}1{{% endif %}}")
            result = template.render(Context(context))
            return result == '1'
        except:
            return True

    def generate_pdf(self, context_data: Dict[str, Any],
                     output_stream: Optional[BytesIO] = None) -> BytesIO:
        """
        Generate PDF from template with context data

        Args:
            context_data: Dictionary containing data for template variables
            output_stream: Optional BytesIO stream to write to

        Returns:
            BytesIO object containing the generated PDF
        """
        start_time = time.time()

        if output_stream is None:
            output_stream = BytesIO()

        # Set up page
        page_size = self.PAGE_SIZES.get(self.template.page_size, A4)
        if self.template.orientation == 'landscape':
            page_size = (page_size[1], page_size[0])

        self.page_width, self.page_height = page_size

        # Create canvas
        self.canvas = canvas.Canvas(
            output_stream,
            pagesize=page_size,
            bottomup=0  # Use top-left origin
        )

        # Set document metadata
        self.canvas.setTitle(self.template.name)
        self.canvas.setAuthor(str(context_data.get('user', 'System')))
        self.canvas.setSubject(self.template.description or '')

        # Process elements
        self._process_elements(context_data)

        # Save PDF
        self.canvas.save()

        # Reset stream position
        output_stream.seek(0)

        # Log generation
        generation_time = time.time() - start_time
        self._log_generation(context_data, generation_time, 'completed')

        return output_stream

    def _process_elements(self, context_data: Dict[str, Any]):
        """Process all template elements"""
        # Get elements for current template
        elements = self.template.elements.filter(
            active_ind=True
        ).order_by('page_number', 'z_index', 'y_position')

        current_page = 1
        page_elements = []

        for element in elements:
            # Check if we need a new page
            if element.page_number and element.page_number > current_page:
                self._render_page_elements(page_elements, context_data)
                self.canvas.showPage()
                current_page = element.page_number
                page_elements = []

            # Check condition
            if element.condition and not self.evaluate_condition(
                    element.condition, context_data
            ):
                continue

            page_elements.append(element)

        # Render remaining elements
        if page_elements:
            self._render_page_elements(page_elements, context_data)

    def _render_page_elements(self, elements, context_data):
        """Render elements on current page"""
        # Draw watermark first if enabled
        if self.template.watermark_enabled and self.template.watermark_text:
            self._draw_watermark()

        # Draw elements by z-index
        for element in sorted(elements, key=lambda e: e.z_index):
            self._render_element(element, context_data)

        # Draw header/footer
        if self.template.header_enabled:
            self._draw_header(context_data)
        if self.template.footer_enabled:
            self._draw_footer(context_data)

    def _render_element(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Render individual element based on type"""
        method_map = {
            'text': self._draw_text,
            'dynamic_text': self._draw_dynamic_text,
            'image': self._draw_image,
            'dynamic_image': self._draw_dynamic_image,
            'line': self._draw_line,
            'rectangle': self._draw_rectangle,
            'circle': self._draw_circle,
            'table': self._draw_table,
            'barcode': self._draw_barcode,
            'qrcode': self._draw_qrcode,
            'signature': self._draw_signature_field,
            'page_break': self._handle_page_break,
        }

        method = method_map.get(element.element_type)
        if method:
            method(element, context_data)

    def _draw_text(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw static or dynamic text"""
        # Get text content based on language
        if self.language == 'ar' and element.text_content_ara:
            text = element.text_content_ara
        else:
            text = element.text_content

        # Process template variables
        text = self.process_template_variables(text, context_data)

        # Process for RTL if needed
        text = self.process_text(text)

        # Calculate position
        x, y = self.calculate_position(element.x_position, element.y_position)

        # Set font
        font_name = self.get_font_name(element)
        try:
            self.canvas.setFont(font_name, element.font_size)
        except:
            self.canvas.setFont('Helvetica', element.font_size)

        # Set color
        self.canvas.setFillColor(HexColor(element.font_color))

        # Handle text alignment
        if element.text_align == 'center':
            self.canvas.drawCentredString(x, y, text)
        elif element.text_align == 'right' or (
                element.text_align == 'left' and self.is_rtl
        ):
            self.canvas.drawRightString(x, y, text)
        else:
            self.canvas.drawString(x, y, text)

    def _draw_dynamic_text(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw dynamic text from data source"""
        # Get value from context using data source path
        value = self._get_value_from_path(element.data_source, context_data)

        # Convert to string and set as text content
        element.text_content = str(value) if value is not None else ''

        # Use regular text drawing
        self._draw_text(element, context_data)

    def _draw_line(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw a line"""
        x1, y1 = self.calculate_position(element.x_position, element.y_position)
        x2, y2 = self.calculate_position(
            element.x_position + (element.width or 100),
            element.y_position + (element.height or 0)
        )

        self.canvas.setStrokeColor(HexColor(element.stroke_color))
        self.canvas.setLineWidth(element.stroke_width)
        self.canvas.line(x1, y1, x2, y2)

    def _draw_rectangle(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw a rectangle"""
        x, y = self.calculate_position(
            element.x_position,
            element.y_position,
            element.width or 100
        )

        width = element.width or 100
        height = element.height or 50

        if element.fill_color:
            self.canvas.setFillColor(HexColor(element.fill_color))
            self.canvas.setStrokeColor(HexColor(element.stroke_color))
            self.canvas.rect(x, y - height, width, height, fill=1, stroke=1)
        else:
            self.canvas.setStrokeColor(HexColor(element.stroke_color))
            self.canvas.rect(x, y - height, width, height, fill=0, stroke=1)

    def _draw_image(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw an image"""
        if not element.image_source:
            return

        try:
            # Process template variables in image source
            image_path = self.process_template_variables(
                element.image_source, context_data
            )

            # Handle different image sources (URL, file path, etc.)
            if image_path.startswith('http'):
                # For URLs, you'd need to download first
                return

            # Calculate position
            x, y = self.calculate_position(
                element.x_position,
                element.y_position,
                element.width or 100
            )

            # Draw image
            self.canvas.drawImage(
                image_path,
                x, y - (element.height or 100),
                width=element.width or 100,
                height=element.height or 100,
                preserveAspectRatio=element.maintain_aspect_ratio
            )
        except Exception as e:
            print(f"Error drawing image: {e}")

    def _draw_table(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw a table from configuration"""
        config = element.table_config
        if not config:
            return

        # Extract table data from context
        data_source = config.get('data_source', '')
        table_data = self._get_value_from_path(data_source, context_data)

        if not table_data:
            return

        # Build table
        headers = config.get('headers', [])
        rows = []

        if headers:
            rows.append(headers)

        # Add data rows
        for item in table_data:
            row = []
            for col in config.get('columns', []):
                value = self._get_value_from_path(col, {'item': item})
                row.append(str(value) if value is not None else '')
            rows.append(row)

        # Create table
        x, y = self.calculate_position(element.x_position, element.y_position)

        table = Table(rows)

        # Apply table style
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), white),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ])

        table.setStyle(style)

        # Draw table
        table.wrapOn(self.canvas, element.width or 400, element.height or 300)
        table.drawOn(self.canvas, x, y)

    def _draw_qrcode(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw a QR code"""
        # Get data for QR code
        qr_data = self.process_template_variables(
            element.text_content, context_data
        )

        if not qr_data:
            return

        x, y = self.calculate_position(
            element.x_position,
            element.y_position,
            element.width or 100
        )

        # Create QR code
        qr_code = qr.QrCodeWidget(qr_data)
        bounds = qr_code.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]

        # Create drawing
        drawing = Drawing(
            element.width or 100,
            element.height or 100,
            transform=[
                (element.width or 100) / width, 0, 0,
                (element.height or 100) / height, 0, 0
            ]
        )
        drawing.add(qr_code)

        # Render
        drawing.drawOn(self.canvas, x, y - (element.height or 100))

    def _draw_barcode(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw a barcode"""
        # Get data for barcode
        barcode_data = self.process_template_variables(
            element.text_content, context_data
        )

        if not barcode_data:
            return

        x, y = self.calculate_position(
            element.x_position,
            element.y_position,
            element.width or 200
        )

        # Create barcode (using Code128 as example)
        barcode = code128.Code128(
            barcode_data,
            barWidth=(element.width or 200) / len(barcode_data) * 0.9,
            barHeight=element.height or 50
        )

        # Draw barcode
        barcode.drawOn(self.canvas, x, y - (element.height or 50))

    def _draw_signature_field(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw a signature field placeholder"""
        # Draw rectangle for signature area
        self._draw_rectangle(element, context_data)

        # Add signature line
        line_element = PDFTemplateElement(
            x_position=element.x_position,
            y_position=element.y_position + (element.height or 50) - 10,
            width=element.width,
            height=0,
            stroke_color='#000000',
            stroke_width=0.5
        )
        self._draw_line(line_element, context_data)

        # Add signature text
        text_element = PDFTemplateElement(
            x_position=element.x_position + 5,
            y_position=element.y_position + (element.height or 50) - 5,
            text_content='Signature / التوقيع',
            font_size=8,
            font_color='#666666'
        )
        self._draw_text(text_element, context_data)

    def _draw_watermark(self):
        """Draw watermark on page"""
        if not self.template.watermark_text:
            return

        # Save state
        self.canvas.saveState()

        # Set watermark properties
        self.canvas.setFont('Helvetica', 60)
        self.canvas.setFillColor(HexColor('#cccccc'))
        self.canvas.setFillAlpha(0.3)

        # Rotate and draw
        self.canvas.translate(self.page_width / 2, self.page_height / 2)
        self.canvas.rotate(45)

        text = self.process_text(self.template.watermark_text)
        self.canvas.drawCentredString(0, 0, text)

        # Restore state
        self.canvas.restoreState()

    def _draw_header(self, context_data: Dict[str, Any]):
        """Draw page header"""
        # This can be customized based on template configuration
        pass

    def _draw_footer(self, context_data: Dict[str, Any]):
        """Draw page footer with page numbers"""
        self.canvas.saveState()

        # Draw line
        self.canvas.setStrokeColor(HexColor('#cccccc'))
        self.canvas.line(
            self.template.margin_left,
            self.page_height - self.template.margin_bottom + 20,
            self.page_width - self.template.margin_right,
            self.page_height - self.template.margin_bottom + 20
        )

        # Draw page number
        self.canvas.setFont('Helvetica', 9)
        self.canvas.setFillColor(HexColor('#666666'))
        self.canvas.drawCentredString(
            self.page_width / 2,
            self.page_height - self.template.margin_bottom + 5,
            f"Page {self.current_page}"
        )

        self.canvas.restoreState()

    def _handle_page_break(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Handle page break"""
        self.canvas.showPage()
        self.current_page += 1

    def _get_value_from_path(self, path: str, context: Dict[str, Any]) -> Any:
        """Get value from nested dictionary/object using dot notation"""
        if not path:
            return None

        parts = path.split('.')
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None

            if value is None:
                return None

        return value

    def _log_generation(self, context_data: Dict[str, Any],
                        generation_time: float, status: str,
                        error_message: str = ''):
        """Log PDF generation activity"""
        try:
            PDFGenerationLog.objects.create(
                template=self.template,
                generated_by=context_data.get('user'),
                context_data=context_data,
                status=status,
                error_message=error_message,
                generation_time=generation_time,
                completed_at=timezone.now() if status == 'completed' else None
            )
        except Exception as e:
            print(f"Error logging PDF generation: {e}")


    def _draw_dynamic_image(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw dynamic image from data source"""
        import os
        import requests
        from io import BytesIO
        from PIL import Image as PILImage

        try:
            # Get image path/URL from context using data source path
            image_source = self._get_value_from_path(element.data_source, context_data)

            if not image_source:
                print(f"Warning: No image found at path {element.data_source}")
                return

            # Calculate position
            x, y = self.calculate_position(
                element.x_position,
                element.y_position,
                element.width or 100
            )

            width = element.width or 100
            height = element.height or 100

            # Handle different image source types
            if isinstance(image_source, str):
                if image_source.startswith('http'):
                    # Download image from URL
                    try:
                        response = requests.get(image_source, timeout=10)
                        response.raise_for_status()
                        image_data = BytesIO(response.content)

                        # Draw image from bytes
                        self.canvas.drawImage(
                            ImageReader(image_data),
                            x, y - height,
                            width=width,
                            height=height,
                            preserveAspectRatio=element.maintain_aspect_ratio
                        )
                    except Exception as e:
                        print(f"Error downloading image from {image_source}: {e}")
                        # Optionally draw placeholder
                        self._draw_placeholder_image(x, y, width, height)

                elif image_source.startswith('/'):
                    # Absolute file path
                    if os.path.exists(image_source):
                        self.canvas.drawImage(
                            image_source,
                            x, y - height,
                            width=width,
                            height=height,
                            preserveAspectRatio=element.maintain_aspect_ratio
                        )
                    else:
                        print(f"Image file not found: {image_source}")
                        self._draw_placeholder_image(x, y, width, height)

                else:
                    # Relative path - prepend media root
                    from django.conf import settings
                    full_path = os.path.join(settings.MEDIA_ROOT, image_source)

                    if os.path.exists(full_path):
                        self.canvas.drawImage(
                            full_path,
                            x, y - height,
                            width=width,
                            height=height,
                            preserveAspectRatio=element.maintain_aspect_ratio
                        )
                    else:
                        print(f"Image file not found: {full_path}")
                        self._draw_placeholder_image(x, y, width, height)

            elif hasattr(image_source, 'read'):
                # File-like object
                self.canvas.drawImage(
                    ImageReader(image_source),
                    x, y - height,
                    width=width,
                    height=height,
                    preserveAspectRatio=element.maintain_aspect_ratio
                )
            else:
                print(f"Unknown image source type: {type(image_source)}")
                self._draw_placeholder_image(x, y, width, height)

        except Exception as e:
            print(f"Error drawing dynamic image: {e}")
            # Draw placeholder on error
            self._draw_placeholder_image(
                element.x_position,
                element.y_position,
                element.width or 100,
                element.height or 100
            )

    def _draw_placeholder_image(self, x: float, y: float, width: float, height: float):
        """Draw a placeholder rectangle when image is not available"""
        # Save current state
        self.canvas.saveState()

        # Draw placeholder rectangle
        self.canvas.setStrokeColor(HexColor('#cccccc'))
        self.canvas.setFillColor(HexColor('#f0f0f0'))
        self.canvas.rect(x, y - height, width, height, fill=1, stroke=1)

        # Draw diagonal lines
        self.canvas.setStrokeColor(HexColor('#cccccc'))
        self.canvas.line(x, y - height, x + width, y)
        self.canvas.line(x, y, x + width, y - height)

        # Add text
        self.canvas.setFillColor(HexColor('#666666'))
        self.canvas.setFont('Helvetica', 10)
        self.canvas.drawCentredString(
            x + width/2,
            y - height/2 - 5,
            "Image Not Available"
        )

        # Restore state
        self.canvas.restoreState()

    def _draw_circle(self, element: PDFTemplateElement, context_data: Dict[str, Any]):
        """Draw a circle"""
        # Calculate center position
        center_x = element.x_position + (element.width or 50) / 2
        center_y = element.y_position + (element.height or 50) / 2

        # Calculate radius (use smaller of width/height for perfect circle)
        radius = min(element.width or 50, element.height or 50) / 2

        # Adjust for RTL if needed
        if self.is_rtl:
            center_x = self.page_width - center_x

        # Adjust Y for ReportLab coordinate system
        center_y = self.page_height - center_y

        # Set colors
        if element.fill_color:
            self.canvas.setFillColor(HexColor(element.fill_color))
        if element.stroke_color:
            self.canvas.setStrokeColor(HexColor(element.stroke_color))

        # Set stroke width
        self.canvas.setLineWidth(element.stroke_width)

        # Draw circle
        self.canvas.circle(
            center_x,
            center_y,
            radius,
            stroke=1 if element.stroke_color else 0,
            fill=1 if element.fill_color else 0
        )
class PDFTemplateService:
    """Service class for PDF template operations"""

    @staticmethod
    def create_template_from_config(config: Dict[str, Any]) -> PDFTemplate:
        """Create a template from configuration dictionary"""
        # Extract template data
        template_data = {
            'name': config['name'],
            'code': config['code'],
            'description': config.get('description', ''),
            'primary_language': config.get('primary_language', 'en'),
            'page_size': config.get('page_size', 'A4'),
            'orientation': config.get('orientation', 'portrait'),
        }

        # Create template
        template = PDFTemplate.objects.create(**template_data)

        # Create elements
        for element_config in config.get('elements', []):
            PDFTemplateElement.objects.create(
                template=template,
                **element_config
            )

        # Create variables
        for var_config in config.get('variables', []):
            PDFTemplateVariable.objects.create(
                template=template,
                **var_config
            )

        return template

    @staticmethod
    def duplicate_template(template: PDFTemplate, new_name: str) -> PDFTemplate:
        """Duplicate an existing template"""
        # Clone template
        new_template = PDFTemplate.objects.create(
            name=new_name,
            code=f"{template.code}_copy",
            description=template.description,
            primary_language=template.primary_language,
            page_size=template.page_size,
            orientation=template.orientation,
            margin_top=template.margin_top,
            margin_bottom=template.margin_bottom,
            margin_left=template.margin_left,
            margin_right=template.margin_right,
        )

        # Clone elements
        for element in template.elements.all():
            element.pk = None
            element.template = new_template
            element.save()

        # Clone variables
        for variable in template.variables.all():
            variable.pk = None
            variable.template = new_template
            variable.save()

        return new_template
