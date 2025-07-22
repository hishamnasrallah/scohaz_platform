from django.http import JsonResponse
from datetime import date

MOCK_USERS = {
    "1231231230": {
        "first_name_enu": "Adam",
        "second_name_enu": "Ali",
        "third_name_enu": "Hassan",
        "last_name_enu": "Omar",
        "gender": 32,
        "dob": "2010-01-01",
        "first_name": "آدم",
        "second_name": "علي",
        "third_name": "حسن",
        "last_name": "عمر",
        "mother_name_enu": "Sara",
        "mother_name_ara": "سارة"
    },
    "1231231231": {
        "first_name_enu": "Yousef",
        "second_name_enu": "Khalid",
        "third_name_enu": "Mahmoud",
        "last_name_enu": "Salem",
        "gender": 33,
        "dob": "1990-05-12",
        "first_name": "يوسف",
        "second_name": "خالد",
        "third_name": "محمود",
        "last_name": "سالم",
        "mother_name_enu": "Lina",
        "mother_name_ara": "لينا"
    },
    "1231231232": {
        "first_name_enu": "Mariam",
        "second_name_enu": "Ahmad",
        "third_name_enu": "Nabil",
        "last_name_enu": "Hussein",
        "gender": 32,
        "dob": "1995-09-23",
        "first_name": "مريم",
        "second_name": "أحمد",
        "third_name": "نبيل",
        "last_name": "حسين",
        "mother_name_enu": "Abeer",
        "mother_name_ara": "عبير"
    },
    "1231231233": {
        "first_name_enu": "Salem",
        "second_name_enu": "Othman",
        "third_name_enu": "Ibrahim",
        "last_name_enu": "Farid",
        "gender": 32,
        "dob": "1950-07-01",
        "first_name": "سالم",
        "second_name": "عثمان",
        "third_name": "إبراهيم",
        "last_name": "فريد",
        "mother_name_enu": "Widad",
        "mother_name_ara": "وداد"
    }
}

def get_user_info(request, national_number):
    user = MOCK_USERS.get(national_number)
    if user:
        return JsonResponse(user)
    return JsonResponse({"error": "User not found"}, status=404)
