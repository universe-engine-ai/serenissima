"""
Unified Criticality System - Fixes for Backend/Frontend Alignment
Bridges the gap between theoretical backend and empirical frontend approaches
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import requests
from collections import defaultdict
import pandas as pd
from scipy import stats
import networkx as nx
import sys
import os

# Add backend paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'il-testimone'))

from il_testimone.criticality_metrics import CriticalityMetrics


class BranchingRatioCalculator:
    """
    Implements branching ratio calculation matching frontend logic
    Missing piece in backend criticality system
    """
    
    def __init__(self):
        self.bin_sizes = [15, 30, 60, 120]  # minutes
        
    def calculate_message_branching(self, messages: List[Dict], 
                                  bin_size_minutes: int = 15) -> List[Dict]:
        """
        Calculate branching ratio for messages
        σ = descendants / ancestors in time bins
        """
        if not messages:
            return []
            
        # Sort messages by timestamp
        sorted_messages = sorted(messages, key=lambda m: m.get('timestamp', m.get('CreatedAt', '')))
        
        if not sorted_messages:
            return []
            
        # Get time range
        start_time = self._parse_timestamp(sorted_messages[0].get('timestamp', sorted_messages[0].get('CreatedAt')))
        end_time = self._parse_timestamp(sorted_messages[-1].get('timestamp', sorted_messages[-1].get('CreatedAt')))
        
        bin_size = timedelta(minutes=bin_size_minutes)
        current_time = start_time
        bins = []
        
        while current_time < end_time - bin_size:
            bin_end = current_time + bin_size
            next_bin_end = bin_end + bin_size
            
            # Count ancestors (messages in current bin)
            ancestors = sum(1 for msg in sorted_messages 
                          if current_time <= self._parse_timestamp(msg.get('timestamp', msg.get('CreatedAt'))) < bin_end)
            
            # Count descendants (replies in next bin)
            descendants = sum(1 for msg in sorted_messages 
                            if bin_end <= self._parse_timestamp(msg.get('timestamp', msg.get('CreatedAt'))) < next_bin_end
                            and msg.get('replyToId') is not None)
            
            sigma = descendants / ancestors if ancestors > 0 else None
            
            bins.append({
                'timestamp': current_time.isoformat(),
                'ancestors': ancestors,
                'descendants': descendants,
                'sigma': sigma,
                'time': current_time.strftime('%Y-%m-%d %H:%M')
            })
            
            current_time += bin_size
            
        return bins
    
    def calculate_economic_branching(self, transactions: List[Dict], 
                                   bin_size_minutes: int = 60) -> List[Dict]:
        """
        Calculate economic branching ratio
        How many transactions are triggered by each transaction
        """
        if not transactions:
            return []
            
        # Build transaction chains
        hourly_bins = defaultdict(lambda: {'triggered': 0, 'original': 0})
        
        for tx in transactions:
            tx_time = self._parse_timestamp(tx.get('timestamp', tx.get('AcceptedAt')))
            hour_key = tx_time.strftime('%Y-%m-%d %H:00')
            
            hourly_bins[hour_key]['original'] += 1
            
            # Find triggered transactions (simplified: by receiver in next hour)
            receiver = tx.get('to', tx.get('Seller'))
            next_hour = tx_time + timedelta(hours=1)
            
            triggered = sum(1 for next_tx in transactions
                          if next_tx.get('from', next_tx.get('Buyer')) == receiver
                          and tx_time < self._parse_timestamp(next_tx.get('timestamp', next_tx.get('AcceptedAt'))) <= next_hour)
            
            next_hour_key = next_hour.strftime('%Y-%m-%d %H:00')
            if next_hour_key in hourly_bins:
                hourly_bins[next_hour_key]['triggered'] += triggered
                
        # Convert to branching ratio format
        bins = []
        for hour, data in sorted(hourly_bins.items()):
            if data['original'] > 0:
                bins.append({
                    'time': hour,
                    'value': data['triggered'] / data['original'],
                    'label': 'σ_econ',
                    'ancestors': data['original'],
                    'descendants': data['triggered']
                })
                
        return bins
    
    def analyze_branching_stability(self, messages: List[Dict]) -> Dict[int, Dict]:
        """
        Analyze branching stability across multiple time scales
        """
        results = {}
        
        for bin_size in self.bin_sizes:
            branching_data = self.calculate_message_branching(messages, bin_size)
            sigmas = [b['sigma'] for b in branching_data if b['sigma'] is not None]
            
            if sigmas:
                mean = np.mean(sigmas)
                std = np.std(sigmas)
                
                results[bin_size] = {
                    'mean': mean,
                    'std': std,
                    'cv': std / mean if mean > 0 else 0,
                    'n_samples': len(sigmas),
                    'critical_fraction': sum(1 for s in sigmas if 0.8 <= s <= 1.2) / len(sigmas)
                }
                
        return results
    
    def detect_critical_transitions(self, branching_data: List[Dict], 
                                  threshold: float = 0.2) -> List[Dict]:
        """
        Detect transitions to/from criticality
        """
        transitions = []
        
        for i in range(1, len(branching_data)):
            prev_sigma = branching_data[i-1].get('sigma')
            curr_sigma = branching_data[i].get('sigma')
            
            if prev_sigma is None or curr_sigma is None:
                continue
                
            prev_critical = abs(prev_sigma - 1.0) < threshold
            curr_critical = abs(curr_sigma - 1.0) < threshold
            
            if not prev_critical and curr_critical:
                transitions.append({
                    'timestamp': branching_data[i]['timestamp'],
                    'transition': 'to_critical',
                    'sigma_before': prev_sigma,
                    'sigma_after': curr_sigma
                })
            elif prev_critical and not curr_critical:
                transitions.append({
                    'timestamp': branching_data[i]['timestamp'],
                    'transition': 'from_critical',
                    'sigma_before': prev_sigma,
                    'sigma_after': curr_sigma
                })
                
        return transitions
    
    def _parse_timestamp(self, timestamp: str) -> datetime:
        """Parse various timestamp formats"""
        if not timestamp:
            return datetime.now()
            
        # Try multiple formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp.replace('+00:00', ''), fmt.replace('%z', ''))
            except:
                continue
                
        # Fallback
        return datetime.now()


class CriticalityDataAdapter:
    """
    Adapts API data to backend criticality metric formats
    Bridges the data structure gap
    """
    
    def __init__(self, api_base_url: str = "https://serenissima.ai/api"):
        self.api_base_url = api_base_url
        
    def fetch_and_prepare_data(self) -> Dict:
        """
        Fetch data from API and prepare for backend analysis
        """
        try:
            # Fetch citizens
            citizens_resp = requests.get(f"{self.api_base_url}/citizens")
            citizens_data = citizens_resp.json()
            citizens = citizens_data.get('citizens', []) if citizens_data.get('success') else []
            
            # Fetch messages
            messages_resp = requests.get(f"{self.api_base_url}/messages")
            messages_data = messages_resp.json()
            messages = messages_data.get('messages', []) if messages_data.get('success') else []
            
            # Fetch contracts for transactions
            contracts_resp = requests.get(f"{self.api_base_url}/contracts")
            contracts_data = contracts_resp.json()
            contracts = contracts_data.get('contracts', []) if contracts_data.get('success') else []
            
            # Fetch relationships for trust network
            relationships_resp = requests.get(f"{self.api_base_url}/relationships")
            relationships_data = relationships_resp.json()
            relationships = relationships_data.get('relationships', []) if relationships_data.get('success') else []
            
            return self.prepare_backend_data(citizens, messages, contracts, relationships)
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return {}
    
    def prepare_backend_data(self, citizens: List[Dict], messages: List[Dict], 
                           contracts: List[Dict], relationships: List[Dict]) -> Dict:
        """
        Convert API data to backend format
        """
        # Prepare citizen states
        citizen_states = []
        for citizen in citizens:
            state = {
                'id': citizen.get('Username'),
                'wealth': float(citizen.get('Wealth', 0)),
                'social_class': citizen.get('SocialClass', 'Unknown'),
                'activity_type': citizen.get('CurrentActivity', 'idle'),
                'location': citizen.get('Position', '0,0')
            }
            citizen_states.append(state)
        
        # Extract transactions from contracts
        transactions = []
        for contract in contracts:
            if contract.get('Status') == 'completed' and contract.get('AcceptedAt'):
                transactions.append({
                    'id': contract.get('ContractId'),
                    'from': contract.get('Buyer'),
                    'to': contract.get('Seller'),
                    'amount': float(contract.get('Price', 0)),
                    'timestamp': contract.get('AcceptedAt'),
                    'type': contract.get('Type', 'trade')
                })
        
        # Build trust network edges
        trust_edges = []
        for rel in relationships:
            if float(rel.get('TrustScore', 0)) > 0:
                # Create bidirectional edges for undirected graph
                trust_edges.append((rel.get('Citizen1'), rel.get('Citizen2')))
        
        # Detect cascades from messages
        cascades = self._detect_message_cascades(messages)
        
        return {
            'citizens_data': citizen_states,
            'transactions': transactions,
            'trust_edges': trust_edges,
            'cascades': cascades,
            'messages': messages,
            'raw_citizens': citizens
        }
    
    def _detect_message_cascades(self, messages: List[Dict]) -> List[int]:
        """
        Simple cascade detection based on reply chains
        Returns list of cascade sizes
        """
        # Build reply graph
        reply_graph = defaultdict(list)
        root_messages = []
        
        for msg in messages:
            if msg.get('replyToId'):
                reply_graph[msg['replyToId']].append(msg['id'])
            else:
                root_messages.append(msg['id'])
        
        # Calculate cascade sizes
        cascade_sizes = []
        
        def get_cascade_size(msg_id: str) -> int:
            size = 1
            for reply_id in reply_graph.get(msg_id, []):
                size += get_cascade_size(reply_id)
            return size
        
        for root_id in root_messages:
            size = get_cascade_size(root_id)
            if size > 1:  # Only count actual cascades
                cascade_sizes.append(size)
                
        return cascade_sizes


class UnifiedCriticalityMetrics:
    """
    Combines backend physics-based metrics with frontend empirical metrics
    Provides comprehensive criticality analysis
    """
    
    def __init__(self):
        self.backend_metrics = CriticalityMetrics()
        self.branching_calculator = BranchingRatioCalculator()
        self.data_adapter = CriticalityDataAdapter()
        
    def calculate_all_metrics(self, data: Optional[Dict] = None) -> Dict:
        """
        Calculate all criticality metrics combining both approaches
        """
        # Fetch data if not provided
        if data is None:
            data = self.data_adapter.fetch_and_prepare_data()
            
        if not data:
            return {'error': 'No data available'}
            
        # Calculate backend metrics
        backend_results = self._calculate_backend_metrics(data)
        
        # Calculate frontend-style metrics
        frontend_results = self._calculate_frontend_metrics(data)
        
        # Combine and analyze
        combined_results = {
            **backend_results,
            **frontend_results,
            'unified_score': self._calculate_unified_score(backend_results, frontend_results),
            'phase_agreement': self._check_phase_agreement(backend_results, frontend_results),
            'data_quality': self._assess_data_quality(data)
        }
        
        return combined_results
    
    def _calculate_backend_metrics(self, data: Dict) -> Dict:
        """
        Calculate all backend physics-based metrics
        """
        results = {}
        
        # Build trust network
        if data.get('trust_edges'):
            trust_network = nx.Graph()
            trust_network.add_edges_from(data['trust_edges'])
            
            results['correlation_length'] = self.backend_metrics.correlation_length(trust_network)
            results['network_size'] = len(trust_network)
            results['percolation'] = self.backend_metrics.trust_network_percolation(trust_network)
        
        # Information entropy
        if data.get('citizens_data'):
            results['information_entropy'] = self.backend_metrics.information_entropy(data['citizens_data'])
        
        # Economic volatility
        if data.get('transactions'):
            results['economic_volatility'] = self.backend_metrics.economic_velocity_volatility(data['transactions'])
        
        # Avalanche distribution
        if data.get('cascades'):
            tau, r_squared = self.backend_metrics.avalanche_size_distribution(data['cascades'])
            results['avalanche_tau'] = tau
            results['avalanche_r2'] = r_squared
        
        # Lyapunov exponent (using wealth trajectory)
        if data.get('citizens_data') and len(data['citizens_data']) > 10:
            wealth_trajectory = np.array([c['wealth'] for c in data['citizens_data']])
            results['lyapunov'] = self.backend_metrics.lyapunov_exponent(wealth_trajectory)
        
        # Integrated backend score
        results['backend_criticality_score'] = self.backend_metrics.integrated_criticality_score(results)
        
        # Phase classification
        if results.get('backend_criticality_score', 0) > 0.7:
            results['backend_phase'] = 'critical'
        elif results.get('lyapunov', 0) > 0.1:
            results['backend_phase'] = 'chaotic'
        else:
            results['backend_phase'] = 'ordered'
            
        return results
    
    def _calculate_frontend_metrics(self, data: Dict) -> Dict:
        """
        Calculate all frontend empirical metrics
        """
        results = {}
        
        # Message branching ratio
        if data.get('messages'):
            message_branching = self.branching_calculator.calculate_message_branching(data['messages'])
            if message_branching:
                sigmas = [b['sigma'] for b in message_branching if b['sigma'] is not None]
                results['message_branching_current'] = message_branching[-1]['sigma'] if message_branching else None
                results['message_branching_mean'] = np.mean(sigmas) if sigmas else None
                results['message_branching_data'] = message_branching
        
        # Economic branching ratio
        if data.get('transactions'):
            economic_branching = self.branching_calculator.calculate_economic_branching(data['transactions'])
            if economic_branching:
                results['economic_branching_current'] = economic_branching[-1]['value'] if economic_branching else None
                results['economic_branching_mean'] = np.mean([b['value'] for b in economic_branching]) if economic_branching else None
                results['economic_branching_data'] = economic_branching
        
        # Wealth distribution analysis
        if data.get('raw_citizens'):
            wealth_values = [float(c.get('Wealth', 0)) for c in data['raw_citizens'] if float(c.get('Wealth', 0)) > 0]
            if wealth_values:
                results['gini_coefficient'] = self._calculate_gini(wealth_values)
                results['wealth_top_10_percent'] = self._calculate_wealth_share(wealth_values, 0.1)
                results['wealth_bottom_50_percent'] = self._calculate_wealth_share(wealth_values, 0.5, bottom=True)
        
        # Frontend phase classification
        msg_sigma = results.get('message_branching_current', 0)
        econ_sigma = results.get('economic_branching_current', 0)
        avg_sigma = (msg_sigma + econ_sigma) / 2 if msg_sigma and econ_sigma else msg_sigma or econ_sigma or 0
        
        if 0.95 <= avg_sigma <= 1.05:
            results['frontend_phase'] = 'critical'
        elif avg_sigma < 0.95:
            results['frontend_phase'] = 'frozen'
        else:
            results['frontend_phase'] = 'bubbling'
            
        return results
    
    def _calculate_unified_score(self, backend: Dict, frontend: Dict) -> float:
        """
        Calculate unified criticality score combining both approaches
        """
        scores = []
        
        # Backend score (if available)
        if 'backend_criticality_score' in backend:
            scores.append(backend['backend_criticality_score'])
        
        # Frontend branching score
        msg_sigma = frontend.get('message_branching_current')
        if msg_sigma is not None:
            # Score based on distance from criticality (σ = 1)
            branching_score = 1.0 - min(abs(msg_sigma - 1.0) / 0.5, 1.0)
            scores.append(branching_score)
        
        # Economic branching score
        econ_sigma = frontend.get('economic_branching_current')
        if econ_sigma is not None:
            econ_score = 1.0 - min(abs(econ_sigma - 1.0) / 0.5, 1.0)
            scores.append(econ_score)
        
        # Wealth distribution score (Gini around 0.6-0.8 is critical)
        gini = frontend.get('gini_coefficient')
        if gini is not None:
            if 0.6 <= gini <= 0.8:
                gini_score = 1.0
            else:
                gini_score = 1.0 - min(abs(gini - 0.7) / 0.3, 1.0)
            scores.append(gini_score)
        
        return np.mean(scores) if scores else 0.0
    
    def _check_phase_agreement(self, backend: Dict, frontend: Dict) -> Dict:
        """
        Check if backend and frontend agree on system phase
        """
        backend_phase = backend.get('backend_phase', 'unknown')
        frontend_phase = frontend.get('frontend_phase', 'unknown')
        
        # Map frontend phases to backend equivalents
        phase_mapping = {
            'frozen': 'ordered',
            'critical': 'critical',
            'bubbling': 'chaotic'
        }
        
        mapped_frontend = phase_mapping.get(frontend_phase, frontend_phase)
        
        return {
            'backend_phase': backend_phase,
            'frontend_phase': frontend_phase,
            'agreement': backend_phase == mapped_frontend,
            'confidence': self._calculate_phase_confidence(backend, frontend)
        }
    
    def _calculate_phase_confidence(self, backend: Dict, frontend: Dict) -> float:
        """
        Calculate confidence in phase determination
        """
        confidences = []
        
        # Backend confidence based on score
        if 'backend_criticality_score' in backend:
            confidences.append(backend['backend_criticality_score'])
        
        # Frontend confidence based on branching stability
        if 'message_branching_mean' in frontend and 'message_branching_current' in frontend:
            mean = frontend['message_branching_mean']
            current = frontend['message_branching_current']
            if mean and current:
                stability = 1.0 - min(abs(current - mean) / mean, 1.0)
                confidences.append(stability)
        
        return np.mean(confidences) if confidences else 0.0
    
    def _assess_data_quality(self, data: Dict) -> Dict:
        """
        Assess quality and completeness of data
        """
        quality_metrics = {
            'citizen_count': len(data.get('citizens_data', [])),
            'message_count': len(data.get('messages', [])),
            'transaction_count': len(data.get('transactions', [])),
            'trust_edge_count': len(data.get('trust_edges', [])),
            'cascade_count': len(data.get('cascades', [])),
            'data_completeness': 0.0
        }
        
        # Calculate completeness score
        expected_fields = ['citizens_data', 'messages', 'transactions', 'trust_edges', 'cascades']
        present_fields = sum(1 for field in expected_fields if data.get(field))
        quality_metrics['data_completeness'] = present_fields / len(expected_fields)
        
        return quality_metrics
    
    def _calculate_gini(self, values: List[float]) -> float:
        """
        Calculate Gini coefficient
        """
        sorted_values = sorted([v for v in values if v > 0])
        n = len(sorted_values)
        if n == 0:
            return 0.0
            
        total = sum(sorted_values)
        if total == 0:
            return 0.0
            
        gini_sum = 0
        for i, value in enumerate(sorted_values):
            gini_sum += (2 * (i + 1) - n - 1) * value
            
        return gini_sum / (n * total)
    
    def _calculate_wealth_share(self, values: List[float], percentile: float, bottom: bool = False) -> float:
        """
        Calculate wealth share of top/bottom percentile
        """
        sorted_values = sorted(values, reverse=not bottom)
        total = sum(values)
        if total == 0:
            return 0.0
            
        count = int(len(sorted_values) * percentile)
        share = sum(sorted_values[:count])
        
        return (share / total) * 100


# Example usage and testing
if __name__ == "__main__":
    print("Testing Unified Criticality System...")
    
    # Initialize unified metrics
    unified = UnifiedCriticalityMetrics()
    
    # Calculate all metrics
    results = unified.calculate_all_metrics()
    
    # Print summary
    print("\n=== Unified Criticality Analysis ===")
    print(f"Unified Score: {results.get('unified_score', 0):.3f}")
    print(f"\nPhase Agreement: {results.get('phase_agreement', {})}")
    print(f"\nBackend Metrics:")
    print(f"  - Criticality Score: {results.get('backend_criticality_score', 0):.3f}")
    print(f"  - Phase: {results.get('backend_phase', 'unknown')}")
    print(f"  - Lyapunov: {results.get('lyapunov', 0):.3f}")
    print(f"  - Correlation Length: {results.get('correlation_length', 0):.2f}")
    
    print(f"\nFrontend Metrics:")
    print(f"  - Message Branching σ: {results.get('message_branching_current', 0):.3f}")
    print(f"  - Economic Branching σ: {results.get('economic_branching_current', 0):.3f}")
    print(f"  - Gini Coefficient: {results.get('gini_coefficient', 0):.3f}")
    print(f"  - Phase: {results.get('frontend_phase', 'unknown')}")
    
    print(f"\nData Quality: {results.get('data_quality', {})}")