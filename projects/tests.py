from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from version.models import Version, LocalVersion
from .models import FlutterProject, Screen


class FlutterProjectModelTest(TestCase):
    """Test cases for FlutterProject model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.version = Version.objects.create(
            version_number='1.0.0',
            operating_system='Android',
            _environment='1',
            active_ind=True
        )
        self.en_lang = LocalVersion.objects.create(
            lang='en',
            language_name='English',
            active_ind=True
        )

    def test_create_flutter_project(self):
        """Test creating a Flutter project"""
        project = FlutterProject.objects.create(
            name='Test App',
            package_name='com.test.app',
            user=self.user,
            app_version=self.version
        )

        self.assertEqual(project.name, 'Test App')
        self.assertEqual(project.package_name, 'com.test.app')
        self.assertEqual(project.user, self.user)
        self.assertEqual(project.version_number, '1.0.0')

    def test_project_languages(self):
        """Test adding languages to project"""
        project = FlutterProject.objects.create(
            name='Multi-lang App',
            package_name='com.test.multilang',
            user=self.user
        )

        project.supported_languages.add(self.en_lang)

        self.assertEqual(project.language_count, 1)
        self.assertIn(self.en_lang, project.supported_languages.all())

    def test_create_default_screen(self):
        """Test creating default home screen"""
        project = FlutterProject.objects.create(
            name='Screen Test App',
            package_name='com.test.screens',
            user=self.user
        )

        screen = project.create_default_screen()

        self.assertTrue(screen.is_home)
        self.assertEqual(screen.route, '/')
        self.assertEqual(screen.project, project)


class ScreenModelTest(TestCase):
    """Test cases for Screen model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project = FlutterProject.objects.create(
            name='Test Project',
            package_name='com.test.project',
            user=self.user
        )

    def test_create_screen(self):
        """Test creating a screen"""
        screen = Screen.objects.create(
            project=self.project,
            name='Login Screen',
            route='/login',
            is_home=False,
            ui_structure={'type': 'scaffold'}
        )

        self.assertEqual(screen.name, 'Login Screen')
        self.assertEqual(screen.route, '/login')
        self.assertFalse(screen.is_home)

    def test_only_one_home_screen(self):
        """Test that only one screen can be home"""
        screen1 = Screen.objects.create(
            project=self.project,
            name='Screen 1',
            route='/screen1',
            is_home=True
        )

        screen2 = Screen.objects.create(
            project=self.project,
            name='Screen 2',
            route='/screen2',
            is_home=True
        )

        # Refresh screen1 from database
        screen1.refresh_from_db()

        self.assertFalse(screen1.is_home)
        self.assertTrue(screen2.is_home)

    def test_component_count(self):
        """Test component counting in UI structure"""
        screen = Screen.objects.create(
            project=self.project,
            name='Complex Screen',
            route='/complex',
            ui_structure={
                'type': 'scaffold',
                'body': {
                    'type': 'column',
                    'children': [
                        {'type': 'text'},
                        {'type': 'button'}
                    ]
                }
            }
        )

        # scaffold + column + text + button = 4
        self.assertEqual(screen.component_count, 4)


class ProjectAPITest(APITestCase):
    """Test cases for Project API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            password='apipass123'
        )
        self.en_lang = LocalVersion.objects.create(
            lang='en',
            language_name='English',
            active_ind=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_project(self):
        """Test creating project via API"""
        url = reverse('projects:flutterproject-list')
        data = {
            'name': 'API Test App',
            'package_name': 'com.api.test',
            'default_language': 'en'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FlutterProject.objects.count(), 1)

        project = FlutterProject.objects.first()
        self.assertEqual(project.name, 'API Test App')
        self.assertEqual(project.user, self.user)

    def test_list_user_projects(self):
        """Test listing only user's own projects"""
        # Create projects for different users
        other_user = User.objects.create_user('other', password='pass')

        FlutterProject.objects.create(
            name='My Project',
            package_name='com.my.project',
            user=self.user
        )

        FlutterProject.objects.create(
            name='Other Project',
            package_name='com.other.project',
            user=other_user
        )

        url = reverse('projects:flutterproject-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'My Project')

    def test_set_version(self):
        """Test setting version for project"""
        project = FlutterProject.objects.create(
            name='Version Test',
            package_name='com.version.test',
            user=self.user
        )

        url = reverse('projects:flutterproject-set-version', args=[project.id])
        data = {
            'version_number': '1.2.3',
            'os': 'Android'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        project.refresh_from_db()
        self.assertIsNotNone(project.app_version)
        self.assertEqual(project.app_version.version_number, '1.2.3')

    def test_add_language(self):
        """Test adding language support"""
        project = FlutterProject.objects.create(
            name='Lang Test',
            package_name='com.lang.test',
            user=self.user
        )

        url = reverse('projects:flutterproject-add-language', args=[project.id])
        data = {'language': 'en'}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.en_lang, project.supported_languages.all())

    def test_package_name_validation(self):
        """Test package name validation"""
        url = reverse('projects:flutterproject-list')

        # Invalid package name
        data = {
            'name': 'Invalid Package',
            'package_name': 'InvalidPackage',  # Should have dots
            'default_language': 'en'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('package_name', response.data)


class ScreenAPITest(APITestCase):
    """Test cases for Screen API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            password='apipass123'
        )
        self.project = FlutterProject.objects.create(
            name='Screen API Test',
            package_name='com.screen.test',
            user=self.user
        )
        self.client.force_authenticate(user=self.user)

    def test_create_screen(self):
        """Test creating screen via API"""
        url = reverse('projects:screen-list')
        data = {
            'project': self.project.id,
            'name': 'Settings Screen',
            'route': '/settings',
            'is_home': False,
            'ui_structure': {
                'type': 'scaffold',
                'body': {'type': 'text'}
            }
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Screen.objects.count(), 1)

        screen = Screen.objects.first()
        self.assertEqual(screen.name, 'Settings Screen')
        self.assertEqual(screen.project, self.project)

    def test_set_as_home(self):
        """Test setting screen as home"""
        screen = Screen.objects.create(
            project=self.project,
            name='New Home',
            route='/new-home',
            is_home=False
        )

        url = reverse('projects:screen-set-as-home', args=[screen.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        screen.refresh_from_db()
        self.assertTrue(screen.is_home)

    def test_duplicate_screen(self):
        """Test duplicating a screen"""
        original = Screen.objects.create(
            project=self.project,
            name='Original',
            route='/original',
            ui_structure={'type': 'scaffold', 'test': True}
        )

        url = reverse('projects:screen-duplicate', args=[original.id])
        data = {
            'name': 'Duplicate',
            'route': '/duplicate'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Screen.objects.count(), 2)

        duplicate = Screen.objects.get(name='Duplicate')
        self.assertEqual(duplicate.ui_structure, original.ui_structure)
        self.assertNotEqual(duplicate.id, original.id)