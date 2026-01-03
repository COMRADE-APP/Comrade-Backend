# Comrade Payment System Documentation

## Overview

The Comrade Payment System is a comprehensive payment management platform that supports individual transactions, group savings/purchases, recurring payments, subscriptions, and product purchases. It's designed to handle both internal (Comrade Balance) and external payment methods with full transaction tracking and verification.

---

## Architecture

### Core Components

1. **Payment Profiles** - User payment accounts with balance tracking
2. **Transactions** - Individual payment records with authorization and verification
3. **Payment Groups** - Collaborative savings and group purchasing
4. **Standing Orders** - Recurring payment automation
5. **Products & Subscriptions** - E-commerce functionality
6. **Targets (Piggy Banks)** - Savings goals and milestones

---

## Models

### PaymentProfile
Represents a user's payment account and balance.

**Fields:**
- `user` - One-to-one relationship with CustomUser
- `comrade_balance` - Current balance in the system (Decimal)
- `total_sent` - Lifetime total amount sent
- `total_received` - Lifetime total amount received
- `payment_methods` - Available payment methods (JSON)
- `default_payment_method` - Preferred payment method
- `created_at`, `updated_at` - Timestamps

**Indexes:** `user`, `comrade_balance`

---

### TransactionToken
Core transaction model with tokenization and verification.

**Fields:**
- `sender` - User initiating the transaction
- `receiver` - User receiving payment (nullable)
- `amount` - Transaction amount (Decimal)
- `token` - Unique transaction token (UUID)
- `payment_method` - INTERNAL or EXTERNAL
- `external_payment_provider` - Provider name if external
- `transaction_type` - TRANSFER, PURCHASE, CONTRIBUTION, etc.
- `status` - PENDING, AUTHORIZED, VERIFIED, COMPLETED, FAILED, CANCELLED
- `description` - Transaction description
- `metadata` - Additional data (JSON)
- `authorization_code` - Payment gateway authorization
- `verification_date` - When transaction was verified
- `created_at`, `updated_at` - Timestamps

**Indexes:** `sender`, `receiver`, `token`, `status`, `created_at`

**Token Format:** `TXN-{UUID4}` (e.g., `TXN-7c6a8f34-2b1e-4d3c-9a5f-1e2d3c4b5a6f`)

---

### PaymentGroups
Group savings or collaborative purchasing system.

**Fields:**
- `name` - Group name
- `description` - Purpose/description
- `admin` - Group administrator (CustomUser)
- `group_type` - SAVINGS or PURCHASE
- `target_amount` - Goal amount (Decimal, nullable)
- `current_amount` - Total contributed so far
- `currency` - Currency code (default: USD)
- `deadline` - Optional deadline for reaching target
- `is_active` - Whether group is accepting contributions
- `created_at`, `updated_at` - Timestamps

**Indexes:** `admin`, `group_type`, `is_active`

---

### GroupMembers
Tracks members in payment groups with roles and contributions.

**Fields:**
- `group` - ForeignKey to PaymentGroups
- `user` - Group member (CustomUser)
- `role` - ADMIN or MEMBER
- `total_contributed` - Member's total contributions
- `joined_at` - When member joined

**Indexes:** `group`, `user`, `role`

**Unique Constraint:** (`group`, `user`) - User can't join same group twice

---

### Contribution
Individual contributions to payment groups.

**Fields:**
- `group` - ForeignKey to PaymentGroups
- `member` - Contributing user
- `amount` - Contribution amount
- `transaction` - Linked TransactionToken
- `contribution_date` - When contribution was made

**Indexes:** `group`, `member`, `contribution_date`

---

### StandingOrder
Recurring payment automation.

**Fields:**
- `user` - User who created the standing order
- `recipient` - Payment recipient (CustomUser, nullable)
- `amount` - Recurring amount
- `frequency` - DAILY, WEEKLY, MONTHLY, YEARLY
- `payment_method` - INTERNAL or EXTERNAL
- `description` - Standing order purpose
- `start_date` - When to start
- `end_date` - When to end (nullable)
- `last_executed` - Last execution timestamp
- `next_execution` - Next scheduled execution
- `is_active` - Whether active
- `created_at`, `updated_at` - Timestamps

**Indexes:** `user`, `is_active`, `next_execution`

---

### GroupInvitation
Invite system for payment groups.

**Fields:**
- `group` - PaymentGroups being invited to
- `inviter` - User sending invitation
- `invitee_email` - Email of invitee
- `status` - PENDING, ACCEPTED, DECLINED, EXPIRED
- `expires_at` - Expiration timestamp
- `created_at` - When invitation was sent

**Indexes:** `group`, `invitee_email`, `status`, `expires_at`

---

