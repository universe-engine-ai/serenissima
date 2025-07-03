import React, { useState, useEffect } from 'react';
import { FaSpinner, FaExclamationTriangle } from 'react-icons/fa';

interface AggregatedTransaction {
  type: string;
  totalAmount: number;
  count: number;
}

interface LedgerData {
  debits: AggregatedTransaction[];
  credits: AggregatedTransaction[];
  summary: {
    totalDebits: number;
    totalCredits: number;
    netChange: number; // Changed from netProfit
  };
}

interface CitizenLedgerProps {
  citizenId: string | null; // Username of the citizen
  citizenName?: string;
}

const formatDucats = (amount: number): string => {
  // Using a non-breaking space for thousands separator and the Ducat symbol ⚜️
  // Keep fr-FR for number format (space as separator), but use English for text.
  return `${amount.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).replace(/\s/g, '\u00A0')} ⚜️`;
};

const CitizenLedger: React.FC<CitizenLedgerProps> = ({ citizenId, citizenName }) => {
  const [ledgerData, setLedgerData] = useState<LedgerData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!citizenId) {
      setLedgerData(null);
      setError(null);
      return;
    }

    const fetchLedgerData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/citizen-economics/${citizenId}`);
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ error: `HTTP error ${response.status}` }));
          throw new Error(errorData.error || `Failed to fetch ledger data: ${response.statusText}`);
        }
        const data = await response.json();
        if (data.success && data.ledger) {
          setLedgerData(data.ledger);
        } else {
          throw new Error(data.error || 'Invalid ledger data format');
        }
      } catch (err) {
        console.error('Error fetching citizen ledger:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        setLedgerData(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchLedgerData();
  }, [citizenId]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-full p-6 bg-amber-50 rounded-lg">
        <FaSpinner className="animate-spin text-amber-700 text-3xl" />
        <p className="ml-3 text-amber-700">Loading ledger...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-700">
        <div className="flex items-center">
          <FaExclamationTriangle className="text-red-500 mr-2 text-xl" />
          <h4 className="font-semibold">Error loading ledger</h4>
        </div>
        <p className="text-sm mt-1">{error}</p>
      </div>
    );
  }

  if (!ledgerData || (ledgerData.debits.length === 0 && ledgerData.credits.length === 0)) {
    return (
      <div className="p-6 bg-amber-50 rounded-lg text-center">
        <p className="text-amber-700 italic">No financial transactions recorded for this citizen in the last 7 days.</p>
      </div>
    );
  }

  const { debits, credits, summary } = ledgerData;

  return (
    <div className="ledger-book p-4 bg-gradient-to-b from-[#fdf6e3] to-[#f0e6d2] shadow-lg relative border-4 border-[#a0522d] rounded-lg h-full overflow-y-auto custom-scrollbar">
      <style jsx global>{`
        .ledger-book {
          font-family: 'Cinzel', serif;
          color: #3a2f28; // Darker brown for text
        }
        .ledger-header h1 {
          font-family: 'Cinzel Decorative', cursive;
          font-size: 22px; // Slightly smaller for citizen panel
          color: #800000; // Maroon
          text-shadow: 1px 1px 1px rgba(0,0,0,0.15);
        }
        .ledger-header .subtitle {
          font-size: 13px; // Slightly smaller
          color: #704214; // Sienna
        }
        .accounts-grid {
          display: grid;
          grid-template-columns: 1fr; 
          gap: 16px; 
        }
        @media (min-width: 600px) { // Adjust breakpoint if needed for panel width
          .accounts-grid {
            grid-template-columns: 1fr 1fr;
          }
        }
        .account-column {
          background: rgba(255,255,255,0.4);
          padding: 12px; 
          border: 1px solid #b8860b; // DarkGoldenRod
          border-radius: 4px;
          position: relative;
        }
        .account-column::before {
          content: attr(data-title);
          position: absolute;
          top: -10px; 
          left: 12px; 
          background: #fdf6e3; // Match ledger background
          padding: 2px 8px; 
          font-size: 12px; 
          font-weight: 700; // Bolder
          color: #800000; // Maroon
          border: 1px solid #b8860b;
          border-radius: 3px;
        }
        .entry-line {
          display: flex;
          justify-content: space-between;
          margin-bottom: 6px; 
          padding: 3px 0; 
          border-bottom: 1px dashed #b8860b;
          font-size: 11px; // Smaller for more entries
        }
        .entry-description {
          flex: 1;
          text-transform: capitalize;
          margin-right: 8px;
        }
        .entry-amount {
          font-weight: 600;
          color: #5d4037; // Brown
          min-width: 70px; 
          text-align: right;
          white-space: nowrap;
        }
        .total-line {
          margin-top: 8px; 
          padding-top: 8px; 
          border-top: 2px solid #800000; // Maroon
          font-size: 13px; 
          font-weight: 700; // Bolder
        }
        .net-change { // Renamed from profit-loss
          text-align: center;
          margin-top: 12px; 
          font-size: 14px; 
          padding: 8px; 
          background: rgba(160,82,45,0.05); // Light sienna background
          border: 1px solid #b8860b;
          border-radius: 4px;
        }
        .profit { color: #228B22; } // ForestGreen
        .loss { color: #B22222; } // Firebrick
      `}</style>

      <div className="ledger-header text-center mb-4">
        <h1>Ledger: {citizenName || 'Citizen'}</h1>
        <div className="subtitle">Period: Last 7 Days</div>
      </div>

      <div className="accounts-grid mb-4">
        <div className="account-column" data-title="Debits (Expenses)">
          {debits.length > 0 ? debits.map(d => (
            <div key={`debit-${d.type}`} className="entry-line">
              <span className="entry-description" title={d.type.replace(/_/g, ' ')}>{d.type.replace(/_/g, ' ')} ({d.count})</span>
              <span className="entry-amount">{formatDucats(d.totalAmount)}</span>
            </div>
          )) : <p className="text-xs italic text-gray-600 py-2">No expenses recorded in the last 7 days.</p>}
          <div className="total-line entry-line">
            <span className="entry-description">Total Expenses</span>
            <span className="entry-amount">{formatDucats(summary.totalDebits)}</span>
          </div>
        </div>

        <div className="account-column" data-title="Credits (Income)">
          {credits.length > 0 ? credits.map(c => (
            <div key={`credit-${c.type}`} className="entry-line">
              <span className="entry-description" title={c.type.replace(/_/g, ' ')}>{c.type.replace(/_/g, ' ')} ({c.count})</span>
              <span className="entry-amount">{formatDucats(c.totalAmount)}</span>
            </div>
          )) : <p className="text-xs italic text-gray-600 py-2">No income recorded in the last 7 days.</p>}
          <div className="total-line entry-line">
            <span className="entry-description">Total Income</span>
            <span className="entry-amount">{formatDucats(summary.totalCredits)}</span>
          </div>
        </div>
      </div>

      <div className={`net-change ${summary.netChange >= 0 ? 'profit' : 'loss'}`}>
        {summary.netChange >= 0 ? 'Net Income' : 'Net Expense'}: {formatDucats(summary.netChange)}
      </div>
    </div>
  );
};

export default CitizenLedger;
