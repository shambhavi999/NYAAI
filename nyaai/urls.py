from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/',        admin.site.urls),
    path('api/auth/',     include('accounts.urls')),
    path('api/cases/',    include('cases.urls')),
    path('dashboard/',    TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('',              TemplateView.as_view(template_name='index.html'),     name='home'),
    path('api/documents/', include('documents.urls')),
    path('case/<int:id>/', TemplateView.as_view(template_name='case_detail.html'), name='case_detail'),
    path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile'),
    path('forum/', TemplateView.as_view(template_name='forum.html'), name='forum'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)