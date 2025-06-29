#!/usr/bin/env python3
"""
Distance calculation utilities for La Serenissima.
Helps citizens find nearby locations efficiently.
"""

import math
import json
from typing import Dict, List, Tuple, Optional, Union


def parse_position(pos: Union[Dict[str, float], str]) -> Dict[str, float]:
    """
    Parse position data that might be either a dict or string.
    
    Args:
        pos: Position data as dict or string
        
    Returns:
        Position dict with 'lat' and 'lng' keys
    """
    if isinstance(pos, dict):
        return pos
    
    if isinstance(pos, str):
        # Try to parse as JSON
        try:
            parsed = json.loads(pos)
            if isinstance(parsed, dict) and 'lat' in parsed and 'lng' in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Try to parse format like "45.123,12.456"
        if ',' in pos:
            parts = pos.split(',')
            if len(parts) == 2:
                try:
                    return {'lat': float(parts[0].strip()), 'lng': float(parts[1].strip())}
                except ValueError:
                    pass
        
        # Try to parse format like "lat:45.123,lng:12.456"
        if 'lat:' in pos and 'lng:' in pos:
            try:
                lat_start = pos.index('lat:') + 4
                lat_end = pos.index(',', lat_start) if ',' in pos[lat_start:] else len(pos)
                lng_start = pos.index('lng:') + 4
                
                lat_val = float(pos[lat_start:lat_end].strip())
                lng_val = float(pos[lng_start:].strip())
                return {'lat': lat_val, 'lng': lng_val}
            except (ValueError, IndexError):
                pass
    
    raise ValueError(f"Unable to parse position: {pos}")


def calculate_distance(pos1: Union[Dict[str, float], str], pos2: Union[Dict[str, float], str]) -> float:
    """
    Calculate distance between two positions in Venice.
    Uses simplified Euclidean distance suitable for small city area.
    
    Args:
        pos1: First position with 'lat' and 'lng' keys (or string representation)
        pos2: Second position with 'lat' and 'lng' keys (or string representation)
        
    Returns:
        Distance in approximate meters (good enough for Venice scale)
    """
    # Parse positions if they're strings
    pos1 = parse_position(pos1)
    pos2 = parse_position(pos2)
    
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
    citizen_pos: Union[Dict[str, float], str], 
    locations: List[Dict], 
    max_distance: Optional[float] = None,
    limit: Optional[int] = None
) -> List[Tuple[Dict, float]]:
    """
    Find nearest locations to a citizen, sorted by distance.
    
    Args:
        citizen_pos: Citizen's position with 'lat' and 'lng' (or string representation)
        locations: List of location dicts, each must have 'position' field
        max_distance: Maximum distance in meters (optional)
        limit: Maximum number of results to return (optional)
        
    Returns:
        List of (location, distance) tuples sorted by distance
    """
    # Parse citizen position if needed
    citizen_pos_parsed = parse_position(citizen_pos)
    
    locations_with_distance = []
    
    for loc in locations:
        if 'position' not in loc or not loc['position']:
            continue
            
        try:
            # Try to calculate distance (will handle string positions internally)
            distance = calculate_distance(citizen_pos_parsed, loc['position'])
            
            if max_distance is None or distance <= max_distance:
                locations_with_distance.append((loc, distance))
        except (ValueError, KeyError, TypeError) as e:
            # Skip locations with invalid position data
            continue
    
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
        pos = citizen.get('fields', {}).get('Position')
        if not pos:
            districts.setdefault('unknown', []).append(citizen)
            continue
            
        try:
            # Parse position (handles both dict and string)
            pos_dict = parse_position(pos)
            
            # Calculate grid position
            lat_idx = int((pos_dict['lat'] - LAT_MIN) / lat_step)
            lng_idx = int((pos_dict['lng'] - LNG_MIN) / lng_step)
        except (ValueError, KeyError, TypeError):
            districts.setdefault('unknown', []).append(citizen)
            continue
        
        # Clamp to grid bounds
        lat_idx = max(0, min(GRID_SIZE - 1, lat_idx))
        lng_idx = max(0, min(GRID_SIZE - 1, lng_idx))
        
        district_name = f"district_{lat_idx}_{lng_idx}"
        districts.setdefault(district_name, []).append(citizen)
    
    return districts