import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from utils.permissions import IsStudent

logger = logging.getLogger(__name__)


class GenerateSummaryView(APIView):
    """POST /api/ai/generate-summary/ — generate a profile summary using OpenAI."""
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request):
        user = request.user
        api_key = getattr(settings, 'OPENAI_API_KEY', '')
        if not api_key:
            return Response(
                {'error': 'AI service not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Build a compact profile snapshot for the prompt
        try:
            p = user.student_profile
        except Exception:
            return Response({'error': 'Student profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        profile_data = {
            'name': user.full_name,
            'degree': p.degree,
            'branch': p.branch,
            'graduation_year': p.graduation_year,
            'college': user.college,
            'skills': p.skills or [],
            'looking_for': p.looking_for,
            'projects': list(user.projects.values('title', 'description', 'tech_stack')),
            'internships': list(user.internships.values('company_name', 'role', 'description')),
            'certifications': list(user.certifications.values('title', 'issuing_organization')),
        }

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are an expert career counselor. '
                            'Write a professional profile summary in 3-4 sentences. '
                            'Make it compelling and suitable for job applications on LinkedIn or Naukri. '
                            'Write in first person. Return only the summary text, no labels or quotes.'
                        ),
                    },
                    {
                        'role': 'user',
                        'content': f'Student profile data: {json.dumps(profile_data)}',
                    },
                ],
                temperature=0.7,
                max_tokens=300,
            )
            summary = response.choices[0].message.content.strip()
            return Response({'summary': summary})
        except Exception as exc:
            logger.warning('AI summary generation failed: %s', exc)
            return Response(
                {'error': 'AI generation failed. Please try again.'},
 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
