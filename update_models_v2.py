
import os

with open('Payment/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

round_orig = "    # Status\n    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')"

round_new = """    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approvals
    approvals = models.ManyToManyField(PaymentGroupMember, related_name='approved_rounds', blank=True)
    rejections = models.ManyToManyField(PaymentGroupMember, related_name='rejected_rounds', blank=True)
    approval_notes = models.JSONField(default=dict, blank=True)"""

if round_orig in content:
    content = content.replace(round_orig, round_new)

round_position_model = """
class RoundPosition(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='chama_positions')
    member = models.ForeignKey(PaymentGroupMember, on_delete=models.CASCADE, related_name='chama_positions')
    position_number = models.PositiveIntegerField(help_text='Position in the sequence (1, 2, 3...)')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['payment_group', 'position_number']
        ordering = ['position_number']
        
    def __str__(self):
        return f"Position {self.position_number} for {self.member.payment_profile.user.user.first_name} in {self.payment_group.name}"

class RoundContribution(models.Model):"""

if 'class RoundContribution(models.Model):' in content:
    content = content.replace('class RoundContribution(models.Model):', round_position_model)

with open('Payment/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
