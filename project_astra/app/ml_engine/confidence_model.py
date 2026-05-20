"""
ML Confidence Engine for Project Astra
Predicts trade success probability using XGBoost/LightGBM
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
import pandas as pd

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logging.warning("XGBoost not installed")

try:
    import lightgbm as lgb
    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False
    logging.warning("LightGBM not installed")

from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class MLConfidenceEngine:
    """
    Predicts trade success probability and expected value
    Uses ensemble of gradient boosting models
    """
    
    def __init__(self):
        self.model_xgb = None
        self.model_lgb = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Feature columns expected by model
        self.feature_columns = [
            'ema_9', 'ema_20', 'ema_50',
            'ema_gap', 'rsi_14', 'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_lower', 'bb_width', 'bb_position',
            'atr_14', 'atr_percent', 'vwap', 'vwap_distance',
            'volume_ratio', 'momentum_5', 'momentum_10',
            'adx', 'stoch_k', 'stoch_d', 'cci', 'willr',
            'vix', 'breadth', 'market_trend', 'relative_strength'
        ]
        
        # Default feature values (for missing data)
        self.default_features = {col: 0.0 for col in self.feature_columns}
        
        logger.info("ML Confidence Engine initialized")
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_type: str = 'xgboost',
        test_size: float = 0.2
    ) -> Dict[str, float]:
        """
        Train the ML model on historical data
        
        Args:
            X: Feature matrix
            y: Labels (1=success, 0=failure)
            model_type: 'xgboost' or 'lightgbm'
            test_size: Test split ratio
            
        Returns:
            Training metrics
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        metrics = {}
        
        if model_type == 'xgboost' and XGB_AVAILABLE:
            # Train XGBoost
            self.model_xgb = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            
            self.model_xgb.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model_xgb.predict(X_test_scaled)
            y_pred_proba = self.model_xgb.predict_proba(X_test_scaled)[:, 1]
            
            metrics = {
                'model': 'xgboost',
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'f1': f1_score(y_test, y_pred),
                'auc_roc': roc_auc_score(y_test, y_pred_proba)
            }
            
            self.is_trained = True
            logger.info(f"XGBoost trained: {metrics}")
            
        elif model_type == 'lightgbm' and LGB_AVAILABLE:
            # Train LightGBM
            self.model_lgb = lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )
            
            self.model_lgb.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model_lgb.predict(X_test_scaled)
            y_pred_proba = self.model_lgb.predict_proba(X_test_scaled)[:, 1]
            
            metrics = {
                'model': 'lightgbm',
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'f1': f1_score(y_test, y_pred),
                'auc_roc': roc_auc_score(y_test, y_pred_proba)
            }
            
            self.is_trained = True
            logger.info(f"LightGBM trained: {metrics}")
        
        else:
            logger.warning("No suitable ML library available for training")
            metrics = {'error': 'No ML library available'}
        
        return metrics
    
    def predict_probability(self, features: Dict[str, float]) -> Tuple[float, float]:
        """
        Predict probability of trade success
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            (probability, confidence_score)
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning default probability")
            return 0.5, 0.0
        
        # Prepare features
        feature_vector = []
        for col in self.feature_columns:
            value = features.get(col, self.default_features[col])
            feature_vector.append(value)
        
        X = np.array([feature_vector])
        X_scaled = self.scaler.transform(X)
        
        # Get prediction from best available model
        if self.model_xgb is not None:
            proba = self.model_xgb.predict_proba(X_scaled)[0, 1]
            confidence = abs(proba - 0.5) * 2  # Confidence based on distance from 0.5
        elif self.model_lgb is not None:
            proba = self.model_lgb.predict_proba(X_scaled)[0, 1]
            confidence = abs(proba - 0.5) * 2
        else:
            proba = 0.5
            confidence = 0.0
        
        return proba, confidence
    
    def calculate_expected_value(
        self,
        win_probability: float,
        avg_win: float,
        avg_loss: float,
        costs: float = 0.0
    ) -> float:
        """
        Calculate expected value of a trade
        
        Formula: EV = (P_win × AvgWin) - (P_loss × AvgLoss) - Costs
        
        Args:
            win_probability: Probability of winning (0-1)
            avg_win: Average profit on winning trades
            avg_loss: Average loss on losing trades (positive number)
            costs: Transaction costs (brokerage, slippage, taxes)
            
        Returns:
            Expected value per trade
        """
        loss_probability = 1 - win_probability
        
        ev = (win_probability * avg_win) - (loss_probability * avg_loss) - costs
        
        return ev
    
    def should_execute_trade(
        self,
        features: Dict[str, float],
        avg_win: float,
        avg_loss: float,
        min_probability: float = 0.55,
        min_ev: float = 0.0,
        costs: float = 0.0
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Decide whether to execute a trade based on ML prediction and EV
        
        Args:
            features: Feature dictionary
            avg_win: Expected average win
            avg_loss: Expected average loss
            min_probability: Minimum win probability threshold
            min_ev: Minimum expected value threshold
            costs: Transaction costs
            
        Returns:
            (should_execute, analysis_dict)
        """
        # Get ML prediction
        win_prob, confidence = self.predict_probability(features)
        
        # Calculate expected value
        ev = self.calculate_expected_value(win_prob, avg_win, avg_loss, costs)
        
        # Decision logic
        should_execute = (
            win_prob >= min_probability and
            ev >= min_ev and
            confidence > 0.3  # Minimum confidence threshold
        )
        
        analysis = {
            'win_probability': win_prob,
            'confidence': confidence,
            'expected_value': ev,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'costs': costs,
            'min_probability_threshold': min_probability,
            'min_ev_threshold': min_ev,
            'should_execute': should_execute,
            'reason': self._get_decision_reason(should_execute, win_prob, ev, confidence, min_probability, min_ev)
        }
        
        return should_execute, analysis
    
    def _get_decision_reason(
        self,
        execute: bool,
        prob: float,
        ev: float,
        conf: float,
        min_prob: float,
        min_ev: float
    ) -> str:
        """Get human-readable reason for decision"""
        if execute:
            return "All criteria met: Probability, EV, and Confidence thresholds satisfied"
        
        reasons = []
        if prob < min_prob:
            reasons.append(f"Win probability ({prob:.2%}) below threshold ({min_prob:.2%})")
        if ev < min_ev:
            reasons.append(f"Expected value ({ev:.2f}) below minimum ({min_ev:.2f})")
        if conf < 0.3:
            reasons.append(f"Model confidence ({conf:.2%}) too low")
        
        return "; ".join(reasons) if reasons else "Unknown"
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from trained model"""
        if not self.is_trained:
            return None
        
        if self.model_xgb is not None:
            importance = self.model_xgb.feature_importances_
            return dict(zip(self.feature_columns, importance))
        elif self.model_lgb is not None:
            importance = self.model_lgb.feature_importances_
            return dict(zip(self.feature_columns, importance))
        
        return None


# Singleton instance
ml_confidence_engine = MLConfidenceEngine()


def get_ml_confidence_engine() -> MLConfidenceEngine:
    """Get ML confidence engine instance"""
    return ml_confidence_engine
