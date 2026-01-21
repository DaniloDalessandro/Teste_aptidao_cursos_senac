from rest_framework import serializers
from .models import Job, Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'title']


class JobSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    requirements_list = serializers.SerializerMethodField()
    responsibilities_list = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'description',
            'requirements',
            'responsibilities',
            'level',
            'level_display',
            'skills',
            'requirements_list',
            'responsibilities_list',
        ]

    def get_requirements_list(self, obj):
        return obj.requirements_list()

    def get_responsibilities_list(self, obj):
        return obj.responsibilities_list()


class JobListSerializer(serializers.ModelSerializer):
    """Serializer leve para listagem de jobs."""
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    skills_count = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'level',
            'level_display',
            'skills_count',
        ]

    def get_skills_count(self, obj):
        return obj.skills.count()
