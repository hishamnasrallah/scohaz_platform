# app_builder/management/commands/convert_erd.py

import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from app_builder.utils.erd_converter import ERDToDjangoConverter, convert_erd_to_django


class Command(BaseCommand):
    help = 'Convert ERD-generated JSON to Django-compatible JSON format'

    def add_arguments(self, parser):
        parser.add_argument(
            'input_file',
            type=str,
            help='Path to the ERD JSON file (e.g., paste-2.txt)'
        )
        parser.add_argument(
            '--output',
            '-o',
            type=str,
            help='Output file path for the converted JSON',
            default=None
        )
        parser.add_argument(
            '--app-name',
            type=str,
            help='App name to use for model references',
            default=None
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate the conversion without saving'
        )
        parser.add_argument(
            '--show-warnings',
            action='store_true',
            help='Show all warnings during conversion'
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Pretty print the output JSON'
        )
        parser.add_argument(
            '--compare',
            type=str,
            help='Compare with another JSON file (your working example)',
            default=None
        )

    def handle(self, *args, **options):
        input_file = options['input_file']
        output_file = options.get('output')
        app_name = options.get('app_name')
        validate_only = options.get('validate_only', False)
        show_warnings = options.get('show_warnings', False)
        pretty = options.get('pretty', False)
        compare_file = options.get('compare')

        # Check if input file exists
        if not os.path.exists(input_file):
            raise CommandError(f"Input file '{input_file}' does not exist")

        try:
            # Load the ERD JSON
            self.stdout.write(f"Loading ERD from '{input_file}'...")
            with open(input_file, 'r', encoding='utf-8') as f:
                erd_data = json.load(f)

            # Perform conversion
            self.stdout.write("Converting ERD to Django format...")
            result = convert_erd_to_django(erd_data, app_name=app_name)

            # Show statistics
            self.stdout.write(self.style.SUCCESS("\nConversion Statistics:"))
            self.stdout.write(f"  Models: {result['model_count']}")
            self.stdout.write(f"  Fields: {result['field_count']}")
            self.stdout.write(f"  Relationships: {result['relationship_count']}")

            # Show warnings if requested or if there are errors
            if show_warnings or result['warnings']:
                self.stdout.write(self.style.WARNING("\nWarnings:"))
                for warning in result['warnings']:
                    self.stdout.write(f"  ⚠ {warning}")

            # Show errors
            if result['errors']:
                self.stdout.write(self.style.ERROR("\nValidation Errors:"))
                for error in result['errors']:
                    self.stdout.write(f"  ✗ {error}")

            # Validation result
            if result['is_valid']:
                self.stdout.write(self.style.SUCCESS("\n✓ Validation passed!"))
            else:
                self.stdout.write(self.style.ERROR("\n✗ Validation failed!"))
                if validate_only:
                    raise CommandError("Validation failed")

            if validate_only:
                return

            # Compare with reference if provided
            if compare_file and os.path.exists(compare_file):
                self._compare_with_reference(result['models'], compare_file)

            # Save or display output
            if output_file:
                # Ensure directory exists
                output_dir = os.path.dirname(output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)

                with open(output_file, 'w', encoding='utf-8') as f:
                    if pretty:
                        json.dump(result['models'], f, indent=2, ensure_ascii=False)
                    else:
                        json.dump(result['models'], f, ensure_ascii=False)

                self.stdout.write(
                    self.style.SUCCESS(f"\n✓ Converted JSON saved to '{output_file}'")
                )

                # Also save a full report if output is specified
                report_file = output_file.replace('.json', '_report.json')
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                self.stdout.write(f"  Full report saved to '{report_file}'")
            else:
                # Print to stdout
                if pretty:
                    print("\n" + "="*60)
                    print("CONVERTED DJANGO MODELS:")
                    print("="*60)
                    print(json.dumps(result['models'], indent=2, ensure_ascii=False))
                else:
                    print(json.dumps(result['models'], ensure_ascii=False))

        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in input file: {e}")
        except Exception as e:
            raise CommandError(f"Error during conversion: {e}")

    def _compare_with_reference(self, converted_models, reference_file):
        """Compare converted models with a reference file."""
        try:
            with open(reference_file, 'r', encoding='utf-8') as f:
                reference_data = json.load(f)

            self.stdout.write(self.style.WARNING("\nComparison with reference:"))

            # Compare model counts
            ref_count = len(reference_data) if isinstance(reference_data, list) else 0
            conv_count = len(converted_models)
            self.stdout.write(f"  Reference models: {ref_count}, Converted models: {conv_count}")

            # Compare model names
            ref_names = {m.get('name') for m in reference_data} if isinstance(reference_data, list) else set()
            conv_names = {m.get('name') for m in converted_models}

            missing = ref_names - conv_names
            extra = conv_names - ref_names

            if missing:
                self.stdout.write(f"  Missing models: {', '.join(missing)}")
            if extra:
                self.stdout.write(f"  Extra models: {', '.join(extra)}")

            if not missing and not extra:
                self.stdout.write(self.style.SUCCESS("  ✓ All models match!"))

        except Exception as e:
            self.stdout.write(f"  Could not compare with reference: {e}")