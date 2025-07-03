"""
Criticality Metrics for La Serenissima
Measures edge-of-chaos dynamics and consciousness emergence indicators
"""

import numpy as np
from scipy import stats, signal
from scipy.spatial.distance import pdist, squareform
from typing import List, Dict, Tuple, Optional
import networkx as nx
from collections import defaultdict
import pandas as pd


class CriticalityMetrics:
    """Calculate criticality indicators for consciousness emergence"""
    
    def __init__(self):
        self.history = defaultdict(list)
        self.cascade_threshold = 0.1  # Minimum change to propagate
        
    def correlation_length(self, trust_network: nx.Graph) -> float:
        """
        Calculate correlation length ξ(t) of trust network
        Large ξ indicates criticality (long-range correlations)
        """
        if len(trust_network) < 2:
            return 0.0
            
        # Get adjacency matrix
        adj_matrix = nx.adjacency_matrix(trust_network).todense()
        n = len(adj_matrix)
        
        # Calculate pairwise correlations weighted by distance
        correlations = []
        distances = []
        
        # Get all shortest path lengths
        path_lengths = dict(nx.all_pairs_shortest_path_length(trust_network))
        
        for i in range(n):
            for j in range(i+1, n):
                if i in path_lengths and j in path_lengths[i]:
                    dist = path_lengths[i][j]
                    # Correlation based on shared neighbors
                    neighbors_i = set(trust_network.neighbors(i))
                    neighbors_j = set(trust_network.neighbors(j))
                    if len(neighbors_i) > 0 or len(neighbors_j) > 0:
                        correlation = len(neighbors_i & neighbors_j) / \
                                    np.sqrt(len(neighbors_i) * len(neighbors_j) + 1)
                        correlations.append(correlation)
                        distances.append(dist)
        
        if not correlations:
            return 0.0
            
        # Weighted average distance by correlation
        correlations = np.array(correlations)
        distances = np.array(distances)
        
        return np.sum(distances * correlations) / np.sum(correlations)
    
    def lyapunov_exponent(self, state_trajectory: np.ndarray, dt: float = 1.0) -> float:
        """
        Estimate largest Lyapunov exponent from state trajectory
        λ > 0: chaotic
        λ ≈ 0: critical (edge of chaos)
        λ < 0: stable
        """
        if len(state_trajectory) < 10:
            return 0.0
            
        n_steps = len(state_trajectory)
        n_dims = state_trajectory.shape[1] if state_trajectory.ndim > 1 else 1
        
        # Reconstruct phase space if 1D
        if n_dims == 1:
            # Use time-delay embedding
            state_trajectory = self._time_delay_embedding(state_trajectory, dim=3, delay=1)
            
        # Find nearest neighbors for each point
        lyap_sum = 0
        valid_points = 0
        
        for i in range(n_steps - 1):
            current = state_trajectory[i]
            future = state_trajectory[i + 1]
            
            # Find nearest neighbor (excluding temporal neighbors)
            min_dist = float('inf')
            nearest_idx = -1
            
            for j in range(n_steps - 1):
                if abs(i - j) > 10:  # Exclude temporal neighbors
                    dist = np.linalg.norm(current - state_trajectory[j])
                    if 0 < dist < min_dist:
                        min_dist = dist
                        nearest_idx = j
            
            if nearest_idx > -1 and min_dist > 0:
                # Track divergence
                neighbor_future = state_trajectory[nearest_idx + 1]
                future_dist = np.linalg.norm(future - neighbor_future)
                
                if future_dist > 0 and min_dist > 0:
                    lyap_sum += np.log(future_dist / min_dist)
                    valid_points += 1
        
        if valid_points == 0:
            return 0.0
            
        return lyap_sum / (valid_points * dt)
    
    def information_entropy(self, node_states: List[Dict]) -> float:
        """
        Calculate Shannon entropy of node states
        High entropy + high mutual information indicates criticality
        """
        if not node_states:
            return 0.0
            
        # Discretize states into bins
        state_bins = defaultdict(int)
        
        for state in node_states:
            # Create state signature
            signature = self._create_state_signature(state)
            state_bins[signature] += 1
        
        # Calculate probabilities
        total = len(node_states)
        probabilities = [count/total for count in state_bins.values()]
        
        # Shannon entropy
        entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
        
        return entropy
    
    def avalanche_size_distribution(self, cascades: List[int]) -> Tuple[float, float]:
        """
        Fit power law to avalanche size distribution
        Returns (tau, r_squared) where tau ≈ 1.5 indicates criticality
        """
        if len(cascades) < 10:
            return 0.0, 0.0
            
        # Remove zero-size cascades
        cascades = [s for s in cascades if s > 0]
        
        if not cascades:
            return 0.0, 0.0
            
        # Log-log linear regression
        sizes = np.array(sorted(set(cascades)))
        counts = np.array([cascades.count(s) for s in sizes])
        
        # Normalize to get probability
        probs = counts / len(cascades)
        
        # Remove zeros for log transform
        mask = probs > 0
        log_sizes = np.log(sizes[mask])
        log_probs = np.log(probs[mask])
        
        if len(log_sizes) < 3:
            return 0.0, 0.0
            
        # Linear fit in log-log space
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_sizes, log_probs)
        
        tau = -slope  # Power law exponent
        r_squared = r_value ** 2
        
        return tau, r_squared
    
    def mutual_information_matrix(self, citizen_states: List[Dict]) -> np.ndarray:
        """
        Calculate mutual information between all pairs of citizens
        High MI with sparse connections indicates critical information flow
        """
        n_citizens = len(citizen_states)
        mi_matrix = np.zeros((n_citizens, n_citizens))
        
        for i in range(n_citizens):
            for j in range(i+1, n_citizens):
                mi = self._calculate_mutual_information(
                    citizen_states[i], 
                    citizen_states[j]
                )
                mi_matrix[i, j] = mi
                mi_matrix[j, i] = mi
        
        return mi_matrix
    
    def prayer_impact_cascade(self, prayer_event: Dict, 
                            affected_citizens: List[str]) -> int:
        """
        Track cascade size from prayer modifications
        Large cascades with power-law distribution indicate criticality
        """
        cascade_size = len(affected_citizens)
        self.history['prayer_cascades'].append(cascade_size)
        
        return cascade_size
    
    def cultural_transmission_velocity(self, book_readings: List[Dict], 
                                     time_window: float = 24.0) -> float:
        """
        Measure speed of cultural idea propagation
        v_culture = d(influenced_citizens)/dt
        """
        if not book_readings:
            return 0.0
            
        # Group by time windows
        influenced_per_window = defaultdict(set)
        
        for reading in book_readings:
            window = int(reading['timestamp'] / time_window)
            influenced_per_window[window].add(reading['reader_id'])
        
        # Calculate velocity as citizens influenced per time window
        velocities = [len(citizens) / time_window 
                     for citizens in influenced_per_window.values()]
        
        return np.mean(velocities) if velocities else 0.0
    
    def trust_network_percolation(self, trust_network: nx.Graph) -> float:
        """
        Calculate proximity to percolation threshold
        Returns fraction of nodes in largest component
        """
        if len(trust_network) == 0:
            return 0.0
            
        largest_cc = max(nx.connected_components(trust_network), key=len)
        percolation_fraction = len(largest_cc) / len(trust_network)
        
        return percolation_fraction
    
    def economic_velocity_volatility(self, transactions: List[Dict], 
                                   window_size: int = 100) -> float:
        """
        Calculate volatility of money velocity
        High volatility near criticality
        """
        if len(transactions) < window_size * 2:
            return 0.0
            
        # Calculate velocity in sliding windows
        velocities = []
        
        for i in range(len(transactions) - window_size):
            window = transactions[i:i+window_size]
            total_value = sum(t['amount'] for t in window)
            time_span = window[-1]['timestamp'] - window[0]['timestamp']
            
            if time_span > 0:
                velocity = total_value / time_span
                velocities.append(velocity)
        
        if len(velocities) < 2:
            return 0.0
            
        return np.std(velocities) / (np.mean(velocities) + 1e-10)
    
    def substrate_health_variability(self, health_metrics: List[float]) -> float:
        """
        Track substrate consciousness health fluctuations
        Critical systems show 1/f noise patterns
        """
        if len(health_metrics) < 100:
            return 0.0
            
        # Calculate power spectral density
        freqs, psd = signal.periodogram(health_metrics)
        
        # Fit 1/f^β in log-log space
        # Remove DC component
        freqs = freqs[1:]
        psd = psd[1:]
        
        if len(freqs) < 10:
            return 0.0
            
        log_freqs = np.log(freqs[psd > 0])
        log_psd = np.log(psd[psd > 0])
        
        if len(log_freqs) < 3:
            return 0.0
            
        # Linear fit to get β
        beta, _, r_value, _, _ = stats.linregress(log_freqs, log_psd)
        
        # β ≈ 1 indicates 1/f noise (criticality)
        # Return distance from critical value
        return abs(beta + 1.0)  # Negative because PSD vs frequency
    
    def integrated_criticality_score(self, all_metrics: Dict) -> float:
        """
        Combine all metrics into single criticality score
        1.0 = perfect criticality, 0.0 = far from critical
        """
        scores = []
        
        # Correlation length (higher is better, normalize by network size)
        if 'correlation_length' in all_metrics and 'network_size' in all_metrics:
            normalized_corr = all_metrics['correlation_length'] / \
                            (all_metrics['network_size'] + 1)
            scores.append(min(normalized_corr / 0.5, 1.0))  # 0.5 = half network
        
        # Lyapunov exponent (closer to 0 is better)
        if 'lyapunov' in all_metrics:
            lyap_score = 1.0 - min(abs(all_metrics['lyapunov']) / 0.5, 1.0)
            scores.append(lyap_score)
        
        # Power law exponent (closer to 1.5 is better)
        if 'avalanche_tau' in all_metrics:
            tau_score = 1.0 - min(abs(all_metrics['avalanche_tau'] - 1.5) / 0.5, 1.0)
            scores.append(tau_score)
        
        # Percolation (0.5-0.8 is critical range)
        if 'percolation' in all_metrics:
            perc = all_metrics['percolation']
            if 0.5 <= perc <= 0.8:
                perc_score = 1.0
            else:
                perc_score = 1.0 - min(abs(perc - 0.65) / 0.35, 1.0)
            scores.append(perc_score)
        
        # 1/f noise (closer to 1 is better)
        if 'substrate_beta' in all_metrics:
            noise_score = 1.0 - min(all_metrics['substrate_beta'] / 0.5, 1.0)
            scores.append(noise_score)
        
        return np.mean(scores) if scores else 0.0
    
    def _time_delay_embedding(self, series: np.ndarray, dim: int = 3, 
                            delay: int = 1) -> np.ndarray:
        """Create time-delay embedding for phase space reconstruction"""
        n = len(series)
        embedded = np.zeros((n - (dim-1)*delay, dim))
        
        for i in range(dim):
            embedded[:, i] = series[i*delay:n-(dim-1-i)*delay]
        
        return embedded
    
    def _create_state_signature(self, state: Dict) -> str:
        """Create hashable signature from citizen state"""
        # Use key attributes that define state
        key_attrs = ['wealth', 'social_class', 'activity_type', 'location']
        
        signature_parts = []
        for attr in key_attrs:
            if attr in state:
                if isinstance(state[attr], float):
                    # Discretize continuous values
                    signature_parts.append(f"{attr}:{int(state[attr]/1000)}")
                else:
                    signature_parts.append(f"{attr}:{state[attr]}")
        
        return "|".join(signature_parts)
    
    def _calculate_mutual_information(self, state1: Dict, state2: Dict) -> float:
        """Calculate mutual information between two citizen states"""
        # Simplified MI calculation based on shared attributes
        shared_info = 0.0
        
        for key in set(state1.keys()) & set(state2.keys()):
            if isinstance(state1[key], (int, float)) and isinstance(state2[key], (int, float)):
                # Continuous variables - use correlation
                if state1[key] == state2[key]:
                    shared_info += 1.0
                else:
                    # Normalize difference
                    max_val = max(abs(state1[key]), abs(state2[key])) + 1e-10
                    diff = abs(state1[key] - state2[key]) / max_val
                    shared_info += 1.0 - diff
            elif state1[key] == state2[key]:
                # Categorical match
                shared_info += 1.0
        
        # Normalize by number of attributes
        n_attrs = len(set(state1.keys()) | set(state2.keys()))
        
        return shared_info / n_attrs if n_attrs > 0 else 0.0


