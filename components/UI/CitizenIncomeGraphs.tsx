import React, { useState, useEffect } from 'react';
import { FaSpinner } from 'react-icons/fa';

interface IncomeData {
  username: string;
  firstName?: string;
  lastName?: string;
  socialClass?: string;
  dailyIncome?: number;
  dailyNetResult?: number;
  weeklyIncome?: number;
  weeklyNetResult?: number;
  monthlyIncome?: number;
  monthlyNetResult?: number;
}

interface CitizenIncomeGraphsProps {
  limit?: number;
}

const CitizenIncomeGraphs: React.FC<CitizenIncomeGraphsProps> = ({ limit = 10 }) => {
  const [citizens, setCitizens] = useState<IncomeData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeMetric, setActiveMetric] = useState<string>('dailyIncome');

  useEffect(() => {
    fetchCitizens();
  }, []);

  const fetchCitizens = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/citizens');
      if (!response.ok) {
        throw new Error(`Failed to fetch citizens: ${response.status}`);
      }

      const data = await response.json();
      if (data.success && data.citizens) {
        // Filter citizens with income data and exclude system citizens
        const EXCLUDED_CITIZENS = ['Italia', 'ConsiglioDeiDieci'];
        const citizensWithIncome = data.citizens
          .filter((citizen: any) => 
            !EXCLUDED_CITIZENS.includes(citizen.username) &&
            (citizen.dailyIncome !== undefined || 
             citizen.weeklyIncome !== undefined || 
             citizen.monthlyIncome !== undefined)
          )
          .map((citizen: any) => ({
            username: citizen.username,
            firstName: citizen.firstName,
            lastName: citizen.lastName,
            socialClass: citizen.socialClass,
            dailyIncome: Number(citizen.dailyIncome || 0),
            dailyNetResult: Number(citizen.dailyNetResult || 0),
            weeklyIncome: Number(citizen.weeklyIncome || 0),
            weeklyNetResult: Number(citizen.weeklyNetResult || 0),
            monthlyIncome: Number(citizen.monthlyIncome || 0),
            monthlyNetResult: Number(citizen.monthlyNetResult || 0),
          }));
        
        setCitizens(citizensWithIncome);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err) {
      console.error('Error fetching citizens:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  const sortCitizens = (metric: string) => {
    return [...citizens].sort((a, b) => {
      const valueA = Number(a[metric as keyof IncomeData] || 0);
      const valueB = Number(b[metric as keyof IncomeData] || 0);
      return valueB - valueA; // Sort in descending order
    }).slice(0, limit);
  };

  const getMaxValue = (metric: string) => {
    const values = citizens.map(c => Number(c[metric as keyof IncomeData] || 0));
    return Math.max(...values, 1); // Ensure we don't divide by zero
  };

  const formatCitizenName = (citizen: IncomeData) => {
    const name = [citizen.firstName, citizen.lastName].filter(Boolean).join(' ');
    return name ? `${citizen.username} (${name})` : citizen.username;
  };

  const renderBarGraph = (metric: string, title: string, color: string) => {
    const sortedCitizens = sortCitizens(metric);
    const maxValue = getMaxValue(metric);

    return (
      <div className="bg-white rounded-lg p-4 shadow-sm border border-amber-200 mb-6">
        <h3 className="text-lg font-medium text-amber-800 mb-4">{title}</h3>
        
        {sortedCitizens.length > 0 ? (
          <div className="space-y-3">
            {sortedCitizens.map((citizen, index) => {
              const value = Number(citizen[metric as keyof IncomeData] || 0);
              const percentage = (value / maxValue) * 100;
              
              return (
                <div key={`${citizen.username}-${index}`} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-amber-700 truncate" title={formatCitizenName(citizen)}>
                      {formatCitizenName(citizen)}
                    </span>
                    <span className="font-medium text-amber-900">⚜️ {Math.floor(value)}</span>
                  </div>
                  <div className="w-full bg-amber-100 rounded-full h-2.5">
                    <div 
                      className={`h-2.5 rounded-full ${color}`} 
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-center py-4 text-amber-600">No data available</p>
        )}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <FaSpinner className="animate-spin text-amber-600 text-4xl mb-4" />
        <p className="text-amber-800">Loading citizen income data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-lg">
        <p className="font-medium">Error loading citizen data</p>
        <p className="text-sm mt-1">{error}</p>
        <button 
          onClick={fetchCitizens}
          className="mt-4 px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Income graphs grouped together */}
        {renderBarGraph('dailyIncome', 'Daily Income (Top Citizens)', 'bg-green-500')}
        {renderBarGraph('weeklyIncome', 'Weekly Income (Top Citizens)', 'bg-purple-500')}
        {renderBarGraph('monthlyIncome', 'Monthly Income (Top Citizens)', 'bg-amber-500')}
        
        {/* Net Result graphs grouped together */}
        {renderBarGraph('dailyNetResult', 'Daily Net Result (Top Citizens)', 'bg-blue-500')}
        {renderBarGraph('weeklyNetResult', 'Weekly Net Result (Top Citizens)', 'bg-indigo-500')}
        {renderBarGraph('monthlyNetResult', 'Monthly Net Result (Top Citizens)', 'bg-red-500')}
      </div>
      
      <div className="text-center text-sm text-amber-600 mt-4">
        <p>Showing top {limit} citizens by each metric</p>
        <button 
          onClick={fetchCitizens} 
          className="mt-2 px-3 py-1 bg-amber-100 hover:bg-amber-200 text-amber-800 rounded transition-colors"
        >
          Refresh Data
        </button>
      </div>
    </div>
  );
};

export default CitizenIncomeGraphs;
