from onesignal_sdk.client import Client
from django.conf import settings
from entity.models import EntityUser
from notifications.models import (UserNotification,
                                  EntityNotification, NotificationType)
from utils.constant_lists_variables import (NotificationTypes,
                                            NotificationActionsEndPoints)
import json


class NotificationHelper(object):
    def __init__(self, obj, type_of_receiver, device_ids=None):
        self.obj = obj
        self.client = Client(app_id=settings.ONESIGNAL_APP_ID,
                             rest_api_key=settings.ONESIGNAL_RESET_API_ID)
        self.device_ids = device_ids
        self.notification_type = obj.notification_type
        self.type_of_receiver = type_of_receiver
        if (self.notification_type.code not in
                NotificationTypes.NEED_TO_PASS_CONTENT):
            self.content = obj.notification_type.content
            temp_extra_data = obj.notification_type.extra_data
            try:
                self.extra_data = json.loads(temp_extra_data)
            except AttributeError:
                self.extra_data = temp_extra_data
        else:
            self.content = obj.content

        self._from = obj._from_id
        self._to = obj._to

        self.notification_body = {}
        self.buttons = []

    def _send_notification(self):
        self.content = self.formatting_content(self.obj)
        self.notification_body = self.preparing_notification_body()
        self.notification_body["include_player_ids"] = (
            self.cleansing_devices_ids())
        if self.notification_body["include_player_ids"]:
            request = self.client.send_notification(self.notification_body)
            return request

    def get_notification_title(self, obj):
        return str(self.notification_type)

    def formatting_content(self, obj):
        # print(obj.content)
        notification_type = self.notification_type
        notification_types = NotificationTypes.NOTIFICATIONS_CONTENT
        # print(notification_type)
        # print(notification_type.code)
        # print(eval(notification_type.code))
        # print(notification_types[notification_type.code])
        # print(self.content)
        # print(obj._from.name)
        # print(str(notification_types[notification_type.code]))
        try:
            content = eval(notification_types[notification_type.code])
        except AttributeError:
            content = obj.content

        return content

    def preparing_notification_body(self):
        if self.type_of_receiver == NotificationTypes.BENEFICIARY_RECEIVER:
            include_player_ids = self.device_ids \
                if self.device_ids else [self._to.beneficiary.device_id]
        elif self.type_of_receiver == NotificationTypes.ENTITY_RECEIVER:
            print(self._to)
            print(self._to.entityuser_set)
            include_player_ids = EntityUser.objects.filter(
                entity=self._to).values_list('device_id', flat=True)

        notification_body = {
            'contents': {'en': f"{self.content}"},
            'include_player_ids': include_player_ids,
            # // TODO : handle extra data
            "data": self.get_extra_data(),
            'buttons': self.get_notification_buttons(),
        }
        return notification_body

    def get_extra_data(self):
        if (self.type_of_receiver
                == NotificationTypes.ENTITY_RECEIVER):
            data = {'beneficiary_id': self._from,
                    "notification_id": self.obj.id,
                    "extra_data": self.extra_data}
        elif (self.type_of_receiver
              == NotificationTypes.BENEFICIARY_RECEIVER):
            data = {'entity_id': self._from,
                    "notification_id": self.obj.id,
                    "extra_data": self.extra_data}
        return data

    def get_notification_buttons(self):
        buttons = []
        if self.notification_type.has_actions_ind:
            if self.obj.is_actioned_ind:
                if not self.notification_type.actions.filter(
                        multiple_actions_ind=False).exists():
                    actions = self.notification_type.actions.filter(
                        multiple_actions_ind=True)
                else:
                    actions = []
            else:
                actions = self.notification_type.actions.all()

            for action in actions:
                try:
                    buttons.append(
                        {
                            "id": action.code,
                            "text": action.name,
                            "endpoint": (
                                    NotificationActionsEndPoints.ENDPOINTS[
                                        NotificationTypes.ACCESS_REQUEST
                                    ][action.name] % (self.obj.id)
                            )
                        }
                    )
                except AttributeError:
                    buttons.append({"id": action.code, "text": action.name})
        return buttons

    def cleansing_devices_ids(self):
        devices_ids = self.notification_body["include_player_ids"]
        cleaned_devices_ids = []
        for device in devices_ids:
            if device:
                if len(device) > 10 and not device.isspace() and device != '':
                    cleaned_devices_ids.append(device)
        return cleaned_devices_ids

    @staticmethod
    def add_new_notification(type_of_receiver, _to,
                             notification_type, _from=None,
                             _admin_ind=False, content=None):
        if type_of_receiver == NotificationTypes.BENEFICIARY_RECEIVER:
            notification = UserNotification.objects.create(
                _from_id=_from, _to_id=_to,
                notification_type=notification_type,
                admin_notification_ind=_admin_ind,
                is_actioned_ind=False, content=content)
            # _request = NotificationHelper(
            #     notification,
            #     type_of_receiver=NotificationTypes.BENEFICIARY_RECEIVER
            # )._send_notification()
            return notification
        elif type_of_receiver == NotificationTypes.ENTITY_RECEIVER:
            notification = EntityNotification.objects.create(
                _from_id=_from, _to_id=_to,
                notification_type=notification_type,
                admin_notification_ind=_admin_ind,
                is_actioned_ind=False, content=content)

            # _request = NotificationHelper(
            #     notification,
            #     type_of_receiver=NotificationTypes.ENTITY_RECEIVER
            # )._send_notification()
            return notification
