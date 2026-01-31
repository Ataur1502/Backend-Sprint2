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

class DocumentRequestHistorySerializer(serializers.ModelSerializer):
    updated_by_email = serializers.EmailField(
        source='updated_by.email',
        read_only=True
    )

    class Meta:
        model = DocumentRequestHistory
        fields = [
            'history_id',
            'status',
            'remark',
            'updated_by_email',
            'updated_at'
        ]
