from rest_framework import permissions

class IsCampusAdmin(permissions.BasePermission):
    """
    Allows access only to College Admins and Academic Coordinators (Campus Admin).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        allowed_roles = ['COLLEGE_ADMIN', 'ACADEMIC_COORDINATOR', 'college_admin', 'accedemic_coordinator']
        return request.user.role in allowed_roles
