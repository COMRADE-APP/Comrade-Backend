"""
Training script for the Comrade RL Pricing Model.

Usage:
    python -m ML.training.train_pricing
    python -m ML.training.train_pricing --episodes 1000 --eval-interval 100
"""

import os
import sys
import csv
import time
import argparse
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ML.training.pricing_env import ComradePricingEnv
from ML.training.agent import ComradeTD3Agent


def evaluate_agent(agent, env, n_episodes=10):
    """Evaluate agent without exploration noise."""
    rewards = []
    tier_upgrades = 0
    avg_prices = []
    avg_savings = []
    
    for _ in range(n_episodes):
        state, _ = env.reset()
        episode_reward = 0
        initial_tier = int(state[6])
        prices = []
        
        done = False
        while not done:
            action = agent.select_action(state, evaluate=True)
            state, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            prices.append(info['price'])
            done = terminated or truncated
        
        rewards.append(episode_reward)
        if int(state[6]) > initial_tier:
            tier_upgrades += 1
        avg_prices.append(np.mean(prices))
        avg_savings.append(info['cumulative_savings'])
    
    return {
        'mean_reward': np.mean(rewards),
        'std_reward': np.std(rewards),
        'tier_upgrade_rate': tier_upgrades / n_episodes,
        'avg_price': np.mean(avg_prices),
        'avg_cumulative_savings': np.mean(avg_savings),
    }


def train(args):
    """Main training loop."""
    print("=" * 60)
    print("  Comrade RL Pricing Model - Training")
    print("=" * 60)
    
    # Setup
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             'models', 'pricing')
    os.makedirs(model_dir, exist_ok=True)
    
    log_path = os.path.join(model_dir, 'training_log.csv')
    
    env = ComradePricingEnv(max_steps=args.max_steps)
    eval_env = ComradePricingEnv(max_steps=args.max_steps)
    agent = ComradeTD3Agent(state_dim=8, action_dim=3)
    
    print(f"\nDevice: {agent.device}")
    print(f"Episodes: {args.episodes}")
    print(f"Max steps/episode: {args.max_steps}")
    print(f"Eval interval: {args.eval_interval}")
    print(f"Model save dir: {model_dir}")
    print()
    
    best_reward = -float('inf')
    
    # CSV logging
    with open(log_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'episode', 'episode_reward', 'critic_loss', 'actor_loss', 'q_value',
            'exploration_noise', 'eval_mean_reward', 'eval_tier_upgrade_rate',
            'eval_avg_price', 'eval_avg_savings', 'time_elapsed'
        ])
    
    start_time = time.time()
    
    for episode in range(1, args.episodes + 1):
        state, _ = env.reset()
        agent.ou_noise.reset()
        episode_reward = 0
        episode_losses = {'critic_loss': [], 'actor_loss': [], 'q_value': []}
        
        done = False
        while not done:
            # Select action
            action = agent.select_action(state)
            
            # Step environment
            next_state, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            # Store and train
            agent.store_transition(state, action, reward, next_state, float(done))
            metrics = agent.train_step()
            
            # Track losses
            if metrics:
                for k in ['critic_loss', 'actor_loss', 'q_value']:
                    if metrics.get(k) is not None:
                        episode_losses[k].append(metrics[k])
            
            episode_reward += reward
            state = next_state
        
        # Logging
        avg_critic_loss = np.mean(episode_losses['critic_loss']) if episode_losses['critic_loss'] else 0
        avg_actor_loss = np.mean(episode_losses['actor_loss']) if episode_losses['actor_loss'] else 0
        avg_q = np.mean(episode_losses['q_value']) if episode_losses['q_value'] else 0
        
        eval_metrics = {}
        
        # Periodic evaluation
        if episode % args.eval_interval == 0:
            eval_metrics = evaluate_agent(agent, eval_env, n_episodes=10)
            elapsed = time.time() - start_time
            
            print(f"Ep {episode:4d}/{args.episodes} | "
                  f"Train R: {episode_reward:7.2f} | "
                  f"Eval R: {eval_metrics['mean_reward']:7.2f}±{eval_metrics['std_reward']:.2f} | "
                  f"Price: ${eval_metrics['avg_price']:.1f} | "
                  f"TierUP: {eval_metrics['tier_upgrade_rate']:.0%} | "
                  f"eps: {agent.exploration_noise:.3f} | "
                  f"Time: {elapsed:.0f}s")
            
            # Save best model
            if eval_metrics['mean_reward'] > best_reward:
                best_reward = eval_metrics['mean_reward']
                agent.save(model_dir)
                print(f"  -> New best model saved! (reward: {best_reward:.2f})")
        
        elif episode % 50 == 0:
            elapsed = time.time() - start_time
            print(f"Ep {episode:4d}/{args.episodes} | "
                  f"Train R: {episode_reward:7.2f} | "
                  f"C_loss: {avg_critic_loss:.4f} | "
                  f"eps: {agent.exploration_noise:.3f} | "
                  f"Buffer: {len(agent.replay_buffer)} | "
                  f"Time: {elapsed:.0f}s")
        
        # CSV log
        with open(log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                episode, episode_reward, avg_critic_loss, avg_actor_loss, avg_q,
                agent.exploration_noise,
                eval_metrics.get('mean_reward', ''),
                eval_metrics.get('tier_upgrade_rate', ''),
                eval_metrics.get('avg_price', ''),
                eval_metrics.get('avg_cumulative_savings', ''),
                time.time() - start_time,
            ])
    
    # Final save
    agent.save(model_dir)
    
    # Final evaluation
    final_eval = evaluate_agent(agent, eval_env, n_episodes=20)
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print("  Training Complete")
    print("=" * 60)
    print(f"  Total time:           {elapsed:.1f}s")
    print(f"  Best eval reward:     {best_reward:.2f}")
    print(f"  Final eval reward:    {final_eval['mean_reward']:.2f} ± {final_eval['std_reward']:.2f}")
    print(f"  Avg price:            ${final_eval['avg_price']:.2f}")
    print(f"  Tier upgrade rate:    {final_eval['tier_upgrade_rate']:.0%}")
    print(f"  Avg savings:          ${final_eval['avg_cumulative_savings']:.2f}")
    print(f"  Model saved to:       {model_dir}")
    print()
    
    return agent


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train Comrade RL Pricing Model')
    parser.add_argument('--episodes', type=int, default=500, help='Number of training episodes')
    parser.add_argument('--max-steps', type=int, default=90, help='Max steps per episode (days)')
    parser.add_argument('--eval-interval', type=int, default=50, help='Evaluate every N episodes')
    parser.add_argument('--resume', action='store_true', help='Resume training from existing weights')
    parser.add_argument('--data-file', type=str, default='', help='Path to actual scraped data chunk')
    args = parser.parse_args()
    
    train(args)
