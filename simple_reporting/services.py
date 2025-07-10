# reporting_templates/services.py

import os
import platform
from io import BytesIO
from typing import Dict, Any, Optional

from django.db.models import Model, QuerySet
from django.conf import settings
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Arabic text support
import arabic_reshaper
from bidi.algorithm import get_display

from .models import PDFTemplate, PDFElement


class DataService:
    """Simple service to fetch data from models"""

    def __init__(self, template: PDFTemplate, object_id: Optional[int] = None):
        self.template = template
        self.object_id = object_id

    def fetch_data(self) -> Dict[str, Any]:
        """Fetch data from the configured model"""
        model_class = self.template.content_type.model_class()
        if not model_class:
            return {}

        # Get queryset
        queryset = model_class.objects.all()

        # Apply filters from template
        if self.template.query_filter:
            queryset = queryset.filter(**self.template.query_filter)

        # Get single object if ID provided
        if self.object_id:
            try:
                obj = queryset.get(pk=self.object_id)
                return {'object': obj}
            except model_class.DoesNotExist:
                return {}

        # Return first object for simplicity
        obj = queryset.first()
        return {'object': obj} if obj else {}


class PDFGenerator:
    """Simple PDF generator with Arabic support for Windows"""

    PAGE_SIZES = {
        'A4': A4,
        'letter': letter,
    }

    # Class variable to track if fonts are registered
    _fonts_registered = False

    def __init__(self, template: PDFTemplate):
        self.template = template
        self.page_size = self.PAGE_SIZES.get(template.page_size, A4)
        self.page_width, self.page_height = self.page_size

        # Register Arabic font once
        if not PDFGenerator._fonts_registered:
            self._register_arabic_font()
            PDFGenerator._fonts_registered = True

    def _register_arabic_font(self):
        """Register Arabic-supporting font for Windows"""
        # Windows font paths - these fonts come pre-installed with Windows
        windows_fonts = [
            # Best options for Arabic on Windows
            ('Arial', 'C:\\Windows\\Fonts\\arial.ttf'),
            ('Arial Unicode MS', 'C:\\Windows\\Fonts\\ARIALUNI.TTF'),
            ('Tahoma', 'C:\\Windows\\Fonts\\tahoma.ttf'),
            ('Simplified Arabic', 'C:\\Windows\\Fonts\\simpo.ttf'),
            ('Traditional Arabic', 'C:\\Windows\\Fonts\\trado.ttf'),
            ('Segoe UI', 'C:\\Windows\\Fonts\\segoeui.ttf'),
            # Fallback to user-provided fonts
            ('Amiri', os.path.join(settings.BASE_DIR, 'simple_reporting', 'fonts', 'Amiri-Regular.ttf')),
        ]

        # Try to register fonts
        registered = False
        for font_name, font_path in windows_fonts:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
                    print(f"Successfully registered {font_name} from {font_path}")
                    registered = True
                    break
                except Exception as e:
                    print(f"Failed to register {font_name}: {str(e)}")
                    continue

        if not registered:
            print("Warning: No Arabic font could be registered. Arabic text will not display correctly.")
            print("Please ensure you have Arial or Tahoma installed in C:\\Windows\\Fonts\\")

    def generate(self, data: Dict[str, Any]) -> BytesIO:
        """Generate PDF from template and data"""
        buffer = BytesIO()

        # Create canvas
        c = canvas.Canvas(buffer, pagesize=self.page_size)

        # Get the main object
        obj = data.get('object')

        # Process elements
        for element in self.template.elements.all():
            self._draw_element(c, element, obj)

        # Save PDF
        c.save()
        buffer.seek(0)

        return buffer

    def _draw_element(self, c: canvas.Canvas, element: PDFElement, obj: Optional[Model]):
        """Draw a single element with Arabic support"""
        # Get text
        if element.is_dynamic and obj:
            text = self._get_value_from_object(obj, element.text_content)
        else:
            text = element.text_content

        # Convert to string
        text = str(text) if text is not None else ''

        # Process Arabic text
        if self._contains_arabic(text):
            text = self._process_arabic_text(text)
            # Use Arabic font
            try:
                c.setFont('ArabicFont', element.font_size)
            except:
                # Fallback to Helvetica if Arabic font not available
                print("Warning: Arabic font not available, using Helvetica")
                c.setFont('Helvetica', element.font_size)
        else:
            # Use default font for non-Arabic text
            c.setFont('Helvetica', element.font_size)

        # Draw text (ReportLab uses bottom-left origin)
        y = self.page_height - element.y_position
        c.drawString(element.x_position, y, text)

    def _contains_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        if not text:
            return False
        # Arabic Unicode ranges
        arabic_ranges = [
            (0x0600, 0x06FF),  # Arabic
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
        ]
        return any(
            any(start <= ord(char) <= end for start, end in arabic_ranges)
            for char in text
        )

    def _process_arabic_text(self, text: str) -> str:
        """Process Arabic text for correct display"""
        try:
            # Reshape Arabic text
            reshaped_text = arabic_reshaper.reshape(text)
            # Apply RTL algorithm
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except Exception as e:
            print(f"Error processing Arabic text: {str(e)}")
            return text

    def _get_value_from_object(self, obj: Model, field_path: str) -> Any:
        """Get value from object using dot notation"""
        if not field_path:
            return None

        value = obj
        for part in field_path.split('.'):
            if hasattr(value, part):
                value = getattr(value, part)
                # Call if it's a method
                if callable(value):
                    value = value()
            else:
                return None

        return value