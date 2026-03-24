from django.apps import AppConfig


class FeedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.feed'

    def ready(self):
        import apps.feed.signals  # noqa: F401 — connect signal handlers
