import React, { useMemo } from 'react';
import { FaInfoCircle, FaExclamationTriangle } from 'react-icons/fa';
import { LineChart, Line, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface PhaseAnalysisProps {
  transactions: any[];
  citizens: any[];
  timeSeriesData: any[];
}

export const EconomicPhaseAnalysis: React.FC<PhaseAnalysisProps> = ({
  transactions,
  citizens,
  timeSeriesData
}) => {
  // Calculate variance and autocorrelation for early warning signals
  const earlyWarningSignals = useMemo(() => {
    if (timeSeriesData.length < 10) return null;
    
    // Calculate rolling variance and lag-1 autocorrelation
    const windowSize = 10;
    const signals = [];
    
    for (let i = windowSize; i < timeSeriesData.length; i++) {
      const window = timeSeriesData.slice(i - windowSize, i);
      const values = window.map(d => d.value);
      
      // Calculate variance
      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
      
      // Calculate lag-1 autocorrelation
      let autocorr = 0;
      if (values.length > 1) {
        const shifted = values.slice(1);
        const original = values.slice(0, -1);
        const correlation = calculateCorrelation(original, shifted);
        autocorr = correlation;
      }
      
      signals.push({
        time: window[window.length - 1].time,
        variance,
        autocorrelation: autocorr,
        criticalSlowingDown: variance > 0.5 && autocorr > 0.7
      });
    }
    
    return signals;
  }, [timeSeriesData]);

  // Calculate phase space data (money velocity vs Gini coefficient)
  const phaseSpaceData = useMemo(() => {
    if (transactions.length === 0 || citizens.length === 0) return [];
    
    // Group transactions by day
    const dailyData: { [date: string]: { transactions: any[], velocity: number } } = {};
    
    transactions.forEach(tx => {
      const date = new Date(tx.timestamp).toISOString().split('T')[0];
      if (!dailyData[date]) {
        dailyData[date] = { transactions: [], velocity: 0 };
      }
      dailyData[date].transactions.push(tx);
    });
    
    // Calculate daily metrics
    return Object.entries(dailyData).map(([date, data]) => {
      // Money velocity = total transaction value / total money supply
      const totalValue = data.transactions.reduce((sum, tx) => sum + tx.amount, 0);
      const totalWealth = citizens.reduce((sum, c) => sum + (parseFloat(c.Wealth) || 0), 0);
      const velocity = totalWealth > 0 ? totalValue / totalWealth : 0;
      
      // Calculate Gini coefficient for this day
      const gini = calculateGiniCoefficient(citizens.map(c => parseFloat(c.Wealth) || 0));
      
      return {
        date,
        velocity,
        gini,
        transactionCount: data.transactions.length
      };
    });
  }, [transactions, citizens]);

  // Detect economic phase
  const currentPhase = useMemo(() => {
    if (phaseSpaceData.length === 0) return 'Unknown';
    
    const latest = phaseSpaceData[phaseSpaceData.length - 1];
    const { velocity, gini } = latest;
    
    if (velocity < 0.1 && gini < 0.4) return 'Stagnant';
    if (velocity < 0.1 && gini >= 0.4) return 'Feudal';
    if (velocity >= 0.1 && gini < 0.4) return 'Socialist';
    if (velocity >= 0.1 && gini >= 0.4) return 'Capitalist';
    
    return 'Transitional';
  }, [phaseSpaceData]);

  // Check for critical warnings
  const criticalWarnings = useMemo(() => {
    const warnings = [];
    
    if (earlyWarningSignals && earlyWarningSignals.length > 0) {
      const recent = earlyWarningSignals.slice(-5);
      const criticalCount = recent.filter(s => s.criticalSlowingDown).length;
      
      if (criticalCount >= 3) {
        warnings.push({
          type: 'critical',
          message: 'Critical slowing down detected - phase transition may be imminent'
        });
      }
    }
    
    if (phaseSpaceData.length > 1) {
      const recent = phaseSpaceData.slice(-2);
      const velocityChange = Math.abs(recent[1].velocity - recent[0].velocity);
      
      if (velocityChange > 0.2) {
        warnings.push({
          type: 'warning',
          message: 'Rapid velocity change detected - economic shock in progress'
        });
      }
    }
    
    return warnings;
  }, [earlyWarningSignals, phaseSpaceData]);

  return (
    <div className="space-y-6">
      {/* Phase Transition Warnings */}
      {criticalWarnings.length > 0 && (
        <div className="space-y-2">
          {criticalWarnings.map((warning, idx) => (
            <div 
              key={idx} 
              className={`p-4 rounded-lg border ${
                warning.type === 'critical' 
                  ? 'bg-red-50 border-red-500 text-red-800' 
                  : 'bg-yellow-50 border-yellow-500 text-yellow-800'
              }`}
            >
              <div className="flex items-start gap-2">
                <FaExclamationTriangle className="w-4 h-4 mt-0.5" />
                <p className="text-sm">{warning.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Current Economic Phase */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-base font-semibold mb-4">Current Economic Phase</h4>
        <div className="text-center">
          <p className="text-3xl font-bold mb-2">{currentPhase}</p>
          <p className="text-sm text-gray-600">
            Based on money velocity and wealth distribution
          </p>
        </div>
      </div>

      {/* Phase Space Portrait */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="mb-4">
          <h4 className="text-base font-semibold">Economic Phase Space</h4>
          <p className="text-sm text-gray-600">
            Money velocity vs wealth inequality trajectory
          </p>
        </div>
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="velocity" 
              label={{ value: 'Money Velocity', position: 'insideBottom', offset: -5 }}
              domain={[0, 'auto']}
            />
            <YAxis 
              dataKey="gini" 
              label={{ value: 'Gini Coefficient', angle: -90, position: 'insideLeft' }}
              domain={[0, 1]}
            />
            <Tooltip 
              formatter={(value: number) => value.toFixed(3)}
              labelFormatter={(label) => `Date: ${label}`}
            />
            <ReferenceLine x={0.1} stroke="#666" strokeDasharray="3 3" />
            <ReferenceLine y={0.4} stroke="#666" strokeDasharray="3 3" />
            <Scatter
              data={phaseSpaceData}
              fill="#8884d8"
              line={{ stroke: '#8884d8', strokeWidth: 1 }}
            />
          </ScatterChart>
        </ResponsiveContainer>
        
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-blue-50 rounded">
            <p className="font-medium">Socialist</p>
            <p className="text-gray-600">High velocity, Low inequality</p>
          </div>
          <div className="p-3 bg-green-50 rounded">
            <p className="font-medium">Capitalist</p>
            <p className="text-gray-600">High velocity, High inequality</p>
          </div>
          <div className="p-3 bg-gray-50 rounded">
            <p className="font-medium">Stagnant</p>
            <p className="text-gray-600">Low velocity, Low inequality</p>
          </div>
          <div className="p-3 bg-red-50 rounded">
            <p className="font-medium">Feudal</p>
            <p className="text-gray-600">Low velocity, High inequality</p>
          </div>
        </div>
      </div>

      {/* Early Warning Signals */}
      {earlyWarningSignals && earlyWarningSignals.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="mb-4">
            <h4 className="text-base font-semibold">Early Warning Signals</h4>
            <p className="text-sm text-gray-600">
              Variance and autocorrelation indicate approaching phase transitions
            </p>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={earlyWarningSignals}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line 
                type="monotone" 
                dataKey="variance" 
                stroke="#8884d8" 
                name="Variance"
                strokeWidth={2}
              />
              <Line 
                type="monotone" 
                dataKey="autocorrelation" 
                stroke="#82ca9d" 
                name="Autocorrelation"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
          
          <div className="mt-4 p-4 bg-gray-100 rounded-lg">
            <div className="flex items-start gap-2">
              <FaInfoCircle className="w-4 h-4 mt-0.5 text-gray-600" />
              <div className="text-sm text-gray-700">
                <p><strong>Rising variance:</strong> System becoming more volatile</p>
                <p><strong>Rising autocorrelation:</strong> System "remembering" states longer</p>
                <p><strong>Both rising together:</strong> Critical slowing down - phase transition approaching</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Helper function to calculate correlation
function calculateCorrelation(x: number[], y: number[]): number {
  const n = x.length;
  if (n !== y.length || n === 0) return 0;
  
  const meanX = x.reduce((a, b) => a + b, 0) / n;
  const meanY = y.reduce((a, b) => a + b, 0) / n;
  
  let numerator = 0;
  let denomX = 0;
  let denomY = 0;
  
  for (let i = 0; i < n; i++) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    numerator += dx * dy;
    denomX += dx * dx;
    denomY += dy * dy;
  }
  
  const denominator = Math.sqrt(denomX * denomY);
  return denominator === 0 ? 0 : numerator / denominator;
}

function calculateGiniCoefficient(values: number[]): number {
  const sorted = values.filter(v => v > 0).sort((a, b) => a - b);
  const n = sorted.length;
  if (n === 0) return 0;
  
  const sum = sorted.reduce((a, b) => a + b, 0);
  if (sum === 0) return 0;
  
  let giniSum = 0;
  sorted.forEach((value, i) => {
    giniSum += (2 * (i + 1) - n - 1) * value;
  });
  
  return giniSum / (n * sum);
}