from django.contrib import admin

# Register your models here.
from foo.models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    ...