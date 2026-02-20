from rest_framework.permissions import BasePermission

class IsCollegeAdmin(BasePermission):
    """
    Allows access only to users with COLLEGE_ADMIN role
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "COLLEGE_ADMIN"
        )

class IsAcademicCoordinator(BasePermission):
    """
    Allows access only to users with ACADEMIC_COORDINATOR role
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ACADEMIC_COORDINATOR"
        )

class IsFaculty(BasePermission):
    """
    Allows access to Faculty or Academic Coordinators
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.role in ["FACULTY", "ACADEMIC_COORDINATOR"])
        )

class IsActiveFaculty(BasePermission):
    """
    Check if faculty is active (requires faculty profile check)
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        if request.user.role not in ["FACULTY", "ACADEMIC_COORDINATOR"]:
            return False
            
        faculty_profile = getattr(request.user, 'faculty_profile', None)
        return faculty_profile and faculty_profile.is_active
