from django.test import RequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()

try:
    student = User.objects.get(email='dev.student@college.ac.in')
    print("Student exists:", student.email)

    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(student)
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

    response = client.get('/api/dashboard/student-data/', HTTP_HOST='localhost')
    print("Student dashboard status:", response.status_code)
    if response.status_code == 200:
        import json
        data = response.json()
        print("Keys:", list(data.keys()))
        print("Profile score:", data['profile']['score'])
        print("Sessions booked:", data['sessions']['total_booked'])
        print("Referrals applied:", data['referrals']['total_applied'])
        print("AI tools used:", data['ai_tools']['total_uses'])
    else:
        print("ERROR:", response.content)
except Exception as e:
    print("Error:", e)
