# reporting_templates/services.py

from io import BytesIO
from typing import Dict, Any, Optional

from django.db.models import Model, QuerySet
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

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
    """Simple PDF generator"""

    PAGE_SIZES = {
        'A4': A4,
        'letter': letter,
    }

    def __init__(self, template: PDFTemplate):
        self.template = template
        self.page_size = self.PAGE_SIZES.get(template.page_size, A4)
        self.page_width, self.page_height = self.page_size

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
        """Draw a single element"""
        # Get text
        if element.is_dynamic and obj:
            text = self._get_value_from_object(obj, element.text_content)
        else:
            text = element.text_content

        # Convert to string
        text = str(text) if text is not None else ''

        # Set font
        c.setFont('Helvetica', element.font_size)

        # Draw text (ReportLab uses bottom-left origin)
        y = self.page_height - element.y_position
        c.drawString(element.x_position, y, text)

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