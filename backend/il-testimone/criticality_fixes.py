"""
Criticality Fixes - Alignment between Backend and Frontend Systems
Implements missing metrics and data adapters for system convergence
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd


class BranchingRatioCalculator:
    """Calculate branching ratio matching frontend implementation"""
    
    @staticmethod
    def calculate_branching_ratio(events: List[Dict], 
                                 bin_size_minutes: int = 15,
                                 event_type: str = 'message') -> List[Dict]:
        """
        Calculate branching ratio σ = descendants / ancestors
        
        Args:
            events: List of events (messages or transactions)
            bin_size_minutes: Time bin size in minutes
            event_type: 'message' or 'transaction'
            
        Returns:
            List of branching data points with timestamp, ancestors, descendants, sigma
        """
        if not events:
            return []
            
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda x: x.get('timestamp', ''))
        
        # Convert timestamps
        timestamps = []
        for event in sorted_events:
            if isinstance(event['timestamp'], str):
                timestamps.append(datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')))
            else:
                timestamps.append(event['timestamp'])
        
        if not timestamps:
            return []
            
        start_time = timestamps[0]
        end_time = timestamps[-1]
        bin_size = timedelta(minutes=bin_size_minutes)
        
        # Create time bins
        branching_data = []
        current_time = start_time
        
        while current_time < end_time:
            bin_end = current_time + bin_size
            next_bin_end = bin_end + bin_size
            
            # Count ancestors (events in current bin)
            ancestors = sum(1 for t in timestamps if current_time <= t < bin_end)
            
            # Count descendants based on event type
            if event_type == 'message':
                # For messages: count replies in next bin
                descendants = 0
                for i, event in enumerate(sorted_events):
                    if current_time <= timestamps[i] < bin_end:
                        # Check for replies in next bin
                        for j, reply in enumerate(sorted_events):
                            if (bin_end <= timestamps[j] < next_bin_end and 
                                reply.get('replyToId') == event.get('id')):
                                descendants += 1
                                
            else:  # transaction
                # For transactions: count triggered transactions
                descendants = 0
                for i, event in enumerate(sorted_events):
                    if current_time <= timestamps[i] < bin_end:
                        # Count transactions by receiver in next bin
                        receiver = event.get('to', event.get('receiver'))
                        for j, next_tx in enumerate(sorted_events):
                            if (bin_end <= timestamps[j] < next_bin_end and 
                                next_tx.get('from', next_tx.get('sender')) == receiver):
                                descendants += 1
            
            # Calculate sigma
            sigma = descendants / ancestors if ancestors > 0 else None
            
            branching_data.append({
                'timestamp': current_time.isoformat(),
                'ancestors': ancestors,
                'descendants': descendants,
                'sigma': sigma
            })
            
            current_time = bin_end
            
        return branching_data
    
    @staticmethod
    def calculate_average_branching_ratio(branching_data: List[Dict]) -> Dict:
        """Calculate statistics for branching ratio"""
        sigmas = [d['sigma'] for d in branching_data if d['sigma'] is not None]
        
        if not sigmas:
            return {'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0}
            
        return {
            'mean': np.mean(sigmas),
            'std': np.std(sigmas),
            'min': np.min(sigmas),
            'max': np.max(sigmas),
            'critical_fraction': sum(1 for s in sigmas if 0.95 <= s <= 1.05) / len(sigmas)
        }


class CriticalityDataAdapter:
    """Convert between API responses and backend expected formats"""
    
    @staticmethod
    def messages_to_events(messages: List[Dict]) -> List[Dict]:
        """Convert API message format to generic event format"""
        events = []
        for msg in messages:
            events.append({
                'id': msg.get('messageId', msg.get('id')),
                'timestamp': msg.get('createdAt', msg.get('timestamp')),
                'sender': msg.get('sender'),
                'receiver': msg.get('receiver', msg.get('to')),
                'content': msg.get('content'),
                'replyToId': msg.get('replyToId'),
                'type': 'message'
            })
        return events
    
    @staticmethod
    def contracts_to_transactions(contracts: List[Dict]) -> List[Dict]:
        """Extract transactions from contract data"""
        transactions = []
        for contract in contracts:
            if contract.get('Status') == 'completed' and contract.get('AcceptedAt'):
                transactions.append({
                    'id': contract.get('ContractId'),
                    'timestamp': contract.get('AcceptedAt'),
                    'from': contract.get('Buyer'),
                    'to': contract.get('Seller'),
                    'sender': contract.get('Buyer'),  # Alias
                    'receiver': contract.get('Seller'),  # Alias
                    'amount': float(contract.get('Price', 0)),
                    'type': contract.get('Type', 'trade'),
                    'resourceType': contract.get('ResourceType')
                })
        return sorted(transactions, key=lambda x: x['timestamp'])
    
    @staticmethod
    def citizens_to_nodes(citizens: List[Dict]) -> List[Dict]:
        """Convert citizen data to node format for network analysis"""
        nodes = []
        for citizen in citizens:
            nodes.append({
                'id': citizen.get('Username'),
                'wealth': float(citizen.get('Wealth', 0)),
                'social_class': citizen.get('SocialClass'),
                'activity_type': citizen.get('CurrentActivity'),
                'location': citizen.get('Location'),
                'is_ai': citizen.get('IsAI', False)
            })
        return nodes
    
    @staticmethod
    def extract_trust_edges(relationships: List[Dict]) -> List[Tuple[str, str]]:
        """Extract trust network edges from relationship data"""
        edges = []
        for rel in relationships:
            if rel.get('RelationshipType') == 'trust' and rel.get('Value', 0) > 0:
                edges.append((rel.get('FromCitizen'), rel.get('ToCitizen')))
        return edges
    
    @staticmethod
    def detect_cascades(events: List[Dict], time_window_minutes: int = 60) -> List[int]:
        """Detect cascades in events and return cascade sizes"""
        if not events:
            return []
            
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda x: x.get('timestamp', ''))
        event_map = {e['id']: e for e in sorted_events if e.get('id')}
        
        # Build reply chains
        cascades = []
        processed = set()
        
        for event in sorted_events:
            if event.get('id') in processed:
                continue
                
            # Build cascade starting from this event
            cascade = [event]
            cascade_ids = {event.get('id')}
            processed.add(event.get('id'))
            
            # Find all descendants within time window
            start_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            window_end = start_time + timedelta(minutes=time_window_minutes)
            
            # BFS to find all connected events
            queue = [event]
            while queue:
                current = queue.pop(0)
                
                # Find replies to current event
                for other in sorted_events:
                    if (other.get('replyToId') == current.get('id') and 
                        other.get('id') not in cascade_ids):
                        
                        other_time = datetime.fromisoformat(other['timestamp'].replace('Z', '+00:00'))
                        if other_time <= window_end:
                            cascade.append(other)
                            cascade_ids.add(other.get('id'))
                            processed.add(other.get('id'))
                            queue.append(other)
            
            if len(cascade) > 1:  # Only count cascades with responses
                cascades.append(len(cascade))
                
        return cascades


class UnifiedCriticalityMetrics:
    """Unified metrics incorporating both backend and frontend approaches"""
    
    def __init__(self):
        self.backend_metrics = None  # Original CriticalityMetrics instance
        self.branching_calc = BranchingRatioCalculator()
        self.adapter = CriticalityDataAdapter()
        
    def calculate_unified_metrics(self, 
                                 messages: List[Dict],
                                 contracts: List[Dict],
                                 citizens: List[Dict],
                                 relationships: List[Dict]) -> Dict:
        """
        Calculate all criticality metrics from API data
        
        Returns unified metric dictionary combining backend and frontend approaches
        """
        # Convert API data to backend formats
        message_events = self.adapter.messages_to_events(messages)
        transactions = self.adapter.contracts_to_transactions(contracts)
        citizen_nodes = self.adapter.citizens_to_nodes(citizens)
        trust_edges = self.adapter.extract_trust_edges(relationships)
        
        # Detect cascades
        message_cascades = self.adapter.detect_cascades(message_events, time_window_minutes=60)
        transaction_cascades = self.adapter.detect_cascades(transactions, time_window_minutes=240)
        
        # Calculate branching ratios
        message_branching = self.branching_calc.calculate_branching_ratio(
            message_events, bin_size_minutes=15, event_type='message'
        )
        transaction_branching = self.branching_calc.calculate_branching_ratio(
            transactions, bin_size_minutes=60, event_type='transaction'
        )
        
        # Calculate branching statistics
        message_branching_stats = self.branching_calc.calculate_average_branching_ratio(message_branching)
        transaction_branching_stats = self.branching_calc.calculate_average_branching_ratio(transaction_branching)
        
        # Calculate economic metrics
        gini = self._calculate_gini_coefficient([c['wealth'] for c in citizen_nodes])
        wealth_distribution = self._fit_power_law([c['wealth'] for c in citizen_nodes if c['wealth'] > 0])
        
        # Compile unified metrics
        return {
            # Frontend-style metrics
            'message_branching': {
                'current': message_branching[-1]['sigma'] if message_branching else None,
                'average': message_branching_stats['mean'],
                'std': message_branching_stats['std'],
                'critical_fraction': message_branching_stats['critical_fraction'],
                'time_series': message_branching
            },
            'economic_branching': {
                'current': transaction_branching[-1]['sigma'] if transaction_branching else None,
                'average': transaction_branching_stats['mean'],
                'std': transaction_branching_stats['std'],
                'time_series': transaction_branching
            },
            'cascades': {
                'message_cascades': {
                    'count': len(message_cascades),
                    'sizes': message_cascades,
                    'average_size': np.mean(message_cascades) if message_cascades else 0,
                    'max_size': max(message_cascades) if message_cascades else 0,
                    'power_law': self._fit_power_law(message_cascades)
                },
                'transaction_cascades': {
                    'count': len(transaction_cascades),
                    'sizes': transaction_cascades,
                    'average_size': np.mean(transaction_cascades) if transaction_cascades else 0,
                    'max_size': max(transaction_cascades) if transaction_cascades else 0,
                    'power_law': self._fit_power_law(transaction_cascades)
                }
            },
            'economic': {
                'gini_coefficient': gini,
                'wealth_distribution': wealth_distribution,
                'active_traders': len(set([t['from'] for t in transactions] + 
                                        [t['to'] for t in transactions])),
                'total_transactions': len(transactions),
                'money_velocity': self._calculate_money_velocity(transactions, citizens)
            },
            'network': {
                'trust_edges': len(trust_edges),
                'trust_nodes': len(set([e[0] for e in trust_edges] + [e[1] for e in trust_edges])),
                'density': len(trust_edges) / (len(citizens) * (len(citizens) - 1)) if len(citizens) > 1 else 0
            },
            # Phase determination
            'phase': self._determine_phase(message_branching_stats, transaction_branching_stats),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _calculate_gini_coefficient(self, values: List[float]) -> float:
        """Calculate Gini coefficient for wealth distribution"""
        sorted_values = sorted([v for v in values if v > 0])
        n = len(sorted_values)
        if n == 0:
            return 0.0
            
        cumsum = np.cumsum(sorted_values)
        return (2 * np.sum((np.arange(n) + 1) * sorted_values)) / (n * cumsum[-1]) - (n + 1) / n
    
    def _fit_power_law(self, values: List[float]) -> Dict:
        """Fit power law to value distribution"""
        if len(values) < 10:
            return {'tau': 0.0, 'r_squared': 0.0, 'p_value': 1.0}
            
        # Create histogram
        unique_values = sorted(set(values))
        counts = [values.count(v) for v in unique_values]
        
        # Log-log regression
        log_values = np.log(unique_values)
        log_counts = np.log(counts)
        
        # Linear regression in log space
        A = np.vstack([log_values, np.ones(len(log_values))]).T
        slope, intercept = np.linalg.lstsq(A, log_counts, rcond=None)[0]
        
        # Calculate R-squared
        predictions = slope * log_values + intercept
        ss_res = np.sum((log_counts - predictions) ** 2)
        ss_tot = np.sum((log_counts - np.mean(log_counts)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            'tau': -slope,
            'r_squared': r_squared,
            'p_value': 0.01 if r_squared > 0.8 else 0.5  # Simplified
        }
    
    def _calculate_money_velocity(self, transactions: List[Dict], citizens: List[Dict]) -> float:
        """Calculate money velocity (transactions per unit wealth per time)"""
        if not transactions or not citizens:
            return 0.0
            
        total_value = sum(t['amount'] for t in transactions)
        total_wealth = sum(float(c.get('Wealth', 0)) for c in citizens)
        
        if total_wealth == 0 or not transactions:
            return 0.0
            
        # Time span in days
        time_span = (datetime.fromisoformat(transactions[-1]['timestamp'].replace('Z', '+00:00')) - 
                    datetime.fromisoformat(transactions[0]['timestamp'].replace('Z', '+00:00'))).days
        
        if time_span == 0:
            time_span = 1
            
        return (total_value / total_wealth) / time_span
    
    def _determine_phase(self, message_stats: Dict, transaction_stats: Dict) -> str:
        """Determine system phase based on branching ratios"""
        avg_sigma = (message_stats['mean'] + transaction_stats['mean']) / 2
        
        if 0.95 <= avg_sigma <= 1.05:
            return 'critical'
        elif avg_sigma < 0.95:
            return 'subcritical'
        else:
            return 'supercritical'


# Example usage function
def run_unified_analysis(api_base_url: str = "https://serenissima.ai/api") -> Dict:
    """
    Run unified criticality analysis using live API data
    
    This would be called from a FastAPI endpoint or scheduled task
    """
    import requests
    
    # Fetch data from API
    messages = requests.get(f"{api_base_url}/messages?limit=500").json().get('messages', [])
    contracts = requests.get(f"{api_base_url}/contracts").json().get('contracts', [])
    citizens = requests.get(f"{api_base_url}/citizens").json().get('citizens', [])
    relationships = requests.get(f"{api_base_url}/relationships").json().get('relationships', [])
    
    # Run analysis
    analyzer = UnifiedCriticalityMetrics()
    results = analyzer.calculate_unified_metrics(messages, contracts, citizens, relationships)
    
    return results