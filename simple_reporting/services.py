# reporting_templates/services.py

import os
import platform
import re
from io import BytesIO
from typing import Dict, Any, Optional
from urllib.parse import unquote
from django.db.models import Model, QuerySet, ForeignKey
from django.conf import settings
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from lookup.models import Lookup

# PDF merging support
from PyPDF2 import PdfReader, PdfWriter
import json
from PIL import Image
from reportlab.lib.utils import ImageReader
from django.conf import settings
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


from reportlab.lib.pagesizes import A4, A3, A5, letter, legal, landscape, portrait

class PDFGenerator:
    """Simple PDF generator with Arabic support for Windows"""

    # Class variable to track if fonts are registered
    _fonts_registered = False

    def __init__(self, template: PDFTemplate):
        self.template = template

        # Get page dimensions from template
        self.page_width, self.page_height = template.get_page_dimensions()
        self.page_size = (self.page_width, self.page_height)

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

        # Draw background first (if not PDF type)
        if self.template.background_type in ['color', 'image']:
            self._draw_background(c)

        # Get the main object
        obj = data.get('object')

        # Process elements
        for element in self.template.elements.all():
            self._draw_element(c, element, obj)  # ✅ CORRECT - handles both text and image!

        # Save PDF
        c.save()
        buffer.seek(0)

        # Handle PDF template backgrounds (requires merging)
        if self.template.background_type == 'pdf' and self.template.background_pdf:
            buffer = self._merge_with_pdf_background(buffer)

        return buffer

    def _draw_background(self, c: canvas.Canvas):
        """Draw background based on template settings"""
        if self.template.background_type == 'color':
            self._draw_color_background(c)
        elif self.template.background_type == 'image':
            self._draw_image_background(c)

    def _draw_color_background(self, c: canvas.Canvas):
        """Draw solid color background"""
        if not self.template.background_color:
            return

        # Parse hex color
        hex_color = self.template.background_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))

        # Set fill color with opacity
        c.setFillColorRGB(r, g, b, alpha=self.template.background_opacity)

        # Draw rectangle covering entire page
        c.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)

    def _draw_image_background(self, c: canvas.Canvas):
        """Draw image background"""
        if not self.template.background_image:
            return

        try:
            # Get image path
            image_path = self.template.background_image.path

            # Draw image covering entire page
            c.saveState()
            c.setFillAlpha(self.template.background_opacity)
            c.drawImage(
                image_path,
                0, 0,
                width=self.page_width,
                height=self.page_height,
                preserveAspectRatio=False
            )
            c.restoreState()
        except Exception as e:
            print(f"Error drawing image background: {str(e)}")

    def _merge_with_pdf_background(self, content_buffer: BytesIO) -> BytesIO:
        """Merge generated content with PDF background template"""
        try:
            # Create PDF reader objects
            content_pdf = PdfReader(content_buffer)
            background_pdf = PdfReader(self.template.background_pdf.path)

            # Create PDF writer
            output = PdfWriter()

            # Get first page of content
            content_page = content_pdf.pages[0]

            # Get first page of background
            if len(background_pdf.pages) > 0:
                background_page = background_pdf.pages[0]

                # Merge pages (background first, then content on top)
                background_page.merge_page(content_page)
                output.add_page(background_page)
            else:
                # If no background page, just add content
                output.add_page(content_page)

            # Write to new buffer
            output_buffer = BytesIO()
            output.write(output_buffer)
            output_buffer.seek(0)

            return output_buffer

        except Exception as e:
            print(f"Error merging PDF background: {str(e)}")
            # Return original content if merge fails
            content_buffer.seek(0)
            return content_buffer

    def _draw_element(self, c: canvas.Canvas, element: PDFElement, obj: Optional[Model]):
        """Draw a single element - text or image"""
        if element.element_type == 'image':
            self._draw_image_element(c, element, obj)
        else:
            self._draw_text_element(c, element, obj)

    def _draw_text_element(self, c: canvas.Canvas, element: PDFElement, obj: Optional[Model]):
        """Draw a text element with Arabic support"""
        # Validate position is within current page bounds
        if element.x_position > self.page_width:
            print(f"Warning: Element x_position {element.x_position} exceeds page width {self.page_width}")
            return
        if element.y_position > self.page_height:
            print(f"Warning: Element y_position {element.y_position} exceeds page height {self.page_height}")
            return

        # Get text
        if element.is_dynamic and obj:
            text = self._get_value_from_object(obj, element.text_content, element)  # Note the 'element' parameter
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
    def _draw_image_element(self, c: canvas.Canvas, element: PDFElement, obj: Optional[Model]):
        """Draw an image element from JSON field"""
        if not obj or not element.image_field_path:
            return

        try:
            # Get the image URL from JSON field
            image_url = self._get_image_from_json_field(obj, element)
            if not image_url:
                print(f"No image found for element at ({element.x_position}, {element.y_position})")
                return
            image_url = unquote(image_url)

            # Convert relative URL to absolute path
            if image_url.startswith('/media/'):
                image_path = os.path.join(settings.MEDIA_ROOT, image_url.replace('/media/', ''))
            else:
                image_path = os.path.join(settings.MEDIA_ROOT, image_url)

            if not os.path.exists(image_path):
                print(f"Image file not found: {image_path}")
                return

            # Calculate dimensions
            width, height = self._calculate_image_dimensions(image_path, element)

            # Draw image (ReportLab uses bottom-left origin)
            y = self.page_height - element.y_position - height

            c.drawImage(
                image_path,
                element.x_position,
                y,
                width=width,
                height=height,
                preserveAspectRatio=element.image_maintain_aspect
            )

        except Exception as e:
            print(f"Error drawing image element: {str(e)}")

    def _get_image_from_json_field(self, obj: Model, element: PDFElement) -> Optional[str]:
        """Extract image URL from JSON field based on element configuration"""
        try:
            # Parse the field path to navigate JSON structure
            field_path = element.image_field_path

            # Extract base field and JSON path
            if '[' in field_path:
                base_field = field_path.split('[')[0]
                json_path = field_path[len(base_field):]
            else:
                base_field = field_path
                json_path = ''

            # Get the base field value
            if hasattr(obj, base_field):
                value = getattr(obj, base_field)

                # If it's a JSONField, it should already be a dict/list
                if json_path and isinstance(value, (dict, list)):
                    # Parse JSON path like "[uploaded_files]"
                    json_path = json_path.strip('[]"\' ')

                    # Navigate to the specified path
                    if json_path and isinstance(value, dict):
                        value = value.get(json_path, [])

                # Now we should have a list of files
                if isinstance(value, list):
                    # Filter by type if specified
                    if element.image_filter_type:
                        matching_files = [
                            f for f in value
                            if isinstance(f, dict) and f.get('type') == element.image_filter_type
                        ]
                    else:
                        matching_files = value

                    # Apply additional filters if specified
                    if element.image_additional_filters and matching_files:
                        for key, filter_value in element.image_additional_filters.items():
                            matching_files = [
                                f for f in matching_files
                                if isinstance(f, dict) and f.get(key) == filter_value
                            ]

                    # Select based on method
                    if matching_files:
                        if element.image_selection_method == 'first':
                            selected = matching_files[0]
                        elif element.image_selection_method == 'last':
                            selected = matching_files[-1]
                        elif element.image_selection_method == 'filename' and element.image_filename_contains:
                            # Find by filename
                            for f in matching_files:
                                if element.image_filename_contains in f.get('file_url', ''):
                                    selected = f
                                    break
                            else:
                                # Fallback to first if no filename match
                                selected = matching_files[0]
                        else:
                            selected = matching_files[0]  # Default to first

                        if isinstance(selected, dict):
                            return selected.get('file_url')
                        elif isinstance(selected, str):
                            return selected

                return None

        except Exception as e:
            print(f"Error extracting image from JSON: {str(e)}")
            return None

    def _calculate_image_dimensions(self, image_path: str, element: PDFElement) -> tuple:
        """Calculate image dimensions based on element settings"""
        try:
            # Get original image dimensions
            with Image.open(image_path) as img:
                orig_width, orig_height = img.size

            # Convert to points (assuming 72 DPI)
            orig_width_pts = orig_width * 72 / 96  # Assuming 96 DPI screen
            orig_height_pts = orig_height * 72 / 96

            # Use specified dimensions or calculate based on aspect ratio
            if element.image_width and element.image_height:
                return element.image_width, element.image_height
            elif element.image_width:
                # Calculate height maintaining aspect ratio
                aspect_ratio = orig_height / orig_width
                return element.image_width, element.image_width * aspect_ratio
            elif element.image_height:
                # Calculate width maintaining aspect ratio
                aspect_ratio = orig_width / orig_height
                return element.image_height * aspect_ratio, element.image_height
            else:
                # Use original dimensions scaled to reasonable size
                max_width = 200  # Default max width in points
                max_height = 200  # Default max height in points

                if orig_width_pts > max_width or orig_height_pts > max_height:
                    scale = min(max_width / orig_width_pts, max_height / orig_height_pts)
                    return orig_width_pts * scale, orig_height_pts * scale
                else:
                    return orig_width_pts, orig_height_pts

        except Exception as e:
            print(f"Error calculating image dimensions: {str(e)}")
            return 100, 100  # Default fallback size

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

    def _get_value_from_object(self, obj: Model, field_path: str, element: PDFElement = None) -> Any:
        """Get value from object using dot notation and bracket notation for JSON fields"""
        if not field_path:
            return None

        # Pattern to match parts like 'field["key"]' or 'field[key]'
        pattern = r'([^.\[]+)(?:\[["\']*([^"\'\]]+)["\']*\])?'
        parts = re.findall(pattern, field_path)

        value = obj

        for field_name, key in parts:
            # Get the field value
            if hasattr(value, field_name):
                value = getattr(value, field_name)

                # Call if it's a method
                if callable(value):
                    value = value()

                # If there's a key, try to access it (for dict/JSON fields)
                if key and value is not None:
                    try:
                        if isinstance(value, dict):
                            value = value.get(key)
                        else:
                            # Try to access as attribute (for objects)
                            value = getattr(value, key, None)
                    except (KeyError, AttributeError, TypeError):
                        return None
            else:
                return None

        # Now check if we should resolve this as a lookup
        if (value is not None and element and
                hasattr(element, 'is_lookup_field') and element.is_lookup_field):
            # This value is a lookup ID, resolve it
            return self._resolve_lookup_value(value, element)

        return value

    def _resolve_lookup_value(self, lookup_id: Any, element: PDFElement) -> str:
        """Resolve a lookup ID to its display value"""
        from lookup.models import Lookup

        try:
            # Convert to int if needed
            if isinstance(lookup_id, str) and lookup_id.isdigit():
                lookup_id = int(lookup_id)

            # Get the lookup instance
            lookup = Lookup.objects.get(pk=lookup_id)

            # Get display value based on language
            if hasattr(element, 'lookup_display_language'):
                if element.lookup_display_language == 'ar':
                    return getattr(lookup, 'name_ara', None) or getattr(lookup, 'name', str(lookup_id))
                elif element.lookup_display_language == 'both':
                    name_en = getattr(lookup, 'name', '')
                    name_ar = getattr(lookup, 'name_ara', '')
                    return f"{name_en} / {name_ar}"
                else:  # default to 'en'
                    return getattr(lookup, 'name', str(lookup_id))
            else:
                return getattr(lookup, 'name', str(lookup_id))

        except (Lookup.DoesNotExist, ValueError):
            # If lookup not found or invalid ID, return original value
            return str(lookup_id)

    @staticmethod
    def get_lookup_fields_for_model(model_class):
        """Get all fields that are ForeignKeys to Lookup model"""
        from lookup.models import Lookup, LookupConfig
        lookup_fields = []

        # Get direct ForeignKey fields to Lookup
        for field in model_class._meta.get_fields():
            if isinstance(field, ForeignKey) and field.related_model == Lookup:
                lookup_fields.append({
                    'field_name': field.name,
                    'field_verbose_name': field.verbose_name,
                    'lookup_category': None
                })

        # Get configured lookup categories
        model_name = model_class._meta.model_name
        configs = LookupConfig.objects.filter(model_name__iexact=model_name)

        for config in configs:
            # Update with category info if exists
            for lf in lookup_fields:
                if lf['field_name'] == config.field_name:
                    lf['lookup_category'] = config.lookup_category
                    break

        return lookup_fields