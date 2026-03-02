"""
Comrade Dynamic Pricing Environment
Gymnasium-compatible RL environment implementing the Qomrade.docx differential equations.

State: [group_size, price, demand, supply, notifications, sentiment, tier_idx, is_student]
Action: [price_adjustment, notification_intensity, promo_discount]
Reward: α·user_savings_pct + (1-α)·supplier_margin + λ·Δgroup_growth
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces


# Tier configuration from Qomrade.docx
TIER_CONFIG = {
    0: {'name': 'free',     'K': 3,   'max_monthly': 6,    'max_notifications': 5},
    1: {'name': 'standard', 'K': 7,   'max_monthly': 25,   'max_notifications': 25},
    2: {'name': 'premium',  'K': 12,  'max_monthly': 45,   'max_notifications': 100},
    3: {'name': 'gold',     'K': 50,  'max_monthly': 1000, 'max_notifications': 500},
}

# Tier transition thresholds (cumulative savings in $)
TIER_THRESHOLDS = {
    0: 50,    # Free → Standard
    1: 200,   # Standard → Premium
    2: 700,   # Premium → Gold
}

# Kenya market calibration parameters from Qomrade.docx
DEFAULT_PARAMS = {
    'r': 0.25,           # Group growth rate
    'beta': 0.08,        # Notification effectiveness
    'gamma_price': 0.003,# Price sensitivity on group growth
    'alpha1': 0.6,       # PID P-gain
    'alpha2': 0.15,      # PID D-gain
    'alpha3': 0.02,      # PID I-gain
    'lambda_d': 15,      # Base demand (users/day)
    'mu': 0.04,          # Price elasticity
    'nu': 0.9,           # Network effect strength
    'delta': 0.12,       # Churn rate
    'eta': 0.4,          # Supplier responsiveness
    'pi_res': 50,        # Supplier reservation profit
    'theta': 0.15,       # Inventory decay
    'rho': 0.25,         # Notification decay
    'kappa': 0.35,       # Sentiment mean reversion
    'sigma_noise': 0.12, # Market volatility
    'phi': 0.06,         # Momentum sensitivity
    'base_cost': 60,     # Base cost per unit
    'fixed_cost': 200,   # Fixed cost
    'retail_price': 100, # Retail reference price
    'student_discount': 0.40,  # 40% student discount
}


class ComradePricingEnv(gym.Env):
    """
    RL environment for dynamic pricing on the Comrade platform.
    
    Simulates a 90-day trajectory of group buying dynamics with
    differential-equation-driven state transitions from the Qomrade document.
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, params=None, max_steps=90, render_mode=None):
        super().__init__()
        self.params = {**DEFAULT_PARAMS, **(params or {})}
        self.max_steps = max_steps
        self.render_mode = render_mode
        
        # Action space: [price_adjustment, notification_intensity, promo_discount]
        # price_adjustment: [-0.3, 0.3] (% change to base price)
        # notification_intensity: [0, 1] 
        # promo_discount: [0, 0.5]
        self.action_space = spaces.Box(
            low=np.array([-0.3, 0.0, 0.0], dtype=np.float32),
            high=np.array([0.3, 1.0, 0.5], dtype=np.float32),
        )
        
        # State space: [G, P, D, S, N, M, tier_idx, is_student]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32),
            high=np.array([100, 500, 200, 100, 500, 1, 3, 1], dtype=np.float32),
        )
        
        self.reset()
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Randomize initial conditions for diversity
        tier_idx = self.np_random.choice([0, 1, 2, 3], p=[0.5, 0.25, 0.15, 0.1])
        is_student = float(self.np_random.random() < 0.3)  # 30% chance student
        
        K = TIER_CONFIG[tier_idx]['K']
        
        self.state = np.array([
            max(1.0, self.np_random.uniform(1, K * 0.5)),   # G: group size
            self.params['retail_price'],                      # P: price (start at retail)
            self.np_random.uniform(5, 20),                    # D: demand
            self.np_random.uniform(0, 5),                     # S: supply
            float(TIER_CONFIG[tier_idx]['max_notifications']),# N: notification capacity
            self.np_random.uniform(0.3, 0.7),                 # M: sentiment
            float(tier_idx),                                  # tier index
            is_student,                                       # student flag
        ], dtype=np.float32)
        
        self.step_count = 0
        self.cumulative_savings = 0.0
        self.prev_group_size = self.state[0]
        self.integral_error = 0.0
        self.prev_dG = 0.0
        self.episode_rewards = []
        
        return self.state.copy(), {}
    
    def step(self, action):
        action = np.clip(action, self.action_space.low, self.action_space.high)
        price_adj, notify_intensity, promo_discount = action
        
        G, P, D, S, N, M, tier_idx, is_student = self.state
        tier_idx = int(tier_idx)
        p = self.params
        K = TIER_CONFIG[tier_idx]['K']
        N_max = TIER_CONFIG[tier_idx]['max_notifications']
        
        # Apply student discount modifier
        student_mult = (1.0 - p['student_discount']) if is_student > 0.5 else 1.0
        
        # Apply actions to compute new price
        new_P = P * (1.0 + price_adj) * student_mult
        new_P = new_P * (1.0 - promo_discount)
        new_P = np.clip(new_P, p['base_cost'] * 0.5, p['retail_price'] * 1.5)
        
        # ── Eq 1: Group Formation Dynamics (logistic growth + viral + price sensitivity) ──
        N_push = notify_intensity * N
        dG = (p['r'] * G * (1 - G / max(K, 1)) + 
              p['beta'] * N_push * np.sqrt(max(D, 0.01)) - 
              p['gamma_price'] * new_P * G)
        
        # ── Eq 2: Price Adjustment (PID Controller) ──
        G_target = 0.8 * K
        error = G_target - G
        self.integral_error += error
        dP = (-p['alpha1'] * error + p['alpha2'] * dG + p['alpha3'] * self.integral_error)
        
        # ── Eq 3: Demand Evolution (price-elastic with network effects) ──
        dD = (p['lambda_d'] * M * np.exp(-p['mu'] * new_P) * 
              (1 + G / 6) ** p['nu'] - p['delta'] * D)
        
        # ── Eq 4: Supplier Commitment (profit-responsive) ──
        profit = (new_P - p['base_cost']) * G - p['fixed_cost']
        dS = max(0, p['eta'] * (profit - p['pi_res'])) - p['theta'] * S
        
        # ── Eq 5: Notification Capacity (tier-constrained renewal) ──
        if N < N_max:
            dN = N_max * 0.1 - p['rho'] * N_push  # Regenerate slowly, consumed by pushes
        else:
            dN = -p['rho'] * N_push
        
        # ── Eq 6: Market Sentiment (stochastic with mean reversion) ──
        noise = p['sigma_noise'] * self.np_random.standard_normal()
        dM = (-p['kappa'] * (M - 0.5) + noise + p['phi'] * dG)
        
        # Update state with dt=1.0 (one day)
        dt = 1.0
        new_G = max(1.0, G + dG * dt)
        # Price uses both PID adjustment and the RL action
        new_P_final = np.clip(new_P + dP * dt * 0.1, p['base_cost'] * 0.3, p['retail_price'] * 2)
        new_D = max(0, D + dD * dt)
        new_S = max(0, S + dS * dt)
        new_N = np.clip(N + dN * dt, 0, N_max)
        new_M = np.clip(M + dM * dt, 0, 1)
        
        # ── Compute reward ──
        # User savings percentage
        user_savings_pct = max(0, (p['retail_price'] - new_P_final) / p['retail_price'])
        
        # Supplier margin
        supplier_revenue = new_P_final * new_G
        supplier_cost = p['base_cost'] * new_G + p['fixed_cost']
        supplier_margin = (supplier_revenue - supplier_cost) / max(supplier_cost, 1)
        supplier_margin = np.clip(supplier_margin, -1, 1)
        
        # Group growth delta
        group_growth = (new_G - self.prev_group_size) / max(self.prev_group_size, 1)
        
        # Purchase probability (sigmoid of value proposition)
        value = user_savings_pct * 5 - 1  # Center around 20% discount
        purchase_prob = 1.0 / (1.0 + np.exp(-value))
        purchased = self.np_random.random() < purchase_prob
        
        # Combined reward
        alpha = 0.5   # Fairness: balance user vs supplier
        lam = 0.1     # Growth incentive
        reward = (alpha * user_savings_pct + 
                  (1 - alpha) * max(0, supplier_margin) + 
                  lam * group_growth)
        
        # Bonus for purchase conversion
        if purchased:
            reward += 0.2
            self.cumulative_savings += (p['retail_price'] - new_P_final) * new_G
        
        # Penalty for unsustainable pricing (negative supplier margin)
        if supplier_margin < 0:
            reward -= 0.3 * abs(supplier_margin)
        
        # ── Tier Transition ──
        new_tier = tier_idx
        if tier_idx < 3 and self.cumulative_savings > TIER_THRESHOLDS.get(tier_idx, float('inf')):
            new_tier = tier_idx + 1
            reward += 0.5  # Bonus for tier upgrade
        
        # Update state
        self.state = np.array([
            new_G, new_P_final, new_D, new_S, new_N, new_M,
            float(new_tier), is_student
        ], dtype=np.float32)
        
        self.prev_group_size = new_G
        self.prev_dG = dG
        self.step_count += 1
        self.episode_rewards.append(reward)
        
        terminated = self.step_count >= self.max_steps
        truncated = False
        
        info = {
            'cumulative_savings': self.cumulative_savings,
            'tier': TIER_CONFIG[new_tier]['name'],
            'purchase_prob': purchase_prob,
            'purchased': purchased,
            'supplier_margin': supplier_margin,
            'user_savings_pct': user_savings_pct,
            'group_size': new_G,
            'price': new_P_final,
        }
        
        return self.state.copy(), float(reward), terminated, truncated, info
    
    def get_state_dict(self):
        """Return current state as a labeled dictionary."""
        G, P, D, S, N, M, tier_idx, is_student = self.state
        return {
            'group_size': G, 'price': P, 'demand': D, 'supply': S,
            'notifications': N, 'sentiment': M,
            'tier': TIER_CONFIG[int(tier_idx)]['name'],
            'is_student': bool(is_student > 0.5),
            'cumulative_savings': self.cumulative_savings,
        }


# Register with Gymnasium
gym.register(
    id='ComradePricing-v0',
    entry_point='ML.training.pricing_env:ComradePricingEnv',
)
