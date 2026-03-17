from django.urls import path
from .views import GenerateSummaryView

app_name = 'ai_tools'

urlpatterns = [
    path('generate-summary/', GenerateSummaryView.as_view(), name='generate-summary'),
]
