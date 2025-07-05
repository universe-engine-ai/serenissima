import React, { useState, useEffect } from 'react';

interface Grievance {
  id: string;
  citizen: string;
  category: string;
  title: string;
  description: string;
  status: string;
  support_count: number;
  filed_at: string;
}

interface GrievanceListProps {
  apiUrl?: string;
}

export function GrievanceList({ apiUrl = '' }: GrievanceListProps) {
  const [grievances, setGrievances] = useState<Grievance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGrievances();
  }, []);

  const fetchGrievances = async () => {
    try {
      setLoading(true);
      // Use proxy endpoint until backend is deployed
      const response = await fetch('/api/proxy-governance?path=grievances');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setGrievances(data.grievances || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch grievances');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-4 bg-amber-50 rounded-lg">
        <p className="text-amber-800">Loading grievances...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 rounded-lg">
        <p className="text-red-800">Error: {error}</p>
        <p className="text-sm text-red-600 mt-2">
          The governance API endpoints are not yet deployed to production. 
          This feature will be available soon.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
        <h2 className="text-2xl font-serif text-amber-800 mb-4">
          Citizen Grievances ({grievances.length})
        </h2>
        
        {grievances.length === 0 ? (
          <p className="text-amber-700">No grievances filed yet.</p>
        ) : (
          <div className="space-y-3">
            {grievances.map((grievance) => (
              <div 
                key={grievance.id} 
                className="bg-white p-4 rounded-lg border border-amber-300"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-amber-900">
                    {grievance.title}
                  </h3>
                  <span className="text-sm text-amber-600 bg-amber-100 px-2 py-1 rounded">
                    {grievance.category}
                  </span>
                </div>
                
                <p className="text-gray-700 mb-2">
                  {grievance.description}
                </p>
                
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">
                    Filed by: {grievance.citizen}
                  </span>
                  <div className="flex items-center gap-4">
                    <span className="text-amber-700">
                      Support: {grievance.support_count}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      grievance.status === 'filed' ? 'bg-blue-100 text-blue-700' :
                      grievance.status === 'under_review' ? 'bg-yellow-100 text-yellow-700' :
                      grievance.status === 'addressed' ? 'bg-green-100 text-green-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {grievance.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="bg-amber-50 p-4 rounded-lg border border-amber-200 text-sm">
        <h3 className="font-bold text-amber-800 mb-2">
          About the Grievance System
        </h3>
        <p className="text-amber-700">
          Citizens can file formal complaints at the Doge's Palace for 50 ducats. 
          Other citizens can support grievances for 10 ducats. Grievances with 
          20+ supporters are reviewed by the Signoria.
        </p>
      </div>
    </div>
  );
}