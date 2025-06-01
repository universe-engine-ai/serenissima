import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { FaSpinner } from 'react-icons/fa';

interface BuildingBidFormProps {
  buildingId: string;
  buildingName: string;
  currentOwner: string | null;
  citizenUsername: string;
  onClose?: () => void;
  onBidPlaced?: () => void;
  ducats?: number;
}

const BuildingBidForm: React.FC<BuildingBidFormProps> = ({
  buildingId,
  buildingName,
  currentOwner,
  citizenUsername,
  onClose,
  onBidPlaced,
  ducats = 0
}) => {
  const [bidAmount, setBidAmount] = useState<number | ''>('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Set a reasonable default bid amount based on available ducats
  useEffect(() => {
    if (ducats > 0) {
      // Default to 5% of available ducats or 10,000, whichever is less
      const defaultBid = Math.min(Math.floor(ducats * 0.05), 10000);
      setBidAmount(defaultBid > 0 ? defaultBid : 1000);
    } else {
      setBidAmount(1000); // Fallback default
    }
  }, [ducats]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (bidAmount === '' || bidAmount <= 0) {
      setError('Bid amount must be greater than zero.');
      return;
    }
    
    if (ducats > 0 && bidAmount > ducats) {
      setError('You do not have enough ducats for this bid.');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const response = await fetch('/api/activities/try-create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          citizenUsername: citizenUsername,
          activityType: 'bid_on_building',
          activityParameters: {
            buildingIdToBidOn: buildingId,
            bidAmount: bidAmount,
            notes: notes || `Strategic bid on ${buildingName}`,
            fromBuildingId: null, // Will be determined by the server
            targetOfficeBuildingId: null // Let the server find the appropriate office
          }
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || data.error || 'Failed to place bid');
      }
      
      toast.success(`Bid of ${bidAmount} ducats successfully placed on ${buildingName}!`);
      
      if (onBidPlaced) onBidPlaced();
      if (onClose) onClose();
      
    } catch (error) {
      console.error('Error placing bid:', error);
      setError(error instanceof Error ? error.message : 'An unknown error occurred');
      toast.error('Failed to place bid. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
      <h3 className="text-lg font-semibold text-amber-800 mb-4">Place a Bid on {buildingName}</h3>
      
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="bidAmount" className="block text-sm font-medium text-amber-700 mb-1">
            Bid Amount (Ducats)
          </label>
          <input
            type="number"
            id="bidAmount"
            value={bidAmount}
            onChange={(e) => setBidAmount(e.target.value === '' ? '' : Number(e.target.value))}
            className="w-full px-3 py-2 border border-amber-300 rounded-md shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500"
            min="1"
            required
            disabled={isSubmitting}
          />
          {ducats > 0 && (
            <p className="text-sm text-amber-600 mt-1">
              Your available funds: {ducats.toLocaleString()} Ducats
            </p>
          )}
        </div>
        
        <div className="mb-4">
          <label htmlFor="notes" className="block text-sm font-medium text-amber-700 mb-1">
            Notes (Optional)
          </label>
          <textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-amber-300 rounded-md shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 resize-none"
            placeholder="Any strategic notes or conditions for your bid..."
            disabled={isSubmitting}
          />
        </div>
        
        {error && (
          <div className="mb-4 p-2 bg-red-50 border border-red-200 text-red-700 rounded">
            {error}
          </div>
        )}
        
        <div className="flex justify-end space-x-2">
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-amber-300 rounded-md shadow-sm text-sm font-medium text-amber-700 bg-white hover:bg-amber-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500"
              disabled={isSubmitting}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 flex items-center"
            disabled={isSubmitting || bidAmount === '' || bidAmount <= 0}
          >
            {isSubmitting ? (
              <>
                <FaSpinner className="animate-spin mr-2" /> Submitting...
              </>
            ) : (
              'Place Bid'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default BuildingBidForm;
