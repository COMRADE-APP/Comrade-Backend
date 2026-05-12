
import os

with open('Payment/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add RoundPositionViewSet
round_pos_viewset = """
class RoundPositionViewSet(ModelViewSet):
    queryset = RoundPosition.objects.all()
    serializer_class = RoundPositionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return RoundPosition.objects.none()
        return RoundPosition.objects.filter(payment_group__members__payment_profile=payment_profile).distinct()

    def perform_create(self, serializer):
        payment_group = serializer.validated_data['payment_group']
        member = serializer.validated_data['member']
        pos = serializer.validated_data['position_number']
        
        # Check if position is already taken
        if RoundPosition.objects.filter(payment_group=payment_group, position_number=pos).exists():
            raise serializers.ValidationError("This position is already taken.")
            
        # Check if member already has a position
        if RoundPosition.objects.filter(payment_group=payment_group, member=member).exists():
            raise serializers.ValidationError("You already have a position in this group.")
            
        serializer.save()

class RoundContributionViewSet(ModelViewSet):"""

if 'class RoundContributionViewSet(ModelViewSet):' in content:
    content = content.replace('class RoundContributionViewSet(ModelViewSet):', round_pos_viewset)

# 2. Update RoundContributionViewSet create and actions
create_override = """    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        group = serializer.validated_data['payment_group']
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            raise serializers.ValidationError("Not a member of this group.")
            
        round_obj = serializer.save(status='pending')
        round_obj.approvals.add(member)

    @action(detail=True, methods=['post'])
    def approve_round(self, request, pk=None):
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=403)
            
        round_obj.approvals.add(member)
        round_obj.rejections.remove(member)
        
        # Check threshold
        threshold = round_obj.payment_group.approval_threshold
        member_count = round_obj.payment_group.members.count()
        if (round_obj.approvals.count() / member_count) * 100 >= threshold:
            round_obj.status = 'active'
            round_obj.start_date = timezone.now()
            
        round_obj.save()
        return Response({'status': 'Round approved', 'current_status': round_obj.status})

    @action(detail=True, methods=['post'])
    def reject_round(self, request, pk=None):
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=403)
            
        round_obj.rejections.add(member)
        round_obj.approvals.remove(member)
        
        notes = request.data.get('note', '')
        if notes:
            round_obj.approval_notes[str(member.id)] = notes
            
        round_obj.save()
        return Response({'status': 'Round rejected'})
"""

# Insert create override after permission_classes
if 'permission_classes = [IsAuthenticated]' in content:
    # Need to be careful to target the right one (RoundContributionViewSet)
    # We'll search for RoundContributionViewSet's permission_classes
    target = "class RoundContributionViewSet(ModelViewSet):\n    queryset = RoundContribution.objects.all()\n    serializer_class = RoundContributionSerializer\n    permission_classes = [IsAuthenticated]\n    "
    if target in content:
        content = content.replace(target, target + create_override + "\n")

# 3. Update start_round logic
start_round_orig = """        # Automated game: randomly assign if method is random and no one is awarded
        if round_obj.assignment_method == 'random' and not round_obj.awarded_to:
            import random
            group_members = list(round_obj.payment_group.members.all())
            # Find members who haven't been awarded in previous rounds
            awarded_member_ids = RoundContribution.objects.filter(payment_group=round_obj.payment_group, awarded_to__isnull=False).values_list('awarded_to_id', flat=True)
            eligible_members = [m for m in group_members if m.id not in awarded_member_ids]
            
            if eligible_members:
                round_obj.awarded_to = random.choice(eligible_members)
            elif group_members:
                # Cycle resets, everyone is eligible again
                round_obj.awarded_to = random.choice(group_members)"""

start_round_new = """        # Automated game: randomly assign if method is random and no one is awarded
        if round_obj.assignment_method == 'random' and not round_obj.awarded_to:
            import random
            group_members = list(round_obj.payment_group.members.all())
            # Find members who haven't been awarded in previous rounds
            awarded_member_ids = RoundContribution.objects.filter(payment_group=round_obj.payment_group, awarded_to__isnull=False).values_list('awarded_to_id', flat=True)
            eligible_members = [m for m in group_members if m.id not in awarded_member_ids]
            
            if eligible_members:
                round_obj.awarded_to = random.choice(eligible_members)
            elif group_members:
                # Cycle resets, everyone is eligible again
                round_obj.awarded_to = random.choice(group_members)
        
        elif round_obj.assignment_method == 'sequential' and not round_obj.awarded_to:
            # Picking position system
            try:
                pos = RoundPosition.objects.get(payment_group=round_obj.payment_group, position_number=round_obj.round_number)
                round_obj.awarded_to = pos.member
            except RoundPosition.DoesNotExist:
                # Fallback or error
                pass"""

if start_round_orig in content:
    content = content.replace(start_round_orig, start_round_new)

with open('Payment/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
