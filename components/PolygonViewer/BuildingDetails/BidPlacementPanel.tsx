import React, { useState } from 'react';
import { FaTimes, FaPaperPlane, FaSpinner } from 'react-icons/fa';
import { toast } from 'react-hot-toast';

interface BidPlacementPanelProps {
  buildingId: string;
  buildingName: string;
  currentOwner: string | null;
  currentUser: string;
  onClose: () => void;
  onBidPlaced: () => void; // Callback after successful bid
}

const BidPlacementPanel: React.FC<BidPlacementPanelProps> = ({
  buildingId,
  buildingName,
  currentOwner,
  currentUser,
  onClose,
  onBidPlaced,
}) => {
  const [bidAmount, setBidAmount] = useState<number | ''>('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmitBid = async (e: React.FormEvent) => {
    e.preventDefault();
    if (bidAmount === '' || bidAmount <= 0) {
      setError('Please enter a valid bid amount.');
      return;
    }
    setError(null);
    setIsSubmitting(true);

    try {
      // Make the actual API call to place a bid using the activities/try-create endpoint
      const response = await fetch('/api/activities/try-create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          citizenUsername: currentUser,
          activityType: 'bid_on_building',
          activityParameters: {
            buildingIdToBidOn: buildingId,
            bidAmount: bidAmount,
            notes: notes || `Bid on ${buildingName}`,
            fromBuildingId: null, // Will be determined by the server based on citizen's current location
            targetOfficeBuildingId: null // Let the server find the appropriate office building
          }
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to place bid.');
      }
      
      const result = await response.json();
      
      toast.success(`Bid of ${bidAmount} Ducats placed for ${buildingName}!`);
      onBidPlaced(); // Call this after successful API call

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      console.error('Error placing bid:', errorMessage);
      setError(errorMessage);
      toast.error('Failed to place bid: ' + errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-[70] flex items-center justify-center p-4">
      <div className="bg-amber-50 w-full max-w-md rounded-lg shadow-xl border-2 border-amber-700 flex flex-col">
        <div className="bg-amber-700 text-white p-4 flex justify-between items-center rounded-t-lg">
          <h3 className="font-serif text-xl">Place Bid for: {buildingName}</h3>
          <button onClick={onClose} className="text-white hover:text-amber-200">
            <FaTimes size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmitBid} className="p-6 space-y-4">
          <p className="text-sm text-amber-700">
            Current Owner: <span className="font-medium">{currentOwner || 'N/A'}</span>
          </p>
          
          <div>
            <label htmlFor="bidAmount" className="block text-sm font-medium text-amber-800 mb-1">
              Your Bid Amount (Ducats)
            </label>
            <input
              id="bidAmount"
              type="number"
              value={bidAmount}
              onChange={(e) => setBidAmount(e.target.value === '' ? '' : Number(e.target.value))}
              className="w-full px-3 py-2 border border-amber-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
              placeholder="e.g., 10000"
              min="1"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-amber-800 mb-1">
              Notes (Optional)
            </label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-amber-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-500 resize-none"
              placeholder="Any conditions or comments for the owner..."
              disabled={isSubmitting}
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-amber-700 bg-amber-100 border border-amber-300 rounded-md hover:bg-amber-200 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || bidAmount === '' || bidAmount <= 0}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:bg-gray-400 flex items-center"
            >
              {isSubmitting ? (
                <>
                  <FaSpinner className="animate-spin mr-2" /> Submitting...
                </>
              ) : (
                <>
                  <FaPaperPlane className="mr-2" /> Submit Bid
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BidPlacementPanel;
