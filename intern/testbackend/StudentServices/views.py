from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import DocumentRequest, DocumentRequestHistory
from .serializers import (
    DocumentRequestSerializer,
    DocumentStatusUpdateSerializer
)
from Creation.permissions import IsCollegeAdmin

class StudentDocumentRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc_request = serializer.save(student=request.user)

        DocumentRequestHistory.objects.create(
            request=doc_request,
            status='UNDER_REVIEW',
            updated_by=request.user
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        qs = DocumentRequest.objects.filter(student=request.user)
        serializer = DocumentRequestSerializer(qs, many=True)
        return Response(serializer.data)

class AdminDocumentRequestListView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request):
        qs = DocumentRequest.objects.all().order_by('-created_at')
        serializer = DocumentRequestSerializer(qs, many=True)
        return Response(serializer.data)

class AdminDocumentRequestUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def patch(self, request, request_id):
        doc_request = DocumentRequest.objects.get(request_id=request_id)

        serializer = DocumentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc_request.status = serializer.validated_data['status']
        doc_request.save()

        DocumentRequestHistory.objects.create(
            request=doc_request,
            status=doc_request.status,
            remark=serializer.validated_data.get('remark'),
            updated_by=request.user
        )

        return Response(
            {"message": "Request status updated"},
            status=status.HTTP_200_OK
        )
