import React, { useState, useEffect } from 'react';
import { FaTimes, FaSpinner, FaChartLine, FaCoins, FaHandHoldingUsd, FaUsers, FaBoxes } from 'react-icons/fa';
import AnimatedDucats from './AnimatedDucats';
import CitizenIncomeGraphs from './CitizenIncomeGraphs';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line } from 'recharts';

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

interface ResourceSummary {
  resourceType: string;
  resourceName: string;
  totalCount: number;
  ownerBreakdown: Array<{
    owner: string;
    count: number;
  }>;
}

interface OwnerResourceSummary {
  owner: string;
  resourceType: string;
  resourceName: string;
  count: number;
}

interface ResourceShortage {
  resourceType: string;
  title: string;
  description: string;
  location: string;
  citizen: string;
  asset: string;
}

const EconomyPanel: React.FC<EconomyPanelProps> = ({ onClose }) => {
  const [economyData, setEconomyData] = useState<EconomyData | null>(null);
  const [transactionsByType, setTransactionsByType] = useState<TransactionTypeData[]>([]);
  const [topResources, setTopResources] = useState<ResourceSummary[]>([]);
  const [topOwnerResources, setTopOwnerResources] = useState<OwnerResourceSummary[]>([]);
  const [resourceShortages, setResourceShortages] = useState<ResourceShortage[]>([]);
  const [hourlyTransactions, setHourlyTransactions] = useState<{hour: string, totalPrice: number, count: number}[]>([]);
  const [activitiesByType, setActivitiesByType] = useState<{type: string, count: number}[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingTransactions, setIsLoadingTransactions] = useState(true);
  const [isLoadingResources, setIsLoadingResources] = useState(true);
  const [isLoadingActivities, setIsLoadingActivities] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'citizens' | 'resources' | 'transactions' | 'activities'>('overview');
  
  // Fetch economy data
  useEffect(() => {
    fetchEconomyData();
    fetchTransactionsByType();
    fetchResourcesData();
    fetchActivitiesData();
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
        
        // Group transactions by hour for the new tab
        const hourlyMap = new Map<string, { totalPrice: number; count: number }>();
        
        recentTransactions.forEach((transaction: any) => {
          const type = transaction.type || 'Unknown';
          const price = transaction.price || 0;
          
          // Process by type
          if (!transactionMap.has(type)) {
            transactionMap.set(type, { totalAmount: 0, count: 0 });
          }
          
          const typeData = transactionMap.get(type)!;
          typeData.totalAmount += price;
          typeData.count += 1;
          
          // Process by hour
          const executedAt = new Date(transaction.executedAt);
          const hourKey = executedAt.toISOString().substring(0, 13) + ':00'; // Format: YYYY-MM-DDTHH:00
          
          if (!hourlyMap.has(hourKey)) {
            hourlyMap.set(hourKey, { totalPrice: 0, count: 0 });
          }
          
          const hourData = hourlyMap.get(hourKey)!;
          hourData.totalPrice += price;
          hourData.count += 1;
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
        
        // Convert hourly data to array and sort by hour
        const hourlyArray = Array.from(hourlyMap.entries())
          .map(([hour, data]) => ({
            hour,
            totalPrice: data.totalPrice,
            count: data.count
          }))
          .sort((a, b) => a.hour.localeCompare(b.hour));
        
        // Fill in missing hours with zero values for the last 24 hours
        const now = new Date();
        const filledHourlyData = [];
        for (let i = 23; i >= 0; i--) {
          const hourDate = new Date(now);
          hourDate.setHours(hourDate.getHours() - i);
          hourDate.setMinutes(0, 0, 0);
          const hourKey = hourDate.toISOString().substring(0, 13) + ':00';
          
          const existingData = hourlyArray.find(h => h.hour === hourKey);
          filledHourlyData.push({
            hour: hourDate.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true }),
            totalPrice: existingData?.totalPrice || 0,
            count: existingData?.count || 0
          });
        }
        
        setHourlyTransactions(filledHourlyData);
      }
    } catch (err) {
      console.error('Error fetching transactions by type:', err);
      // Don't set error state since this is a secondary feature
    } finally {
      setIsLoadingTransactions(false);
    }
  };
  
  const fetchResourcesData = async () => {
    try {
      setIsLoadingResources(true);
      
      const response = await fetch('/api/resources-economics');
      if (!response.ok) {
        throw new Error(`Failed to fetch resources data: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success) {
        setTopResources(data.topResources || []);
        setTopOwnerResources(data.topOwnerResources || []);
        setResourceShortages(data.resourceShortages || []);
      }
    } catch (err) {
      console.error('Error fetching resources data:', err);
    } finally {
      setIsLoadingResources(false);
    }
  };
  
  const fetchActivitiesData = async () => {
    try {
      setIsLoadingActivities(true);
      
      const response = await fetch('/api/activities-economics');
      if (!response.ok) {
        throw new Error(`Failed to fetch activities data: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success) {
        setActivitiesByType(data.activitiesByType || []);
      }
    } catch (err) {
      console.error('Error fetching activities data:', err);
    } finally {
      setIsLoadingActivities(false);
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
            <button
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'resources' 
                  ? 'border-amber-600 text-amber-800' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('resources')}
            >
              Resources
            </button>
            <button
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'transactions' 
                  ? 'border-amber-600 text-amber-800' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('transactions')}
            >
              Transactions
            </button>
            <button
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'activities' 
                  ? 'border-amber-600 text-amber-800' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('activities')}
            >
              Activities
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
          ) : activeTab === 'transactions' ? (
            <div className="space-y-6">
              {isLoadingTransactions ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <FaSpinner className="animate-spin text-amber-600 text-4xl mb-4" />
                  <p className="text-amber-800">Loading transaction data...</p>
                </div>
              ) : (
                <>
                  {/* Hourly Transaction Volume Chart */}
                  <div className="bg-white rounded-lg p-6 shadow-sm border border-amber-200">
                    <h3 className="text-lg font-medium text-amber-800 mb-4 flex items-center">
                      <FaChartLine className="mr-2" />
                      24-Hour Transaction Volume
                    </h3>
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={hourlyTransactions} margin={{ top: 10, right: 30, left: 40, bottom: 40 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#FED7AA" />
                          <XAxis 
                            dataKey="hour" 
                            tick={{ fill: '#92400E', fontSize: 12 }}
                            angle={-45}
                            textAnchor="end"
                            height={60}
                          />
                          <YAxis 
                            tick={{ fill: '#92400E' }}
                            label={{ value: 'Total Ducats', angle: -90, position: 'insideLeft', fill: '#92400E' }}
                          />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#FEF3C7', border: '1px solid #F59E0B' }}
                            formatter={(value: number, name: string) => {
                              if (name === 'totalPrice') return [`⚜️ ${Math.floor(value)}`, 'Total Value'];
                              return [value, name];
                            }}
                            labelFormatter={(label) => `Hour: ${label}`}
                          />
                          <Line 
                            type="monotone" 
                            dataKey="totalPrice" 
                            stroke="#F59E0B" 
                            strokeWidth={3}
                            dot={{ fill: '#92400E', r: 4 }}
                            activeDot={{ r: 6 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    
                    {/* Summary Stats */}
                    <div className="mt-6 grid grid-cols-3 gap-4">
                      <div className="bg-amber-50 rounded-lg p-4 text-center">
                        <p className="text-sm text-amber-700">Total Volume (24h)</p>
                        <p className="text-xl font-bold text-amber-900">
                          ⚜️ {Math.floor(hourlyTransactions.reduce((sum, h) => sum + h.totalPrice, 0))}
                        </p>
                      </div>
                      <div className="bg-amber-50 rounded-lg p-4 text-center">
                        <p className="text-sm text-amber-700">Total Transactions</p>
                        <p className="text-xl font-bold text-amber-900">
                          {hourlyTransactions.reduce((sum, h) => sum + h.count, 0)}
                        </p>
                      </div>
                      <div className="bg-amber-50 rounded-lg p-4 text-center">
                        <p className="text-sm text-amber-700">Average per Hour</p>
                        <p className="text-xl font-bold text-amber-900">
                          ⚜️ {Math.floor(hourlyTransactions.reduce((sum, h) => sum + h.totalPrice, 0) / 24)}
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Hourly Transaction Count */}
                  <div className="bg-white rounded-lg p-6 shadow-sm border border-amber-200">
                    <h3 className="text-lg font-medium text-amber-800 mb-4">Transaction Count by Hour</h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={hourlyTransactions} margin={{ top: 10, right: 30, left: 40, bottom: 40 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#FED7AA" />
                          <XAxis 
                            dataKey="hour" 
                            tick={{ fill: '#92400E', fontSize: 11 }}
                            angle={-45}
                            textAnchor="end"
                          />
                          <YAxis 
                            tick={{ fill: '#92400E' }}
                            label={{ value: 'Number of Transactions', angle: -90, position: 'insideLeft', fill: '#92400E' }}
                          />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#FEF3C7', border: '1px solid #F59E0B' }}
                            formatter={(value: number) => [value, 'Transactions']}
                            labelFormatter={(label) => `Hour: ${label}`}
                          />
                          <Bar dataKey="count" fill="#10B981" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  
                  {/* Peak Hours Analysis */}
                  <div className="bg-amber-50 rounded-lg p-6 shadow-sm border border-amber-200">
                    <h3 className="text-lg font-medium text-amber-800 mb-4">Trading Activity Analysis</h3>
                    <div className="space-y-3">
                      {(() => {
                        const sortedByVolume = [...hourlyTransactions].sort((a, b) => b.totalPrice - a.totalPrice);
                        const peakHour = sortedByVolume[0];
                        const quietHour = sortedByVolume[sortedByVolume.length - 1];
                        
                        return (
                          <>
                            <div className="flex justify-between items-center pb-2 border-b border-amber-200">
                              <span className="text-amber-700">Peak Trading Hour</span>
                              <span className="font-medium text-amber-900">
                                {peakHour?.hour} (⚜️ {Math.floor(peakHour?.totalPrice || 0)})
                              </span>
                            </div>
                            <div className="flex justify-between items-center pb-2 border-b border-amber-200">
                              <span className="text-amber-700">Quietest Hour</span>
                              <span className="font-medium text-amber-900">
                                {quietHour?.hour} (⚜️ {Math.floor(quietHour?.totalPrice || 0)})
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-amber-700">Average Transaction Size</span>
                              <span className="font-medium text-amber-900">
                                ⚜️ {Math.floor(
                                  hourlyTransactions.reduce((sum, h) => sum + h.totalPrice, 0) / 
                                  Math.max(1, hourlyTransactions.reduce((sum, h) => sum + h.count, 0))
                                )}
                              </span>
                            </div>
                          </>
                        );
                      })()}
                    </div>
                    <p className="mt-4 text-sm text-amber-600 italic">
                      The Rialto never sleeps, but even merchants must rest. Track the ebb and flow of commerce through Venice's trading day.
                    </p>
                  </div>
                </>
              )}
            </div>
          ) : activeTab === 'resources' ? (
            <div className="space-y-6">
              {isLoadingResources ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <FaSpinner className="animate-spin text-amber-600 text-4xl mb-4" />
                  <p className="text-amber-800">Loading resource data...</p>
                </div>
              ) : (
                <>
                  {/* Top Resources Bar Chart */}
                  {topResources.length > 0 && (
                    <div className="bg-white rounded-lg p-6 shadow-sm border border-amber-200">
                      <h3 className="text-lg font-medium text-amber-800 mb-4 flex items-center">
                        <FaBoxes className="mr-2" />
                        Top 10 Resources by Total Count
                      </h3>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={topResources} margin={{ top: 20, right: 30, left: 40, bottom: 60 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#FED7AA" />
                            <XAxis 
                              dataKey="resourceName" 
                              angle={-45}
                              textAnchor="end"
                              height={100}
                              tick={{ fill: '#92400E' }}
                            />
                            <YAxis tick={{ fill: '#92400E' }} />
                            <Tooltip 
                              contentStyle={{ backgroundColor: '#FEF3C7', border: '1px solid #F59E0B' }}
                              formatter={(value: number) => [`${Math.floor(value)} units`, 'Total Count']}
                              labelFormatter={(label) => `Resource: ${label}`}
                            />
                            <Bar dataKey="totalCount" fill="#F59E0B" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Owner breakdown for selected resource */}
                      {topResources.length > 0 && (
                        <div className="mt-6 space-y-4">
                          <h4 className="text-sm font-medium text-amber-700">Owner Distribution (Top 5 Resources)</h4>
                          {topResources.slice(0, 5).map((resource) => (
                            <div key={resource.resourceType} className="bg-amber-50 rounded-lg p-3">
                              <h5 className="font-medium text-amber-800 mb-2">{resource.resourceName}</h5>
                              <div className="space-y-1">
                                {resource.ownerBreakdown.slice(0, 5).map((owner) => (
                                  <div key={`${resource.resourceType}-${owner.owner}`} className="flex justify-between text-sm">
                                    <span className="text-amber-700">{owner.owner}</span>
                                    <span className="font-medium text-amber-900">{Math.floor(owner.count)} units</span>
                                  </div>
                                ))}
                                {resource.ownerBreakdown.length > 5 && (
                                  <div className="text-xs text-amber-600 italic mt-1">
                                    ...and {resource.ownerBreakdown.length - 5} more owners
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Top Owner-Resource Combinations */}
                  {topOwnerResources.length > 0 && (
                    <div className="bg-white rounded-lg p-6 shadow-sm border border-amber-200">
                      <h3 className="text-lg font-medium text-amber-800 mb-4">
                        Top 10 Owner-Resource Holdings
                      </h3>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart 
                            data={topOwnerResources} 
                            margin={{ top: 20, right: 30, left: 40, bottom: 80 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#FED7AA" />
                            <XAxis 
                              dataKey="owner"
                              angle={-45}
                              textAnchor="end"
                              height={120}
                              tick={{ fill: '#92400E', fontSize: 12 }}
                            />
                            <YAxis tick={{ fill: '#92400E' }} />
                            <Tooltip 
                              contentStyle={{ backgroundColor: '#FEF3C7', border: '1px solid #F59E0B' }}
                              formatter={(value: number, name: string, props: any) => [
                                `${Math.floor(value)} units`,
                                props.payload.resourceName
                              ]}
                              labelFormatter={(label) => `Owner: ${label}`}
                            />
                            <Bar dataKey="count" fill="#10B981" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Detailed list */}
                      <div className="mt-4 bg-amber-50 rounded-lg p-4">
                        <h4 className="text-sm font-medium text-amber-700 mb-2">Detailed Holdings</h4>
                        <div className="space-y-1 text-sm">
                          {topOwnerResources.map((item, index) => (
                            <div key={`${item.owner}-${item.resourceType}-${index}`} className="flex justify-between">
                              <span className="text-amber-700">
                                {item.owner} - {item.resourceName}
                              </span>
                              <span className="font-medium text-amber-900">
                                {Math.floor(item.count)} units
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Resource Shortages */}
                  {resourceShortages.length > 0 && (
                    <div className="bg-red-50 rounded-lg p-6 shadow-sm border border-red-300">
                      <h3 className="text-lg font-medium text-red-800 mb-4 flex items-center">
                        <span className="mr-2">⚠️</span>
                        Active Resource Shortages
                      </h3>
                      <div className="space-y-3">
                        {resourceShortages.map((shortage) => (
                          <div key={shortage.resourceType} className="bg-white rounded-lg p-4 border border-red-200">
                            <h4 className="font-medium text-red-900 mb-1">{shortage.title}</h4>
                            <p className="text-sm text-red-700 mb-2">{shortage.description}</p>
                            <div className="flex justify-between text-xs text-red-600">
                              <span>Location: {shortage.location}</span>
                              <span>Reported by: {shortage.citizen}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                      <p className="mt-4 text-sm text-red-600 italic">
                        These shortages represent critical supply issues that may affect production and trade across Venice.
                      </p>
                    </div>
                  )}
                  
                  {/* Summary Statistics */}
                  <div className="bg-amber-50 rounded-lg p-6 shadow-sm border border-amber-200">
                    <h3 className="text-lg font-medium text-amber-800 mb-2">Resource Economy Overview</h3>
                    <p className="text-amber-700 italic mb-4">
                      Venice's wealth flows through its warehouses and workshops, where merchants carefully track every ducat's worth of goods from the furthest reaches of the known world.
                    </p>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center">
                        <p className="text-2xl font-bold text-amber-900">{topResources.length}</p>
                        <p className="text-sm text-amber-700">Active Resource Types</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-amber-900">
                          {Math.floor(topResources.reduce((sum, r) => sum + r.totalCount, 0))}
                        </p>
                        <p className="text-sm text-amber-700">Total Resource Units</p>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          ) : activeTab === 'activities' ? (
            <div className="space-y-6">
              {isLoadingActivities ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <FaSpinner className="animate-spin text-amber-600 text-4xl mb-4" />
                  <p className="text-amber-800">Loading activities data...</p>
                </div>
              ) : (
                <>
                  {/* Activities by Type Pie Chart */}
                  {activitiesByType.length > 0 && (
                    <div className="bg-white rounded-lg p-6 shadow-sm border border-amber-200">
                      <h3 className="text-lg font-medium text-amber-800 mb-4 flex items-center">
                        <FaUsers className="mr-2" />
                        24-Hour Activity Distribution
                      </h3>
                      <div className="h-96">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={activitiesByType.slice(0, 10)} // Show top 10 activity types
                              cx="50%"
                              cy="50%"
                              labelLine={false}
                              label={({ type, count, percent }) => 
                                `${type}: ${count} (${(percent * 100).toFixed(0)}%)`
                              }
                              outerRadius={120}
                              fill="#8884d8"
                              dataKey="count"
                            >
                              {activitiesByType.slice(0, 10).map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip 
                              formatter={(value: number, name: string, props: any) => [
                                `${value} activities`,
                                props.payload.type
                              ]}
                              contentStyle={{ backgroundColor: '#FEF3C7', border: '1px solid #F59E0B' }}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="mt-4 text-sm text-amber-600 text-center">
                        Total: {activitiesByType.reduce((sum, t) => sum + t.count, 0)} activities across {activitiesByType.length} types
                      </div>
                    </div>
                  )}
                  
                  {/* Top Activity Types List */}
                  {activitiesByType.length > 0 && (
                    <div className="bg-white rounded-lg p-6 shadow-sm border border-amber-200">
                      <h3 className="text-lg font-medium text-amber-800 mb-4">Most Common Activities</h3>
                      <div className="space-y-2">
                        {activitiesByType.slice(0, 15).map((activity, index) => {
                          const percentage = (activity.count / activitiesByType.reduce((sum, a) => sum + a.count, 0)) * 100;
                          return (
                            <div key={activity.type} className="flex items-center justify-between pb-2 border-b border-amber-100">
                              <div className="flex items-center">
                                <div 
                                  className="w-4 h-4 rounded-full mr-3" 
                                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                                />
                                <span className="text-amber-700">{activity.type}</span>
                              </div>
                              <div className="flex items-center gap-4">
                                <div className="w-24 bg-amber-100 rounded-full h-2">
                                  <div 
                                    className="bg-amber-600 h-2 rounded-full" 
                                    style={{ width: `${percentage}%` }}
                                  />
                                </div>
                                <span className="font-medium text-amber-900 w-16 text-right">{activity.count}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      {activitiesByType.length > 15 && (
                        <p className="mt-3 text-xs text-amber-600 italic">
                          ...and {activitiesByType.length - 15} more activity types
                        </p>
                      )}
                    </div>
                  )}
                  
                  {/* Activity Insights */}
                  <div className="bg-amber-50 rounded-lg p-6 shadow-sm border border-amber-200">
                    <h3 className="text-lg font-medium text-amber-800 mb-4">Activity Insights</h3>
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <h4 className="text-sm font-medium text-amber-700 mb-2">Most Active Citizens</h4>
                        <p className="text-xs text-amber-600">
                          The busiest activities typically involve movement (goto_location), work (production), and trade operations.
                        </p>
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-amber-700 mb-2">Activity Patterns</h4>
                        <p className="text-xs text-amber-600">
                          Venice's citizens balance their time between productive work, social interactions, and essential needs.
                        </p>
                      </div>
                    </div>
                    <p className="mt-4 text-sm text-amber-700 italic">
                      "In Venice, every moment is precious - from the dawn prayers at San Marco to the midnight deals in shadowed alleys."
                    </p>
                  </div>
                </>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default EconomyPanel;
