from django.urls import path
from . import views

urlpatterns = [
    path('download/<int:case_id>/', views.download_legal_notice, name='download_legal_notice'),
]