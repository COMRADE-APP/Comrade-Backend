"""
Production Pricing Engine — Inference module for the trained RL model.

Loads the saved TD3 model and provides pricing decisions for the Comrade platform.
Falls back to rule-based pricing if the model is unavailable.
"""

import os
import json
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class PricingDecision:
    """Result of a pricing computation."""
    base_price: float
    offered_price: float
    discount_pct: float
    tier: str
    is_student: bool
    price_action: float
    notify_action: float
    promo_action: float
    model_version: str
    is_fallback: bool = False


@dataclass
class TierRecommendation:
    """Recommendation for tier upgrade."""
    current_tier: str
    recommended_tier: str
    cumulative_savings: float
    savings_threshold: float
    progress_pct: float
    estimated_monthly_savings: float


# Tier configuration from Qomrade.docx
TIER_CONFIG = {
    'free':     {'idx': 0, 'K': 3,  'max_monthly': 6,    'max_notifications': 5},
    'standard': {'idx': 1, 'K': 7,  'max_monthly': 25,   'max_notifications': 25},
    'premium':  {'idx': 2, 'K': 12, 'max_monthly': 45,   'max_notifications': 100},
    'gold':     {'idx': 3, 'K': 50, 'max_monthly': 1000, 'max_notifications': 500},
}

TIER_THRESHOLDS = {
    'free': 50,       # Free → Standard
    'standard': 200,  # Standard → Premium
    'premium': 700,   # Premium → Gold
}

STUDENT_DISCOUNT = 0.40  # 40%


class PricingEngine:
    """
    Production inference engine for the RL pricing model.
    
    Usage:
        engine = PricingEngine()
        decision = engine.get_price(state_vector)
        recommendation = engine.get_tier_recommendation(cumulative_savings, current_tier)
    """
    
    def __init__(self, model_dir=None):
        self.model_dir = model_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'pricing'
        )
        self.agent = None
        self.config = None
        self.model_version = 'v1'
        self._load_model()
    
    def _load_model(self):
        """Load the trained RL model if available."""
        config_path = os.path.join(self.model_dir, 'config.json')
        actor_path = os.path.join(self.model_dir, 'actor.pth')
        
        if not os.path.exists(config_path) or not os.path.exists(actor_path):
            print(f"[PricingEngine] No trained model found at {self.model_dir}, using rule-based fallback")
            return
        
        try:
            import torch
            from ML.training.agent import ComradeTD3Agent
            
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            
            self.agent = ComradeTD3Agent(
                state_dim=self.config.get('state_dim', 8),
                action_dim=self.config.get('action_dim', 3),
            )
            self.agent.load(self.model_dir)
            self.agent.actor.eval()
            self.model_version = f"v1-it{self.config.get('total_iterations', 0)}"
            print(f"[PricingEngine] Model loaded from {self.model_dir} ({self.model_version})")
        except Exception as e:
            print(f"[PricingEngine] Failed to load model: {e}, using rule-based fallback")
            self.agent = None
    
    def get_price(self, state_vector, base_price=100.0):
        """
        Compute dynamic price for a given state.
        
        Args:
            state_vector: np.array of shape (8,) [G, P, D, S, N, M, tier_idx, is_student]
            base_price: The retail/base price of the product
            
        Returns:
            PricingDecision
        """
        state_vector = np.array(state_vector, dtype=np.float32)
        state_vector[1] = base_price  # Override price with actual base
        
        tier_idx = int(state_vector[6])
        is_student = state_vector[7] > 0.5
        tier_name = ['free', 'standard', 'premium', 'gold'][min(tier_idx, 3)]
        
        if self.agent is not None:
            # Use RL model
            action = self.agent.select_action(state_vector, evaluate=True)
            price_adj, notify_intensity, promo_discount = action
        else:
            # Rule-based fallback
            action = self._rule_based_action(state_vector)
            price_adj, notify_intensity, promo_discount = action
        
        # Apply actions
        student_mult = (1.0 - STUDENT_DISCOUNT) if is_student else 1.0
        offered_price = base_price * (1.0 + price_adj) * student_mult * (1.0 - promo_discount)
        
        # Price floors and ceilings
        min_price = base_price * 0.3  # Never below 30% of base
        max_price = base_price * 1.2  # Never above 120% of base
        offered_price = np.clip(offered_price, min_price, max_price)
        
        discount_pct = (base_price - offered_price) / base_price * 100
        
        return PricingDecision(
            base_price=base_price,
            offered_price=round(float(offered_price), 2),
            discount_pct=round(float(discount_pct), 2),
            tier=tier_name,
            is_student=is_student,
            price_action=float(price_adj),
            notify_action=float(notify_intensity),
            promo_action=float(promo_discount),
            model_version=self.model_version,
            is_fallback=self.agent is None,
        )
    
    def get_student_price(self, state_vector, base_price=100.0):
        """Compute price with student discount applied."""
        state_vector = np.array(state_vector, dtype=np.float32)
        state_vector[7] = 1.0  # Force student flag
        return self.get_price(state_vector, base_price)
    
    def get_tier_recommendation(self, cumulative_savings, current_tier='free'):
        """
        Recommend whether user should upgrade tier.
        
        Args:
            cumulative_savings: Total user savings from platform pricing
            current_tier: Current tier name
            
        Returns:
            TierRecommendation
        """
        tier_order = ['free', 'standard', 'premium', 'gold']
        current_idx = tier_order.index(current_tier)
        
        if current_idx >= 3:
            # Already at max tier
            return TierRecommendation(
                current_tier=current_tier,
                recommended_tier='gold',
                cumulative_savings=cumulative_savings,
                savings_threshold=0,
                progress_pct=100.0,
                estimated_monthly_savings=0,
            )
        
        threshold = TIER_THRESHOLDS.get(current_tier, float('inf'))
        next_tier = tier_order[current_idx + 1]
        progress = min(100.0, cumulative_savings / threshold * 100)
        
        recommended = next_tier if cumulative_savings >= threshold else current_tier
        
        return TierRecommendation(
            current_tier=current_tier,
            recommended_tier=recommended,
            cumulative_savings=cumulative_savings,
            savings_threshold=threshold,
            progress_pct=round(progress, 1),
            estimated_monthly_savings=round(cumulative_savings / max(1, 30), 2),
        )
    
    def _rule_based_action(self, state_vector):
        """
        Simple rule-based pricing when no RL model is available.
        Implements basic PID-like pricing from the document.
        """
        G, P, D, S, N, M, tier_idx, is_student = state_vector
        tier_idx = int(tier_idx)
        
        K = [3, 7, 12, 50][min(tier_idx, 3)]
        
        # PID-like price adjustment
        G_target = 0.8 * K
        error = G_target - G
        
        # If under target group size, lower price; if over, raise
        price_adj = np.clip(-0.01 * error, -0.15, 0.15)
        
        # Notification intensity scales with demand
        notify = np.clip(D / 20.0, 0.0, 1.0)
        
        # Promo discount based on sentiment
        promo = np.clip(0.1 * (1.0 - M), 0.0, 0.3)
        
        return np.array([price_adj, notify, promo])
    
    def reload(self):
        """Reload model from disk (e.g., after retraining)."""
        self._load_model()


# Singleton instance
_engine = None

def get_pricing_engine():
    """Get or create the global pricing engine singleton."""
    global _engine
    if _engine is None:
        _engine = PricingEngine()
    return _engine
