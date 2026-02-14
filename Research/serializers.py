from rest_framework import serializers
from .models import (
    ResearchProject, ParticipantRequirements, ParticipantPosition,
    ResearchParticipant, ParticipantMatching, ResearchGuidelines,
    PeerReview, ResearchPublication, ResearchMilestone
)
from Authentication.models import CustomUser

class UserMiniSerializer(serializers.ModelSerializer):
    """Minimal user info for displays"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'avatar_url', 'user_type']
    
    def get_full_name(self, obj):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or obj.email
    
    def get_avatar_url(self, obj):
        try:
            profile = getattr(obj, 'user_profile', None) or getattr(obj, 'profile', None)
            if profile and profile.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.avatar.url)
                return profile.avatar.url
        except:
            pass
        return None

class ParticipantRequirementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParticipantRequirements
        fields = '__all__'

class ParticipantPositionSerializer(serializers.ModelSerializer):
    requirements = ParticipantRequirementsSerializer(read_only=True)
    is_full = serializers.ReadOnlyField()
    
    class Meta:
        model = ParticipantPosition
        fields = '__all__'

class ResearchParticipantSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    position = ParticipantPositionSerializer(read_only=True)
    
    class Meta:
        model = ResearchParticipant
        fields = '__all__'

class ResearchMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchMilestone
        fields = '__all__'

class ResearchGuidelinesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchGuidelines
        fields = '__all__'

class PeerReviewSerializer(serializers.ModelSerializer):
    reviewer = UserMiniSerializer(read_only=True)
    
    class Meta:
        model = PeerReview
        fields = '__all__'

class ResearchPublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchPublication
        fields = '__all__'

class ResearchProjectSerializer(serializers.ModelSerializer):
    principal_investigator = UserMiniSerializer(read_only=True)
    co_investigators = UserMiniSerializer(many=True, read_only=True)
    milestones = ResearchMilestoneSerializer(many=True, read_only=True)
    positions = ParticipantPositionSerializer(many=True, read_only=True)
    publication = ResearchPublicationSerializer(read_only=True)
    requirements = ParticipantRequirementsSerializer(many=True, read_only=True)
    
    class Meta:
        model = ResearchProject
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'views']

class ResearchProjectDetailSerializer(ResearchProjectSerializer):
    """Detailed serializer including guidelines and participants for authorized users"""
    guidelines = ResearchGuidelinesSerializer(read_only=True)
    # participants = ResearchParticipantSerializer(many=True, read_only=True) # Might be too heavy, keep separate endpoint
