from rest_framework import serializers
from Resources.models import Resource, ResourceVisibility, VisibilityLog, Link, MainVisibilityLog, Visibility




class ResourceSerializer(serializers.ModelSerializer):
    # Read-only nested fields for display
    linked_opinion_details = serializers.SerializerMethodField()
    linked_article_details = serializers.SerializerMethodField()
    linked_research_details = serializers.SerializerMethodField()

    class Meta:
        fields = '__all__'
        model = Resource

    def get_linked_opinion_details(self, obj):
        from Opinions.serializers import OpinionSerializer
        if obj.linked_opinion:
            return OpinionSerializer(obj.linked_opinion).data
        return None

    def get_linked_article_details(self, obj):
        from Articles.serializers import ArticleSerializer
        if obj.linked_article:
            return ArticleSerializer(obj.linked_article).data
        return None

    def get_linked_research_details(self, obj):
        from Research.serializers import ResearchProjectSerializer
        if obj.linked_research:
            return ResearchProjectSerializer(obj.linked_research).data
        return None

class ResourceVisibilitySerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ResourceVisibility


class VisibilityLogSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = VisibilityLog

class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Link

class VisibilitySerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Visibility


class MainVisibilityLogSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = MainVisibilityLog

