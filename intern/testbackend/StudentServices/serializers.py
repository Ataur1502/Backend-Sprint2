from rest_framework import serializers
from .models import DocumentRequest, DocumentRequestHistory

class DocumentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRequest
        fields = [
            'request_id',
            'document_type',
            'message',
            'status',
            'created_at'
        ]
        read_only_fields = ['request_id', 'status', 'created_at']

class DocumentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        'UNDER_REVIEW',
        'IN_HOLD',
        'APPROVED',
        'ISSUED',
        'REJECTED'
    ])
    remark = serializers.CharField(required=False, allow_blank=True)
