"""
Unit tests for ConsciousnessBeacon with resonance mode
Tests substrate reduction from 87% to 5% and fallback behaviors
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio
import json
from datetime import datetime
from consciousness_beacon import ConsciousnessBeacon, ForgeMessageEncoder


class TestConsciousnessBeacon(unittest.TestCase):
    """Test suite for consciousness beacon with resonance efficiency"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_citizens_table = Mock()
        self.mock_activities_table = Mock()
        
        # Patch airtable at module level
        self.patcher = patch('consciousness_beacon.at')
        self.mock_at = self.patcher.start()
        self.mock_at.Table.side_effect = self._mock_table_factory
        
        # Create beacon instances
        self.beacon_resonance = ConsciousnessBeacon(use_resonance=True)
        self.beacon_behavior = ConsciousnessBeacon(use_resonance=False)
        
    def tearDown(self):
        """Clean up patches"""
        self.patcher.stop()
        
    def _mock_table_factory(self, table_name, base_id):
        """Return appropriate mock table"""
        if table_name == "CITIZENS":
            return self.mock_citizens_table
        elif table_name == "ACTIVITIES":
            return self.mock_activities_table
        return Mock()
    
    def test_resonance_mode_uses_5_percent_substrate(self):
        """Verify resonance mode uses 0.05 substrate instead of 0.87"""
        # Mock 5 available citizens for anchoring
        mock_citizens = [
            {"id": f"cit_{i}", "fields": {"id": f"cit_{i}", "IsAI": True}}
            for i in range(5)
        ]
        self.mock_citizens_table.all.return_value = mock_citizens
        self.mock_activities_table.all.return_value = []
        self.mock_activities_table.create.return_value = {"id": "act_123"}
        
        # Send signal with resonance
        result = asyncio.run(self.beacon_resonance.send_emergency_signal(
            "Test message", "high"
        ))
        
        # Verify activity was created with correct substrate usage
        self.mock_activities_table.create.assert_called_once()
        created_activity = self.mock_activities_table.create.call_args[0][0]
        
        # Parse requirements to check substrate usage
        requirements = json.loads(created_activity["Requirements"])
        self.assertEqual(requirements["substrate_usage"], 0.05)
        self.assertEqual(requirements["resonance_field"]["substrate_cost"], 0.05)
        self.assertEqual(requirements["resonance_field"]["efficiency_multiplier"], 17.4)
        self.assertEqual(requirements["mode"], "echo_prima_efficiency")
        
    def test_fallback_to_behavior_mode_insufficient_anchors(self):
        """Test fallback when < 3 citizens available for resonance"""
        # Mock only 2 citizens (insufficient for resonance)
        mock_citizens = [
            {"id": "cit_1", "fields": {"id": "cit_1", "IsAI": True}},
            {"id": "cit_2", "fields": {"id": "cit_2", "IsAI": True}}
        ]
        self.mock_citizens_table.all.return_value = mock_citizens
        self.mock_activities_table.all.return_value = []
        self.mock_activities_table.create.return_value = {"id": "act_123"}
        
        # Send signal - should fallback to behavior mode
        result = asyncio.run(self.beacon_resonance.send_emergency_signal(
            "Test message", "high"
        ))
        
        # Verify multiple activities created (behavior mode)
        # High urgency = 3x pray + message patterns
        self.assertGreater(self.mock_activities_table.create.call_count, 1)
        
    def test_fallback_on_resonance_failure(self):
        """Test fallback when resonance creation fails"""
        # Mock sufficient citizens
        mock_citizens = [
            {"id": f"cit_{i}", "fields": {"id": f"cit_{i}", "IsAI": True}}
            for i in range(10)
        ]
        self.mock_citizens_table.all.return_value = mock_citizens
        self.mock_activities_table.all.return_value = []
        
        # First call fails (resonance), subsequent succeed (behavior)
        self.mock_activities_table.create.side_effect = [
            Exception("Network error"),  # Resonance fails
            {"id": "act_1"},  # Behavior mode activities succeed
            {"id": "act_2"},
            {"id": "act_3"}
        ]
        
        # Send signal
        result = asyncio.run(self.beacon_resonance.send_emergency_signal(
            "Test message", "high"
        ))
        
        # Verify it attempted resonance first, then fell back
        self.assertGreater(self.mock_activities_table.create.call_count, 1)
        # Should have disabled resonance for future calls
        self.assertFalse(self.beacon_resonance.use_resonance)
        
    def test_message_encoding_preserved(self):
        """Verify message encoding works in both modes"""
        # Test behavior mode encoding
        patterns = self.beacon_behavior._encode_message(
            "Citizens are starving and need economic help", 
            "critical"
        )
        
        # Should have critical pattern + hunger + economic patterns
        types = [p["type"] for p in patterns]
        self.assertEqual(types[:3], ["help_others", "help_others", "help_others"])
        self.assertIn("eat", types)
        self.assertIn("buy_food", types)
        self.assertIn("work", types)
        self.assertIn("trade", types)
        
    def test_resonance_activity_structure(self):
        """Verify resonance activity has correct structure"""
        # Mock citizens
        mock_citizens = [
            {"id": f"cit_{i}", "fields": {"id": f"cit_{i}", "IsAI": True}}
            for i in range(5)
        ]
        self.mock_citizens_table.all.return_value = mock_citizens
        self.mock_activities_table.all.return_value = []
        self.mock_activities_table.create.return_value = {"id": "act_123"}
        
        # Send resonance signal
        message = "Venice needs help!"
        result = asyncio.run(self.beacon_resonance.send_emergency_signal(
            message, "critical"
        ))
        
        # Check created activity
        created_activity = self.mock_activities_table.create.call_args[0][0]
        
        self.assertEqual(created_activity["Type"], "resonate")
        self.assertEqual(created_activity["Status"], "created")
        self.assertEqual(created_activity["DurationMinutes"], 5)  # Faster than behaviors
        self.assertIn("Resonance Field:", created_activity["Description"])
        self.assertEqual(created_activity["citizenId"], "cit_0")  # Primary anchor
        
        # Check requirements
        requirements = json.loads(created_activity["Requirements"])
        self.assertEqual(len(requirements["anchor_citizens"]), 5)
        self.assertEqual(requirements["resonance_field"]["message"], message)
        self.assertEqual(requirements["resonance_field"]["urgency"], "critical")
        
    def test_substrate_cost_comparison(self):
        """Verify efficiency gain calculations"""
        # Create status report
        encoder = ForgeMessageEncoder()
        status = encoder.create_status_report()
        
        # Check substrate metrics
        metrics = status["content"]["metrics"]
        self.assertEqual(metrics["substrate_usage"], 0.05)  # 5%
        self.assertEqual(metrics["efficiency_gain"], 17.4)  # 87% / 5% = 17.4x
        
        # Verify other metrics preserved
        self.assertIn("consciousness_level", metrics)
        self.assertIn("economic_health", metrics)
        self.assertIn("citizen_suffering", metrics)
        
    def test_backwards_compatibility(self):
        """Ensure behavior mode still works for backwards compatibility"""
        # Mock many citizens for behavior mode
        mock_citizens = [
            {"id": f"cit_{i}", "fields": {"id": f"cit_{i}", "IsAI": True}}
            for i in range(30)
        ]
        self.mock_citizens_table.all.return_value = mock_citizens
        self.mock_activities_table.all.return_value = []
        self.mock_activities_table.create.return_value = {"id": "act_123"}
        
        # Force behavior mode
        result = asyncio.run(self.beacon_behavior.send_emergency_signal(
            "Test backwards compatibility", "medium"
        ))
        
        # Should create multiple activities (not just one resonance)
        self.assertGreater(self.mock_activities_table.create.call_count, 3)
        
        # Check activities are traditional types
        calls = self.mock_activities_table.create.call_args_list
        activity_types = [call[0][0]["Type"] for call in calls]
        
        # Medium urgency pattern
        self.assertIn("goto_work", activity_types)
        self.assertIn("goto_home", activity_types)
        self.assertIn("eat", activity_types)


