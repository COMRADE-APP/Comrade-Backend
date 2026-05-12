import os

with open('Payment/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# WithdrawalRequestViewSet update
withdrawal_orig = """        withdrawal.status = 'approved'
        withdrawal.approved_by = admin_member
        withdrawal.approval_date = timezone.now()
        
        # In a real scenario, process the payout to withdrawal.destination_wallet here
        withdrawal.destination_wallet.comrade_balance += withdrawal.amount
        withdrawal.destination_wallet.save()"""
        
withdrawal_new = """        withdrawal.status = 'approved'
        withdrawal.approved_by = admin_member
        withdrawal.approval_date = timezone.now()
        
        # Process the payout to withdrawal.destination_wallet
        deduction = Decimal('0.00')
        if withdrawal.withdrawal_type == 'exit' and not withdrawal.payment_group.is_matured and getattr(withdrawal.payment_group, 'is_lifetime', False) == False:
            deduction = Decimal(str(withdrawal.calculate_immature_deduction()))
            withdrawal.immature_exit_deduction = deduction
            
        payout = withdrawal.amount - deduction
        withdrawal.destination_wallet.comrade_balance += payout
        withdrawal.destination_wallet.save()
        
        # Deduct from group amount
        withdrawal.payment_group.current_amount -= payout
        withdrawal.payment_group.save()"""
        
content = content.replace(withdrawal_orig, withdrawal_new)

# RoundContributionViewSet update
round_orig = """        # Check if round completed (all members contributed)
        if round_obj.contributions.count() >= round_obj.payment_group.members.count():
            round_obj.status = 'completed'
            round_obj.award_date = timezone.now()
            # Payout logic would go here if automated"""

round_new = """        # Check if round completed (all members contributed)
        if round_obj.contributions.count() >= round_obj.payment_group.members.count():
            round_obj.status = 'completed'
            round_obj.award_date = timezone.now()
            # Payout logic automatically
            if round_obj.awarded_to:
                awarded_profile = round_obj.awarded_to.payment_profile
                awarded_profile.comrade_balance += round_obj.total_collected
                awarded_profile.save()"""

content = content.replace(round_orig, round_new)

round_start_endpoint = """    @action(detail=True, methods=['post'])
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
                
        round_obj.status = 'active'
        round_obj.start_date = timezone.now()
        round_obj.save()
        
        return Response({'status': 'Round started', 'awarded_to': str(round_obj.awarded_to.id) if round_obj.awarded_to else None})

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def contribute(self"""

content = content.replace("    @action(detail=True, methods=['post'])\n    @db_transaction.atomic\n    def contribute(self", round_start_endpoint)

# GroupSettingsChangeRequestViewSet update
vote_orig = """        # For now, let's just increment and check status
        if vote_type == 'for':
            change_req.votes_for += 1
        else:
            change_req.votes_against += 1"""

vote_new = """        # For now, let's just increment and check status
        if vote_type == 'for':
            change_req.votes_for += 1
        else:
            change_req.votes_against += 1
            
        note = request.data.get('note', '')
        if note:
            # Store sentiments safely
            current_sentiments = change_req.voter_sentiments
            current_sentiments[str(member.id)] = {'vote': vote_type, 'note': note}
            change_req.voter_sentiments = current_sentiments"""

content = content.replace(vote_orig, vote_new)

with open('Payment/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
