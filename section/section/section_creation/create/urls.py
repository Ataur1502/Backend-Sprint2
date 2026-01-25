from django.urls import path
from .views import SectionAPIView

urlpatterns = [
    path('sections/', SectionAPIView.as_view(), name='sections'),               # GET, POST
    path('sections/<uuid:section_id>/', SectionAPIView.as_view(), name='section-update'),  # PUT
]
