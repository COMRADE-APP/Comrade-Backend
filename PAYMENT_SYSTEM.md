# Payment System - Feature Documentation

## Overview
The Comrade Payment System provides a comprehensive solution for managing individual and group payments, transactions, and collaborative savings.

---

## Core Models

### 1. PaymentProfile
User payment account with balance tracking.

**Fields:**
- `user` - ForeignKey to Profile
- `payment_option` - Preferred payment method
- `comrade_balance` - Internal balance (Decimal)
- `profile_token` - Unique identifier

### 2. TransactionToken
Individual transactions between users.

**Fields:**
- `transaction_code` - UUID primary key
- `payment_profile` - Sender
- `recipient_profile` - Receiver
- `amount` - Transaction amount
- `transaction_type` - purchase, transfer, deposit, etc.
- `payment_option` - Payment method used
- `created_at` - Timestamp

**Types:**
- Purchase
- Refund
- Withdrawal
- Deposit
- Transfer
- Bid
- Donation
- Contribution

---

## Group Payment Features

### 3. PaymentGroups
Collaborative savings pools for group purchases.

**Fields:**
- `id` - UUID
- `name` - Group name
- `description` - Purpose
- `creator` - Group creator
- `max_capacity` - Member limit
- `target_amount` - Savings goal
- `current_amount` - Current balance
- `expiry_date` - Optional deadline
- `auto_purchase` - Auto-trigger when target met
- `requires_approval` - Admin approval for joins

**Use Cases:**
- Group gift purchases
- Event funding
- Shared expenses
- Community projects

### 4. PaymentGroupMember
Membership and contribution tracking.

**Fields:**
- `payment_group` - Group reference
- `payment_profile` - Member
- `is_admin` - Admin privileges
- `contribution_percentage` - Expected share
- `total_contributed` - Running total
- `joined_at` - Membership date

**Permissions:**
- Regular members: contribute, view
- Admins: invite, manage settings

### 5. Contribution
Individual payment records to groups.

**Fields:**
- `id` - UUID
- `payment_group` - Target group
- `member` - Contributing member
- `amount` - Contribution amount
- `transaction` - Linked transaction
- `contributed_at` - Timestamp
- `notes` - Optional message

### 6. StandingOrder
Recurring automated contributions.

**Fields:**
- `member` - Member with standing order
- `amount` - Recurring amount
- `frequency` - daily/weekly/monthly
- `next_contribution_date` - Next payment
- `is_active` - Enable/disable

**Frequencies:**
- Daily
- Weekly
- Bi-weekly
- Monthly

### 7. GroupInvitation
Invite system for groups.

**Fields:**
- `id` - UUID
- `payment_group` - Target group
- `invited_profile` - Invitee
- `invited_by` - Inviter
- `status` - pending/accepted/rejected/expired
- `invitation_link` - Unique URL
- `expires_at` - Expiration date

### 8. GroupTarget
Specific savings goals within groups.

**Fields:**
- `payment_group` - Parent group
- `target_item` - Optional item reference
- `target_amount` - Goal amount
- `description` - Goal description
- `target_date` - Optional deadline
- `achieved` - Completion status
- `achieved_at` - Completion date

---

## API Endpoints

### Profile Management
```http
GET /api/payments/profiles/my_profile/
GET /api/payments/profiles/balance/
```

### Transactions
```http
POST /api/payments/transactions/create_transaction/
{
  "recipient_email": "user@example.com",
  "amount": 50.00,
  "transaction_type": "transfer",
  "payment_option": "comrade_balance",
  "notes": "Optional note"
}

GET /api/payments/transactions/history/
```

### Payment Groups
```http
# List user's groups
GET /api/payments/groups/

# Create group
POST /api/payments/groups/
{
  "name": "Weekend Trip Fund",
  "description": "Saving for summer vacation",
  "max_capacity": 10,
  "target_amount": 1000.00,
  "expiry_date": "2024-12-31T23:59:59Z",
  "auto_purchase": false,
  "requires_approval": true
}

# Join group
POST /api/payments/groups/{id}/join/

# Contribute to group
POST /api/payments/groups/{id}/contribute/
{
  "amount": 50.00,
  "notes": "Monthly contribution"
}

# Invite member
POST /api/payments/groups/{id}/invite/
{
  "email": "friend@example.com"
}

# View members
GET /api/payments/groups/{id}/members/

# View contributions
GET /api/payments/groups/{id}/contributions_list/
```

---

## Usage Examples

### Example 1: Create Savings Group
```python
# User creates group for shared purchase
group = PaymentGroups.objects.create(
    name="Gaming Console Fund",
    description="Saving for PS5",
    creator=user_payment_profile,
    max_capacity=5,
    target_amount=500.00,
    auto_purchase=True
)

# Creator automatically added as admin
PaymentGroupMember.objects.create(
    payment_group=group,
    payment_profile=user_payment_profile,
    is_admin=True
)
```

### Example 2: Member Contributes
```python
# Check balance
if member.payment_profile.comrade_balance >= 50:
    # Deduct from member
    member.payment_profile.comrade_balance -= 50
    member.payment_profile.save()
    
    # Add to group
    group.current_amount += 50
    group.save()
    
    # Update member total
    member.total_contributed += 50
    member.save()
    
    # Record contribution
    Contribution.objects.create(
        payment_group=group,
        member=member,
        amount=50
    )
```

### Example 3: Standing Order
```python
# Set up recurring monthly contribution
StandingOrder.objects.create(
    member=group_member,
    amount=25.00,
    frequency='monthly',
    next_contribution_date=next_month,
    is_active=True
)
```

---

## Business Rules

### Group Creation
- Minimum capacity: 2 members
- Maximum capacity: configurable (default 10)
- Creator automatically becomes admin
- Optional target amount

### Contributions
- Must be group member
- Cannot exceed personal balance
- Atomic transactions (rollback on failure)
- Tracked individually per member

### Invitations
- Admins and creator can invite
- Unique invitation links
- 7-day expiry (configurable)
- Cannot exceed max_capacity

### Auto-Purchase
- Triggers when current_amount >= target_amount
- Only if auto_purchase = True
- Requires linked PaymentItem

---

## Security Features

- ✅ Atomic transactions (database-level)
- ✅ Balance verification before transfers
- ✅ Admin-only actions (invites, settings)
- ✅ Unique invitation links
- ✅ Expiry on invitations
- ✅ Permission checks on all actions
- ✅ UUID for sensitive IDs

---

## Future Enhancements

- [ ] Split payment calculations
- [ ] Payment reminders
- [ ] Group analytics
- [ ] Export reports
- [ ] Payment disputes
- [ ] External gateway integration
- [ ] Scheduled auto-purchase
