from django.contrib.auth.models import User, Group
from rest_framework import serializers
from drfexts.filtersets.backends import AutoFilterBackend

from foo.models import Client


class UserSerializer(serializers.ModelSerializer):
    # groups = serializers.ManyRelatedField(child_relation=G)

    class Meta:
        model = User
        fields = ['id', 'url', 'username', 'is_active', 'date_joined', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"


