from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from Creation.models import School, Department, Degree, Regulation, Semester
from .models import Faculty, Student, FacultyMapping, DepartmentAdminAssignment
from .serializers import UserRoleSerializer
from datetime import date
import traceback
import sys

User = get_user_model()

class FilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Campus Admin User
        self.admin_user = User.objects.create_user(
            username='filter_admin', password='password', role='COLLEGE_ADMIN', email='filter_admin@test.com'
        )
        self.client.force_authenticate(user=self.admin_user)

        # --- Setup School & Degree & Dept ---
        self.school = School.objects.create(school_name="School of Engineering", school_code="SOE")
        self.degree = Degree.objects.create(
            degree_name="B.Tech", degree_code="BTECH", 
            degree_duration=4, number_of_semesters=8, school=self.school
        )
        self.dept_cse = Department.objects.create(
            dept_name="Computer Science", dept_code="CSE", degree=self.degree
        )
        self.dept_ece = Department.objects.create(
            dept_name="Electronics", dept_code="ECE", degree=self.degree
        )

        # --- Setup Regulation & Semester ---
        self.regulation = Regulation.objects.create(
            degree=self.degree, regulation_code="R20", batch="2020-2024"
        )
        self.semester = Semester.objects.create(
            degree=self.degree, sem_number=1, sem_name="Sem 1", year=1
        )

        # --- Setup Faculty ---
        self.f_user1 = User.objects.create_user(username='filter_f1', role='FACULTY', email='filter_f1@test.com')
        self.faculty1 = Faculty.objects.create(
            user=self.f_user1, employee_id="FT001", faculty_name="Faculty One",
            faculty_email="filter_f1@test.com", faculty_gender="MALE"
        )
        # Map Faculty 1 to SOE - CSE
        FacultyMapping.objects.create(faculty=self.faculty1, school=self.school, department=self.dept_cse)

        self.f_user2 = User.objects.create_user(username='filter_f2', role='FACULTY', email='filter_f2@test.com')
        self.faculty2 = Faculty.objects.create(
            user=self.f_user2, employee_id="FT002", faculty_name="Faculty Two",
            faculty_email="filter_f2@test.com", faculty_gender="FEMALE"
        )
        # Map Faculty 2 to SOE - ECE
        FacultyMapping.objects.create(faculty=self.faculty2, school=self.school, department=self.dept_ece)

        # --- Setup Students ---
        self.s_user1 = User.objects.create_user(username='filter_s1', role='STUDENT', email='filter_s1@test.com')
        self.student1 = Student.objects.create(
            user=self.s_user1, roll_no="ST001", student_name="Student One",
            student_email="filter_s1@test.com", student_gender="MALE", student_date_of_birth=date(2000, 1, 1),
            student_phone_number="1234567890", parent_name="Parent1", parent_phone_number="0987654321",
            batch="2020-2024", degree=self.degree, department=self.dept_cse,
            regulation=self.regulation, semester=self.semester, section="A"
        )

        self.s_user2 = User.objects.create_user(username='filter_s2', role='STUDENT', email='filter_s2@test.com')
        self.student2 = Student.objects.create(
            user=self.s_user2, roll_no="ST002", student_name="Student Two",
            student_email="filter_s2@test.com", student_gender="FEMALE", student_date_of_birth=date(2000, 1, 2),
            student_phone_number="1234567890", parent_name="Parent2", parent_phone_number="0987654321",
            batch="2020-2024", degree=self.degree, department=self.dept_cse,
            regulation=self.regulation, semester=self.semester, section="B"
        )

    def test_faculty_filter_by_dept(self):
        # Filter for CSE (Faculty One)
        response = self.client.get("/users/faculty/filter/", {'dept_code': 'CSE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['employee_id'], "FT001")

    def test_faculty_filter_by_school(self):
        # Filter for SOE (Both Faculty One and Two)
        response = self.client.get("/users/faculty/filter/", {'school_code': 'SOE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_student_filter_by_dept_and_section(self):
        # Filter for CSE and Section A (Student One)
        response = self.client.get("/users/students/filter/", {'dept_code': 'CSE', 'section': 'A'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['roll_no'], "ST001")

    def test_student_filter_by_degree(self):
        # Filter for BTECH (Both students)
        response = self.client.get("/users/students/filter/", {'degree': 'BTECH'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_student_filter_by_regulation(self):
        # Filter for R20 (Both students)
        response = self.client.get("/users/students/filter/", {'regulation': 'R20'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

class DualRoleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # School, Degree, Dept
        self.school = School.objects.create(school_name="Test School", school_code="TS")
        self.degree = Degree.objects.create(
            degree_name="Test Degree", degree_code="TD", 
            degree_duration=4, number_of_semesters=8, school=self.school
        )
        self.dept = Department.objects.create(
            dept_name="Test Dept", dept_code="TDEPT", degree=self.degree
        )
        
        # Campus Admin to perform assignment
        self.ca_user = User.objects.create_user(
            username='ca_user', role='COLLEGE_ADMIN', email='ca@test.com'
        )
        
        # Faculty user
        self.f_user = User.objects.create_user(
            username='f_user', role='FACULTY', email='f_user@test.com'
        )
        self.faculty = Faculty.objects.create(
            user=self.f_user, employee_id="F123", faculty_name="Faculty User",
            faculty_email="f_user@test.com", faculty_gender="MALE"
        )

    def test_faculty_to_ca_promotion(self):
        # 1. Verify initial role
        self.assertEqual(self.f_user.role, 'FACULTY')
        self.assertTrue(self.f_user.is_faculty)
        
        # 2. Assign as Dept Admin
        # In a real view, this is done by a Campus Admin
        DepartmentAdminAssignment.objects.create(
            faculty=self.faculty,
            school=self.school,
            degree=self.degree,
            department=self.dept,
            assigned_by=self.ca_user
        )
        
        # 3. Verify role update
        self.f_user.refresh_from_db()
        self.assertEqual(self.f_user.role, 'ACADEMIC_COORDINATOR')
        self.assertTrue(self.f_user.is_faculty)
        
        # 4. Verify Serializer output
        serializer = UserRoleSerializer(self.f_user)
        profile_details = serializer.data['profile_details']
        self.assertEqual(profile_details['name'], "Faculty User")
        self.assertEqual(profile_details['id'], "F123")
        self.assertIn("(Dept Admin)", profile_details['details'])
