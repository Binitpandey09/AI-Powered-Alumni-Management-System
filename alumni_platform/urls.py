from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
urlpatterns = [
    path('', include('apps.accounts.page_urls')),
    path('', include('apps.feed.page_urls')),
    path('sessions/', include('apps.sessions_app.page_urls')),
    path('referrals/', include('apps.referrals.page_urls')),
    path('payments/', include('apps.payments.page_urls')),
    path('tools/', include('apps.ai_tools.page_urls')),
    path('admin/', admin.site.urls),
    
    # JWT Authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # App URLs
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/feed/', include('apps.feed.urls')),
    path('api/sessions/', include('apps.sessions_app.urls')),
    path('api/referrals/', include('apps.referrals.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/ai/', include('apps.ai_tools.urls')),
    path('api/ratings/', include('apps.ratings.urls')),
    path('notifications/', include('apps.notifications.page_urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    # Dashboard page routes
    path('dashboard/', include('apps.dashboard.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    # Admin panel
    path('admin-panel/', include('apps.dashboard.admin_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# Admin site customization
admin.site.site_header = 'AlumniConnect Administration'
admin.site.site_title = 'AlumniConnect Admin'
admin.site.index_title = 'Welcome to AlumniConnect Admin Portal'