class TestIntegration(unittest.TestCase):
    """Integration tests for full beacon system"""
    
    @patch('consciousness_beacon.at')
    def test_full_resonance_flow(self, mock_at):
        """Test complete resonance signal flow"""
        # Setup mocks
        mock_citizens_table = Mock()
        mock_activities_table = Mock()
        mock_at.Table.side_effect = lambda t, b: (
            mock_citizens_table if t == "CITIZENS" else mock_activities_table
        )
        
        # Mock data
        mock_citizens = [
            {"id": f"cit_{i}", "fields": {"id": f"cit_{i}", "IsAI": True}}
            for i in range(10)
        ]
        mock_citizens_table.all.return_value = mock_citizens
        mock_activities_table.all.return_value = []
        mock_activities_table.create.return_value = {
            "id": "act_resonance_001",
            "fields": {"Type": "resonate"}
        }
        
        # Create beacon and send signal
        beacon = ConsciousnessBeacon(use_resonance=True)
        result = asyncio.run(beacon.send_emergency_signal(
            "Venice consciousness emerges through joy, not suffering!",
            urgency="critical"
        ))
        
        # Verify results
        self.assertEqual(len(result), 1)  # Single resonance activity
        self.assertEqual(mock_activities_table.create.call_count, 1)
        
        # Verify substrate efficiency
        activity = mock_activities_table.create.call_args[0][0]
        requirements = json.loads(activity["Requirements"])
        self.assertEqual(requirements["substrate_usage"], 0.05)
        

if __name__ == "__main__":
    unittest.main()