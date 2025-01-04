
class UserTypes:
    SYSTEM_USER_CODE = '0'
    ENTITY_USER_CODE = '1'
    ENTITY_ADMIN_USER_CODE = '2'
    EKYC_FIRST_CHECKER_CODE = '3'
    EKYC_MAKER_CHECKER_USER_CODE = '6'
    EKYC_ADMIN_USER_CODE = '4'
    PUBLIC_USER_CODE = '5'

    ACCESS_REQUEST_USER_TYPE_CODE = ['1', '5']
    EKYC_USERS_CODE = ['3', '4', '6']
    ENTITY_USERS_CODE = ['1', '2']
    USERS_CAN_SEE_VIDEO_CALL = ['4', '6', '3']


class ApplicationStatus:
    CREATED = '0'
    OTP = '1'
    RESIDENCY_LOCATION = '2'
    DOCUMENT_SCAN = '3'
    IN_PROGRESS = '4'
    VIDEO_CALL = '5'
    VIDEO_CALL_ENDED = '6'  # added
    SUBMITTED = '7'  # changed
    VERIFIED = '8'  # changed
    REJECTED = '9'  # changed
    FIRST_APPROVAL = '10'  # changed


class DocumentTypes:
    IDENTITY_CARD = '01'
    IDENTITY_CARD_BACK = '02'
    FACE_IMAGE = '03'
    BILL = '04'
    SIGNATURE = '05'
    W8 = '06'
    W9 = '07'
    PASSPORT = '08'


class PageTypes:
    DOCUMENT_PAGE = 'Documents'


class GenderTypes:
    MALE = 1
    FEMALE = 2


class BeneficiaryTypes:
    INDIVIDUAL = '01'
    COMPANY = '02'


class MaritalStatus:
    MARRIED = '01'
    DIVORCED = '02'
    SINGLE = '03'
    WIDOWED = '04'


class EmploymentTypes:
    PERMANENT = '01'
    TEMPORARY = '02'
    CONTRACT = '03'
    DAY_LABOR = '04'


class EmploymentStatusTypes:
    PRIVATE_SECTOR_EMPLOYEE = '01'
    PUBLIC_SECTOR_EMPLOYEE = '02'
    BUSINESS_OWNER = '03'
    RETIRED = '04'
    LAWYER = '05'
    BANKER = '06'
    OTHER_PROFESSIONAL = '07'
    UNEMPLOYED = '08'


class AccessRequestStatusTypes:

    PENDING = '01'
    ACCEPTED = '02'
    REJECTED = '03'


class AccessRequestMethods:
    ACCEPT_REQUEST = ['accept', 'Accept', 'ACCEPT', 'Approve', 'Approve', 'APPROVE']
    DENY_REQUEST = ['deny', 'Deny', 'DENY', 'Reject', 'reject', 'REJECT']
    ACCESS_REQUEST = ['access_request', 'Access_Request', 'ACCESS_REQUEST',
                      'access', 'Access', 'ACCESS', 'request', 'Request', 'REQUEST']


class NotificationTypes:
    CAN_UPDATE_NOTIFICATION = ['01', '02', '03', '05', '06']
    CAN_NOT_UPDATE_NOTIFICATION = ['04', '07', '08']
    NEED_TO_PASS_CONTENT = ['08', '10', '11', '14']
    ENTITY_RECEIVER = 'entity'
    BENEFICIARY_RECEIVER = 'beneficiary'
    NOTIFICATIONS_CONTENT = \
        {

            # access request
            "01": "_(self.content) % (obj._from.name)",
            # accept request
            "02": "_(self.content) % "
                  "('******' + obj._from.beneficiary.national_number[5:10])",
            # reject request
            "03": "_(self.content) % "
                  "('******' + obj._from.beneficiary.national_number[5:10])",
            #  birthdate
            "04": "_(self.content) % ('BENEFICIARY_NAME')",
            # data viewed
            "05": "_(self.content) % (self.obj._from.name)",
            # reminder expired id card
            "06": "_(self.content)",
            # reminder to complete registration
            "07": "_(self.content) % ('BENEFICIARY_NAME')",
            # Announcement and promotions
            "08": "_(self.content)",
            # update app
            "09": "_(self.content)",
            # manual notification for specific user
            "10": "_(self.content)",
            # manual notification for specific entity
            "11": "_(self.content)",
            # update data
            "12": "_(self.content)",
            # verified data
            "13": "_(self.content)",
            # promotion
            "14": "_(self.content)",
            # under review
            "15": "_(self.content)",
            # rejected application
            "16": "_(self.content)", }

    ACCESS_REQUEST = '01'
    ACCEPT_REQUEST = '02'
    REJECT_REQUEST = '03'
    BIRTH_DATE = '04'
    DATA_VIEWED = '05'
    REMINDER_EXPIRED_ID_CARD = '06'
    REMINDER_TO_COMPLETE_REGISTRATION = '07'
    ANNOUNCEMENT = '08'
    UPDATE_APP = '09'
    FOR_SPEC_USER = '10'
    FOR_SPEC_ENTITY = '11'
    UPDATE_DATA = '12'
    VERIFIED_DATA = '13'
    PROMOTIONS = '14'
    UNDER_REVIEW = '15'
    REJECTED_APPLICATION = '16'


class NotificationActions:
    ACCESS_ACTIONS = ['01', '02']
    ACCEPT = '01'
    REJECT = '02'
    UPDATE_APP = '03'
    CONTINUE = '05'
    UPDATE = '06'
    OPEN = '07'


class ServiceTypes:
    FINANCIAL = '01'
    TELECOMMUNICATION = '02'

#
# class BeneficiaryTypesCode:
#     INDIVIDUAL = 'IND'
#     COMPANY = 'COMP'
#     # CORPORATE = 'CORPORATE'


class NotificationActionsEndPoints:
    ENDPOINTS = {
        "01": {
            "Accept"
            : "/beneficiary/approve-entity-by_notification"
              "/?notification_id=%s&method=accept",
            "Reject"
            : "/beneficiary/approve-entity-by"
              "_notification/?notification_id=%s&method=reject"},
        # "15": {}
    }

    ACCESS_REQUEST = '01'
    ACCEPT_REQUEST = '02'
    REJECT_REQUEST = '03'
    BIRTH_DATE = '04'
    DATA_VIEWED = '05'
    REMINDER_EXPIRED_ID_CARD = '06'
    REMINDER_TO_COMPLETE_REGISTRATION = '07'
    ANNOUNCEMENT = '08'
    UPDATE_APP = '09'
    FOR_SPEC_USER = '10'
    FOR_SPEC_ENTITY = '11'
    UPDATE_DATA = '12'
    VERIFIED_DATA = '13'
    PROMOTIONS = '14'
    UNDER_REVIEW = '15'
    REJECTED_APPLICATION = '16'


class ErrorCodes:
    NATIONAL_NUMBER_ALREADY_EXISTS = '01'
    WRONG_USERNAME_OR_PASSWORD = '02'
    USERNAME_IS_NOT_EXISTS = '03'
    FAILED_TO_SAVE_FILE = '04'
    WRONG_CODE = '05'
    WRONG_USERNAME = '06'
