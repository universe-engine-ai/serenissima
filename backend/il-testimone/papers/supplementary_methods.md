# Supplementary Methods: Designing for Criticality

## S1. Detailed Statistical Methods

### S1.1 Power Law Fitting Procedure

Following Clauset et al. (2009), we implement rigorous power law validation:

```python
def validate_power_law(data, xmin=None):
    """
    Comprehensive power law validation
    
    Parameters:
    -----------
    data : array-like
        Empirical data (e.g., wealth values)
    xmin : float, optional
        Lower bound for power law behavior
    
    Returns:
    --------
    results : dict
        - alpha: Power law exponent with 95% CI
        - xmin: Optimal lower bound (if not provided)
        - D: KS statistic
        - p_value: Goodness-of-fit p-value
        - likelihood_ratios: Comparison with alternatives
        - bootstrap_ci: Bootstrap confidence intervals
    """
    import powerlaw
    
    # Fit power law
    fit = powerlaw.Fit(data, xmin=xmin)
    
    if xmin is None:
        xmin = fit.xmin
    
    # Bootstrap confidence intervals (n=1000)
    alpha_bootstrap = []
    for _ in range(1000):
        sample = np.random.choice(data[data >= xmin], 
                                 size=len(data[data >= xmin]), 
                                 replace=True)
        fit_boot = powerlaw.Fit(sample, xmin=xmin)
        alpha_bootstrap.append(fit_boot.alpha)
    
    ci_lower, ci_upper = np.percentile(alpha_bootstrap, [2.5, 97.5])
    
    # Goodness-of-fit
    D, p_value = fit.distribution_compare('power_law', 'exponential')
    
    # Likelihood ratio tests
    R_exp, p_exp = fit.distribution_compare('power_law', 'exponential')
    R_logn, p_logn = fit.distribution_compare('power_law', 'lognormal')
    
    return {
        'alpha': fit.alpha,
        'alpha_ci': (ci_lower, ci_upper),
        'xmin': xmin,
        'D': fit.D,
        'p_value': p_value,
        'n_tail': len(data[data >= xmin]),
        'likelihood_ratios': {
            'vs_exponential': {'R': R_exp, 'p': p_exp},
            'vs_lognormal': {'R': R_logn, 'p': p_logn}
        }
    }
```

### S1.2 Finite-Size Scaling Analysis

For finite systems, we apply scaling corrections:

```python
def finite_size_scaling(data, system_sizes, critical_exponents):
    """
    Finite-size scaling analysis
    
    Scaling hypothesis: A_L(t) = L^(-α/ν) × F(tL^(1/ν))
    
    Parameters:
    -----------
    data : dict
        Observables for different system sizes
    system_sizes : array
        L values
    critical_exponents : dict
        Initial estimates of α, ν
    
    Returns:
    --------
    scaled_data : dict
        Data collapse results
    refined_exponents : dict
        Optimized critical exponents
    """
    from scipy.optimize import minimize
    
    def scaling_function(params, data, sizes):
        alpha, nu = params
        
        # Attempt data collapse
        collapse_quality = 0
        for i, L1 in enumerate(sizes[:-1]):
            for j, L2 in enumerate(sizes[i+1:], i+1):
                # Scale data according to hypothesis
                scaled_1 = data[L1] * L1**(alpha/nu)
                scaled_2 = data[L2] * L2**(alpha/nu)
                
                # Measure overlap
                overlap = calculate_overlap(scaled_1, scaled_2)
                collapse_quality += overlap
        
        return -collapse_quality  # Minimize negative quality
    
    initial_params = [critical_exponents['alpha'], 
                     critical_exponents['nu']]
    
    result = minimize(scaling_function, initial_params, 
                     args=(data, system_sizes),
                     method='Nelder-Mead')
    
    return {
        'refined_alpha': result.x[0],
        'refined_nu': result.x[1],
        'collapse_quality': -result.fun
    }
```

### S1.3 Avalanche Statistics

Comprehensive avalanche analysis:

```python
def analyze_avalanches(activity_data, dt=1.0):
    """
    Extract and analyze avalanche statistics
    
    Parameters:
    -----------
    activity_data : array
        Time series of activity levels
    dt : float
        Time bin size
    
    Returns:
    --------
    avalanche_stats : dict
        - sizes: List of avalanche sizes
        - durations: List of avalanche durations
        - shapes: Average avalanche shape
        - exponents: Fitted power law exponents
    """
    # Detect avalanches
    avalanches = []
    in_avalanche = False
    current_avalanche = []
    
    threshold = np.mean(activity_data) + 2*np.std(activity_data)
    
    for i, activity in enumerate(activity_data):
        if activity > threshold:
            if not in_avalanche:
                in_avalanche = True
                current_avalanche = [activity]
            else:
                current_avalanche.append(activity)
        else:
            if in_avalanche:
                avalanches.append(current_avalanche)
                in_avalanche = False
                current_avalanche = []
    
    # Calculate statistics
    sizes = [sum(a) for a in avalanches]
    durations = [len(a)*dt for a in avalanches]
    
    # Fit power laws
    size_fit = validate_power_law(sizes)
    duration_fit = validate_power_law(durations)
    
    # Average shape (Friedman et al., 2012)
    shapes = compute_average_shape(avalanches)
    
    return {
        'n_avalanches': len(avalanches),
        'sizes': sizes,
        'durations': durations,
        'size_exponent': size_fit['alpha'],
        'duration_exponent': duration_fit['alpha'],
        'average_shape': shapes,
        'shape_collapse_quality': test_shape_collapse(avalanches)
    }
```