### GroupTarget
Savings goals/milestones for groups (piggy bank feature).

**Fields:**
- `group` - ForeignKey to PaymentGroups
- `name` - Target name
- `description` - Target description
- `target_amount` - Goal amount
- `current_amount` - Amount saved so far
- `target_date` - Target completion date (nullable)
- `is_achieved` - Whether target is reached
- `created_at`, `updated_at` - Timestamps

**Indexes:** `group`, `is_achieved`, `target_date`

---

### PaymentItem
Items/purposes for transactions.

**Fields:**
- `name` - Item name
- `description` - Item description
- `price` - Item price
- `currency` - Currency code
- `is_active` - Whether available

**Indexes:** `is_active`

---

### Product
Products available for purchase.

**Fields:**
- `name` - Product name
- `description` - Product description
- `price` - Product price
- `category` - Product category
- `is_available` - Stock availability
- `created_at`, `updated_at` - Timestamps

**Indexes:** `category`, `is_available`

---

### UserSubscription
Subscription management for users.

**Fields:**
- `user` - Subscribed user
- `subscription_type` - BASIC, PREMIUM, etc.
- `status` - ACTIVE, CANCELLED, EXPIRED
- `start_date` - Subscription start
- `end_date` - Subscription end
- `auto_renew` - Auto-renewal flag
- `created_at`, `updated_at` - Timestamps

**Indexes:** `user`, `status`, `subscription_type`

---

## API Endpoints

Base URL: `/payments/`

### Payment Profiles

**GET `/payments/payment-profiles/`**
- List all payment profiles (admin only)

**GET `/payments/payment-profiles/{id}/`**
- Get specific payment profile

**GET `/payments/payment-profiles/my_profile/`**
- Get current user's payment profile
- Response: `{user, comrade_balance, total_sent, total_received, payment_methods}`

**GET `/payments/payment-profiles/balance/`**
- Get current user's balance only
- Response: `{balance: "123.45"}`

---

### Transactions

**GET `/payments/transactions/`**
- List current user's transactions (filtered automatically)

**POST `/payments/transactions/create_transaction/`**
- Create new transaction
- Body:
  ```json
  {
    "receiver_id": 123,
    "amount": "50.00",
    "payment_method": "INTERNAL",
    "transaction_type": "TRANSFER",
    "description": "Payment for services",
    "metadata": {}
  }
  ```
- Response: Transaction details with token

**GET `/payments/transactions/history/`**
- Get transaction history for current user
- Optional query params: `?status=COMPLETED&limit=10`

---

### Payment Groups

**GET `/payments/payment-groups/`**
- List payment groups where user is admin or member

**POST `/payments/payment-groups/`**
- Create new payment group
- Body:
  ```json
  {
    "name": "Vacation Fund",
    "description": "Summer trip savings",
    "group_type": "SAVINGS",
    "target_amount": "5000.00",
    "deadline": "2026-06-01"
  }
  ```

**GET `/payments/payment-groups/{id}/`**
- Get payment group details

**POST `/payments/payment-groups/{id}/join/`**
- Join a payment group

**POST `/payments/payment-groups/{id}/contribute/`**
- Make contribution to group
- Body:
  ```json
  {
    "amount": "100.00",
    "payment_method": "INTERNAL"
  }
  ```

**POST `/payments/payment-groups/{id}/invite/`**
- Invite user to group
- Body:
  ```json
  {
    "invitee_email": "friend@example.com"
  }
  ```

**GET `/payments/payment-groups/my_groups/`**
- Get all groups for current user

**GET `/payments/payment-groups/{id}/members/`**
- Get all members of a group

**GET `/payments/payment-groups/{id}/contributions_list/`**
- Get all contributions for a group

---

### Products

**GET `/payments/products/`**
- List available products

**GET `/payments/products/{id}/`**
- Get product details

**GET `/payments/products/recommendations/`**
- Get recommended products for current user

---

### Group Targets (Piggy Banks)

**GET `/payments/targets/`**
- List targets for user's groups

**POST `/payments/targets/`**
- Create new savings target
- Body:
  ```json
  {
    "group": 1,
    "name": "Emergency Fund",
    "description": "3 months expenses",
    "target_amount": "3000.00",
    "target_date": "2026-12-31"
  }
  ```

**POST `/payments/targets/{id}/contribute/`**
- Contribute to a target
- Body:
  ```json
  {
    "amount": "50.00"
  }
  ```

---

### Subscriptions

**GET `/payments/subscriptions/`**
- Get current user's subscriptions

**POST `/payments/subscriptions/`**
- Create/update subscription

---

## Transaction Flow

### Internal Transfer Flow

