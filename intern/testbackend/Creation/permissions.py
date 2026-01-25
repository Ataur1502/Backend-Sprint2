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
