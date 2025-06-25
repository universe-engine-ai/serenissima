import React, { useState, useEffect } from 'react';
import { FaTimes, FaSpinner, FaChartLine, FaCoins, FaHandHoldingUsd, FaUsers } from 'react-icons/fa';
import AnimatedDucats from './AnimatedDucats';
import CitizenIncomeGraphs from './CitizenIncomeGraphs';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface EconomyPanelProps {
  onClose: () => void;
}

interface EconomyData {
  totalDucats: number;
  transactionsTotal: number;
  projectedYearlyGDP: number;
  totalLoans: number;
  citizenCount: number;
  transactionCount: number;
  loanCount: number;
  giniCoefficient: number;
  lastUpdated: string;
}

interface TransactionTypeData {
  type: string;
  totalAmount: number;
  count: number;
}

const EconomyPanel: React.FC<EconomyPanelProps> = ({ onClose }) => {
  const [economyData, setEconomyData] = useState<EconomyData | null>(null);
  const [transactionsByType, setTransactionsByType] = useState<TransactionTypeData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingTransactions, setIsLoadingTransactions] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'citizens'>('overview');
  
  // Fetch economy data
  useEffect(() => {
    fetchEconomyData();
    fetchTransactionsByType();
  }, []);
  
  const fetchEconomyData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch('/api/economy');
      if (!response.ok) {
        throw new Error(`Failed to fetch economy data: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success && data.economy) {
        setEconomyData(data.economy);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err) {
      console.error('Error fetching economy data:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };
  
  const fetchTransactionsByType = async () => {
    try {
      setIsLoadingTransactions(true);
      
      // Calculate 24 hours ago
      const twentyFourHoursAgo = new Date();
      twentyFourHoursAgo.setHours(twentyFourHoursAgo.getHours() - 24);
      
      const response = await fetch('/api/transactions/history');
      if (!response.ok) {
        throw new Error(`Failed to fetch transactions: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success && data.transactions) {
        // Filter transactions from the last 24 hours
        const recentTransactions = data.transactions.filter((transaction: any) => {
          const executedAt = new Date(transaction.executedAt);
          return executedAt >= twentyFourHoursAgo;
        });
        
        // Group transactions by type and sum amounts
        const transactionMap = new Map<string, { totalAmount: number; count: number }>();
        
        recentTransactions.forEach((transaction: any) => {
          const type = transaction.type || 'Unknown';
          const price = transaction.price || 0;
          
          if (!transactionMap.has(type)) {
            transactionMap.set(type, { totalAmount: 0, count: 0 });
          }
          
          const typeData = transactionMap.get(type)!;
          typeData.totalAmount += price;
          typeData.count += 1;
        });
        
        // Convert to array and sort by totalAmount
        const transactionArray = Array.from(transactionMap.entries())
          .map(([type, data]) => ({
            type,
            totalAmount: data.totalAmount,
            count: data.count
          }))
          .sort((a, b) => b.totalAmount - a.totalAmount);
        
        console.log('Transaction types data:', transactionArray);
        setTransactionsByType(transactionArray);
      }
    } catch (err) {
      console.error('Error fetching transactions by type:', err);
      // Don't set error state since this is a secondary feature
    } finally {
      setIsLoadingTransactions(false);
    }
  };
  
  // Pie chart colors
  const COLORS = [
    '#EF4444', // red-500
    '#F59E0B', // amber-500
    '#10B981', // emerald-500
    '#3B82F6', // blue-500
    '#8B5CF6', // violet-500
    '#EC4899', // pink-500
    '#14B8A6', // teal-500
    '#6366F1', // indigo-500
    '#F97316', // orange-500
    '#84CC16', // lime-500
  ];
  
  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  return (
    <div className="fixed inset-0 bg-black/80 z-50 overflow-auto">
      <div className="bg-amber-50 border-2 border-amber-700 rounded-lg p-6 max-w-4xl mx-auto my-20">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-3xl font-serif text-amber-800 flex items-center">
            <FaChartLine className="mr-3" />
            Economy of La Serenissima
          </h2>
          <button 
            onClick={onClose}
            className="text-amber-600 hover:text-amber-800 transition-colors"
            aria-label="Close"
          >
            <FaTimes size={24} />
          </button>
        </div>
        
        {/* Tabs */}
        <div className="border-b border-amber-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview' 
                  ? 'border-amber-600 text-amber-800' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('overview')}
            >
              Overview
            </button>
            <button
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'citizens' 
                  ? 'border-amber-600 text-amber-800' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('citizens')}
            >
              Citizens
            </button>
          </nav>
        </div>
        
        {/* Content */}
        <div className="p-2">
          {isLoading && activeTab === 'overview' ? (
            <div className="flex flex-col items-center justify-center py-12">
              <FaSpinner className="animate-spin text-amber-600 text-4xl mb-4" />
              <p className="text-amber-800">Loading economic data...</p>
            </div>
          ) : error && activeTab === 'overview' ? (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg">
              <p className="font-medium">Error loading economic data</p>
              <p className="text-sm mt-1">{error}</p>
              <button 
                onClick={fetchEconomyData}
                className="mt-4 px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          ) : activeTab === 'overview' && economyData ? (
            <div className="space-y-6">
              {/* Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-amber-100 rounded-lg p-4 shadow-sm">
                  <div className="flex items-center text-amber-800 mb-2">
                    <FaCoins className="mr-2" />
                    <h3 className="font-medium">Total Ducats</h3>
                  </div>
                  <p className="text-2xl font-bold text-amber-900">
                    <AnimatedDucats value={economyData.totalDucats} suffix="" prefix="⚜️ " />
                  </p>
                  <p className="text-xs text-amber-700 mt-2">
                    Across {economyData.citizenCount} citizens
                  </p>
                </div>
                
                <div className="bg-amber-100 rounded-lg p-4 shadow-sm">
                  <div className="flex items-center text-amber-800 mb-2">
                    <FaChartLine className="mr-2" />
                    <h3 className="font-medium">Yearly GDP</h3>
                  </div>
                  <p className="text-2xl font-bold text-amber-900">
                    <AnimatedDucats value={economyData.projectedYearlyGDP} suffix="" prefix="⚜️ " />
                  </p>
                  <p className="text-xs text-amber-700 mt-2">
                    Based on {economyData.transactionCount} transactions
                  </p>
                </div>
                
                <div className="bg-amber-100 rounded-lg p-4 shadow-sm">
                  <div className="flex items-center text-amber-800 mb-2">
                    <FaHandHoldingUsd className="mr-2" />
                    <h3 className="font-medium">Outstanding Loans</h3>
                  </div>
                  <p className="text-2xl font-bold text-amber-900">
                    <AnimatedDucats value={economyData.totalLoans} suffix="" prefix="⚜️ " />
                  </p>
                  <p className="text-xs text-amber-700 mt-2">
                    Across {economyData.loanCount} active loans
                  </p>
                </div>
              </div>
              
              {/* Additional Statistics */}
              <div className="bg-white rounded-lg p-6 shadow-sm border border-amber-200">
                <h3 className="text-lg font-medium text-amber-800 mb-4">Economic Indicators</h3>
                
                <div className="space-y-4">
                  <div className="flex justify-between items-center pb-2 border-b border-amber-100">
                    <span className="text-amber-700">Per Capita Wealth</span>
                    <span className="font-medium text-amber-900">
                      ⚜️ {Math.floor(economyData.totalDucats / Math.max(1, economyData.citizenCount))}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center pb-2 border-b border-amber-100">
                    <span className="text-amber-700">Average Transaction Value</span>
                    <span className="font-medium text-amber-900">
                      ⚜️ {Math.floor(economyData.transactionsTotal / Math.max(1, economyData.transactionCount))}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center pb-2 border-b border-amber-100">
                    <span className="text-amber-700">Average Loan Amount</span>
                    <span className="font-medium text-amber-900">
                      ⚜️ {Math.floor(economyData.totalLoans / Math.max(1, economyData.loanCount))}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center pb-2 border-b border-amber-100">
                    <span className="text-amber-700">Debt to GDP Ratio</span>
                    <span className="font-medium text-amber-900">
                      {((economyData.totalLoans / Math.max(1, economyData.projectedYearlyGDP)) * 100).toFixed(1)}%
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center pb-2 border-b border-amber-100">
                    <span className="text-amber-700 flex items-center">
                      Gini Coefficient
                      <span className="ml-1 text-xs text-amber-600 italic">(excl. ConsiglioDeiDieci, Italia)</span>
                    </span>
                    <span className="font-medium text-amber-900">
                      {economyData.giniCoefficient.toFixed(3)}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Transaction Types Pie Chart */}
              {!isLoadingTransactions && transactionsByType.length > 0 && (
                <div className="bg-white rounded-lg p-6 shadow-sm border border-amber-200">
                  <h3 className="text-lg font-medium text-amber-800 mb-4">24-Hour Transaction Volume by Type</h3>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={transactionsByType}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ type, totalAmount, percent }) => 
                            `${type}: ⚜️${Math.floor(totalAmount)} (${(percent * 100).toFixed(0)}%)`
                          }
                          outerRadius={100}
                          fill="#8884d8"
                          dataKey="totalAmount"
                        >
                          {transactionsByType.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip 
                          formatter={(value: number, name: string, props: any) => [
                            `⚜️ ${Math.floor(value)} (${props.payload.count} transactions)`,
                            props.payload.type
                          ]}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-4 text-sm text-amber-600">
                    Total: ⚜️ {Math.floor(transactionsByType.reduce((sum, t) => sum + t.totalAmount, 0))} across {transactionsByType.reduce((sum, t) => sum + t.count, 0)} transactions
                  </div>
                </div>
              )}
              
              {/* Historical Context */}
              <div className="bg-amber-50 rounded-lg p-6 shadow-sm border border-amber-200">
                <h3 className="text-lg font-medium text-amber-800 mb-2">Historical Context</h3>
                <p className="text-amber-700 italic">
                  "In the 16th century, Venice was one of the richest cities in Europe. The Republic's wealth came from its maritime trade, manufacturing, and banking activities. The city's economy was carefully regulated by the government to ensure stability and prosperity."
                </p>
              </div>
              
              <div className="text-right text-xs text-amber-600">
                Last updated: {formatDate(economyData.lastUpdated)}
              </div>
            </div>
          ) : activeTab === 'overview' ? (
            <div className="text-center py-8 text-amber-700">
              No economic data available
            </div>
          ) : activeTab === 'citizens' ? (
            <CitizenIncomeGraphs limit={10} />
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default EconomyPanel;
