from django.urls import path
from .views import (
    AIToolsHubPageView,
    ResumeCheckPageView,
    AIInterviewPageView,
    ResumeBuilderPageView,
    SkillGapPageView,
)

# Mounted at /tools/
urlpatterns = [
    path('', AIToolsHubPageView.as_view(), name='ai_tools_hub'),
    path('resume-check/', ResumeCheckPageView.as_view(), name='resume_check'),
    path('ai-interview/', AIInterviewPageView.as_view(), name='ai_interview'),
    path('resume-builder/', ResumeBuilderPageView.as_view(), name='resume_builder'),
    path('skill-gap/', SkillGapPageView.as_view(), name='skill_gap'),
]
