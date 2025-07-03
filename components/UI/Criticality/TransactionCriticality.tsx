import React, { useState, useEffect, useMemo } from 'react';
import { FaInfoCircle, FaChartLine, FaSpinner, FaNetworkWired, FaChartBar } from 'react-icons/fa';
import LogLogPlot from './charts/LogLogPlot';
import TimeSeriesChart from './charts/TimeSeriesChart';
import Histogram from './charts/Histogram';
import { EconomicPhaseAnalysis } from './EconomicPhaseAnalysis';
import { format } from 'date-fns';

interface Transaction {
  id: string;
  from: string;
  to: string;
  amount: number;
  timestamp: string;
  type: string;
  resourceType?: string;
}

interface EconomicAvalanche {
  id: string;
  transactions: Transaction[];
  totalValue: number;
  duration: number;
  startTime: string;
  endTime: string;
  participants: string[];
}

interface CitizenWealth {
  username: string;
  wealth: number;
  socialClass: string;
  transactionCount: number;
}

export const TransactionCriticality: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [contracts, setContracts] = useState<any[]>([]);
  const [citizens, setCitizens] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState<number>(3600); // 1 hour in seconds
  const [selectedTab, setSelectedTab] = useState('avalanches');

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch contracts (contains transaction data)
        const contractsRes = await fetch('/api/contracts');
        const contractsData = await contractsRes.json();
        
        // Fetch citizens for wealth data
        const citizensRes = await fetch('/api/citizens');
        const citizensData = await citizensRes.json();
        
        // Fetch economy data
        const economyRes = await fetch('/api/economy');
        const economyData = await economyRes.json();
        
        if (contractsData.success && citizensData.success) {
          setContracts(contractsData.contracts || []);
          setCitizens(citizensData.citizens || []);
          
          // Extract transactions from contracts
          const extractedTransactions = extractTransactionsFromContracts(contractsData.contracts || []);
          setTransactions(extractedTransactions);
        } else {
          setError('Failed to fetch data');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Extract transactions from contracts
  const extractTransactionsFromContracts = (contracts: any[]): Transaction[] => {
    const transactions: Transaction[] = [];
    
    contracts.forEach(contract => {
      if (contract.Status === 'completed' && contract.AcceptedAt) {
        transactions.push({
          id: contract.ContractId,
          from: contract.Buyer,
          to: contract.Seller,
          amount: parseFloat(contract.Price) || 0,
          timestamp: contract.AcceptedAt,
          type: contract.Type || 'trade',
          resourceType: contract.ResourceType
        });
      }
    });
    
    return transactions.sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  };

  // Calculate economic avalanches
  const avalanches = useMemo(() => {
    if (transactions.length === 0) return [];
    
    const avalancheList: EconomicAvalanche[] = [];
    const processed = new Set<string>();
    
    transactions.forEach((transaction, index) => {
      if (processed.has(transaction.id)) return;
      
      const avalanche: Transaction[] = [transaction];
      const participants = new Set<string>([transaction.from, transaction.to]);
      processed.add(transaction.id);
      
      // Find cascading transactions
      let currentTime = new Date(transaction.timestamp).getTime();
      let lastAddedTime = currentTime;
      
      for (let i = index + 1; i < transactions.length; i++) {
        const nextTx = transactions[i];
        const nextTime = new Date(nextTx.timestamp).getTime();
        
        // Check if within time window and involves a participant
        if (nextTime - lastAddedTime <= timeWindow * 1000 && 
            (participants.has(nextTx.from) || participants.has(nextTx.to))) {
          avalanche.push(nextTx);
          participants.add(nextTx.from);
          participants.add(nextTx.to);
          processed.add(nextTx.id);
          lastAddedTime = nextTime;
        }
      }
      
      if (avalanche.length >= 2) {
        avalancheList.push({
          id: `avalanche-${index}`,
          transactions: avalanche,
          totalValue: avalanche.reduce((sum, tx) => sum + tx.amount, 0),
          duration: lastAddedTime - currentTime,
          startTime: transaction.timestamp,
          endTime: avalanche[avalanche.length - 1].timestamp,
          participants: Array.from(participants)
        });
      }
    });
    
    return avalancheList;
  }, [transactions, timeWindow]);

  // Calculate avalanche size distribution
  const avalancheSizeDistribution = useMemo(() => {
    const sizes = avalanches.map(a => a.transactions.length);
    return createDistributionForLogLog(sizes);
  }, [avalanches]);

  // Calculate wealth movement distribution
  const wealthMovementDistribution = useMemo(() => {
    const values = avalanches.map(a => a.totalValue).filter(v => v > 0);
    return createDistributionForLogLog(values);
  }, [avalanches]);

  // Calculate economic branching ratio over time
  const branchingRatioData = useMemo(() => {
    if (transactions.length === 0) return [];
    
    const hourlyBins: { [hour: string]: { triggered: number; original: number } } = {};
    
    transactions.forEach(tx => {
      const hour = format(new Date(tx.timestamp), 'yyyy-MM-dd HH:00');
      if (!hourlyBins[hour]) {
        hourlyBins[hour] = { triggered: 0, original: 0 };
      }
      hourlyBins[hour].original++;
      
      // Count triggered transactions (simplified: transactions by receiver in next hour)
      const nextHour = new Date(new Date(tx.timestamp).getTime() + 3600000);
      const nextHourKey = format(nextHour, 'yyyy-MM-dd HH:00');
      
      const triggeredCount = transactions.filter(nextTx => {
        const txTime = new Date(nextTx.timestamp);
        return nextTx.from === tx.to && 
               txTime >= nextHour && 
               txTime < new Date(nextHour.getTime() + 3600000);
      }).length;
      
      if (hourlyBins[nextHourKey]) {
        hourlyBins[nextHourKey].triggered += triggeredCount;
      }
    });
    
    return Object.entries(hourlyBins)
      .filter(([_, data]) => data.original > 0)
      .map(([hour, data]) => ({
        time: hour,
        value: data.triggered / data.original,
        label: 'σ_econ'
      }));
  }, [transactions]);

  // Calculate wealth distribution
  const wealthDistribution = useMemo(() => {
    const wealthData = citizens
      .filter(c => c.Wealth > 0)
      .map(c => ({
        username: c.Username,
        wealth: parseFloat(c.Wealth) || 0,
        socialClass: c.SocialClass || 'Unknown'
      }))
      .sort((a, b) => b.wealth - a.wealth);
    
    return wealthData.map((citizen, index) => ({
      size: index + 1,
      count: citizen.wealth,
      label: citizen.username
    }));
  }, [citizens]);

  // Helper function to create distribution data for LogLogPlot
  function createDistributionForLogLog(values: number[]): { size: number; count: number }[] {
    const counts: { [key: number]: number } = {};
    values.forEach(v => {
      counts[v] = (counts[v] || 0) + 1;
    });
    
    return Object.entries(counts)
      .map(([value, count]) => ({
        size: parseFloat(value),
        count: count
      }))
      .filter(d => d.size > 0 && d.count > 0)
      .sort((a, b) => a.size - b.size);
  }

  // Helper function to create distribution data for other charts
  function createDistribution(values: number[]): { x: number; y: number }[] {
    const counts: { [key: number]: number } = {};
    values.forEach(v => {
      counts[v] = (counts[v] || 0) + 1;
    });
    
    return Object.entries(counts)
      .map(([value, count]) => ({
        x: parseFloat(value),
        y: count
      }))
      .filter(d => d.x > 0 && d.y > 0)
      .sort((a, b) => a.x - b.x);
  }

  if (loading) {
    return (
      <div className="p-8 text-center">
        <FaSpinner className="w-8 h-8 animate-spin mx-auto mb-4" />
        <p>Loading transaction data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-4 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6 p-4">
      <div className="bg-white rounded-lg shadow-md">
        <div className="p-6 border-b">
          <h3 className="text-xl font-semibold flex items-center gap-2">
            <FaChartLine className="w-5 h-5" />
            Economic Criticality Analysis
          </h3>
          <p className="text-gray-600 mt-1">
            Analyzing self-organized criticality in La Serenissima's transaction network
          </p>
        </div>
        <div className="p-6">
          <div className="mb-4 flex gap-4 items-center">
            <select 
              value={timeWindow.toString()} 
              onChange={(e) => setTimeWindow(parseInt(e.target.value))}
              className="w-48 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="900">15 minutes</option>
              <option value="3600">1 hour</option>
              <option value="14400">4 hours</option>
              <option value="86400">24 hours</option>
            </select>
            <span className="text-sm text-gray-600">
              Time window for cascade detection
            </span>
          </div>

          <div className="space-y-6">
            <div className="flex space-x-1 border-b">
              {['avalanches', 'branching', 'wealth', 'network', 'phase'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setSelectedTab(tab)}
                  className={`px-4 py-2 font-medium capitalize transition-colors ${
                    selectedTab === tab
                      ? 'text-blue-600 border-b-2 border-blue-600'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {selectedTab === 'avalanches' && (
              <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="mb-4">
                    <h4 className="text-base font-semibold">Economic Avalanche Sizes</h4>
                    <p className="text-sm text-gray-600">
                      Power-law distribution of transaction cascade sizes
                    </p>
                  </div>
                    <div className="h-64">
                      <LogLogPlot
                        data={avalancheSizeDistribution}
                        xlabel="Avalanche Size (transactions)"
                        ylabel="Frequency"
                        expectedSlope={-1.5}
                      />
                    </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="mb-4">
                    <h4 className="text-base font-semibold">Wealth Movement Distribution</h4>
                    <p className="text-sm text-gray-600">
                      Total value moved in economic avalanches
                    </p>
                  </div>
                    <div className="h-64">
                      <LogLogPlot
                        data={wealthMovementDistribution}
                        xlabel="Total Ducats Moved"
                        ylabel="Frequency"
                        expectedSlope={-2.0}
                      />
                    </div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-base font-semibold mb-4">Avalanche Statistics</h4>
                  <div className="grid grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Total Avalanches</p>
                      <p className="text-2xl font-bold">{avalanches.length}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Avg Size</p>
                      <p className="text-2xl font-bold">
                        {avalanches.length > 0 
                          ? (avalanches.reduce((sum, a) => sum + a.transactions.length, 0) / avalanches.length).toFixed(1)
                          : '0'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Largest Cascade</p>
                      <p className="text-2xl font-bold">
                        {avalanches.length > 0 
                          ? Math.max(...avalanches.map(a => a.transactions.length))
                          : '0'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Max Value Moved</p>
                      <p className="text-2xl font-bold">
                        {avalanches.length > 0 
                          ? Math.max(...avalanches.map(a => a.totalValue)).toLocaleString()
                          : '0'} D
                      </p>
                    </div>
                  </div>
              </div>
              </div>
            )}

            {selectedTab === 'branching' && (
              <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="mb-4">
                  <h4 className="text-base font-semibold">Economic Branching Ratio (σ_econ)</h4>
                  <p className="text-sm text-gray-600">
                    How many transactions are triggered by each transaction
                  </p>
                </div>
                  <div style={{ height: 400 }}>
                    <TimeSeriesChart
                      data={branchingRatioData}
                      yField="value"
                      xlabel="Time"
                      ylabel="Branching Ratio (σ)"
                      criticalLine={1.0}
                    />
                  </div>
                  <div className="mt-4 p-4 bg-gray-100 rounded-lg">
                    <div className="flex items-start gap-2">
                      <FaInfoCircle className="w-4 h-4 mt-0.5 text-gray-600" />
                      <div className="text-sm text-gray-700">
                        <p><strong>σ &lt; 1:</strong> Frozen economy - money velocity decreasing</p>
                        <p><strong>σ = 1:</strong> Critical state - sustainable economic activity</p>
                        <p><strong>σ &gt; 1:</strong> Bubbling economy - unsustainable growth</p>
                      </div>
                    </div>
                  </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-base font-semibold mb-4">Branching Statistics</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Current σ</p>
                      <p className="text-2xl font-bold">
                        {branchingRatioData.length > 0 
                          ? branchingRatioData[branchingRatioData.length - 1].value.toFixed(3)
                          : '0.000'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Average σ</p>
                      <p className="text-2xl font-bold">
                        {branchingRatioData.length > 0 
                          ? (branchingRatioData.reduce((sum, d) => sum + d.value, 0) / branchingRatioData.length).toFixed(3)
                          : '0.000'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Economic State</p>
                      <p className="text-2xl font-bold">
                        {branchingRatioData.length > 0 
                          ? branchingRatioData[branchingRatioData.length - 1].value < 0.95 
                            ? 'Frozen'
                            : branchingRatioData[branchingRatioData.length - 1].value > 1.05
                              ? 'Bubbling'
                              : 'Critical'
                          : 'Unknown'}
                      </p>
                    </div>
                  </div>
              </div>
              </div>
            )}

            {selectedTab === 'wealth' && (
              <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="mb-4">
                  <h4 className="text-base font-semibold">Wealth Distribution (Zipf Plot)</h4>
                  <p className="text-sm text-gray-600">
                    Power-law distribution of citizen wealth
                  </p>
                </div>
                  <div className="h-64">
                    <LogLogPlot
                      data={wealthDistribution}
                      xlabel="Wealth Rank"
                      ylabel="Wealth (Ducats)"
                      expectedSlope={-1.0}
                    />
                  </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-base font-semibold mb-4">Wealth Statistics</h4>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-600">Gini Coefficient</p>
                      <p className="text-2xl font-bold">
                        {calculateGiniCoefficient(citizens.map(c => parseFloat(c.Wealth) || 0)).toFixed(3)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Wealth Concentration</p>
                      <div className="space-y-2 mt-2">
                        <div className="flex justify-between">
                          <span className="text-sm">Top 10%</span>
                          <span className="font-medium">{calculateWealthShare(citizens, 0.1).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm">Top 20%</span>
                          <span className="font-medium">{calculateWealthShare(citizens, 0.2).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm">Bottom 50%</span>
                          <span className="font-medium">{calculateWealthShare(citizens, 0.5, true).toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
              </div>
              </div>
            )}

            {selectedTab === 'network' && (
              <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-base font-semibold mb-4">Transaction Network Analysis</h4>
                  <div className="space-y-4">
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start gap-2">
                        <FaInfoCircle className="w-4 h-4 text-blue-600 mt-0.5" />
                        <p className="text-sm text-blue-800">
                          Full network visualization coming soon. Current analysis based on {transactions.length} transactions.
                        </p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">Unique Trading Pairs</p>
                        <p className="text-2xl font-bold">
                          {new Set(transactions.map(t => `${t.from}-${t.to}`)).size}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Active Traders</p>
                        <p className="text-2xl font-bold">
                          {new Set([...transactions.map(t => t.from), ...transactions.map(t => t.to)]).size}
                        </p>
                      </div>
                    </div>
                  </div>
              </div>
              </div>
            )}

            {selectedTab === 'phase' && (
              <div className="space-y-6">
                <EconomicPhaseAnalysis 
                  transactions={transactions}
                  citizens={citizens}
                  timeSeriesData={branchingRatioData}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper functions
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

function calculateWealthShare(citizens: any[], percentile: number, bottom: boolean = false): number {
  const sorted = citizens
    .map(c => parseFloat(c.Wealth) || 0)
    .filter(w => w > 0)
    .sort((a, b) => bottom ? a - b : b - a);
  
  const totalWealth = sorted.reduce((sum, w) => sum + w, 0);
  if (totalWealth === 0) return 0;
  
  const count = Math.floor(sorted.length * percentile);
  const shareWealth = sorted.slice(0, count).reduce((sum, w) => sum + w, 0);
  
  return (shareWealth / totalWealth) * 100;
}