from django.urls import path
from .views import AlumniDashboardView, StudentDashboardView, FacultyDashboardView

urlpatterns = [
    path('alumni/', AlumniDashboardView.as_view(), name='alumni_dashboard'),
    path('student/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('faculty/', FacultyDashboardView.as_view(), name='faculty_dashboard'),
]
