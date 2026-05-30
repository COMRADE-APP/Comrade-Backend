import re
import sys

def main():
    file_path = r'c:\Users\Imani\Documents\Comrade\Comrade-Backend\Payment\views.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Extract the body of `withdraw` to `_execute_withdraw`
    # Replace `@action(detail=True, methods=['post'])\n    @db_transaction.atomic\n    def withdraw(self, request, pk=None):`
    # We will rename the original `withdraw` function to `_execute_withdraw_internal` taking (target, amount, payment_profile, request)
    # Then we redefine `withdraw`.
    
    # Let's find the `withdraw` method start.
    match = re.search(r'(@action\(detail=True, methods=\[\'post\'\]\)\s+@db_transaction\.atomic\s+def withdraw\(self, request, pk=None\):)', content)
    if not match:
        print("Could not find withdraw method")
        return
        
    start_idx = match.start()
    end_idx = content.find('def lock(self, request, pk=None):', start_idx)
    
    withdraw_code = content[start_idx:end_idx]
    
    new_withdraw_code = """    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def withdraw(self, request, pk=None):
        \"\"\"Withdraw from a piggy bank — enforces savings_type rules.\"\"\"
        target = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
            
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if target.payment_group:
            # Group Piggy Bank -> requires approval
            from Payment.models import PiggyBankActionRequest, PaymentGroupMember
            # check if member
            if not PaymentGroupMember.objects.filter(payment_group=target.payment_group, payment_profile=payment_profile).exists():
                return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
            
            req = PiggyBankActionRequest.objects.create(
                piggy_bank=target,
                requested_by=payment_profile,
                action_type='withdraw',
                amount=amount,
                reason=request.data.get('reason', '')
            )
            return Response({'status': 'Withdrawal request created, pending group approval', 'request_id': str(req.id)})
        else:
            # Individual Piggy Bank -> execute immediately
            return self._execute_withdraw_internal(target, amount, payment_profile, request)

    def _execute_withdraw_internal(self, target, amount, payment_profile, request):
        from decimal import Decimal
        from Payment.models import TransactionToken, TransactionHistory, PaymentAuthorization, PaymentVerification, PaymentGroupMember
        import uuid
        import secrets
        from django.utils import timezone
        
        # ── Savings-type enforcement ──
        can_wd, wd_message = target.can_withdraw()
        if not can_wd:
            return Response({'error': wd_message}, status=status.HTTP_403_FORBIDDEN)
        
        # Legacy locking_status checks (on top of savings_type)
        if target.locking_status == 'locked':
            return Response({'error': 'This piggy bank is locked'}, status=status.HTTP_403_FORBIDDEN)
        
        if target.locking_status == 'locked_time':
            if target.maturity_date and target.maturity_date > timezone.now():
                return Response({
                    'error': f'Piggy bank is locked until {target.maturity_date.strftime("%Y-%m-%d")}'
                }, status=status.HTTP_403_FORBIDDEN)
        
        if target.locking_status == 'locked_goal':
            if target.current_amount < target.target_amount:
                return Response({'error': 'Piggy bank is locked until goal is reached'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check available amount
        if target.current_amount < amount:
            return Response({'error': 'Insufficient funds in piggy bank'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check min/max withdrawal amount constraints
        if target.min_withdrawal_amount and amount < float(target.min_withdrawal_amount):
            return Response({'error': f'Minimum withdrawal amount is ${float(target.min_withdrawal_amount):.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        if target.max_withdrawal_amount and amount > float(target.max_withdrawal_amount):
            return Response({'error': f'Maximum withdrawal amount is ${float(target.max_withdrawal_amount):.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check minimum balance constraint
        if target.require_min_balance:
            remaining = float(target.current_amount) - amount
            if remaining < float(target.require_min_balance):
                return Response({'error': f'Must maintain minimum balance of ${float(target.require_min_balance):.2f}. Current remaining would be ${remaining:.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check minimum savings period (days since creation)
        if target.require_min_savings_period_days:
            days_since_creation = (timezone.now() - target.created_at).days
            if days_since_creation < target.require_min_savings_period_days:
                return Response({'error': f'Must save for at least {target.require_min_savings_period_days} days before withdrawing. You have saved for {days_since_creation} days.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check minimum contribution amount
        if target.require_min_contribution_amount:
            member_total = 0
            if target.payment_group:
                try:
                    member = PaymentGroupMember.objects.get(payment_group=target.payment_group, payment_profile=payment_profile)
                    member_total = float(member.total_contributed)
                except:
                    pass
            else:
                member_total = sum(float(c.amount) for c in target.contributions.filter(payment_profile=payment_profile))
            
            if member_total < float(target.require_min_contribution_amount):
                return Response({'error': f'Must have contributed at least ${float(target.require_min_contribution_amount):.2f}. You have contributed ${member_total:.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check max withdrawals per day
        if target.max_withdrawals_per_day > 0 and target.last_withdrawal_date:
            from datetime import timedelta
            if target.last_withdrawal_date.date() == timezone.now().date():
                time_since_last = timezone.now() - target.last_withdrawal_date
                if time_since_last < timedelta(hours=24):
                    pass
        
        # Check member age requirement
        if target.require_min_member_age_days and target.payment_group:
            try:
                member = PaymentGroupMember.objects.get(payment_group=target.payment_group, payment_profile=payment_profile)
                days_since_joined = (timezone.now() - member.joined_at).days
                if days_since_joined < target.require_min_member_age_days:
                    return Response({'error': f'Must be a member for at least {target.require_min_member_age_days} days before withdrawing. You have been a member for {days_since_joined} days.'}, status=status.HTTP_400_BAD_REQUEST)
            except PaymentGroupMember.DoesNotExist:
                pass
        
        # ── Fixed-deposit penalty calculation ──
        penalty = target.calculate_withdrawal_penalty(amount)
        net_amount = amount - penalty
        forfeited_interest = 0
        
        if target.savings_type == 'fixed_deposit' and not target.is_matured:
            # Forfeit all accrued interest
            forfeited_interest = float(target.accrued_interest)
            target.accrued_interest = 0
        
        # Deduct from piggy bank
        target.current_amount -= Decimal(str(amount))
        target.save()
        
        # Add net amount to user balance (after penalty)
        payment_profile.comrade_balance += Decimal(str(net_amount))
        payment_profile.save()
        
        # Create detailed audit trail for withdrawal
        description = f'Withdrawal from Piggy Bank "{target.name}"'
        if target.payment_group:
            description += f' (Group: {target.payment_group.name})'
        description += f'. Original amount: ${float(amount):.2f}'
        if penalty > 0:
            description += f', Penalty applied: ${penalty:.2f}'
            if forfeited_interest > 0:
                description += f', Forfeited interest: ${forfeited_interest:.2f}'
        description += f', Net transferred to wallet: ${net_amount:.2f}'
        
        t1 = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=Decimal(str(net_amount)),
            transaction_type='piggy_bank_withdrawal',
            description=description,
            payment_group=target.payment_group,
            piggy_bank=target
        )
        
        TransactionHistory.objects.create(
            payment_profile=payment_profile,
            transaction_token=t1,
            authorization_token=PaymentAuthorization.objects.create(
                payment_profile=payment_profile,
                authorization_code=secrets.token_hex(16)
            ),
            verification_token=PaymentVerification.objects.create(
                payment_profile=payment_profile,
                verification_code=secrets.token_hex(16)
            ),
            amount=Decimal(str(net_amount)),
            status='completed'
        )
        
        # Also record the deduction from piggy bank as savings withdrawal
        withdrawal_type = 'savings_withdrawal' if penalty == 0 else 'savings_withdrawal_penalty'
        penalty_info = f' (Penalty: ${penalty:.2f}, Forfeited interest: ${forfeited_interest:.2f})' if penalty > 0 else ''
        t2 = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=Decimal(str(amount)),
            transaction_type=withdrawal_type,
            description=f'Savings withdrawal from "{target.name}". Original amount: ${float(amount):.2f}{penalty_info}. Net transferred to wallet: ${net_amount:.2f}. Remaining balance: ${float(target.current_amount):.2f}',
            payment_group=target.payment_group,
            piggy_bank=target
        )
        
        TransactionHistory.objects.create(
            payment_profile=payment_profile,
            transaction_token=t2,
            authorization_token=PaymentAuthorization.objects.create(
                payment_profile=payment_profile,
                authorization_code=secrets.token_hex(16)
            ),
            verification_token=PaymentVerification.objects.create(
                payment_profile=payment_profile,
                verification_code=secrets.token_hex(16)
            ),
            amount=Decimal(str(amount)),
            status='completed'
        )
        
        response_data = {
            'status': 'Withdrawal successful',
            'amount_withdrawn': amount,
            'penalty_applied': penalty,
            'forfeited_interest': forfeited_interest,
            'net_received': net_amount,
            'remaining_amount': float(target.current_amount),
            'new_balance': float(payment_profile.comrade_balance)
        }
        
        if penalty > 0:
            response_data['penalty_note'] = f'A {float(target.penalty_rate)}% early withdrawal penalty of ${penalty:.2f} was applied. Accrued interest of ${forfeited_interest:.2f} was forfeited.'
        
        return Response(response_data)
        
    @action(detail=True, methods=['post'])
    def extend_maturity(self, request, pk=None):
        target = self.get_object()
        new_date_str = request.data.get('maturity_date')
        if not new_date_str:
            return Response({'error': 'New maturity date is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from dateutil.parser import parse
        try:
            new_date = parse(new_date_str)
        except Exception:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
            
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if target.payment_group:
            from Payment.models import PiggyBankActionRequest, PaymentGroupMember
            if not PaymentGroupMember.objects.filter(payment_group=target.payment_group, payment_profile=payment_profile).exists():
                return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
            req = PiggyBankActionRequest.objects.create(
                piggy_bank=target,
                requested_by=payment_profile,
                action_type='extend_maturity',
                new_maturity_date=new_date,
                reason=request.data.get('reason', '')
            )
            return Response({'status': 'Maturity extension request created, pending group approval', 'request_id': str(req.id)})
        else:
            return self._execute_extend_maturity_internal(target, new_date)

    def _execute_extend_maturity_internal(self, target, new_date):
        target.maturity_date = new_date
        target.save()
        return Response({'status': 'Maturity date extended successfully', 'new_maturity_date': target.maturity_date})
        
    @action(detail=True, methods=['post'])
    def dissolve(self, request, pk=None):
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if target.payment_group:
            from Payment.models import PiggyBankActionRequest, PaymentGroupMember
            if not PaymentGroupMember.objects.filter(payment_group=target.payment_group, payment_profile=payment_profile).exists():
                return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
            req = PiggyBankActionRequest.objects.create(
                piggy_bank=target,
                requested_by=payment_profile,
                action_type='dissolve',
                reason=request.data.get('reason', '')
            )
            return Response({'status': 'Dissolve request created, pending group approval', 'request_id': str(req.id)})
        else:
            return self._execute_dissolve_internal(target, payment_profile, request)

    def _execute_dissolve_internal(self, target, payment_profile, request):
        amount = float(target.current_amount)
        if amount > 0:
            wd_res = self._execute_withdraw_internal(target, amount, payment_profile, request)
            if wd_res.status_code != 200:
                return wd_res
        
        target.status = 'inactive'
        target.is_active = False
        target.save()
        return Response({'status': 'Piggy bank dissolved and deactivated successfully', 'withdrawn_amount': amount})

    @action(detail=True, methods=['get'])
    def action_requests(self, request, pk=None):
        target = self.get_object()
        from Payment.models import PiggyBankActionRequest, PiggyBankActionRequestVote
        from Payment.serializers import PiggyBankActionRequestSerializer
        reqs = PiggyBankActionRequest.objects.filter(piggy_bank=target).order_by('-created_at')
        data = PiggyBankActionRequestSerializer(reqs, many=True).data
        
        # add user vote status
        payment_profile = get_or_create_payment_profile(request.user)
        for r in data:
            vote = PiggyBankActionRequestVote.objects.filter(request_id=r['id'], voter=payment_profile).first()
            r['current_user_vote'] = vote.vote if vote else None
            
        return Response(data)

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def vote_action(self, request, pk=None):
        target = self.get_object()
        request_id = request.data.get('request_id')
        vote_choice = request.data.get('vote')
        
        if vote_choice not in ['approve', 'reject']:
            return Response({'error': 'Invalid vote'}, status=status.HTTP_400_BAD_REQUEST)
            
        from Payment.models import PiggyBankActionRequest, PiggyBankActionRequestVote, PaymentGroupMember
        action_req = PiggyBankActionRequest.objects.filter(id=request_id, piggy_bank=target).first()
        if not action_req:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if action_req.status != 'pending':
            return Response({'error': f'Request already {action_req.status}'}, status=status.HTTP_400_BAD_REQUEST)
            
        payment_profile = get_or_create_payment_profile(request.user)
        if not PaymentGroupMember.objects.filter(payment_group=target.payment_group, payment_profile=payment_profile).exists():
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
            
        vote_obj, created = PiggyBankActionRequestVote.objects.update_or_create(
            request=action_req,
            voter=payment_profile,
            defaults={'vote': vote_choice}
        )
        
        # check 100% consensus
        total_members = target.payment_group.members.count()
        approvals = action_req.votes.filter(vote='approve').count()
        rejections = action_req.votes.filter(vote='reject').count()
        
        if approvals == total_members:
            action_req.status = 'approved'
            action_req.save()
            # execute action
            if action_req.action_type == 'withdraw':
                res = self._execute_withdraw_internal(target, float(action_req.amount), action_req.requested_by, request)
                if res.status_code == 200:
                    action_req.status = 'executed'
                else:
                    action_req.status = 'failed'
                action_req.save()
            elif action_req.action_type == 'extend_maturity':
                res = self._execute_extend_maturity_internal(target, action_req.new_maturity_date)
                action_req.status = 'executed'
                action_req.save()
            elif action_req.action_type == 'dissolve':
                res = self._execute_dissolve_internal(target, action_req.requested_by, request)
                if res.status_code == 200:
                    action_req.status = 'executed'
                else:
                    action_req.status = 'failed'
                action_req.save()
                
            return Response({'status': 'Vote recorded and action executed due to 100% consensus'})
        
        if rejections > 0:
            # 100% consensus failed
            action_req.status = 'rejected'
            action_req.save()
            return Response({'status': 'Vote recorded. Action rejected because 100% consensus is required.'})
            
        return Response({'status': 'Vote recorded successfully', 'approvals': approvals, 'total': total_members})
    """
    
    new_content = content.replace(withdraw_code, new_withdraw_code)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print("Patched views.py successfully")

if __name__ == '__main__':
    main()
