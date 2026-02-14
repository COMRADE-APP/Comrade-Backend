from django.contrib.auth import authenticate
import re
from rest_framework import serializers
from Authentication.models import (
    Student, CustomUser, Lecturer, OrgStaff, StudentAdmin, 
    OrgAdmin, InstAdmin, InstStaff, Profile, Author, Editor, 
    Moderator, ComradeAdmin, RoleChangeRequest, UserProfile,
    AccountDeletionRequest, ArchivedUserData
)
from Opinions.models import Follow


class BaseUserSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'other_names', 'email', 'password', 'confirm_password', 'phone_number', 'user_type']
    
    def validate(self, data):
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password too short. Use 8 characters or more."})
        if (not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or 
            not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password)):
            raise serializers.ValidationError({"password": "Password must contain at least one uppercase, lowercase, numeric, and special character."})
        if not data.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'The password should be confirmed'})
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        
        if len(data['phone_number']) < 10:
            raise serializers.ValidationError({'phone_number': 'Phone number must be at least 10 digits.'})
        
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        if password is not None:
            user = CustomUser.objects.create_user(password=password, is_active=False, **validated_data)
        else:
            user = CustomUser.objects.create_user(is_active=False, **validated_data)
        
        # Create UserProfile for the new user
        UserProfile.objects.create(user=user)
        
        return user
    


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'other_names', 'phone_number', 'user_type', 'is_active']
        read_only_fields = ['id', 'is_active'] 


class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username_or_email = data['username_or_email']
        password = data['password']

        user = CustomUser.objects.filter(email=username_or_email).first()
        
        if not user:
            raise serializers.ValidationError({"error": "User not found."})
        
        # Check account status
        if user.account_status == 'deactivated':
            raise serializers.ValidationError({
                "error": "Account is deactivated.",
                "account_deactivated": True,
                "email": user.email
            })
        
        if user.account_status == 'pending_deletion':
            raise serializers.ValidationError({
                "error": "Account is pending deletion. Contact support to cancel.",
                "pending_deletion": True
            })
        
        authenticated = authenticate(username=user.email, password=password)

        if not authenticated:
            raise serializers.ValidationError({"error": "Invalid credentials."})

        self.user = authenticated
        return {
            'user_id': authenticated.id,
            'email': authenticated.email,
        }


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'

    def validate(self, data):
        if data.get('expecte_year_of_graduation') and data.get('year_of_admission'):
            if data['expecte_year_of_graduation'] < data['year_of_admission']:
                raise serializers.ValidationError({'expecte_year_of_graduation': 'Expected graduation year cannot be less than admission year'})
        return data


class LecturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecturer
        fields = '__all__'


class OrgStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgStaff
        fields = '__all__'


class StudentAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAdmin
        fields = '__all__'


class OrgAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAdmin
        fields = '__all__'


class InstAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstAdmin
        fields = '__all__'


class InstStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstStaff
        fields = '__all__'


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'


class EditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Editor
        fields = '__all__'


class ModeratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moderator
        fields = '__all__'


class ComradeAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComradeAdmin
        fields = '__all__'


class RoleChangeRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.CharField(source='reviewed_by.email', read_only=True)
    
    class Meta:
        model = RoleChangeRequest
        fields = [
            'id', 'user', 'user_email', 'user_name', 'current_role', 
            'requested_role', 'reason', 'supporting_documents',
            'status', 'review_notes', 'reviewed_by', 'reviewed_by_name',
            'created_on', 'reviewed_on'
        ]
        read_only_fields = ['id', 'user', 'created_on', 'reviewed_on', 'reviewed_by']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class UserProfileSerializer(serializers.ModelSerializer):
    """Full user profile with privacy-aware data"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    other_names = serializers.CharField(source='user.other_names', read_only=True)
    user_type = serializers.CharField(source='user.user_type', read_only=True)
    full_name = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    affiliations = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'user_id', 'email', 'phone_number', 'first_name', 'last_name', 
            'other_names', 'user_type', 'full_name', 'is_owner',
            'avatar', 'avatar_url', 'cover_image', 'cover_url',
            'bio', 'location', 'occupation', 'website', 'interests',
            'show_email', 'show_phone', 'allow_messages', 
            'show_activity_status', 'show_read_receipts',
            'is_following', 'followers_count', 'following_count',
            'created_at', 'updated_at', 'affiliations'
        ]
        read_only_fields = ['user_id', 'created_at', 'updated_at']
    
    def get_affiliations(self, obj):
        """Return user's institutional and organizational affiliations"""
        affiliations = {
            'institutions': [],
            'organisations': []
        }
        user = obj.user
        
        # Check for Student affiliation
        if hasattr(user, 'student'):
            # Student model stores institution name as string, need to handle this
            # ideally it should be ForeignKey but model shows CharField
            # "institution = models.CharField(max_length=2000)"
            # If so, we can't get ID easily unless we lookup Institution model by name
            # For now, let's use what we have.
            # Wait, InstStaff has ForeignKey.
            pass

        # Check for Lecturer
        if hasattr(user, 'lecturer') and user.lecturer.institution:
            inst = user.lecturer.institution
            affiliations['institutions'].append({
                'id': inst.id,
                'name': inst.name,
                'type': 'lecturer'
            })
            
        # Check for InstStaff
        if hasattr(user, 'inst_staff'):
            # InstStaff has institution and inst_branch
            staff = user.inst_staff
            if staff.institution:
                inst_data = {
                    'id': staff.institution.id,
                    'name': staff.institution.name,
                    'type': 'staff',
                    'role': staff.staff_role,
                    'branches': []
                }
                if staff.inst_branch:
                    inst_data['branches'].append({
                        'id': staff.inst_branch.id,
                        'name': staff.inst_branch.name
                    })
                affiliations['institutions'].append(inst_data)

        # Check for OrgStaff
        if hasattr(user, 'org_staff'):
            staff = user.org_staff
            if staff.current_organisation:
                org_data = {
                    'id': staff.current_organisation.id,
                    'name': staff.current_organisation.name,
                    'type': 'staff',
                    'role': staff.staff_role,
                    'branches': []
                }
                if staff.current_org_branch:
                    org_data['branches'].append({
                        'id': staff.current_org_branch.id,
                        'name': staff.current_org_branch.name
                    })
                affiliations['organisations'].append(org_data)
        
        return affiliations
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.id == obj.user.id
        return False
    
    def get_email(self, obj):
        """Return email based on privacy settings"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None if obj.show_email != 'public' else obj.user.email
        
        if request.user.id == obj.user.id:
            return obj.user.email
        
        if obj.show_email == 'public':
            return obj.user.email
        elif obj.show_email == 'followers':
            if Follow.objects.filter(follower=request.user, following=obj.user).exists():
                return obj.user.email
        return None
    
    def get_phone_number(self, obj):
        """Return phone based on privacy settings"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None if obj.show_phone != 'public' else obj.user.phone_number
        
        if request.user.id == obj.user.id:
            return obj.user.phone_number
        
        if obj.show_phone == 'public':
            return obj.user.phone_number
        elif obj.show_phone == 'followers':
            if Follow.objects.filter(follower=request.user, following=obj.user).exists():
                return obj.user.phone_number
        return None
    
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.id != obj.user.id:
            return Follow.objects.filter(follower=request.user, following=obj.user).exists()
        return False
    
    def get_followers_count(self, obj):
        return obj.user.followers.count()
    
    def get_following_count(self, obj):
        return obj.user.following.count()
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def get_cover_url(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating profile data"""
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    other_names = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'first_name', 'last_name', 'other_names',
            'bio', 'location', 'occupation', 'website', 'interests',
            'show_email', 'show_phone', 'allow_messages',
            'show_activity_status', 'show_read_receipts'
        ]
    
    def update(self, instance, validated_data):
        # Update user fields if provided
        user = instance.user
        if 'first_name' in validated_data:
            user.first_name = validated_data.pop('first_name')
        if 'last_name' in validated_data:
            user.last_name = validated_data.pop('last_name')
        if 'other_names' in validated_data:
            user.other_names = validated_data.pop('other_names')
        user.save()
        
        # Update profile fields
        return super().update(instance, validated_data)


class AccountDeletionRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='email', read_only=True)
    user_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    days_until_deletion = serializers.SerializerMethodField()
    
    class Meta:
        model = AccountDeletionRequest
        fields = [
            'id', 'user', 'email', 'user_email', 'user_name', 'user_type',
            'reason', 'status', 'review_notes', 'reviewed_by', 'reviewed_by_name',
            'requested_at', 'reviewed_at', 'scheduled_deletion_date', 'days_until_deletion'
        ]
        read_only_fields = ['id', 'user', 'email', 'requested_at', 'reviewed_at', 'reviewed_by']
    
    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return "Deleted User"
    
    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.email
        return None
    
    def get_days_until_deletion(self, obj):
        if obj.scheduled_deletion_date:
            from datetime import date
            delta = obj.scheduled_deletion_date - date.today()
            return max(0, delta.days)
        return None


class ArchivedUserDataSerializer(serializers.ModelSerializer):
    archived_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ArchivedUserData
        fields = [
            'id', 'original_user_id', 'email', 'first_name', 'last_name',
            'user_type', 'user_data', 'activity_summary', 'deletion_reason',
            'archived_at', 'archived_by', 'archived_by_name'
        ]
        read_only_fields = ['id', 'archived_at']
    
    def get_archived_by_name(self, obj):
        if obj.archived_by:
            return obj.archived_by.email
        return None

