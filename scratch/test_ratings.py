import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alumni_platform.settings.dev')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
User = get_user_model()

student = User.objects.get(email='dev.student@college.ac.in')
alumni = User.objects.get(email='dev.alumni@techcompany.com')

# Get a completed booking if it exists
from apps.sessions_app.models import Booking
booking = Booking.objects.filter(student=student, status='completed').first()
if not booking:
    # Mark an existing booking as completed for testing
    booking = Booking.objects.filter(student=student).first()
    if booking:
        booking.status = 'completed'
        booking.session.scheduled_at = timezone.now()
        booking.session.save()
        booking.save()
        print("Booking marked completed:", booking.id)
else:
    booking.session.scheduled_at = timezone.now()
    booking.session.save()
    booking.save()

if booking:
    client = APIClient()
    refresh = RefreshToken.for_user(student)
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

    # Submit rating
    r = client.post('/api/ratings/session/', {
        'booking_id': booking.id,
        'overall_rating': 5,
        'communication_rating': 5,
        'value_rating': 4,
        'professionalism_rating': 5,
        'would_recommend': True,
        'review_text': 'Excellent session! Very clear explanation and great examples.',
    }, format='json', HTTP_HOST='localhost')
    print("Rating submit status:", r.status_code)
    try:
        print("Response:", r.json())
    except:
        print("Response:", r.content)

    # Check aggregate
    from apps.ratings.models import UserRatingAggregate
    agg = UserRatingAggregate.objects.filter(user=alumni).first()
    if agg:
        print("Alumni average rating:", agg.host_average_overall)
        print("Total ratings:", agg.host_total_ratings)

    # Get user ratings
    r2 = client.get(f'/api/ratings/user/{alumni.id}/', HTTP_HOST='localhost')
    print("User ratings status:", r2.status_code)
    print("Average:", r2.json().get('summary', {}).get('average_overall'))

    # Check pending ratings
    r3 = client.get('/api/ratings/pending/', HTTP_HOST='localhost')
    print("Pending ratings:", r3.json())
