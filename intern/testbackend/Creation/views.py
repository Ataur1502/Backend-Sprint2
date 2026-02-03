from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from .models import School, Degree, Department, Semester, Regulation
from .serializers import DegreeSerializer, SchoolSerializer, DepartmentSerializer, SemesterSerializer,RegulationSerializer
from .permissions import IsCollegeAdmin
from rest_framework.permissions import IsAuthenticated

# ------------------------------------------
# SEMESTER 
# ------------------------------------------

class SemesterAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    # GET semesters
    def get(self, request, sem_id=None):
        if sem_id:
            semester = get_object_or_404(Semester, sem_id=sem_id)
            return Response(SemesterSerializer(semester).data)

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

    def delete(self, request, sem_id):
        semester = get_object_or_404(Semester, sem_id=sem_id)
        semester.delete()
        return Response({"message": "Semester deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

#School creation
class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    lookup_field = 'school_id'  # Allow looking up by school_id instead of default PK if desired
    permission_classes = [IsAuthenticated, IsCollegeAdmin]



"""
-----------------------------------------------------------------------------------------------------------------------------
                                            DEGREE CREATION
-----------------------------------------------------------------------------------------------------------------------------
"""



# ------------------------------------------
# DEGREE LIST (FLAT)
# ------------------------------------------
class DegreeListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request, degree_id=None):
        if degree_id:
            degree = get_object_or_404(Degree, degree_id=degree_id)
            return Response(DegreeSerializer(degree).data)
            
        school_id = request.query_params.get('school_id')
        if school_id:
            degrees = Degree.objects.filter(school_id=school_id)
        else:
            degrees = Degree.objects.all()
        serializer = DegreeSerializer(degrees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, degree_id):
        degree = get_object_or_404(Degree, degree_id=degree_id)
        serializer = DegreeSerializer(degree, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"msg": "Degree updated successfully", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, degree_id):
        degree = get_object_or_404(Degree, degree_id=degree_id)
        degree.delete()
        return Response({"msg": "Degree deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class DegreeView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    # ---------------- GET ----------------
    def get(self, request, school_id):
        school = get_object_or_404(School, school_id=school_id)
        degrees = Degree.objects.filter(school=school)

        serializer = DegreeSerializer(degrees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ---------------- POST ----------------
    def post(self, request, school_id):
        school = get_object_or_404(School, school_id=school_id)
        data = request.data

        serializer = DegreeSerializer(data=data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 1️⃣ Create Degree
        degree = serializer.save(school=school)

        # 2️⃣ Auto-create Semester ENTITIES
        semesters = [
    Semester(
        degree=degree,
        sem_number=i,
        sem_name=f"Semester {i}",
        year=((i - 1) // 2) + 1,   
               
    )
    for i in range(1, degree.number_of_semesters + 1)
]


        Semester.objects.bulk_create(semesters)

        return Response(
            {
                "message": "Degree and Semesters created successfully",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    # ---------------- PUT ----------------
    def put(self, request, school_id, degree_id):
        school = get_object_or_404(School, school_id=school_id)
        degree = get_object_or_404(
            Degree,
            degree_id=degree_id,
            school=school
        )

        serializer = DegreeSerializer(degree, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        old_sem_count = degree.number_of_semesters

        # Save degree (updates number_of_semesters automatically)
        degree = serializer.save()

        new_sem_count = degree.number_of_semesters

        # 🔁 Sync semesters
        if new_sem_count > old_sem_count:
            new_sems = [
                Semester(
                    degree=degree,
                    sem_number=i,
                    sem_name=f"Semester {i}",
                    year=((i - 1) // 2) + 1,
                    
                )
                for i in range(old_sem_count + 1, new_sem_count + 1)
            ]
            Semester.objects.bulk_create(new_sems)

        elif new_sem_count < old_sem_count:
            Semester.objects.filter(
                degree=degree,
                sem_number__gt=new_sem_count
            ).delete()

        return Response(
            {
                "message": "Degree and semesters updated successfully",
                "data": DegreeSerializer(degree).data
            },
            status=status.HTTP_200_OK
        )



'''
---------------------------------------------------------------------------------------------------------------------------------
                                            Department Creation
---------------------------------------------------------------------------------------------------------------------------------
'''
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
    def get(self, request, dept_id=None):
        if dept_id:
            department = get_object_or_404(Department, dept_id=dept_id)
            return Response(DepartmentSerializer(department).data)

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
        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Department updated successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, dept_id):
        department = get_object_or_404(Department, dept_id=dept_id)
        department.delete()
        return Response({"message": "Department deleted successfully"}, status=status.HTTP_204_NO_CONTENT)



# ------------------------------------------
# REGULATION
# ------------------------------------------


class RegulationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request, regulation_id=None):
        if regulation_id:
            regulation = get_object_or_404(Regulation, regulation_id=regulation_id)
            return Response(RegulationSerializer(regulation).data)
            
        regulations = Regulation.objects.all()
        degree_id = request.query_params.get('degree_id')

        if degree_id:
            regulations = regulations.filter(degree_id=degree_id)

        serializer = RegulationSerializer(regulations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RegulationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        regulation = serializer.save()

        return Response(
            {
                "msg": "Regulation created successfully",
                "regulation_id": regulation.regulation_id,
                "batch": regulation.batch,
                "end_year": serializer.get_end_year(regulation)
            },
            status=status.HTTP_201_CREATED
        )

    def put(self, request, regulation_id):
        regulation = get_object_or_404(Regulation, regulation_id=regulation_id)
        serializer = RegulationSerializer(regulation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"msg": "Regulation updated successfully", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, regulation_id):
        regulation = get_object_or_404(Regulation, regulation_id=regulation_id)
        regulation.delete()
        return Response({"msg": "Regulation deleted successfully"}, status=status.HTTP_204_NO_CONTENT)



