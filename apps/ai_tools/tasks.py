"""
apps/ai_tools/tasks.py
Async Celery tasks for AI tool processing.
Used when AI calls take too long for a synchronous request.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def process_resume_score_async(usage_id, job_role=None):
    """
    Processes resume scoring asynchronously.
    Triggered when resume scoring is offloaded from the request cycle.
    Saves result to AIToolUsage.result_data and sends a notification.
    """
    try:
        from apps.payments.models import AIToolUsage
        usage = AIToolUsage.objects.get(id=usage_id)
        user  = usage.user

        # Skip if already processed
        if usage.result_data:
            logger.info('Resume score already cached for usage_id=%s', usage_id)
            return

        from apps.ai_tools.views import get_student_profile_data
        profile_data = get_student_profile_data(user)

        # Extract resume text from PDF
        resume_text = ''
        try:
            sp = user.student_profile
            if sp.resume_file:
                import PyPDF2
                import io
                sp.resume_file.seek(0)
                reader = PyPDF2.PdfReader(io.BytesIO(sp.resume_file.read()))
                for page in reader.pages:
                    resume_text += page.extract_text() or ''
        except Exception as e:
            logger.warning('PDF extraction failed in async task for user %s: %s', user.id, e)

        if not resume_text.strip():
            resume_text = (
                f"Skills: {', '.join(profile_data.get('skills', []))}\n"
                f"Education: {profile_data.get('education_summary', '')}\n"
                f"Projects: {profile_data.get('projects_summary', '')}"
            )

        from utils.ai_tools_service import score_resume
        ai_result = score_resume(resume_text, profile_data, job_role)

        if ai_result['success']:
            usage.result_data = ai_result['data']
            usage.save(update_fields=['result_data'])
            logger.info(
                'Resume scored async for usage_id=%s score=%s',
                usage_id,
                ai_result['data'].get('overall_score'),
            )

            # Notify student
            try:
                from apps.notifications.models import Notification
                score = ai_result['data'].get('overall_score', 0)
                grade = ai_result['data'].get('grade', '')
                Notification.objects.create(
                    recipient=user,
                    title='Your resume score is ready!',
                    message=f'Your resume scored {score}/100. Grade: {grade}',
                    link='/tools/resume-check/',
                )
            except Exception as notify_err:
                logger.warning('Notification failed for usage_id=%s: %s', usage_id, notify_err)
        else:
            logger.error(
                'Resume scoring failed async for usage_id=%s: %s',
                usage_id,
                ai_result['error'],
            )

    except Exception as e:
        logger.error('process_resume_score_async failed for usage_id=%s: %s', usage_id, e)
