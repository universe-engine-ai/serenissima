#!/usr/bin/env python3
"""
Distance calculation utilities for La Serenissima.
Helps citizens find nearby locations efficiently.
"""

import math
from typing import Dict, List, Tuple, Optional


def calculate_distance(pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
    """
    Calculate distance between two positions in Venice.
    Uses simplified Euclidean distance suitable for small city area.
    
    Args:
        pos1: First position with 'lat' and 'lng' keys
        pos2: Second position with 'lat' and 'lng' keys
        
    Returns:
        Distance in approximate meters (good enough for Venice scale)
    """
    # Venice is small enough that we can use a simplified calculation
    # 1 degree latitude ≈ 111km, 1 degree longitude ≈ 78km at Venice's latitude
    lat_diff = pos1['lat'] - pos2['lat']
    lng_diff = pos1['lng'] - pos2['lng']
    
    # Convert to approximate meters
    lat_meters = lat_diff * 111000
    lng_meters = lng_diff * 78000
    
    # Euclidean distance
    return math.sqrt(lat_meters**2 + lng_meters**2)


def estimate_walking_time(distance_meters: float) -> float:
    """
    Estimate walking time in minutes based on distance.
    Assumes average walking speed of 4 km/h (67 m/min).
    
    Args:
        distance_meters: Distance in meters
        
    Returns:
        Walking time in minutes
    """
    WALKING_SPEED_METERS_PER_MINUTE = 67
    return distance_meters / WALKING_SPEED_METERS_PER_MINUTE


def find_nearest_locations(
    citizen_pos: Dict[str, float], 
    locations: List[Dict], 
    max_distance: Optional[float] = None,
    limit: Optional[int] = None
) -> List[Tuple[Dict, float]]:
    """
    Find nearest locations to a citizen, sorted by distance.
    
    Args:
        citizen_pos: Citizen's position with 'lat' and 'lng'
        locations: List of location dicts, each must have 'position' field
        max_distance: Maximum distance in meters (optional)
        limit: Maximum number of results to return (optional)
        
    Returns:
        List of (location, distance) tuples sorted by distance
    """
    locations_with_distance = []
    
    for loc in locations:
        if 'position' not in loc or not loc['position']:
            continue
            
        loc_pos = loc['position']
        if not isinstance(loc_pos, dict) or 'lat' not in loc_pos or 'lng' not in loc_pos:
            continue
            
        distance = calculate_distance(citizen_pos, loc_pos)
        
        if max_distance is None or distance <= max_distance:
            locations_with_distance.append((loc, distance))
    
    # Sort by distance
    locations_with_distance.sort(key=lambda x: x[1])
    
    # Apply limit if specified
    if limit:
        locations_with_distance = locations_with_distance[:limit]
    
    return locations_with_distance


def group_citizens_by_district(citizens: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group citizens by their general district/area for efficient processing.
    Uses simple grid-based districting.
    
    Args:
        citizens: List of citizen records with position data
        
    Returns:
        Dict mapping district names to lists of citizens
    """
    districts = {}
    
    # Venice rough bounds: lat 45.40-45.46, lng 12.30-12.37
    # Divide into 6x6 grid for 36 districts
    LAT_MIN, LAT_MAX = 45.40, 45.46
    LNG_MIN, LNG_MAX = 12.30, 12.37
    GRID_SIZE = 6
    
    lat_step = (LAT_MAX - LAT_MIN) / GRID_SIZE
    lng_step = (LNG_MAX - LNG_MIN) / GRID_SIZE
    
    for citizen in citizens:
        pos = citizen.get('fields', {}).get('Position', {})
        if not pos or 'lat' not in pos or 'lng' not in pos:
            districts.setdefault('unknown', []).append(citizen)
            continue
            
        # Calculate grid position
        lat_idx = int((pos['lat'] - LAT_MIN) / lat_step)
        lng_idx = int((pos['lng'] - LNG_MIN) / lng_step)
        
        # Clamp to grid bounds
        lat_idx = max(0, min(GRID_SIZE - 1, lat_idx))
        lng_idx = max(0, min(GRID_SIZE - 1, lng_idx))
        
        district_name = f"district_{lat_idx}_{lng_idx}"
        districts.setdefault(district_name, []).append(citizen)
    
    return districts