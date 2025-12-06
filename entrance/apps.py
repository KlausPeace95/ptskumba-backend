from django.apps import AppConfig


class EntranceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entrance'
    verbose_name = 'Seminary Entrance Examination'

    # def ready(self):
    #     import entrance.signals  # noqa