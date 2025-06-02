import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface RelationshipEvaluationProps {
  citizen1: string;
  citizen2: string;
  className?: string;
}

interface RelationshipEvaluation {
  title: string;
  description: string;
}

const RelationshipEvaluationCard: React.FC<RelationshipEvaluationProps> = ({ 
  citizen1, 
  citizen2,
  className = '' 
}) => {
  const [evaluation, setEvaluation] = useState<RelationshipEvaluation | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchEvaluation = async () => {
      if (!citizen1 || !citizen2) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`/api/relationships/evaluate?citizen1=${encodeURIComponent(citizen1)}&citizen2=${encodeURIComponent(citizen2)}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch relationship evaluation: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.evaluation) {
          setEvaluation(data.evaluation);
        } else {
          throw new Error(data.error || 'Unknown error occurred');
        }
      } catch (err) {
        console.error('Error fetching relationship evaluation:', err);
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    };
    
    fetchEvaluation();
  }, [citizen1, citizen2]);

  if (loading) {
    return (
      <div className={`bg-amber-50 border border-amber-200 rounded-lg p-4 ${className}`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-amber-700"></div>
          <span className="ml-2 text-amber-800">Evaluating relationship...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}>
        <h3 className="text-red-800 font-medium">Error Evaluating Relationship</h3>
        <p className="text-red-700 text-sm">{error}</p>
      </div>
    );
  }

  if (!evaluation) {
    return null;
  }

  return (
    <div className={`bg-amber-50 border border-amber-200 rounded-lg overflow-hidden ${className}`}>
      <div className="p-3 bg-amber-100 border-b border-amber-200">
        <h3 className="font-medium text-amber-900">{evaluation.title}</h3>
      </div>
      <div className="p-3 text-sm">
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          className="prose prose-amber prose-sm max-w-none"
        >
          {evaluation.description}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default RelationshipEvaluationCard;
