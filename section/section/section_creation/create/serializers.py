from rest_framework import serializers
from .models import Section

class SectionSerializer(serializers.ModelSerializer):
    """
    Serializer for Section creation and listing.
    """

    class Meta:
        model = Section
        fields = ['id', 'section_name']
        read_only_fields = ['id']

    def validate_section_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Section name cannot be empty."
            )

        if len(value) > 50:
            raise serializers.ValidationError(
                "Section name must not exceed 50 characters."
            )

        return value