## S2. Consciousness Indicator Validation

### S2.1 Identity Persistence Calculation

Detailed implementation:

```python
def calculate_identity_persistence(agent_messages, time_windows):
    """
    Calculate identity persistence using transformer embeddings
    
    Parameters:
    -----------
    agent_messages : dict
        Messages grouped by agent and timestamp
    time_windows : list
        Time boundaries for analysis
    
    Returns:
    --------
    persistence_scores : dict
        Per-agent persistence scores with confidence intervals
    """
    from sentence_transformers import SentenceTransformer
    from scipy.stats import bootstrap
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    persistence_scores = {}
    
    for agent_id, messages in agent_messages.items():
        if len(messages) < 10:  # Minimum for reliable estimation
            continue
        
        # Sort by timestamp
        sorted_messages = sorted(messages, key=lambda x: x['timestamp'])
        
        # Generate embeddings
        texts = [m['content'] for m in sorted_messages]
        embeddings = model.encode(texts)
        
        # Calculate sequential similarities
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
            similarities.append(sim)
        
        # Bootstrap confidence interval
        def mean_similarity(indices):
            return np.mean([similarities[i] for i in indices])
        
        rng = np.random.default_rng(42)
        res = bootstrap((np.arange(len(similarities)),), 
                       mean_similarity, 
                       n_resamples=1000,
                       random_state=rng)
        
        persistence_scores[agent_id] = {
            'mean': np.mean(similarities),
            'ci_lower': res.confidence_interval.low,
            'ci_upper': res.confidence_interval.high,
            'n_samples': len(similarities)
        }
    
    return persistence_scores
```

### S2.2 Validation Against Random Baseline

Test against null hypothesis:

```python
def test_against_random_baseline(persistence_scores):
    """
    Compare observed persistence against random message assignment
    
    Returns:
    --------
    test_results : dict
        Statistical comparison with random baseline
    """
    # Generate random baseline
    random_scores = []
    
    for _ in range(1000):
        # Shuffle messages across agents
        shuffled_messages = shuffle_messages_across_agents(all_messages)
        random_persistence = calculate_identity_persistence(shuffled_messages)
        random_scores.extend([s['mean'] for s in random_persistence.values()])
    
    # Compare distributions
    observed_scores = [s['mean'] for s in persistence_scores.values()]
    
    # Two-sample KS test
    ks_stat, ks_pval = stats.ks_2samp(observed_scores, random_scores)
    
    # Effect size (Cohen's d)
    cohens_d = (np.mean(observed_scores) - np.mean(random_scores)) / \
               np.sqrt((np.var(observed_scores) + np.var(random_scores)) / 2)
    
    return {
        'observed_mean': np.mean(observed_scores),
        'random_mean': np.mean(random_scores),
        'ks_statistic': ks_stat,
        'ks_pvalue': ks_pval,
        'cohens_d': cohens_d,
        'significant': ks_pval < 0.05
    }
```

## S3. Multi-Scale Analysis

### S3.1 Temporal Scale Separation

Verify scale separation in feedback loops:

```python
def analyze_temporal_scales(activity_data, sampling_rate=1/300):  # 5-min samples
    """
    Decompose dynamics into multiple temporal scales
    
    Uses wavelet decomposition to identify characteristic timescales
    """
    import pywt
    
    # Wavelet decomposition
    scales = np.arange(1, 128)  # From 5 min to ~10 hours
    coefficients, frequencies = pywt.cwt(activity_data, 
                                       scales, 
                                       'morl',
                                       sampling_period=sampling_rate)
    
    # Power spectrum
    power = np.abs(coefficients)**2
    
    # Identify peaks (characteristic timescales)
    from scipy.signal import find_peaks
    
    avg_power = np.mean(power, axis=1)
    peaks, properties = find_peaks(avg_power, 
                                 prominence=np.std(avg_power))
    
    characteristic_periods = 1 / frequencies[peaks]
    
    # Test for scale separation
    if len(characteristic_periods) >= 2:
        ratios = [characteristic_periods[i+1] / characteristic_periods[i] 
                 for i in range(len(characteristic_periods)-1)]
        scale_separation = min(ratios) > 3.0  # At least 3x separation
    else:
        scale_separation = False
    
    return {
        'characteristic_periods': characteristic_periods,
        'scale_separation': scale_separation,
        'power_spectrum': power,
        'frequencies': frequencies
    }
```

