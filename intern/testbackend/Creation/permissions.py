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
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ACADEMIC_COORDINATOR"
        )

class IsCampusAdmin(BasePermission):
    """
    Allows access only to ACADEMIC_COORDINATOR or COLLEGE_ADMIN roles.
    This aligns with logic used in UserDataManagement for high-level management.
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["COLLEGE_ADMIN", "ACADEMIC_COORDINATOR"]
        )

class IsFaculty(BasePermission):
    """
    Allows access to both pure Faculty and Academic Coordinators (who are also Faculty).
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["FACULTY", "ACADEMIC_COORDINATOR"]
        )

class IsActiveFaculty(BasePermission):
    """
    Ensures the user is a Faculty/Coordinator AND has an active faculty profile.
    Critical for teaching-related features.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role in ["FACULTY", "ACADEMIC_COORDINATOR"]):
            return False
            
        return hasattr(user, 'faculty_profile') and user.faculty_profile.is_active


'''
---------------------------------------------------------------------------------------------------------------------------------
                                        Faculty permissions(faculty)
---------------------------------------------------------------------------------------------------------------------------------
'''


from rest_framework.permissions import BasePermission
from CourseManagement.models import FacultyAllocation


from UserDataManagement.models import Faculty


class IsAllocationOwner(BasePermission):
    """
    Checks whether allocation belongs to logged-in faculty.
    """

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        return obj.faculty == request.user