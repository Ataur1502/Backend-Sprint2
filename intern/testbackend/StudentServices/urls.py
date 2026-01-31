from django.urls import path
from .views import (
    StudentDocumentRequestView,
    AdminDocumentRequestListView,
    AdminDocumentRequestUpdateView
)

urlpatterns = [
    path('requests/', StudentDocumentRequestView.as_view()),
    path('admin/requests/', AdminDocumentRequestListView.as_view()),
    path('admin/requests/<uuid:request_id>/', AdminDocumentRequestUpdateView.as_view()),
]
