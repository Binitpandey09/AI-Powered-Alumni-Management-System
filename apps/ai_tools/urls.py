from django.urls import path
from .views import (
    GenerateSummaryView,
    ResumeScoreView,
    ResumeBuildView,
    AIInterviewView,
    SkillGapView,
)

app_name = 'ai_tools'

urlpatterns = [
    # Existing
    path('generate-summary/', GenerateSummaryView.as_view(), name='generate-summary'),
    # New AI tools
    path('resume-score/',     ResumeScoreView.as_view(),    name='resume-score'),
    path('resume-build/',     ResumeBuildView.as_view(),    name='resume-build'),
    path('interview/',        AIInterviewView.as_view(),    name='interview'),
    path('skill-gap/',        SkillGapView.as_view(),       name='skill-gap'),
]
