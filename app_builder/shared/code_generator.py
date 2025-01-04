import os
from django.conf import settings


class CodeGenerator:
    """
    Handles dynamic code generation for Django applications.
    """

    def __init__(self, app_name: str, base_dir: str = None):
        self.app_name = app_name
        self.base_dir = base_dir or settings.BASE_DIR
        self.app_dir = os.path.join(self.base_dir, app_name)

    def create_app_structure(self):
        """
        Create the basic structure of the Django application.
        """
        try:
            # Define directories to be created
            directories = [
                self.app_dir,
                os.path.join(self.app_dir, 'migrations'),
                os.path.join(self.app_dir, 'templates', self.app_name),
                os.path.join(self.app_dir, 'static', self.app_name),
            ]

            # Create directories
            for directory in directories:
                os.makedirs(directory, exist_ok=True)

            # Create initial files
            self._create_init_files()
            self._create_base_files()

            print(f"Application structure created successfully for {self.app_name}")
        except Exception as e:
            raise Exception(f"Error creating application structure: {e}")

    def _create_init_files(self):
        """
        Create __init__.py files for the application and its subdirectories.
        """
        init_files = [
            os.path.join(self.app_dir, '__init__.py'),
            os.path.join(self.app_dir, 'migrations', '__init__.py'),
        ]
        for file in init_files:
            with open(file, 'w') as f:
                f.write("# Auto-generated __init__.py")

    def _create_base_files(self):
        """
        Create basic files like models.py, views.py, etc.
        """
        files = {
            'models.py': "# Auto-generated models.py\nfrom django.db import models\n",
            'views.py': "# Auto-generated views.py\nfrom django.shortcuts import render\n",
            'serializers.py': "# Auto-generated serializers.py\nfrom rest_framework import serializers\n",
            'urls.py': (
                "# Auto-generated urls.py\n"
                "from django.urls import path\n\nurlpatterns = []\n"
            ),
            'admin.py': "# Auto-generated admin.py\nfrom django.contrib import admin\n",
        }

        for file_name, content in files.items():
            with open(os.path.join(self.app_dir, file_name), 'w') as f:
                f.write(content)

    def add_model(self, model_name: str, fields: list, relationships: list = None):
        """
        Add a model to the application's models.py file.
        :param model_name: Name of the model.
        :param fields: List of field definitions.
                       Each field should be a dict with 'name', 'type', 'options'.
        :param relationships: List of relationship fields (ForeignKey, OneToOne, ManyToMany).
                              Each item should be a dict with 'name', 'type', 'related_model', 'options'.
        """
        try:
            models_file = os.path.join(self.app_dir, 'models.py')

            with open(models_file, 'a') as f:
                f.write(f"\n\nclass {model_name}(models.Model):\n")
                for field in fields:
                    field_name = field['name']
                    field_type = field['type']
                    options = field.get('options', '')
                    f.write(f"    {field_name} = models.{field_type}({options})\n")

                if relationships:
                    for rel in relationships:
                        rel_name = rel['name']
                        rel_type = rel['type']
                        related_model = rel['related_model']
                        options = rel.get('options', '')
                        f.write(f"    {rel_name} = models.{rel_type}('{related_model}', {options})\n")

                f.write("\n    def __str__(self):\n")
                f.write(f"        return self.{fields[0]['name']}\n")
            print(f"Model '{model_name}' added to models.py")
        except Exception as e:
            raise Exception(f"Error adding model to models.py: {e}")

    def generate_migration(self):
        """
        Generate migration for the newly created model.
        """
        os.system(f"python manage.py makemigrations {self.app_name}")

    def apply_migrations(self):
        """
        Apply migrations for the newly created model.
        """
        os.system("python manage.py migrate")
