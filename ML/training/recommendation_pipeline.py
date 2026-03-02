"""
Product Categorization & Recommendation Neural Network Pipeline

This implements a Dual-Stream Neural Network:
1. Categorization Stream: Text embedding classification to categorize newly scraped products.
2. Recommendation Stream: RL Agent (DQN) that uses user state variables to recommend categories.

Supports loading REAL scraped data from --data-dir or falls back to synthetic data.
"""

import os
import time
import glob
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import pandas as pd
from datetime import datetime

# Setup directories
PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REC_DATA_DIR = os.path.join(os.path.dirname(PIPELINE_DIR), 'data', 'recommendation_data')
MODEL_DIR = os.path.join(os.path.dirname(PIPELINE_DIR), 'models', 'recommendation')
os.makedirs(REC_DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


class DualStreamRecModel(nn.Module):
    """
    Dual-stream NN:
    Stream A: Categorizes text (via simple character/word hashing embeddings for speed).
    Stream B: Recommends categories based on User State + Item State.
    """
    def __init__(self, vocab_size=10000, embed_dim=64, num_categories=500, user_state_dim=15):
        super(DualStreamRecModel, self).__init__()
        
        # Categorization Stream (Text -> Category)
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.text_fc1 = nn.Linear(embed_dim, 128)
        self.text_fc2 = nn.Linear(128, num_categories)
        self.dropout = nn.Dropout(0.2)
        
        # Recommendation Stream (DQN: User State -> Category Q-Values)
        self.rec_fc1 = nn.Linear(user_state_dim, 128)
        self.rec_fc2 = nn.Linear(128, 256)
        self.rec_out = nn.Linear(256, num_categories)
        
    def forward_categorization(self, text_indices):
        """Predicts the category [batch_size, num_categories] from text sequences [batch_size, seq_len]"""
        # Average pooling over sequence length
        embedded = self.embedding(text_indices)
        pooled = embedded.mean(dim=1)
        
        x = F.relu(self.text_fc1(pooled))
        x = self.dropout(x)
        category_logits = self.text_fc2(x)
        return category_logits
        
    def forward_recommendation(self, user_state):
        """DQN estimating Q-values for recommending each of the 500 categories"""
        x = F.relu(self.rec_fc1(user_state))
        x = F.relu(self.rec_fc2(x))
        q_values = self.rec_out(x)
        return q_values


class RecommendationTrainer:
    def __init__(self, model, data_dir=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model.to(self.device)
        self.cat_optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.rec_optimizer = optim.Adam(self.model.parameters(), lr=0.0005)
        self.cat_criterion = nn.CrossEntropyLoss()
        self.rec_criterion = nn.MSELoss()
        
        # Load real data if available
        self.real_data = None
        self.vocab = {}
        self.category_map = {}
        self.num_categories = 500
        
        self.data_dir = data_dir or REC_DATA_DIR
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
        print(f"Loaded {len(self.real_data)} real product rows from {len(files)} files.")
        
        # Build vocabulary from product names
        all_words = set()
        for name in self.real_data['product_name'].dropna():
            for word in str(name).lower().split():
                all_words.add(word)
        
        # Map words to indices (reserve 0 for padding)
        self.vocab = {w: i+1 for i, w in enumerate(list(all_words)[:9999])}
        
        # Map categories to indices
        categories = self.real_data['category'].dropna().unique().tolist()
        self.category_map = {c: i for i, c in enumerate(categories)}
        actual_cats = len(categories)
        
        # Rebuild model output layer if needed
        if actual_cats != self.num_categories and actual_cats > 0:
            self.num_categories = actual_cats
            vocab_size = len(self.vocab) + 1
            self.model = DualStreamRecModel(
                vocab_size=max(vocab_size, 10000), 
                embed_dim=64, 
                num_categories=actual_cats,
                user_state_dim=15
            ).to(self.device)
            self.cat_optimizer = optim.Adam(self.model.parameters(), lr=0.001)
            self.rec_optimizer = optim.Adam(self.model.parameters(), lr=0.0005)
            print(f"Model rebuilt with {actual_cats} categories and {vocab_size} vocab.")
    
    def _text_to_indices(self, text, seq_len=10):
        """Convert a product name to token indices."""
        words = str(text).lower().split()[:seq_len]
        indices = [self.vocab.get(w, 0) for w in words]
        # Pad to seq_len
        indices += [0] * (seq_len - len(indices))
        return indices
        
    def _real_text_batch(self, batch_size=64, seq_len=10):
        """Generate a training batch from real scraped data."""
        sample = self.real_data.sample(n=min(batch_size, len(self.real_data)), replace=True)
        
        texts = []
        targets = []
        for _, row in sample.iterrows():
            indices = self._text_to_indices(row.get('product_name', ''), seq_len)
            texts.append(indices)
            cat = row.get('category', 'General')
            targets.append(self.category_map.get(cat, 0))
        
        return (torch.tensor(texts, dtype=torch.long).to(self.device),
                torch.tensor(targets, dtype=torch.long).to(self.device))
    
    def _synthetic_text_batch(self, batch_size=64, seq_len=10, vocab_size=10000, num_categories=500):
        texts = torch.randint(1, vocab_size, (batch_size, seq_len)).to(self.device)
        targets = torch.randint(0, num_categories, (batch_size,)).to(self.device)
        return texts, targets
        
    def _synthetic_user_batch(self, batch_size=64, state_dim=15, num_categories=500):
        states = torch.rand(batch_size, state_dim).to(self.device)
        target_q = torch.rand(batch_size, num_categories).to(self.device)
        return states, target_q
        
    def train_step(self):
        self.model.train()
        
        # 1. Train Categorization Stream
        if self.real_data is not None and len(self.real_data) > 0:
            texts, targets = self._real_text_batch()
        else:
            texts, targets = self._synthetic_text_batch(num_categories=self.num_categories)
        
        self.cat_optimizer.zero_grad()
        cat_logits = self.model.forward_categorization(texts)
        cat_loss = self.cat_criterion(cat_logits, targets)
        cat_loss.backward()
        self.cat_optimizer.step()
        
        # 2. Train Recommendation Stream (DQN Update)
        states, target_q = self._synthetic_user_batch(num_categories=self.num_categories)
        self.rec_optimizer.zero_grad()
        pred_q = self.model.forward_recommendation(states)
        rec_loss = self.rec_criterion(pred_q, target_q)
        rec_loss.backward()
        self.rec_optimizer.step()
        
        return cat_loss.item(), rec_loss.item()
        
    def train(self, epochs=50):
        """Run standalone training loop."""
        data_source = "real scraped data" if self.real_data is not None else "synthetic data"
        print(f"Starting Recommendation Model Training on {self.device} ({data_source})...")
        print(f"Categories: {self.num_categories} | Vocab: {len(self.vocab)}")
        
        log_file = os.path.join(MODEL_DIR, 'rec_training_log.csv')
        with open(log_file, 'w') as f:
            f.write("epoch,cat_loss,rec_loss,timestamp\n")
            
        for epoch in range(1, epochs + 1):
            epoch_cat_loss = 0
            epoch_rec_loss = 0
            steps = 20
            
            for _ in range(steps):
                c_loss, r_loss = self.train_step()
                epoch_cat_loss += c_loss
                epoch_rec_loss += r_loss
                
            avg_cat_loss = epoch_cat_loss / steps
            avg_rec_loss = epoch_rec_loss / steps
            
            if epoch % 5 == 0 or epoch == 1:
                print(f"Epoch {epoch}/{epochs} | Cat Loss: {avg_cat_loss:.4f} | Rec Loss: {avg_rec_loss:.4f}")
            
            with open(log_file, 'a') as f:
                ts = datetime.now().isoformat()
                f.write(f"{epoch},{avg_cat_loss:.4f},{avg_rec_loss:.4f},{ts}\n")
                
        # Save final weights
        torch.save(self.model.state_dict(), os.path.join(MODEL_DIR, "dual_stream_rec.pth"))
        print(f"\nTraining Complete! Model saved. Final Cat Loss: {avg_cat_loss:.4f}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--data-dir", type=str, default="")
    args = parser.parse_args()
    
    data_dir = args.data_dir if args.data_dir else None
    model = DualStreamRecModel()
    trainer = RecommendationTrainer(model, data_dir=data_dir)
    trainer.train(epochs=args.epochs)
