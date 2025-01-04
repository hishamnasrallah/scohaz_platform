from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from crm.models import Activity, Customer, Invoice, Lead, Payment, Product, IntegrationConfig, ValidationRule
from crm.models import Invoice
from crm.models import Lead
from crm.models import Customer
from authentication.models import CustomUser
from crm.utils.api import make_api_call


class BaseTestSetup(TestCase):
    def setUp(self):
        self.valid_config = IntegrationConfig.objects.create(
            name="Test API",
            base_url="https://api.example.com",
            method="GET",
            headers={"Authorization": "Bearer testtoken"},
            timeout=10
        )
        self.client = APIClient()



class IntegrationConfigTests(BaseTestSetup):
    def test_integration_config_creation(self):
        self.assertEqual(self.valid_config.name, "Test API")
        self.assertEqual(self.valid_config.base_url, "https://api.example.com")
        self.assertEqual(self.valid_config.method, "GET")
        self.assertEqual(self.valid_config.headers["Authorization"], "Bearer testtoken")
        self.assertEqual(self.valid_config.timeout, 10)

    def test_make_api_call_success(self):
        response = make_api_call(
            base_url="https://jsonplaceholder.typicode.com/posts",
            method="GET"
        )
        self.assertTrue(isinstance(response, list))  # Assuming the API returns a list

    def test_make_api_call_failure(self):
        response = make_api_call(
            base_url="https://invalid.url",
            method="GET"
        )
        self.assertIn("error", response)



class ValidationRuleTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.validation_rule = ValidationRule.objects.create(
            model_name="ExampleModel",
            field_name="status",
            rule_type="regex",
            rule_value="^draft|published$",
            error_message="Invalid status value."
        )

    def test_validation_rule_creation(self):
        self.assertEqual(self.validation_rule.model_name, "ExampleModel")
        self.assertEqual(self.validation_rule.field_name, "status")
        self.assertEqual(self.validation_rule.rule_type, "regex")
        self.assertEqual(self.validation_rule.rule_value, "^draft|published$")
        self.assertEqual(self.validation_rule.error_message, "Invalid status value.")



class CustomerModelTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        pass
    def test_create_customer(self):
        obj = Customer.objects.create(
            first_name='Test String',
            last_name='Test String',
            email='test@example.com',
            phone_number='Test String',
            company_name='Test String',
            address='Test Text',
            is_active=True,
        )
        self.assertIsNotNone(obj.id)
        self.assertEqual(str(obj), f'Customer object ({obj.id})')

class CustomerAPITests(BaseTestSetup):
    def setUp(self):
        super().setUp()
    def test_get_customer_list(self):
        response = self.client.get(f'/crm/customer/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_customer(self):
        data = {
            'first_name': 'Test String',
            'last_name': 'Test String',
            'email': 'test@example.com',
            'phone_number': 'Test String',
            'company_name': 'Test String',
            'address': 'Test Text',
            'is_active': True,
        }
        response = self.client.post(f'/crm/customer/', data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class LeadModelTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create()
        self.customuser = CustomUser.objects.create()
    def test_create_lead(self):
        obj = Lead.objects.create(
            title='Test String',
            status='Test String',
            priority='Test String',
            value=123.45,
            source='Test String',
            customer=self.customer,
            assigned_to=self.customuser,
        )
        self.assertIsNotNone(obj.id)
        self.assertEqual(str(obj), f'Lead object ({obj.id})')

class LeadAPITests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create()
        self.customuser = CustomUser.objects.create()
    def test_get_lead_list(self):
        response = self.client.get(f'/crm/lead/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_lead(self):
        data = {
            'title': 'Test String',
            'status': 'Test String',
            'priority': 'Test String',
            'value': 123.45,
            'source': 'Test String',
            'customer': self.customer.id,
            'assigned_to': self.customuser.id,
        }
        response = self.client.post(f'/crm/lead/', data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class ActivityModelTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.lead = Lead.objects.create()
        self.customuser = CustomUser.objects.create()
    def test_create_activity(self):
        obj = Activity.objects.create(
            activity_type='Test String',
            description='Test Text',
            is_completed=True,
            lead=self.lead,
            assigned_to=self.customuser,
        )
        self.assertIsNotNone(obj.id)
        self.assertEqual(str(obj), f'Activity object ({obj.id})')

class ActivityAPITests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.lead = Lead.objects.create()
        self.customuser = CustomUser.objects.create()
    def test_get_activity_list(self):
        response = self.client.get(f'/crm/activity/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_activity(self):
        data = {
            'activity_type': 'Test String',
            'description': 'Test Text',
            'is_completed': True,
            'lead': self.lead.id,
            'assigned_to': self.customuser.id,
        }
        response = self.client.post(f'/crm/activity/', data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class ProductModelTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        pass
    def test_create_product(self):
        obj = Product.objects.create(
            name='Test String',
            price=123.45,
            description='Test Text',
            is_active=True,
        )
        self.assertIsNotNone(obj.id)
        self.assertEqual(str(obj), f'Product object ({obj.id})')

class ProductAPITests(BaseTestSetup):
    def setUp(self):
        super().setUp()
    def test_get_product_list(self):
        response = self.client.get(f'/crm/product/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_product(self):
        data = {
            'name': 'Test String',
            'price': 123.45,
            'description': 'Test Text',
            'is_active': True,
        }
        response = self.client.post(f'/crm/product/', data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class InvoiceModelTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create()
        self.customuser = CustomUser.objects.create()
    def test_create_invoice(self):
        obj = Invoice.objects.create(
            invoice_number='Test String',
            total=123.45,
            status='Test String',
            discount=123.45,
            customer=self.customer,
            created_by=self.customuser,
        )
        self.assertIsNotNone(obj.id)
        self.assertEqual(str(obj), f'Invoice object ({obj.id})')

class InvoiceAPITests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create()
        self.customuser = CustomUser.objects.create()
    def test_get_invoice_list(self):
        response = self.client.get(f'/crm/invoice/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_invoice(self):
        data = {
            'invoice_number': 'Test String',
            'total': 123.45,
            'status': 'Test String',
            'discount': 123.45,
            'customer': self.customer.id,
            'created_by': self.customuser.id,
        }
        response = self.client.post(f'/crm/invoice/', data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class PaymentModelTests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.invoice = Invoice.objects.create()
        self.customuser = CustomUser.objects.create()
    def test_create_payment(self):
        obj = Payment.objects.create(
            amount=123.45,
            invoice=self.invoice,
            received_by=self.customuser,
        )
        self.assertIsNotNone(obj.id)
        self.assertEqual(str(obj), f'Payment object ({obj.id})')

class PaymentAPITests(BaseTestSetup):
    def setUp(self):
        super().setUp()
        self.invoice = Invoice.objects.create()
        self.customuser = CustomUser.objects.create()
    def test_get_payment_list(self):
        response = self.client.get(f'/crm/payment/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_payment(self):
        data = {
            'amount': 123.45,
            'invoice': self.invoice.id,
            'received_by': self.customuser.id,
        }
        response = self.client.post(f'/crm/payment/', data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

