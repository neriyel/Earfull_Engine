from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    timezone = models.CharField(max_length=64, default='America/Vancouver')
    onboarding_complete = models.BooleanField(default=False)
    data_collection_enabled = models.BooleanField(default=True)
    week_starts_on = models.SmallIntegerField(default=0) # User preference on how their calendar week is structured