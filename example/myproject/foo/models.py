from django.db import models
from django.contrib.auth.models import User, Group
# Create your models here.


class Client(models.Model):

    user = models.ForeignKey(User, to_field="username", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=16, null=True)
