from sendgrid import SendGridAPIClient, Substitution
from sendgrid.helpers.mail import Mail

from scohaz_platform.settings import EMAIL_SENDER, EMAIL_HOST_PASSWORD


class ScohazEmailHelper:
    sender = EMAIL_SENDER

    @staticmethod
    def create_mail(context):
        message = Mail(
            from_email=ScohazEmailHelper.sender,
            to_emails=context["to"],
            subject=context["subject"])
        for substitution in context["substitutions"].keys():
            message.personalizations[0].add_substitution(
                Substitution(substitution, context["substitutions"][substitution]),
            )
        message.template_id = context["template_id"]
        return message

    @staticmethod
    def send_email(message):
        try:
            sg = SendGridAPIClient(EMAIL_HOST_PASSWORD)
            response = sg.send(message)
            print(response)
            print(response.status_code)
            print(response.body)
        except Exception as e:
            print(str(e))
