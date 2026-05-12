import re

with open('Payment/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def create(self, request, *args, **kwargs):
        self.logger.debug(f"CREATE DONATION - Request data: {request.data}")
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            raise serializers.ValidationError("Could not create payment profile")

        # Determine donor type
        payment_group_id = self.request.data.get('payment_group')
        if payment_group_id:
            serializer.save()
        else:
            serializer.save(donor_profile=payment_profile)

    @action(detail=True, methods=['post'])
    def start_round(self, request, pk=None):
        round_obj = self.get_object()
        
        if round_obj.status != 'pending':
            return Response({'error': 'Round is already active or completed'}, status=400)
            
        # Automated game: randomly assign if method is random and no one is awarded
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
                pass
                
        round_obj.status = 'active'
        round_obj.start_date = timezone.now()
        round_obj.save()
        
        return Response({'status': 'Round started', 'awarded_to': str(round_obj.awarded_to.id) if round_obj.awarded_to else None})"""

replacement = """    def create(self, request, *args, **kwargs):
        self.logger.debug(f"CREATE DONATION - Request data: {request.data}")
        self.logger.debug(f"CREATE DONATION - Files: {request.FILES}")
        self.logger.debug(f"CREATE DONATION - User: {request.user}")
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Donation.objects.none()

        queryset = Donation.objects.filter(
            Q(donor_profile=payment_profile) |
            Q(payment_group__members__payment_profile=payment_profile)
        ).distinct()
        
        group_id = self.request.query_params.get('payment_group', None)
        if group_id:
            queryset = queryset.filter(payment_group_id=group_id)
            
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            raise serializers.ValidationError("Could not create payment profile")

        payment_group_id = self.request.data.get('payment_group')
        if payment_group_id:
            serializer.save()
        else:
            serializer.save(donor_profile=payment_profile)"""

if target in content:
    content = content.replace(target, replacement)
    with open('Payment/views.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('TARGET NOT FOUND')
