import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface RelationshipEvaluation {
  title: string;
  description: string;
}

interface RelationshipEvaluationCardProps {
  citizen1Username: string;
  citizen2Username: string;
  evaluation: RelationshipEvaluation | null;
  isLoading: boolean;
  error: string | null;
}

const RelationshipEvaluationCard: React.FC<RelationshipEvaluationCardProps> = ({
  citizen1Username,
  citizen2Username,
  evaluation,
  isLoading,
  error
}) => {
  return (
    <Card className="w-full bg-white shadow-md hover:shadow-lg transition-shadow duration-300">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold flex justify-between items-center">
          <span>Relationship Analysis</span>
          {evaluation && (
            <span className="text-sm px-2 py-1 bg-amber-100 text-amber-800 rounded-full">
              {evaluation.title}
            </span>
          )}
        </CardTitle>
        <CardDescription>
          Between {citizen1Username} and {citizen2Username}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : error ? (
          <div className="text-red-500 text-sm p-2 bg-red-50 rounded-md">
            {error}
          </div>
        ) : evaluation ? (
          <div className="text-gray-700 text-sm">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              className="prose prose-sm max-w-none"
            >
              {evaluation.description}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="text-gray-500 text-sm italic">
            No relationship data available
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RelationshipEvaluationCard;
