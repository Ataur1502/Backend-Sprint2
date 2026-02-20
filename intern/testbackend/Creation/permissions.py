from rest_framework.permissions import BasePermission

#faculty imports:
from rest_framework.permissions import BasePermission
from CourseManagement.models import FacultyAllocation

class RoleBasedPermission(BasePermission):
    """
    Generic role-based permission.
    Views must define: allowed_roles = ["ROLE1", "ROLE2"]
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        allowed_roles = getattr(view, "allowed_roles", [])
        user_role = str(user.role).upper()

        return user_role in allowed_roles


class IsCollegeAdmin(BasePermission):
    """
    Allows access only to COLLEGE_ADMIN role.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return str(user.role).upper() == "COLLEGE_ADMIN"

class IsAcademicCoordinator(BasePermission):
    """
    Allows access only to ACADEMIC_COORDINATOR role.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return str(user.role).upper() == "ACADEMIC_COORDINATOR"


'''
---------------------------------------------------------------------------------------------------------------------------------
                                        Faculty permissions(faculty)
---------------------------------------------------------------------------------------------------------------------------------
'''


from rest_framework.permissions import BasePermission
from CourseManagement.models import FacultyAllocation


from UserDataManagement.models import Faculty

class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        return Faculty.objects.filter(user=request.user).exists()



from rest_framework.permissions import BasePermission
from UserDataManagement.models import Faculty


class IsActiveFaculty(BasePermission):
    def has_permission(self, request, view):
        faculty = Faculty.objects.filter(user=request.user).first()
        return faculty is not None


class IsAllocationOwner(BasePermission):
    """
    Checks whether allocation belongs to logged-in faculty.
    """

    def has_object_permission(self, request, view, obj):
        return obj.faculty == request.user
