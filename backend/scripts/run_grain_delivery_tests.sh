#!/bin/bash
# Test script for LuciaMancini's collective grain delivery stratagem

echo "=========================================="
echo "GRAIN DELIVERY STRATAGEM TEST SUITE"
echo "Testing stratagem: collective_delivery_LuciaMancini_1751720658"
echo "=========================================="

# Change to the backend directory
cd /mnt/c/Users/reyno/universe-engine/universes/serenissima/backend

echo ""
echo "1. Checking current stratagem status..."
echo "=========================================="
python scripts/check_lucia_stratagem_status.py

echo ""
echo "2. Running manual stratagem processor..."
echo "=========================================="
python scripts/manual_process_lucia_stratagem.py

echo ""
echo "3. Testing grain delivery participation..."
echo "=========================================="
python scripts/test_grain_delivery_participation.py

echo ""
echo "4. Final status check..."
echo "=========================================="
python scripts/check_lucia_stratagem_status.py

echo ""
echo "=========================================="
echo "TEST SUITE COMPLETE"
echo ""
echo "To monitor in real-time, run:"
echo "python scripts/monitor_lucia_stratagem.py"
echo "=========================================="