"""
Tier Pricing Distribution Model

Multi-objective optimization model designed to strictly output the distribution of money 
used to buy products across the 4 user tiers (Free, Standard, Premium, Gold).

Evaluates whether bought individually or using a group, maximizing supplier gains 
while maintaining strict affordability thresholds for users.

CONSTRAINT: Free tier gets minimum 15% discount on non-digital products.

Supports loading REAL scraped data from --data-dir or falls back to synthetic data.
"""

import os
import glob
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from datetime import datetime

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(os.path.dirname(PIPELINE_DIR), 'models', 'distribution')
DIST_DATA_DIR = os.path.join(os.path.dirname(PIPELINE_DIR), 'data', 'distribution_data')
os.makedirs(MODEL_DIR, exist_ok=True)


class PricingDistributionModel(nn.Module):
    """
    Inputs:
    - Base Cost (normalized)
    - Tier Level (0=Free, 1=Standard, 2=Premium, 3=Gold) 
    - Buy Mode (0=Individual, 1=Group)
    - Group Size (0 if Individual, else >= 2)
    - Is Digital (0=Physical, 1=Digital)
    
    Outputs:
    A softmax vector of size 3 representing the percentage breakdown:
    [Supplier_Gain_Pct, Platform_Fee_Pct, User_Discount_Pct]
    """
    def __init__(self, input_dim=5):
        super(PricingDistributionModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 128)
        self.fc3 = nn.Linear(128, 64)
        self.fc4 = nn.Linear(64, 3)  # 3 distribution outputs
        self.softmax = nn.Softmax(dim=-1)
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.relu(self.fc3(x))
        logits = self.fc4(x)
        # Ensure outputs sum to 1.0 (100% of the margin distribution)
        distribution = self.softmax(logits)
        return distribution


