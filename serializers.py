from rest_framework import serializers
from models import TaskTable

class TimeTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTable
        fields = '__all__'
