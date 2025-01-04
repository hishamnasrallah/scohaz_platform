# translations/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_files, name='list_files'),
    path('edit/<str:filename>/', views.edit_translation,
         name='edit_translation'),
    path('delete_translation/<str:filename>/<str:key>/',
         views.delete_translation, name='delete_translation'),

]
