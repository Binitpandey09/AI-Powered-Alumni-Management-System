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


class CanCreatePost(permissions.BasePermission):
    """Only alumni and faculty can create posts. Students cannot."""
    message = 'Only alumni and faculty can create posts.'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['alumni', 'faculty']
        )


class IsPostAuthorOrAdmin(permissions.BasePermission):
    """Only the post author or admin can edit/delete."""
    message = 'Only the post author or an admin can perform this action.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user or request.user.role == 'admin'


class CanHostSession(permissions.BasePermission):
    """Only alumni and faculty can create/manage sessions."""
    message = 'Only alumni and faculty can host sessions.'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['alumni', 'faculty']
        )


class IsSessionHostOrAdmin(permissions.BasePermission):
    """Only session host or admin can edit/cancel session."""
    message = 'Only the session host or an admin can perform this action.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.host == request.user or request.user.role == 'admin'


class IsBookingOwner(permissions.BasePermission):
    """Only the student who made the booking can view/cancel it."""
    message = 'Only the booking owner or an admin can perform this action.'

    def has_object_permission(self, request, view, obj):
        return obj.student == request.user or request.user.role == 'admin'


class CanPostReferral(permissions.BasePermission):
    """Only alumni and faculty can create referrals. All authenticated users can read."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role in ['alumni', 'faculty']


class IsReferralAuthorOrAdmin(permissions.BasePermission):
    """Only referral author or admin can edit/deactivate."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.posted_by == request.user or request.user.role == 'admin'


class IsApplicationOwnerOrReferralAuthor(permissions.BasePermission):
    """Student who applied OR referral author can view/update application."""

    def has_object_permission(self, request, view, obj):
        return (
            obj.student == request.user
            or obj.referral.posted_by == request.user
            or request.user.role == 'admin'
        )
