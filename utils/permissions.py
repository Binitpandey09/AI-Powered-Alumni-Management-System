from rest_framework import permissions


class IsAlumni(permissions.BasePermission):
    """
    Permission class to check if user is an Alumni
    """
    message = 'Only alumni users can perform this action.'
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'alumni'


class IsStudent(permissions.BasePermission):
    """
    Permission class to check if user is a Student
    """
    message = 'Only student users can perform this action.'
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'student'


class IsFaculty(permissions.BasePermission):
    """
    Permission class to check if user is a Faculty member
    """
    message = 'Only faculty users can perform this action.'
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'faculty'


class IsAlumniOrFaculty(permissions.BasePermission):
    """
    Permission class to check if user is Alumni or Faculty
    Used for mentorship and paid services
    """
    message = 'Only alumni or faculty users can perform this action.'
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['alumni', 'faculty']
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class to check if user is the owner of the object or an admin
    """
    message = 'You must be the owner of this object or an admin to perform this action.'
    
    def has_object_permission(self, request, view, obj):
        # Admin users have full access
        if request.user and request.user.is_staff:
            return True
        
        # Check if object has 'user' attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object has 'owner' attribute
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # Check if object has 'created_by' attribute
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        # If object is the user itself
        if obj == request.user:
            return True
        
        return False


class IsOwner(permissions.BasePermission):
    """
    Permission class to check if user is the owner of the object
    """
    message = 'You must be the owner of this object to perform this action.'
    
    def has_object_permission(self, request, view, obj):
        # Check if object has 'user' attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object has 'owner' attribute
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # Check if object has 'created_by' attribute
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        # If object is the user itself
        if obj == request.user:
            return True
        
        return False


class IsAdminUser(permissions.BasePermission):
    """
    Permission class to check if user is an admin
    """
    message = 'Only admin users can perform this action.'
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


class ReadOnly(permissions.BasePermission):
    """
    Permission class for read-only access
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
