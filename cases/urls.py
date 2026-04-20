"""
NYAAI - cases/urls.py
"""

from django.urls import path
from .views import CaseListCreateView, CaseDetailView, AnalyseCaseView

urlpatterns = [
    path('',              CaseListCreateView.as_view(), name='cases-list'),
    path('create/',       CaseListCreateView.as_view(), name='cases-create'),
    path('<int:case_id>/', CaseDetailView.as_view(),    name='case-detail'),
    path('<int:case_id>/analyse/', AnalyseCaseView.as_view(), name='case-analyse'),
]