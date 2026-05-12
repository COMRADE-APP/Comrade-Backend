
import os

file_path = r'C:\Users\Imani\Documents\Comrade\Comrade-Backend\Payment\serializers.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix duplicates and crashes in RoundContributionSerializer
old_def = """class RoundContributionSerializer(serializers.ModelSerializer):
    awarded_to_name = serializers.CharField(source='awarded_to.payment_profile.user.user.get_full_name', read_only=True)
    progress_percentage = serializers.FloatField(source='get_progress_percentage', read_only=True)
    member_contributions = RoundMemberContributionSerializer(many=True, read_only=True)
    round_number = serializers.IntegerField(read_only=True)  # Auto-generated in perform_create
    round_name = serializers.CharField(required=False, allow_blank=True)
    approvals = RoundApprovalMemberSerializer(many=True, read_only=True)
    rejections = RoundApprovalMemberSerializer(many=True, read_only=True)
    user_has_approved = serializers.SerializerMethodField()
    user_has_rejected = serializers.SerializerMethodField()
    user_position = serializers.SerializerMethodField()
    
    # New computed fields
    members_rotation = serializers.SerializerMethodField()
    cycle_contributions = serializers.SerializerMethodField()
    cycles_completed = serializers.IntegerField(source='total_cycles_completed', read_only=True)
    awarded_to_name = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()"""

new_def = """class RoundContributionSerializer(serializers.ModelSerializer):
    member_contributions = RoundMemberContributionSerializer(many=True, read_only=True)
    round_number = serializers.IntegerField(read_only=True)
    round_name = serializers.CharField(required=False, allow_blank=True)
    approvals = RoundApprovalMemberSerializer(many=True, read_only=True)
    rejections = RoundApprovalMemberSerializer(many=True, read_only=True)
    user_has_approved = serializers.SerializerMethodField()
    user_has_rejected = serializers.SerializerMethodField()
    user_position = serializers.SerializerMethodField()
    members_rotation = serializers.SerializerMethodField()
    cycle_contributions = serializers.SerializerMethodField()
    cycles_completed = serializers.IntegerField(source='total_cycles_completed', read_only=True)
    awarded_to_name = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()"""

content = content.replace(old_def, new_def)

# Fix duplicate get_cycle_contributions
old_method = """    def get_cycle_contributions(self, obj):
        \"\"\"Returns contributions for the current cycle.\"\"\"
        from Payment.models import RoundMemberContribution
        contributions = RoundMemberContribution.objects.filter(round=obj, cycle_number=obj.current_cycle)
        return RoundMemberContributionSerializer(contributions, many=True).data

    def get_cycle_contributions(self, obj):
        \"\"\"Returns contributions specifically for the current cycle.\"\"\"
        contributions = obj.member_contributions.filter(cycle_number=obj.current_cycle)
        return RoundMemberContributionSerializer(contributions, many=True, context=self.context).data"""

new_method = """    def get_cycle_contributions(self, obj):
        \"\"\"Returns contributions specifically for the current cycle.\"\"\"
        contributions = obj.member_contributions.filter(cycle_number=obj.current_cycle)
        return RoundMemberContributionSerializer(contributions, many=True, context=self.context).data"""

content = content.replace(old_method, new_method)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("RoundContributionSerializer cleaned and fixed!")