1. **Initiate Transaction**
   - POST to `/payments/transactions/create_transaction/`
   - System generates unique token
   - Status: PENDING

2. **Authorization**
   - System validates sender has sufficient balance
   - Deducts from sender's `comrade_balance`
   - Status: AUTHORIZED

3. **Verification**
   - System verifies transaction integrity
   - Updates receiver's balance
   - Status: VERIFIED

4. **Completion**
   - Transaction marked as COMPLETED
   - Both profiles updated (total_sent/total_received)
   - Status: COMPLETED

### External Payment Flow

1. **Initiate Transaction**
   - POST to `/payments/transactions/create_transaction/`
   - Include `external_payment_provider`
   - Status: PENDING

2. **Payment Gateway Integration**
   - Redirect to payment provider
   - Get authorization code
   - Status: AUTHORIZED

3. **Webhook Verification**
   - Provider sends webhook confirmation
   - System verifies payment
   - Status: VERIFIED

4. **Completion**
   - Update balances
   - Status: COMPLETED

---

## Group Payment Features

### Creating a Savings Group

```python
# Example: Create vacation fund
POST /payments/payment-groups/
{
  "name": "Team Vacation 2026",
  "description": "Group savings for summer trip",
  "group_type": "SAVINGS",
  "target_amount": "5000.00",
  "deadline": "2026-06-01"
}
```

### Contributing to Group

```python
# Member makes contribution
POST /payments/payment-groups/3/contribute/
{
  "amount": "100.00",
  "payment_method": "INTERNAL"
}
```

System automatically:
- Creates Transaction record
- Updates member's total_contributed
- Updates group's current_amount
- Creates Contribution record linking transaction to group

### Group Targets (Multiple Goals)

Groups can have multiple targets:

```python
# Create target within group
POST /payments/targets/
{
  "group": 3,
  "name": "Flights",
  "target_amount": "2000.00"
}

POST /payments/targets/
{
  "group": 3,
  "name": "Accommodation",
  "target_amount": "1500.00"
}
```

---

## Security Features

1. **Tokenization**: All transactions use unique UUID tokens
2. **Authorization**: Multi-step verification before completion
3. **Balance Validation**: Prevents overdrafts
4. **Rate Limiting**: Configured in settings (user: 1000/hour)
5. **Database Indexes**: Optimized queries on frequent lookups
6. **Audit Trail**: Complete transaction history with timestamps

---

## Integration Requirements

### Environment Variables

```bash
# Payment Gateway (when integrated)
STRIPE_API_KEY=
STRIPE_WEBHOOK_SECRET=
PAYPAL_CLIENT_ID=
PAYPAL_SECRET=

# Currency & Localization
DEFAULT_CURRENCY=USD
```

### Future Integrations

- **Stripe**: Credit card payments
- **PayPal**: PayPal transfers
- **M-Pesa**: Mobile money (Kenya)
- **Bank Transfers**: Direct bank integration

---

## Usage Examples

### Check User Balance

```python
GET /payments/payment-profiles/my_profile/
Response: {
  "user": {...},
  "comrade_balance": "450.75",
  "total_sent": "1200.00",
  "total_received": "1650.75"
}
```

### Send Money to Friend

```python
POST /payments/transactions/create_transaction/
{
  "receiver_id": 42,
  "amount": "25.00",
  "payment_method": "INTERNAL",
  "transaction_type": "TRANSFER",
  "description": "Lunch money"
}

Response: {
  "id": 156,
  "token": "TXN-a7b8c9d0-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "status": "COMPLETED",
  "amount": "25.00",
  ...
}
```

### Create Purchase Group

```python
POST /payments/payment-groups/
{
  "name": "New Laptop Fund",
  "group_type": "PURCHASE",
  "target_amount": "1500.00",
  "description": "Saving for MacBook Pro"
}

# Invite friends
POST /payments/payment-groups/5/invite/
{
  "invitee_email": "friend@example.com"
}
```

---

## Database Optimization

**Indexed Fields:**
- PaymentProfile: user, comrade_balance
- TransactionToken: sender, receiver, status, token, created_at
- PaymentGroups: admin, group_type, is_active
- GroupMembers: group, user, role
- Contribution: group, member, contribution_date

**Total Indexes**: 25+ across all payment models

---

## Limits & Quotas

Configured in `Payment/utils.py`:

- **Purchase Limits**: Based on subscription tier
- **Group Creation**: Limited by user type
- **Group Members**: Max members per subscription type
- **Transaction Rate**: 1000/hour for authenticated users

---

## Notes

- All monetary amounts use Decimal type for precision
- Timestamps are timezone-aware (UTC)
- Soft deletes not implemented (use is_active flags)
- Transaction tokens are immutable after creation
- Group admins have full control over their groups