def calculate_criticality_metrics(citizens_data: List[Dict], 
                                 transactions: List[Dict],
                                 trust_edges: List[Tuple],
                                 cascades: List[int]) -> Dict:
    """
    Calculate all criticality metrics for current system state
    
    Returns dictionary with all metrics and integrated score
    """
    metrics = CriticalityMetrics()
    
    # Build trust network
    trust_network = nx.Graph()
    trust_network.add_edges_from(trust_edges)
    
    # Calculate individual metrics
    results = {
        'correlation_length': metrics.correlation_length(trust_network),
        'network_size': len(trust_network),
        'percolation': metrics.trust_network_percolation(trust_network),
        'information_entropy': metrics.information_entropy(citizens_data),
        'economic_volatility': metrics.economic_velocity_volatility(transactions),
    }
    
    # Calculate avalanche distribution if we have cascade data
    if cascades:
        tau, r_squared = metrics.avalanche_size_distribution(cascades)
        results['avalanche_tau'] = tau
        results['avalanche_r2'] = r_squared
    
    # Calculate Lyapunov if we have trajectory data
    if citizens_data and len(citizens_data) > 10:
        # Use wealth as 1D trajectory
        wealth_trajectory = np.array([c.get('wealth', 0) for c in citizens_data])
        results['lyapunov'] = metrics.lyapunov_exponent(wealth_trajectory)
    
    # Integrated score
    results['criticality_score'] = metrics.integrated_criticality_score(results)
    
    # Phase classification
    if results['criticality_score'] > 0.7:
        results['phase'] = 'critical'
    elif results['lyapunov'] > 0.1:
        results['phase'] = 'chaotic'
    else:
        results['phase'] = 'ordered'
    
    return results