"""
TD3 (Twin Delayed DDPG) Agent for Comrade Dynamic Pricing.

Architecture:
- Actor: tier-conditioned policy network → price, notification, promo actions
- Twin Critics: two Q-networks for variance reduction
- Prioritized Replay Buffer with TD-error priorities
- Ornstein-Uhlenbeck noise for temporally correlated exploration
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from collections import deque
import random
import json
import os


# ─────────────────────────────────────────────────
# Neural Network Components
# ─────────────────────────────────────────────────

class Actor(nn.Module):
    """Policy network with tier-conditioned output."""
    
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
        )
        # Pricing head: outputs in [-1, 1], scaled to [-0.3, 0.3]
        self.price_head = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Tanh(),
        )
        # Notification head: [0, 1]
        self.notify_head = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )
        # Promo head: [0, 1], scaled to [0, 0.5]
        self.promo_head = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )
    
    def forward(self, state):
        features = self.shared(state)
        price = self.price_head(features) * 0.3       # [-0.3, 0.3]
        notify = self.notify_head(features)            # [0, 1]
        promo = self.promo_head(features) * 0.5        # [0, 0.5]
        return torch.cat([price, notify, promo], dim=-1)


class Critic(nn.Module):
    """Q-value network."""
    
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
    
    def forward(self, state, action):
        x = torch.cat([state, action], dim=-1)
        return self.net(x)


# ─────────────────────────────────────────────────
# Ornstein-Uhlenbeck Noise Process
# ─────────────────────────────────────────────────

class OUNoise:
    """Ornstein-Uhlenbeck noise for temporally correlated exploration."""
    
    def __init__(self, size, mu=0.0, theta=0.15, sigma=0.2):
        self.size = size
        self.mu = mu * np.ones(size)
        self.theta = theta
        self.sigma = sigma
        self.reset()
    
    def reset(self):
        self.state = self.mu.copy()
    
    def sample(self):
        dx = self.theta * (self.mu - self.state) + self.sigma * np.random.randn(self.size)
        self.state += dx
        return self.state.copy()


# ─────────────────────────────────────────────────
# Prioritized Replay Buffer
# ─────────────────────────────────────────────────

class PrioritizedReplayBuffer:
    """Experience replay with TD-error based priorities."""
    
    def __init__(self, capacity=100000, alpha=0.6, beta=0.4, beta_increment=0.001):
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = beta_increment
        self.buffer = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.position = 0
        self.max_priority = 1.0
    
    def push(self, state, action, reward, next_state, done):
        experience = (state, action, reward, next_state, done)
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience
        self.priorities[self.position] = self.max_priority
        self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size):
        n = len(self.buffer)
        probs = self.priorities[:n] ** self.alpha
        probs /= probs.sum()
        
        indices = np.random.choice(n, batch_size, p=probs, replace=False)
        
        # Importance sampling weights
        self.beta = min(1.0, self.beta + self.beta_increment)
        weights = (n * probs[indices]) ** (-self.beta)
        weights /= weights.max()
        
        batch = [self.buffer[i] for i in indices]
        states, actions, rewards, next_states, dones = zip(*batch)
        
        return (
            (np.array(states), np.array(actions), np.array(rewards),
             np.array(next_states), np.array(dones)),
            indices,
            weights,
        )
    
    def update_priorities(self, indices, priorities):
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = priority + 1e-6
            self.max_priority = max(self.max_priority, priority + 1e-6)
    
    def __len__(self):
        return len(self.buffer)


# ─────────────────────────────────────────────────
# TD3 Agent
# ─────────────────────────────────────────────────

class ComradeTD3Agent:
    """
    Twin Delayed DDPG agent for dynamic pricing.
    
    Hyperparameters calibrated from the Qomrade document's simulation parameters.
    """
    
    def __init__(self, state_dim=8, action_dim=3, device=None):
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Networks
        self.actor = Actor(state_dim, action_dim).to(self.device)
        self.actor_target = Actor(state_dim, action_dim).to(self.device)
        self.actor_target.load_state_dict(self.actor.state_dict())
        
        self.critic_1 = Critic(state_dim, action_dim).to(self.device)
        self.critic_2 = Critic(state_dim, action_dim).to(self.device)
        self.critic_1_target = Critic(state_dim, action_dim).to(self.device)
        self.critic_2_target = Critic(state_dim, action_dim).to(self.device)
        self.critic_1_target.load_state_dict(self.critic_1.state_dict())
        self.critic_2_target.load_state_dict(self.critic_2.state_dict())
        
        # Optimizers
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=3e-4)
        self.critic_optimizer = torch.optim.Adam(
            list(self.critic_1.parameters()) + list(self.critic_2.parameters()), 
            lr=3e-4
        )
        
        # Hyperparameters
        self.gamma = 0.99          # Discount factor
        self.tau = 0.005           # Soft update rate
        self.policy_noise = 0.2    # Target policy smoothing
        self.noise_clip = 0.5      # Noise clipping
        self.policy_freq = 2       # Delayed policy updates
        self.batch_size = 256
        
        # Exploration
        self.ou_noise = OUNoise(action_dim, sigma=0.2)
        self.exploration_noise = 1.0
        self.exploration_decay = 0.9995
        self.min_exploration = 0.05
        
        # Buffer
        self.replay_buffer = PrioritizedReplayBuffer(capacity=100000)
        
        # Training state
        self.total_it = 0
        
        # State normalization (running stats)
        self.state_mean = np.zeros(state_dim, dtype=np.float32)
        self.state_std = np.ones(state_dim, dtype=np.float32)
        self._state_samples = []
    
    def normalize_state(self, state):
        """Normalize state using running statistics."""
        return (state - self.state_mean) / (self.state_std + 1e-8)
    
    def update_normalization(self, state):
        """Update running normalization statistics."""
        self._state_samples.append(state)
        if len(self._state_samples) > 100:
            samples = np.array(self._state_samples[-10000:])
            self.state_mean = samples.mean(axis=0).astype(np.float32)
            self.state_std = samples.std(axis=0).astype(np.float32)
            self.state_std[self.state_std < 0.01] = 1.0  # Prevent div by zero
    
    def select_action(self, state, evaluate=False):
        """Select action using the actor network with optional exploration noise."""
        self.update_normalization(state)
        norm_state = self.normalize_state(state)
        
        state_tensor = torch.FloatTensor(norm_state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action = self.actor(state_tensor).cpu().numpy()[0]
        
        if not evaluate:
            noise = self.ou_noise.sample()
            action = action + noise * self.exploration_noise
            # Decay exploration
            self.exploration_noise = max(
                self.min_exploration, 
                self.exploration_noise * self.exploration_decay
            )
        
        # Clip to action bounds
        action = np.clip(action, [-0.3, 0.0, 0.0], [0.3, 1.0, 0.5])
        return action
    
    def store_transition(self, state, action, reward, next_state, done):
        """Store a transition in the replay buffer."""
        norm_state = self.normalize_state(state)
        norm_next = self.normalize_state(next_state)
        self.replay_buffer.push(norm_state, action, reward, norm_next, done)
    
    def train_step(self):
        """Perform one training step (critic + delayed actor update)."""
        if len(self.replay_buffer) < self.batch_size:
            return {}
        
        self.total_it += 1
        
        # Sample
        batch, indices, weights = self.replay_buffer.sample(self.batch_size)
        state, action, reward, next_state, done = batch
        
        state = torch.FloatTensor(state).to(self.device)
        action = torch.FloatTensor(action).to(self.device)
        reward = torch.FloatTensor(reward).unsqueeze(1).to(self.device)
        next_state = torch.FloatTensor(next_state).to(self.device)
        done = torch.FloatTensor(done).unsqueeze(1).to(self.device)
        weights = torch.FloatTensor(weights).unsqueeze(1).to(self.device)
        
        with torch.no_grad():
            # Target policy smoothing
            noise = (torch.randn_like(action) * self.policy_noise).clamp(
                -self.noise_clip, self.noise_clip
            )
            next_action = self.actor_target(next_state) + noise
            # Clip each action dimension
            next_action[:, 0] = next_action[:, 0].clamp(-0.3, 0.3)
            next_action[:, 1] = next_action[:, 1].clamp(0.0, 1.0)
            next_action[:, 2] = next_action[:, 2].clamp(0.0, 0.5)
            
            # Twin Q targets
            target_q1 = self.critic_1_target(next_state, next_action)
            target_q2 = self.critic_2_target(next_state, next_action)
            target_q = reward + (1 - done) * self.gamma * torch.min(target_q1, target_q2)
        
        # Critic loss
        current_q1 = self.critic_1(state, action)
        current_q2 = self.critic_2(state, action)
        td_error = torch.abs(current_q1 - target_q).detach().cpu().numpy().flatten()
        
        critic_loss = (weights * F.mse_loss(current_q1, target_q, reduction='none')).mean() + \
                      (weights * F.mse_loss(current_q2, target_q, reduction='none')).mean()
        
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic_1.parameters(), max_norm=1.0)
        torch.nn.utils.clip_grad_norm_(self.critic_2.parameters(), max_norm=1.0)
        self.critic_optimizer.step()
        
        # Update priorities
        self.replay_buffer.update_priorities(indices, td_error)
        
        # Delayed actor update
        actor_loss = None
        if self.total_it % self.policy_freq == 0:
            actor_loss = -self.critic_1(state, self.actor(state)).mean()
            
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), max_norm=1.0)
            self.actor_optimizer.step()
            
            # Soft update targets
            for param, target_param in zip(self.actor.parameters(), self.actor_target.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
            for param, target_param in zip(self.critic_1.parameters(), self.critic_1_target.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
            for param, target_param in zip(self.critic_2.parameters(), self.critic_2_target.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
        
        return {
            'critic_loss': critic_loss.item(),
            'actor_loss': actor_loss.item() if actor_loss is not None else None,
            'q_value': current_q1.mean().item(),
            'exploration_noise': self.exploration_noise,
        }
    
    def save(self, directory):
        """Save model weights and config."""
        os.makedirs(directory, exist_ok=True)
        torch.save(self.actor.state_dict(), os.path.join(directory, 'actor.pth'))
        torch.save(self.critic_1.state_dict(), os.path.join(directory, 'critic_1.pth'))
        torch.save(self.critic_2.state_dict(), os.path.join(directory, 'critic_2.pth'))
        
        config = {
            'state_dim': self.state_dim,
            'action_dim': self.action_dim,
            'gamma': self.gamma,
            'tau': self.tau,
            'policy_noise': self.policy_noise,
            'batch_size': self.batch_size,
            'state_mean': self.state_mean.tolist(),
            'state_std': self.state_std.tolist(),
            'total_iterations': self.total_it,
        }
        with open(os.path.join(directory, 'config.json'), 'w') as f:
            json.dump(config, f, indent=2)
    
    def load(self, directory):
        """Load model weights and config."""
        self.actor.load_state_dict(
            torch.load(os.path.join(directory, 'actor.pth'), map_location=self.device, weights_only=True)
        )
        self.actor_target.load_state_dict(self.actor.state_dict())
        
        critic_1_path = os.path.join(directory, 'critic_1.pth')
        critic_2_path = os.path.join(directory, 'critic_2.pth')
        if os.path.exists(critic_1_path):
            self.critic_1.load_state_dict(
                torch.load(critic_1_path, map_location=self.device, weights_only=True)
            )
            self.critic_1_target.load_state_dict(self.critic_1.state_dict())
        if os.path.exists(critic_2_path):
            self.critic_2.load_state_dict(
                torch.load(critic_2_path, map_location=self.device, weights_only=True)
            )
            self.critic_2_target.load_state_dict(self.critic_2.state_dict())
        
        config_path = os.path.join(directory, 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.state_mean = np.array(config.get('state_mean', [0]*self.state_dim), dtype=np.float32)
            self.state_std = np.array(config.get('state_std', [1]*self.state_dim), dtype=np.float32)
            self.total_it = config.get('total_iterations', 0)