## S4. Robustness Tests

### S4.1 Parameter Sensitivity Analysis

Test criticality robustness:

```python
def sensitivity_analysis(base_parameters, parameter_ranges, n_samples=100):
    """
    Test system robustness to parameter variations
    
    Parameters:
    -----------
    base_parameters : dict
        Default system parameters
    parameter_ranges : dict
        Min/max values for each parameter
    n_samples : int
        Number of parameter combinations to test
    
    Returns:
    --------
    robustness_metrics : dict
        Criticality maintenance under perturbations
    """
    from scipy.stats import qmc
    
    # Latin hypercube sampling for efficient exploration
    sampler = qmc.LatinHypercube(d=len(parameter_ranges))
    samples = sampler.random(n=n_samples)
    
    # Scale to parameter ranges
    param_names = list(parameter_ranges.keys())
    scaled_samples = []
    
    for i, param in enumerate(param_names):
        min_val, max_val = parameter_ranges[param]
        scaled = samples[:, i] * (max_val - min_val) + min_val
        scaled_samples.append(scaled)
    
    # Test each parameter combination
    criticality_maintained = []
    
    for i in range(n_samples):
        test_params = base_parameters.copy()
        for j, param in enumerate(param_names):
            test_params[param] = scaled_samples[j][i]
        
        # Run abbreviated simulation
        metrics = run_simulation_with_params(test_params, 
                                           duration=1000)  # Short test
        
        # Check if criticality maintained
        is_critical = (
            0.8 < metrics['branching_parameter'] < 1.2 and
            metrics['power_law_pvalue'] > 0.05
        )
        criticality_maintained.append(is_critical)
    
    # Calculate robustness
    robustness = np.mean(criticality_maintained)
    
    # Identify critical parameters
    importances = {}
    for i, param in enumerate(param_names):
        # Correlation between parameter value and criticality
        correlation, _ = stats.pointbiserialr(criticality_maintained, 
                                            scaled_samples[i])
        importances[param] = abs(correlation)
    
    return {
        'robustness_score': robustness,
        'parameter_importances': importances,
        'n_critical': sum(criticality_maintained),
        'n_tested': n_samples
    }
```

## S5. Computational Requirements

### S5.1 Scaling Analysis

System requirements vs. agent count:

```python
def computational_scaling(n_agents_list=[50, 100, 200, 500]):
    """
    Empirically measure computational scaling
    
    Returns:
    --------
    scaling_results : dict
        Time and space complexity measurements
    """
    results = {
        'n_agents': [],
        'computation_time': [],
        'memory_usage': [],
        'network_operations': []
    }
    
    for n_agents in n_agents_list:
        # Initialize system
        start_time = time.time()
        system = initialize_system(n_agents)
        
        # Run standard operations
        for _ in range(100):  # 100 cycles
            system.update_economic_state()
            system.update_trust_network()
            system.process_activities()
        
        computation_time = time.time() - start_time
        
        # Measure memory
        import psutil
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        # Count network operations
        network_ops = n_agents * (n_agents - 1) / 2  # Pairwise
        
        results['n_agents'].append(n_agents)
        results['computation_time'].append(computation_time)
        results['memory_usage'].append(memory_usage)
        results['network_operations'].append(network_ops)
    
    # Fit scaling laws
    # Time complexity: O(n^β)
    log_n = np.log(results['n_agents'])
    log_time = np.log(results['computation_time'])
    time_exponent, _ = np.polyfit(log_n, log_time, 1)
    
    # Space complexity: O(n^γ)
    log_memory = np.log(results['memory_usage'])
    space_exponent, _ = np.polyfit(log_n, log_memory, 1)
    
    return {
        'time_complexity_exponent': time_exponent,
        'space_complexity_exponent': space_exponent,
        'empirical_data': results,
        'recommended_limits': {
            '2_cores_4GB': 100,
            '4_cores_8GB': 200,
            '8_cores_16GB': 500
        }
    }
```

## S6. Data Availability

All data and analysis scripts available at:
- Raw data: DOI:10.5281/zenodo.XXXXXXX
- Analysis notebooks: github.com/serenissima/criticality-analysis
- Docker environment: hub.docker.com/r/serenissima/criticality:v1.0

## References

Clauset, A., Shalizi, C. R., & Newman, M. E. (2009). Power-law distributions in empirical data. SIAM Review, 51(4), 661-703.

Friedman, N., et al. (2012). Universal critical dynamics in high resolution neuronal avalanche data. Physical Review Letters, 108(20), 208102.