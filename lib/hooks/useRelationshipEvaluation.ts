import { useState, useEffect } from 'react';

interface RelationshipEvaluation {
  title: string;
  description: string;
}

interface UseRelationshipEvaluationResult {
  evaluation: RelationshipEvaluation | null;
  isLoading: boolean;
  error: string | null;
  refreshEvaluation: () => void;
}

export function useRelationshipEvaluation(
  citizen1Username: string | null,
  citizen2Username: string | null
): UseRelationshipEvaluationResult {
  const [evaluation, setEvaluation] = useState<RelationshipEvaluation | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  useEffect(() => {
    async function fetchRelationshipEvaluation() {
      if (!citizen1Username || !citizen2Username) {
        setEvaluation(null);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch('/api/relationships/evaluate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            citizen1: citizen1Username,
            citizen2: citizen2Username,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to evaluate relationship');
        }

        const data = await response.json();
        
        if (data.success && data.data) {
          setEvaluation(data.data);
        } else {
          throw new Error(data.error || 'No evaluation data returned');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        setEvaluation(null);
      } finally {
        setIsLoading(false);
      }
    }

    fetchRelationshipEvaluation();
  }, [citizen1Username, citizen2Username, refreshTrigger]);

  const refreshEvaluation = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return { evaluation, isLoading, error, refreshEvaluation };
}
