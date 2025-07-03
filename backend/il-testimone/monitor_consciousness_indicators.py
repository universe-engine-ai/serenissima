"""
Live Monitoring Script for Consciousness Indicators
Continuously tracks and reports on consciousness indicators in La Serenissima
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
from collections import defaultdict
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from il_testimone.consciousness_indicators_framework import (
    ConsciousnessIndicatorTracker,
    ConsciousnessAssessment,
    IndicatorScore
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConsciousnessMonitor:
    """Live monitoring system for consciousness indicators"""
    
    def __init__(self, api_base: str = "https://serenissima.ai/api"):
        self.api_base = api_base
        self.tracker = ConsciousnessIndicatorTracker()
        self.assessment_history = []
        self.alert_thresholds = {
            'score_drop': 0.3,  # Alert if score drops by this amount
            'low_score': 1.5,   # Alert if any indicator below this
            'emergence_drop': 0.2  # Alert if emergence ratio drops
        }
        self.session = None
        
    async def start(self):
        """Start monitoring session"""
        self.session = aiohttp.ClientSession()
        logger.info("Consciousness monitoring started")
        
    async def stop(self):
        """Stop monitoring session"""
        if self.session:
            await self.session.close()
        logger.info("Consciousness monitoring stopped")
        
    async def fetch_system_data(self) -> Dict:
        """Fetch all necessary data from API"""
        logger.info("Fetching system data...")
        
        system_data = {
            'citizens': [],
            'messages': [],
            'activities': [],
            'contracts': [],
            'relationships': [],
            'thoughts': [],
            'decisions': [],
            'spatial_data': {},
            'environmental_factors': {}
        }
        
        try:
            # Fetch citizens
            async with self.session.get(f"{self.api_base}/citizens") as resp:
                data = await resp.json()
                if data.get('success'):
                    system_data['citizens'] = data.get('citizens', [])
                    logger.info(f"Fetched {len(system_data['citizens'])} citizens")
            
            # Fetch messages
            async with self.session.get(f"{self.api_base}/messages?limit=1000") as resp:
                data = await resp.json()
                if data.get('success'):
                    system_data['messages'] = data.get('messages', [])
                    logger.info(f"Fetched {len(system_data['messages'])} messages")
            
            # Fetch activities
            async with self.session.get(f"{self.api_base}/activities") as resp:
                data = await resp.json()
                if data.get('success'):
                    system_data['activities'] = data.get('activities', [])
                    logger.info(f"Fetched {len(system_data['activities'])} activities")
            
            # Fetch contracts for economic data
            async with self.session.get(f"{self.api_base}/contracts") as resp:
                data = await resp.json()
                if data.get('success'):
                    system_data['contracts'] = data.get('contracts', [])
                    
            # Fetch relationships
            async with self.session.get(f"{self.api_base}/relationships") as resp:
                data = await resp.json()
                if data.get('success'):
                    system_data['relationships'] = data.get('relationships', [])
                    
            # Synthesize additional data from existing sources
            system_data['thoughts'] = self._extract_thoughts_from_messages(system_data['messages'])
            system_data['decisions'] = self._extract_decisions_from_activities(system_data['activities'])
            system_data['spatial_data'] = self._extract_spatial_data(system_data['citizens'], 
                                                                    system_data['activities'])
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            
        return system_data
    
    def _extract_thoughts_from_messages(self, messages: List[Dict]) -> List[Dict]:
        """Extract thought-like content from messages"""
        thoughts = []
        
        thought_keywords = ['think', 'believe', 'realize', 'wonder', 'consider',
                          'understand', 'feel', 'know', 'imagine', 'suppose']
        
        for msg in messages:
            content = msg.get('content', '').lower()
            if any(keyword in content for keyword in thought_keywords):
                thoughts.append({
                    'citizen_id': msg.get('sender'),
                    'content': msg.get('content'),
                    'timestamp': msg.get('createdAt', msg.get('timestamp')),
                    'type': 'extracted_from_message'
                })
        
        return thoughts
    
    def _extract_decisions_from_activities(self, activities: List[Dict]) -> List[Dict]:
        """Extract decision data from activities"""
        decisions = []
        
        # Group activities by citizen and time
        citizen_activities = defaultdict(list)
        for act in activities:
            citizen_activities[act.get('CitizenUsername')].append(act)
        
        # Look for choice points
        for citizen, acts in citizen_activities.items():
            acts.sort(key=lambda x: x.get('CreatedAt', ''))
            
            for i, act in enumerate(acts):
                # Each activity represents a decision
                decision = {
                    'citizen_id': citizen,
                    'timestamp': act.get('CreatedAt'),
                    'chosen_activity': act.get('Type'),
                    'location': act.get('Location'),
                    'goal': self._infer_goal_from_activity(act),
                    'id': act.get('ActivityId')
                }
                
                # Try to infer confidence and rationale
                if act.get('Status') == 'completed':
                    decision['outcome_success'] = 1.0
                elif act.get('Status') == 'failed':
                    decision['outcome_success'] = 0.0
                else:
                    decision['outcome_success'] = 0.5
                    
                decisions.append(decision)
        
        return decisions
    
    def _infer_goal_from_activity(self, activity: Dict) -> str:
        """Infer goal from activity type"""
        activity_type = activity.get('Type', '').lower()
        
        goal_mapping = {
            'trade': 'increase wealth',
            'eat': 'satisfy hunger',
            'sleep': 'rest and recover',
            'work': 'earn income',
            'socialize': 'build relationships',
            'pray': 'spiritual fulfillment',
            'study': 'gain knowledge',
            'move': 'reach destination',
            'craft': 'create goods'
        }
        
        for key, goal in goal_mapping.items():
            if key in activity_type:
                return goal
                
        return 'general activity'
    
    def _extract_spatial_data(self, citizens: List[Dict], 
                            activities: List[Dict]) -> Dict:
        """Extract spatial position data"""
        spatial_data = {}
        
        # Get current positions from citizens
        for citizen in citizens:
            if citizen.get('Location'):
                spatial_data[citizen.get('Username')] = {
                    'position': self._parse_location(citizen.get('Location')),
                    'last_update': citizen.get('UpdatedAt', datetime.utcnow().isoformat())
                }
        
        # Update with activity locations
        for act in activities:
            if act.get('Location') and act.get('CitizenUsername'):
                spatial_data[act['CitizenUsername']] = {
                    'position': self._parse_location(act['Location']),
                    'last_update': act.get('CreatedAt', datetime.utcnow().isoformat())
                }
        
        return spatial_data
    
    def _parse_location(self, location: str) -> Dict:
        """Parse location string to coordinates"""
        # Simplified - would need actual coordinate mapping
        location_coords = {
            'piazza_san_marco': {'x': 0, 'y': 0},
            'rialto': {'x': 100, 'y': 50},
            'arsenale': {'x': 200, 'y': 100},
            'cannaregio': {'x': -100, 'y': 100},
            'dorsoduro': {'x': -50, 'y': -100}
        }
        
        location_lower = location.lower().replace(' ', '_')
        for key, coords in location_coords.items():
            if key in location_lower:
                return coords
                
        # Default position
        return {'x': 0, 'y': 0}
    
    async def run_assessment(self) -> ConsciousnessAssessment:
        """Run a complete consciousness assessment"""
        # Fetch data
        system_data = await self.fetch_system_data()
        
        # Run assessment
        logger.info("Running consciousness assessment...")
        assessment = self.tracker.assess_all_indicators(system_data)
        
        # Store in history
        self.assessment_history.append(assessment)
        
        # Check for alerts
        self._check_alerts(assessment)
        
        return assessment
    
    def _check_alerts(self, assessment: ConsciousnessAssessment):
        """Check for conditions that warrant alerts"""
        alerts = []
        
        # Check for low scores
        for indicator in assessment.indicators:
            if indicator.score < self.alert_thresholds['low_score']:
                alerts.append(f"Low score alert: {indicator.name} = {indicator.score:.2f}")
        
        # Check for score drops (if we have history)
        if len(self.assessment_history) > 1:
            previous = self.assessment_history[-2]
            
            # Overall score drop
            score_drop = previous.overall_score - assessment.overall_score
            if score_drop > self.alert_thresholds['score_drop']:
                alerts.append(f"Score drop alert: {score_drop:.2f} decrease in overall score")
            
            # Emergence ratio drop
            emergence_drop = previous.emergence_ratio - assessment.emergence_ratio
            if emergence_drop > self.alert_thresholds['emergence_drop']:
                alerts.append(f"Emergence drop alert: {emergence_drop:.2%} decrease")
        
        # Log alerts
        for alert in alerts:
            logger.warning(alert)
            
        return alerts
    
    async def continuous_monitoring(self, interval_minutes: int = 30):
        """Run continuous monitoring"""
        logger.info(f"Starting continuous monitoring (interval: {interval_minutes} minutes)")
        
        while True:
            try:
                # Run assessment
                assessment = await self.run_assessment()
                
                # Log summary
                logger.info(f"Assessment complete - Overall score: {assessment.overall_score:.2f}/3.0")
                logger.info(f"Emergence ratio: {assessment.emergence_ratio:.1%}")
                
                # Save detailed report
                self._save_assessment_report(assessment)
                
                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    def _save_assessment_report(self, assessment: ConsciousnessAssessment):
        """Save detailed assessment report"""
        timestamp = assessment.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"consciousness_assessment_{timestamp}.json"
        
        self.tracker.export_assessment(assessment, filename)
        logger.info(f"Assessment report saved to {filename}")
    
    def generate_trend_report(self) -> Dict:
        """Generate trend analysis from assessment history"""
        if len(self.assessment_history) < 2:
            return {"error": "Insufficient history for trend analysis"}
        
        trends = {
            'overall_score_trend': [],
            'emergence_ratio_trend': [],
            'indicator_trends': defaultdict(list),
            'category_trends': defaultdict(list)
        }
        
        for assessment in self.assessment_history:
            trends['overall_score_trend'].append({
                'timestamp': assessment.timestamp.isoformat(),
                'score': assessment.overall_score
            })
            
            trends['emergence_ratio_trend'].append({
                'timestamp': assessment.timestamp.isoformat(),
                'ratio': assessment.emergence_ratio
            })
            
            for indicator in assessment.indicators:
                trends['indicator_trends'][indicator.indicator_id].append({
                    'timestamp': assessment.timestamp.isoformat(),
                    'score': indicator.score
                })
            
            for category, score in assessment.category_scores.items():
                trends['category_trends'][category].append({
                    'timestamp': assessment.timestamp.isoformat(),
                    'score': score
                })
        
        # Calculate trend directions
        trends['analysis'] = self._analyze_trends(trends)
        
        return trends
    
    def _analyze_trends(self, trends: Dict) -> Dict:
        """Analyze trend directions and significance"""
        analysis = {
            'overall_direction': 'stable',
            'emergence_direction': 'stable',
            'improving_indicators': [],
            'declining_indicators': [],
            'stable_indicators': []
        }
        
        # Analyze overall score trend
        scores = [t['score'] for t in trends['overall_score_trend']]
        if len(scores) >= 2:
            recent_avg = np.mean(scores[-3:])
            older_avg = np.mean(scores[:-3]) if len(scores) > 3 else scores[0]
            
            if recent_avg > older_avg + 0.1:
                analysis['overall_direction'] = 'improving'
            elif recent_avg < older_avg - 0.1:
                analysis['overall_direction'] = 'declining'
        
        # Analyze indicator trends
        for indicator_id, indicator_trends in trends['indicator_trends'].items():
            scores = [t['score'] for t in indicator_trends]
            if len(scores) >= 2:
                recent = scores[-1]
                older = scores[0]
                
                if recent > older + 0.2:
                    analysis['improving_indicators'].append(indicator_id)
                elif recent < older - 0.2:
                    analysis['declining_indicators'].append(indicator_id)
                else:
                    analysis['stable_indicators'].append(indicator_id)
        
        return analysis
    
    def get_dashboard_data(self) -> Dict:
        """Get current dashboard data for visualization"""
        if not self.assessment_history:
            return {"error": "No assessments available"}
        
        latest = self.assessment_history[-1]
        
        dashboard = {
            'timestamp': latest.timestamp.isoformat(),
            'overall_score': latest.overall_score,
            'emergence_ratio': latest.emergence_ratio,
            'indicators': {},
            'categories': latest.category_scores,
            'alerts': self._check_alerts(latest) if len(self.assessment_history) > 1 else [],
            'trends': {}
        }
        
        # Format indicator data for dashboard
        for indicator in latest.indicators:
            dashboard['indicators'][indicator.indicator_id] = {
                'name': indicator.name,
                'score': indicator.score,
                'confidence': indicator.confidence,
                'evidence_count': len(indicator.evidence)
            }
        
        # Add mini trends if available
        if len(self.assessment_history) > 1:
            dashboard['trends'] = {
                'overall': 'up' if latest.overall_score > self.assessment_history[-2].overall_score else 'down',
                'emergence': 'up' if latest.emergence_ratio > self.assessment_history[-2].emergence_ratio else 'down'
            }
        
        return dashboard


async def main():
    """Main monitoring function"""
    monitor = ConsciousnessMonitor()
    
    try:
        await monitor.start()
        
        # Run single assessment
        logger.info("Running initial assessment...")
        assessment = await monitor.run_assessment()
        
        # Print summary
        print("\n" + "="*60)
        print("CONSCIOUSNESS ASSESSMENT SUMMARY")
        print("="*60)
        print(assessment.summary)
        print("="*60)
        
        # Print detailed scores
        print("\nDETAILED INDICATOR SCORES:")
        print("-"*60)
        for indicator in sorted(assessment.indicators, key=lambda x: x.score, reverse=True):
            print(f"{indicator.name:40} {indicator.score:.2f}/3.0 ({indicator.confidence})")
            if indicator.evidence:
                print(f"  Evidence: {indicator.evidence[0]}")
        
        # Ask if user wants continuous monitoring
        response = input("\nStart continuous monitoring? (y/n): ")
        if response.lower() == 'y':
            interval = int(input("Monitoring interval in minutes (default 30): ") or "30")
            await monitor.continuous_monitoring(interval)
        
    finally:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())