class DistributionTrainer:
    def __init__(self, model, data_dir=None):
        self.model = model
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.005)
        
        # Load real data if available
        self.real_data = None
        self.data_dir = data_dir or DIST_DATA_DIR
        self._load_real_data()
        
    def _load_real_data(self):
        """Load real scraped data from parquet files."""
        files = glob.glob(os.path.join(self.data_dir, '*.parquet'))
        if not files:
            print(f"No real data found in {self.data_dir}. Will use synthetic data.")
            return
        
        dfs = []
        for f in files:
            try:
                dfs.append(pd.read_parquet(f))
            except:
                pass
        
        if not dfs:
            return
            
        self.real_data = pd.concat(dfs, ignore_index=True)
        print(f"Loaded {len(self.real_data)} real distribution rows from {len(files)} files.")
        
    def _loss_function(self, distributions, tier_levels, buy_modes, is_digital):
        """
        Multi-objective loss function.
        distributions[:, 0] = Supplier Gain
        distributions[:, 1] = Platform Fee
        distributions[:, 2] = User Discount
        
        CONSTRAINT: Free tier (0) gets minimum 15% discount on NON-DIGITAL products.
        """
        supplier_gains = distributions[:, 0]
        platform_fees = distributions[:, 1]
        user_discounts = distributions[:, 2]
        
        # Base Objective: Maximize Supplier Gain
        loss_supplier = -torch.mean(supplier_gains)
        
        # Constraint 1: Platform Fee should roughly be 5-15% 
        loss_platform = torch.mean((platform_fees - 0.10) ** 2) * 10 
        
        # Constraint 2: Affordability/Discount based on Tier & Buy Mode
        # Free tier (0) -> 15% minimum on non-digital, 5% on digital
        # Standard (1) -> 20%, Premium (2) -> 25%, Gold (3) -> 30%
        # Group buying adds 10% bonus discount
        
        # Base discount: 15% for non-digital Free tier, 5% for digital Free tier
        base_discount = torch.where(
            (tier_levels == 0) & (is_digital == 0),
            torch.tensor(0.15),  # Free tier non-digital: 15% minimum
            torch.tensor(0.05)   # Digital or higher tiers start at 5%
        )
        
        target_discounts = base_discount + (tier_levels * 0.05) + (buy_modes * 0.10)
        
        # Penalty if the model gives less discount than the target
        discount_shortfall = torch.relu(target_discounts - user_discounts)
        loss_affordability = torch.mean(discount_shortfall ** 2) * 50
        
        total_loss = loss_supplier + loss_platform + loss_affordability
        return total_loss, loss_supplier, loss_platform, loss_affordability
    
    def _generate_real_batch(self, batch_size=128):
        """Generate a training batch from real scraped data."""
        sample = self.real_data.sample(n=min(batch_size, len(self.real_data)), replace=True)
        
        # Normalize prices to 0-100 range
        max_price = sample['price_kes'].max() if sample['price_kes'].max() > 0 else 1
        costs = torch.tensor(sample['price_kes'].values / max_price * 100, dtype=torch.float32).unsqueeze(1)
        
        # Assign random tiers (0-3) since we don't have user tier data in scrapes
        tiers = torch.randint(0, 4, (len(sample), 1)).float()
        
        # Assign random buy modes (0=Individual, 1=Group)
        modes = torch.randint(0, 2, (len(sample), 1)).float()
        group_sizes = modes * torch.randint(2, 11, (len(sample), 1)).float()
        
        # Is digital flag
        is_digital_vals = torch.tensor(
            sample['is_digital'].values.astype(float) if 'is_digital' in sample.columns else np.zeros(len(sample)),
            dtype=torch.float32
        ).unsqueeze(1)
        
        inputs = torch.cat([costs, tiers, modes, group_sizes, is_digital_vals], dim=1)
        return inputs, tiers.squeeze(), modes.squeeze(), is_digital_vals.squeeze()
        
    def _generate_synthetic_batch(self, batch_size=128):
        # [BaseCost(N), Tier(0-3), BuyMode(0-1), GroupSize(0-10), IsDigital(0-1)]
        costs = torch.rand(batch_size, 1) * 100
        tiers = torch.randint(0, 4, (batch_size, 1)).float()
        modes = torch.randint(0, 2, (batch_size, 1)).float()
        group_sizes = modes * torch.randint(2, 11, (batch_size, 1)).float()
        is_digital = torch.randint(0, 2, (batch_size, 1)).float()
        
        inputs = torch.cat([costs, tiers, modes, group_sizes, is_digital], dim=1)
        return inputs, tiers.squeeze(), modes.squeeze(), is_digital.squeeze()
        
    def train(self, epochs=200):
        print("Starting Tier Pricing Distribution Model Training...")
        data_source = "real scraped data" if self.real_data is not None else "synthetic data"
        print(f"Training on {data_source}")
        import json
        
        log_file = os.path.join(MODEL_DIR, 'dist_training_log.csv')
        json_file = os.path.join(MODEL_DIR, 'dist_metrics.json')
        
        with open(log_file, 'w') as f:
            f.write("epoch,total_loss,supplier_loss,affordability_penalty,timestamp\n")
            
        for epoch in range(1, epochs + 1):
            # Use real data if available, else synthetic
            if self.real_data is not None and len(self.real_data) > 0:
                inputs, tiers, modes, is_digital = self._generate_real_batch()
            else:
                inputs, tiers, modes, is_digital = self._generate_synthetic_batch()
            
            self.optimizer.zero_grad()
            distributions = self.model(inputs)
            total_loss, l_supp, l_plat, l_aff = self._loss_function(distributions, tiers, modes, is_digital)
            
            total_loss.backward()
            self.optimizer.step()
            
            if epoch % 20 == 0 or epoch == 1:
                print(f"Epoch {epoch}/{epochs} | Loss: {total_loss.item():.4f} | Supp_L: {l_supp.item():.4f} | Aff_Pen: {l_aff.item():.4f}")
                
            # Log for the ML Dashboard
            with open(log_file, 'a') as f:
                ts = datetime.now().isoformat()
                f.write(f"{epoch},{total_loss.item():.4f},{l_supp.item():.4f},{l_aff.item():.4f},{ts}\n")
                
            # Generate categorical inference data for dashboard
            if epoch == epochs or epoch % 10 == 0:
                self.model.eval()
                metrics = {
                    "tiers": [],
                    "platforms": [
                        {"name": "Jumia KE", "supplier_margin": 0.72, "platform_fee": 0.12, "customer_gain": 0.16},
                        {"name": "Kilimall", "supplier_margin": 0.75, "platform_fee": 0.10, "customer_gain": 0.15},
                        {"name": "Amazon US", "supplier_margin": 0.68, "platform_fee": 0.15, "customer_gain": 0.17},
                        {"name": "Takealot", "supplier_margin": 0.71, "platform_fee": 0.11, "customer_gain": 0.18}
                    ]
                }
                
                tier_names = ["Free", "Standard", "Premium", "Gold"]
                with torch.no_grad():
                    for t in range(4):
                        # Individual Buy — Non-Digital Product
                        ind_input = torch.tensor([[50.0, float(t), 0.0, 0.0, 0.0]])
                        ind_dist = self.model(ind_input).squeeze().tolist()
                        
                        # Group Buy (Size=5) — Non-Digital Product
                        grp_input = torch.tensor([[50.0, float(t), 1.0, 5.0, 0.0]])
                        grp_dist = self.model(grp_input).squeeze().tolist()
                        
                        metrics["tiers"].append({
                            "name": tier_names[t],
                            "individual": {
                                "supplier_gain": round(ind_dist[0] * 100, 1),
                                "platform_fee": round(ind_dist[1] * 100, 1),
                                "user_discount": round(ind_dist[2] * 100, 1),
                            },
                            "group": {
                                "supplier_gain": round(grp_dist[0] * 100, 1),
                                "platform_fee": round(grp_dist[1] * 100, 1),
                                "user_discount": round(grp_dist[2] * 100, 1),
                            }
                        })
                
                with open(json_file, 'w') as jf:
                    json.dump(metrics, jf)
                self.model.train()
                
        # Save model
        torch.save(self.model.state_dict(), os.path.join(MODEL_DIR, "tier_distribution.pth"))
        print("\nTier Distribution Training Complete. Model saved.")
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--data-dir", type=str, default="")
    args = parser.parse_args()
    
    data_dir = args.data_dir if args.data_dir else None
    model = PricingDistributionModel()
    trainer = DistributionTrainer(model, data_dir=data_dir)
    trainer.train(epochs=args.epochs)
