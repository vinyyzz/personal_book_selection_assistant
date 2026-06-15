# model.py - Sentence-BERT + Logistic Regression Model
import pickle
import os
import numpy as np
import sqlite3
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sentence_transformers import SentenceTransformer
import re

class BookRecommenderModel:
    def __init__(self):
        self.model = None
        self.embedder = None
        self.is_trained = False
        
        # Load Sentence-BERT (small, fast, free)
        print("Loading Sentence-BERT model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        print("Sentence-BERT loaded!")
        
        # Try to load existing classifier
        model_path = 'data/model.pkl'
        if os.path.exists(model_path):
            try:
                self.load_model(model_path)
                self.is_trained = True
                print("Loaded existing classifier")
            except:
                print("No existing classifier found")
    
    def encode_text(self, text):
        """Convert text to embedding vector using Sentence-BERT."""
        if not text or not isinstance(text, str):
            text = ""
        return self.embedder.encode(text, convert_to_tensor=False)
    
    def prepare_training_data(self):
        """Load ratings and book descriptions from SQLite."""
        db_path = 'data/bookrecommender.db'
        if not os.path.exists(db_path):
            return [], []
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.rating, b.description
            FROM ratings r
            LEFT JOIN books b ON LOWER(r.book_title) = LOWER(b.title)
            WHERE b.description IS NOT NULL AND b.description != ''
               AND b.description != 'No description available'
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        descriptions = []
        labels = []
        
        for row in rows:
            rating = row['rating']
            desc = row['description']
            
            if rating >= 4:
                label = 2  # BUY
            elif rating == 3:
                label = 1  # TRY
            else:
                label = 0  # SKIP
            
            if desc and len(desc) > 10:
                descriptions.append(desc)
                labels.append(label)
        
        return descriptions, labels
    
    def train(self, descriptions=None, ratings=None):
        """Train the model using Sentence-BERT embeddings."""
        
        if descriptions is None or ratings is None:
            descriptions, labels = self.prepare_training_data()
        else:
            labels = []
            for r in ratings:
                if r >= 4:
                    labels.append(2)
                elif r == 3:
                    labels.append(1)
                else:
                    labels.append(0)
        
        if len(descriptions) < 5:
            self.is_trained = False
            print(f"Need 5+ ratings, have {len(descriptions)}")
            return {'accuracy': 0, 'status': 'insufficient_data'}
        
        print(f"Encoding {len(descriptions)} books with Sentence-BERT...")
        
        # Convert all descriptions to embeddings
        X = np.array([self.encode_text(d) for d in descriptions])
        y = np.array(labels)
        
        print(f"Embeddings shape: {X.shape}")
        
        # Split data
        if len(descriptions) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
        else:
            X_train, y_train = X, y
        
        # Train Logistic Regression
        self.model = LogisticRegression(
            multi_class='multinomial',
            solver='lbfgs',
            max_iter=1000,
            C=1.0,
            class_weight='balanced'
        )
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        metrics = {'status': 'trained'}
        if len(descriptions) >= 10:
            y_pred = self.model.predict(X_test)
            metrics['accuracy'] = accuracy_score(y_test, y_pred)
            print(f"Model trained! Accuracy: {metrics['accuracy']:.1%}")
        else:
            metrics['accuracy'] = 0.5
            print("Model trained with limited data")
        
        # Save
        self.save_model('data/model.pkl')
        return metrics
    
    def predict(self, description):
        """Predict recommendation using Sentence-BERT embeddings."""
        
        if not self.is_trained or self.model is None:
            return self._fallback(description)
        
        try:
            # Encode with Sentence-BERT
            embedding = self.encode_text(description)
            X = embedding.reshape(1, -1)
            
            probs = self.model.predict_proba(X)[0]
            pred = np.argmax(probs)
            
            label_map = {0: "SKIP", 1: "TRY", 2: "BUY"}
            category = label_map[pred]
            confidence = probs[pred]
            
            prob_dict = {}
            for i, label in label_map.items():
                prob_dict[label] = round(float(probs[i]), 2) if i < len(probs) else 0.0
            
            return category, confidence, prob_dict
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return self._fallback(description)
    
    def _fallback(self, description):
        """Fallback when model not available."""
        desc_lower = description.lower() if description else ""
        
        positive = ['masterpiece', 'brilliant', 'excellent', 'amazing', 
                    'bestseller', 'award', 'classic', 'acclaimed']
        negative = ['boring', 'disappointing', 'slow', 'tedious']
        
        pos = sum(1 for w in positive if w in desc_lower)
        neg = sum(1 for w in negative if w in desc_lower)
        
        if pos > neg:
            return "BUY", 0.65, {"BUY": 0.65, "TRY": 0.25, "SKIP": 0.10}
        elif neg > pos:
            return "SKIP", 0.60, {"BUY": 0.15, "TRY": 0.25, "SKIP": 0.60}
        else:
            return "TRY", 0.45, {"BUY": 0.25, "TRY": 0.45, "SKIP": 0.30}
    
    def save_model(self, model_path):
        """Save classifier to disk."""
        os.makedirs('data', exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        print(f"Model saved to {model_path}")
    
    def load_model(self, model_path):
        """Load classifier from disk."""
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        self.is_trained = True
        print("Model loaded successfully")
    
    def retrain_from_ratings(self):
        """Retrain using all ratings in database."""
        descriptions, labels = self.prepare_training_data()
        if len(descriptions) >= 5:
            return self.train(descriptions, labels)
        return {'accuracy': 0, 'status': 'insufficient_data'}


# Global model instance
_model = None

def get_model():
    """Get or create the global model instance."""
    global _model
    if _model is None:
        _model = BookRecommenderModel()
    return _model


def predict_recommendation(description):
    """Get recommendation using Sentence-BERT + Logistic Regression."""
    model = get_model()
    return model.predict(description)