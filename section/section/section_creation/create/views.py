from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Section
from .serializers import SectionSerializer


class SectionAPIView(APIView):
    """
    GET  : List all sections
    POST : Create a new section
    PUT  : Update an existing section
    """

    # --------------------
    # GET: List Sections
    # --------------------
    def get(self, request):
        sections = Section.objects.all()
        serializer = SectionSerializer(sections, many=True)
        return Response(
            {
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    # --------------------
    # POST: Create Section
    # --------------------
    def post(self, request):
        serializer = SectionSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Section created successfully",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # --------------------
    # PUT: Update Section
    # --------------------
    def put(self, request, section_id):
        section = get_object_or_404(Section, id=section_id)
        serializer = SectionSerializer(section, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Section updated successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
