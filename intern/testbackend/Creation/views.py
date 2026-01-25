from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from .models import School, Degree, Department, Semester
from .serializers import DegreeSerializer, SchoolSerializer, DepartmentSerializer, SemesterSerializer
from .permissions import IsCollegeAdmin
from rest_framework.permissions import IsAuthenticated

# ------------------------------------------
# SEMESTER 
# ------------------------------------------

class SemesterAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    # GET semesters
    def get(self, request):
        degree_id = request.query_params.get('degree_id')
        department_id = request.query_params.get('department_id')

        semesters = Semester.objects.all()

        if degree_id:
            semesters = semesters.filter(degree_id=degree_id)

        if department_id:
            semesters = semesters.filter(department_id=department_id)

        semesters = semesters.order_by('sem_number')

        serializer = SemesterSerializer(semesters, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST create semester
    def post(self, request):
        serializer = SemesterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Semester created successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # PUT update semester
    def put(self, request, sem_id):
        semester = get_object_or_404(Semester, sem_id=sem_id)
        serializer = SemesterSerializer(semester, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Semester updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#School creation
class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    lookup_field = 'school_id'  # Allow looking up by school_id instead of default PK if desired
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

#Degree creation
class DegreeView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]
    # ---------------- GET ----------------
    def get(self, request, school_id=None):
        if school_id:
            school = get_object_or_404(School, school_id=school_id)
            degrees = Degree.objects.filter(school=school)
        else:
            degrees = Degree.objects.all()

        serializer = DegreeSerializer(degrees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ---------------- POST ----------------
    def post(self, request, school_id=None):
        data = request.data
        
        # If school_id not in URL, check if it's in body
        effective_school_id = school_id or data.get('school_id') or data.get('school')
        
        if not effective_school_id:
            return Response({"message": "School ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        school = get_object_or_404(School, school_id=effective_school_id)

        required_fields = [
            'degree_code',
            'degree_name',
            'degree_duration',
            'number_of_semesters'
        ]

        # Required field validation
        if not all(field in data and data[field] for field in required_fields):
            return Response(
                {"message": "All required fields must be filled"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Duplicate Degree Code check
        if Degree.objects.filter(degree_code=data['degree_code']).exists():
            return Response(
                {"message": "Degree Code already exists"},
                status=status.HTTP_409_CONFLICT
            )

        # Duplicate Degree Name under same School
        if Degree.objects.filter(
            degree_name=data['degree_name'],
            school=school
        ).exists():
            return Response(
                {"message": "Degree Name already exists under this School"},
                status=status.HTTP_409_CONFLICT
            )

        serializer = DegreeSerializer(data=data)
        if serializer.is_valid():
            serializer.save(school=school)
            return Response(
                {
                    "message": "Degree created successfully",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ---------------- PUT ----------------
    def put(self, request, degree_id, school_id=None):
        # We prefer degree_id directly as it's the unique PK/UUID for records
        degree = get_object_or_404(Degree, degree_id=degree_id)
        
        # If school_id is provided, verify it matches (extra safety)
        if school_id:
            school = get_object_or_404(School, school_id=school_id)
            if degree.school != school:
                return Response({"message": "Degree does not belong to this school"}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent duplicate Degree Name during update
        if 'degree_name' in request.data:
            if Degree.objects.filter(
                degree_name=request.data['degree_name'],
                school=degree.school
            ).exclude(degree_id=degree_id).exists():
                return Response(
                    {"message": "Degree Name already exists under this School"},
                    status=status.HTTP_409_CONFLICT
                )

        serializer = DegreeSerializer(
            degree,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Degree updated successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




#Department Creation

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Department
from .serializers import DepartmentSerializer
from .permissions import IsCollegeAdmin


class DepartmentAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    # GET Departments
    def get(self, request):
        degree_id = request.query_params.get('degree_id')

        if degree_id:
            departments = Department.objects.filter(degree_id=degree_id)
        else:
            departments = Department.objects.all()

        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST Create Department
    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Department created successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # PUT Update Department
    def put(self, request, dept_id):
        department = get_object_or_404(Department, dept_id=dept_id)
        serializer = DepartmentSerializer(
            department,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Department updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ------------------------------------------
# REGULATION
# ------------------------------------------
from .models import Regulation
from .serializers import RegulationSerializer

class RegulationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request):
        regulations = Regulation.objects.all()
        degree_id = request.query_params.get('degree_id')
        if degree_id:
            regulations = regulations.filter(degree_id=degree_id)
        
        serializer = RegulationSerializer(regulations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RegulationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Regulation created successfully",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, regulation_id):
        regulation = get_object_or_404(Regulation, regulation_id=regulation_id)
        serializer = RegulationSerializer(regulation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Regulation updated successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
