from django.contrib import admin
from .models import SessionRating, ReferralRating, UserRatingAggregate

@admin.register(SessionRating)
class SessionRatingAdmin(admin.ModelAdmin):
    list_display = ['rater_email','ratee_email','rating_type','overall_rating','created_at']
    list_filter = ['rating_type','overall_rating']
    search_fields = ['rater__email','ratee__email']
    def rater_email(self, obj): return obj.rater.email
    def ratee_email(self, obj): return obj.ratee.email

@admin.register(ReferralRating)
class ReferralRatingAdmin(admin.ModelAdmin):
    list_display = ['rater_email','ratee_email','overall_rating','created_at']
    def rater_email(self, obj): return obj.rater.email
    def ratee_email(self, obj): return obj.ratee.email

@admin.register(UserRatingAggregate)
class UserRatingAggregateAdmin(admin.ModelAdmin):
    list_display = ['user_email','host_average_overall','host_total_ratings','updated_at']
    def user_email(self, obj): return obj.user.email
