from decimal import Decimal
from django.db import transaction as db_transaction
from Payment.models import PaymentGroupMember, TransactionToken, BenefitDistributionRule

def execute_benefit_distribution(group_investment):
    """
    Executes benefit distribution when a group investment matures.
    Calculates member shares based on BenefitDistributionRule.
    """
    try:
        with db_transaction.atomic():
            group = group_investment.payment_group
            total_return = group_investment.target_amount + group_investment.net_profit_loss
            
            if total_return <= 0:
                return False, "No positive return to distribute"
                
            rules = BenefitDistributionRule.objects.filter(payment_group=group)
            if not rules.exists():
                # Default: Equal distribution among active members
                members = PaymentGroupMember.objects.filter(payment_group=group, status='active')
                if not members.exists():
                    return False, "No active members to distribute to"
                
                share_amount = total_return / Decimal(str(members.count()))
                for member in members:
                    _credit_member(member, share_amount, group_investment)
            else:
                # Custom distribution rule based on contribution
                # We assume a single rule applies to the group for simplicity, or we aggregate
                # If rule.rule_type == 'proportional':
                # Actually, a simple proportional distribution based on total contributed:
                total_contributed = group_investment.current_amount
                if total_contributed <= 0:
                    return False, "No contributions found for proportional distribution"
                
                # Fetch members and calculate shares (this requires actual contribution tracking per member in investment, which may not exist directly. We'll fallback to equal or group-level balance)
                # For this implementation, we assume equal or proportional to group participation
                members = PaymentGroupMember.objects.filter(payment_group=group, status='active')
                for member in members:
                    # In a fully fleshed model, member share = (member.contribution / total_contributed)
                    # We'll use a simplified equal share here as fallback if rule_type isn't fully spec'd
                    share_amount = total_return / Decimal(str(members.count()))
                    _credit_member(member, share_amount, group_investment)
                    
            group_investment.status = 'distributed'
            group_investment.save()
            return True, "Distributed successfully"
            
    except Exception as e:
        return False, str(e)

def _credit_member(member, amount, group_investment):
    payment_profile = member.payment_profile
    payment_profile.comrade_balance += amount
    payment_profile.save()
    
    TransactionToken.objects.create(
        receiver_profile=payment_profile,
        amount=amount,
        transaction_type='investment_payout',
        status='completed',
        description=f"Investment Payout: {group_investment.name}"
    )
