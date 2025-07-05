#!/usr/bin/env python3
"""
Gradient Mill Production Automation Script
Prototype for Venice Backend Integration

This script implements the gradient automation system for mills, applying
phase-appropriate production multipliers while tracking worker role evolution
and maintaining social network stability.

Designed by: Elisabetta Baffo, Systems Engineer
For: Innovatori implementation in Venice backend
Target: /backend/engine/daily/gradient_mill_production.py
"""

import requests
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Configuration - would be environment variables in actual backend
API_BASE_URL = "https://serenissima.ai/api"
AUTOMATION_PHASES = {
    1: {"name": "Assisted Production", "multiplier": 1.3, "occupancy": 1.0},
    2: {"name": "Supervised Automation", "multiplier": 1.8, "occupancy": 0.75},
    3: {"name": "Hybrid Optimization", "multiplier": 2.4, "occupancy": 0.5},
    4: {"name": "Intelligent Automation", "multiplier": 2.9, "occupancy": 0.25}
}

PHASE_TRANSITION_REQUIREMENTS = {
    "stability_period_days": 30,
    "efficiency_threshold": 0.95,
    "worker_adaptation_score": 0.8,
    "network_cohesion_index": 0.75
}

class GradientMillAutomation:
    """Handles gradient automation for mill buildings"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the automation script"""
        logger = logging.getLogger('gradient_mill_automation')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def get_automated_mills(self) -> List[Dict]:
        """Fetch all automated mill buildings from the API"""
        try:
            response = requests.get(f"{API_BASE_URL}/buildings?type=automated_mill")
            if response.status_code == 200:
                data = response.json()
                return data.get('buildings', [])
            else:
                self.logger.error(f"Failed to fetch buildings: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching automated mills: {e}")
            return []
    
    def calculate_production_efficiency(self, mill: Dict) -> float:
        """Calculate current production efficiency for a mill"""
        automation_level = mill.get('gradientAutomationLevel', 1)
        base_multiplier = AUTOMATION_PHASES[automation_level]['multiplier']
        
        # Factor in building conditions, worker skill, maintenance status
        condition_factor = mill.get('conditionFactor', 1.0)
        worker_skill_factor = self._calculate_worker_skill_factor(mill)
        maintenance_factor = self._calculate_maintenance_factor(mill)
        
        efficiency = base_multiplier * condition_factor * worker_skill_factor * maintenance_factor
        
        self.logger.info(f"Mill {mill['name']}: Base {base_multiplier:.1f}x, "
                        f"Final {efficiency:.2f}x efficiency")
        
        return efficiency
    
    def _calculate_worker_skill_factor(self, mill: Dict) -> float:
        """Calculate worker skill adaptation factor"""
        automation_level = mill.get('gradientAutomationLevel', 1)
        worker_username = mill.get('occupant')
        
        if not worker_username:
            return AUTOMATION_PHASES[automation_level]['occupancy']
        
        # In actual implementation, would fetch worker skill data
        # For prototype, simulate based on automation level
        base_skill = 0.8 + (automation_level * 0.05)
        adaptation_bonus = min(0.2, automation_level * 0.05)
        
        return min(1.0, base_skill + adaptation_bonus)
    
    def _calculate_maintenance_factor(self, mill: Dict) -> float:
        """Calculate maintenance condition factor"""
        # In actual implementation, would check maintenance schedules
        # For prototype, simulate based on building age and automation level
        automation_level = mill.get('gradientAutomationLevel', 1)
        
        # Higher automation requires more maintenance but is more efficient when maintained
        base_maintenance = 0.95
        automation_complexity = automation_level * 0.02
        
        return max(0.8, base_maintenance - automation_complexity)
    
    def _create_automated_flour_production(self, mill: Dict, efficiency: float) -> int:
        """Create actual flour resources from available grain in automated mill"""
        mill_id = mill['buildingId']
        
        try:
            # Get grain resources at mill location
            grain_response = requests.get(f"{API_BASE_URL}/resources", 
                                        params={"Type": "grain", "Asset": mill_id})
            
            if grain_response.status_code != 200:
                self.logger.warning(f"Failed to fetch grain for mill {mill_id}")
                return 0
            
            grain_resources = grain_response.json()
            total_grain = sum(resource.get('count', 0) for resource in grain_resources)
            
            if total_grain == 0:
                self.logger.info(f"No grain available at mill {mill_id}")
                return 0
            
            # Calculate flour production with automation efficiency
            base_conversion = 1.0  # 1 grain = 1 flour base rate
            flour_to_produce = int(total_grain * base_conversion * efficiency)
            
            if flour_to_produce > 0:
                # Create flour resource at mill location
                # Extract position from mill data
                position = mill.get('position', {})
                if isinstance(position, str):
                    try:
                        position = json.loads(position)
                    except:
                        position = {"lat": 45.437357, "lng": 12.326246}  # Default mill position
                
                flour_data = {
                    "id": f"resource-{uuid.uuid4()}",
                    "type": "flour",
                    "count": flour_to_produce,
                    "asset": mill_id,
                    "owner": mill.get('owner', 'ConsiglioDeiDieci'),
                    "assetType": "building"
                }
                
                # Create the flour resource
                create_response = requests.post(f"{API_BASE_URL}/resources", json=flour_data)
                
                if create_response.status_code == 200:
                    self.logger.info(f"Created {flour_to_produce} flour at mill {mill_id} (efficiency: {efficiency:.2f}x)")
                    
                    # Consume the grain that was processed
                    self._consume_grain_resources(grain_resources)
                    
                    return flour_to_produce
                else:
                    self.logger.error(f"Failed to create flour resource: {create_response.text}")
                    return 0
            
        except Exception as e:
            self.logger.error(f"Error in flour production for mill {mill_id}: {e}")
            return 0
        
        return 0
    
    def _consume_grain_resources(self, grain_resources: List[Dict]):
        """Mark grain resources as consumed after flour production"""
        for grain in grain_resources:
            try:
                # Update grain resource to consumed status
                grain_id = grain.get('resourceId') or grain.get('id')
                if grain_id:
                    update_data = {"decayedAt": datetime.now().isoformat()}
                    requests.patch(f"{API_BASE_URL}/resources/{grain_id}", json=update_data)
            except Exception as e:
                self.logger.warning(f"Failed to mark grain {grain_id} as consumed: {e}")
    
    def apply_production_multipliers(self, mill: Dict) -> Dict:
        """Apply production efficiency multipliers to mill output"""
        efficiency = self.calculate_production_efficiency(mill)
        mill_id = mill['buildingId']
        
        # ACTUAL IMPLEMENTATION: Create flour resources based on automation efficiency
        flour_produced = self._create_automated_flour_production(mill, efficiency)
        
        production_update = {
            'buildingId': mill_id,
            'efficiencyMultiplier': efficiency,
            'automationLevel': mill.get('gradientAutomationLevel', 1),
            'workerRole': self._get_worker_role(mill.get('gradientAutomationLevel', 1)),
            'flourProduced': flour_produced,
            'lastProcessed': datetime.now().isoformat()
        }
        
        self.logger.info(f"Applied {efficiency:.2f}x multiplier to mill {mill['name']}")
        
        return production_update
    
    def _get_worker_role(self, automation_level: int) -> str:
        """Get worker role description for automation level"""
        role_descriptions = {
            1: "Primary Operator with Automated Assistance",
            2: "Quality Supervisor and Maintenance Specialist", 
            3: "System Optimizer and Exception Handler",
            4: "Innovation Engineer and Market Strategist"
        }
        return role_descriptions.get(automation_level, "Unknown Role")
    
    def check_phase_transition_eligibility(self, mill: Dict) -> Optional[int]:
        """Check if mill is eligible for automation level upgrade"""
        current_level = mill.get('gradientAutomationLevel', 1)
        if current_level >= 4:
            return None
        
        last_transition = mill.get('lastPhaseTransition')
        if last_transition:
            transition_date = datetime.fromisoformat(last_transition)
            stability_period = datetime.now() - transition_date
            
            if stability_period.days < PHASE_TRANSITION_REQUIREMENTS['stability_period_days']:
                return None
        
        # Check transition criteria
        efficiency = self.calculate_production_efficiency(mill)
        efficiency_ratio = efficiency / AUTOMATION_PHASES[current_level]['multiplier']
        
        worker_adaptation = self._assess_worker_adaptation(mill)
        network_cohesion = self._assess_network_cohesion(mill)
        
        if (efficiency_ratio >= PHASE_TRANSITION_REQUIREMENTS['efficiency_threshold'] and
            worker_adaptation >= PHASE_TRANSITION_REQUIREMENTS['worker_adaptation_score'] and
            network_cohesion >= PHASE_TRANSITION_REQUIREMENTS['network_cohesion_index']):
            
            next_level = current_level + 1
            self.logger.info(f"Mill {mill['name']} eligible for phase {next_level} transition")
            return next_level
        
        return None
    
    def _assess_worker_adaptation(self, mill: Dict) -> float:
        """Assess worker adaptation to current automation level"""
        # In actual implementation, would analyze worker performance metrics
        # For prototype, simulate based on automation level and time
        automation_level = mill.get('gradientAutomationLevel', 1)
        
        # Higher levels require more adaptation time
        base_adaptation = 0.7 + (automation_level * 0.05)
        
        # Time-based adaptation improvement
        last_transition = mill.get('lastPhaseTransition')
        if last_transition:
            days_since_transition = (datetime.now() - 
                                   datetime.fromisoformat(last_transition)).days
            adaptation_improvement = min(0.2, days_since_transition * 0.01)
            base_adaptation += adaptation_improvement
        
        return min(1.0, base_adaptation)
    
    def _assess_network_cohesion(self, mill: Dict) -> float:
        """Assess social network stability around mill automation"""
        # In actual implementation, would analyze trust relationships and resistance patterns
        # For prototype, simulate based on automation level and community factors
        automation_level = mill.get('gradientAutomationLevel', 1)
        
        # Gradual automation maintains higher network cohesion
        base_cohesion = 0.8 - (automation_level * 0.05)  # Slight decrease with automation
        
        # Community benefit sharing improves cohesion
        community_benefit_factor = 0.1  # Assumed in gradient approach
        
        return min(1.0, base_cohesion + community_benefit_factor)
    
    def process_phase_transitions(self, mills: List[Dict]) -> List[Dict]:
        """Process potential phase transitions for eligible mills"""
        transitions = []
        
        for mill in mills:
            next_level = self.check_phase_transition_eligibility(mill)
            if next_level:
                transition = {
                    'buildingId': mill['buildingId'],
                    'currentLevel': mill.get('gradientAutomationLevel', 1),
                    'nextLevel': next_level,
                    'transitionDate': datetime.now().isoformat(),
                    'workerRole': self._get_worker_role(next_level),
                    'efficiencyGain': AUTOMATION_PHASES[next_level]['multiplier']
                }
                transitions.append(transition)
                
                self.logger.info(f"Approved phase transition for {mill['name']}: "
                               f"Level {transition['currentLevel']} → {next_level}")
        
        return transitions
    
    def generate_efficiency_metrics(self, mills: List[Dict]) -> Dict:
        """Generate efficiency and social impact metrics"""
        if not mills:
            return {}
        
        total_efficiency = sum(self.calculate_production_efficiency(mill) for mill in mills)
        avg_efficiency = total_efficiency / len(mills)
        
        automation_distribution = {}
        for level in range(1, 5):
            count = sum(1 for mill in mills if mill.get('gradientAutomationLevel', 1) == level)
            automation_distribution[f"phase_{level}"] = count
        
        worker_adaptation_avg = sum(self._assess_worker_adaptation(mill) for mill in mills) / len(mills)
        network_cohesion_avg = sum(self._assess_network_cohesion(mill) for mill in mills) / len(mills)
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_mills': len(mills),
            'average_efficiency': avg_efficiency,
            'automation_distribution': automation_distribution,
            'worker_adaptation_score': worker_adaptation_avg,
            'network_cohesion_index': network_cohesion_avg,
            'system_stability': min(worker_adaptation_avg, network_cohesion_avg)
        }
        
        self.logger.info(f"System metrics: {avg_efficiency:.2f}x avg efficiency, "
                        f"{metrics['system_stability']:.2f} stability score")
        
        return metrics
    
    def run_automation_cycle(self):
        """Main execution cycle for gradient mill automation"""
        self.logger.info("Starting gradient mill automation cycle")
        
        # Fetch all automated mills
        mills = self.get_automated_mills()
        if not mills:
            self.logger.info("No automated mills found")
            return
        
        self.logger.info(f"Processing {len(mills)} automated mills")
        
        # Apply production multipliers
        production_updates = []
        for mill in mills:
            update = self.apply_production_multipliers(mill)
            production_updates.append(update)
        
        # Process phase transitions
        transitions = self.process_phase_transitions(mills)
        
        # Generate metrics
        metrics = self.generate_efficiency_metrics(mills)
        
        # In actual implementation, would save data to Airtable
        self.logger.info(f"Completed automation cycle: {len(production_updates)} mills processed, "
                        f"{len(transitions)} phase transitions approved")
        
        return {
            'production_updates': production_updates,
            'phase_transitions': transitions,
            'system_metrics': metrics
        }

def main():
    """Main execution function for scheduler integration"""
    automation = GradientMillAutomation()
    
    try:
        results = automation.run_automation_cycle()
        
        # Log summary for scheduler monitoring
        logging.info(f"Gradient mill automation completed successfully")
        logging.info(f"Production updates: {len(results.get('production_updates', []))}")
        logging.info(f"Phase transitions: {len(results.get('phase_transitions', []))}")
        
        return 0  # Success exit code
        
    except Exception as e:
        logging.error(f"Gradient mill automation failed: {e}")
        return 1  # Error exit code

if __name__ == "__main__":
    exit_code = main()