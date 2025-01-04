import json
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Generate a JSON schema for creating a Django app dynamically'

    def handle(self, *args, **options):
        schema = []
        num_models = int(input("Enter the number of models: "))

        for _ in range(num_models):
            model_name = input("Enter model name: ")
            fields = []
            num_fields = int(input(f"Enter number of fields for {model_name}: "))
            for _ in range(num_fields):
                field_name = input("Enter field name: ")
                field_type = input("Enter field type: ")
                options = input("Enter field options (comma-separated, leave blank if none): ")
                fields.append({
                    "name": field_name,
                    "type": field_type,
                    "options": options
                })

            relationships = []
            num_relationships = int(input(f"Enter number of relationships for {model_name}: "))
            for _ in range(num_relationships):
                relation_name = input("Enter relationship name: ")
                relation_type = input("Enter relationship type: ")
                related_model = input("Enter related model (e.g., app_name.ModelName): ")
                options = input("Enter relationship options (comma-separated, leave blank if none): ")
                relationships.append({
                    "name": relation_name,
                    "type": relation_type,
                    "related_model": related_model,
                    "options": options
                })

            meta = {}
            meta_input = input("Enter meta options (e.g., verbose_name='Name', ordering=['-id']): ")
            if meta_input:
                meta = eval(meta_input)  # Be cautious with eval.

            schema.append({
                "name": model_name,
                "fields": fields,
                "relationships": relationships,
                "meta": meta
            })

        file_name = input("Enter the output file name (e.g., model_schema.json): ")
        with open(file_name, 'w') as json_file:
            json.dump(schema, json_file, indent=4)
            self.stdout.write(self.style.SUCCESS(f"Schema saved to {file_name}"))
