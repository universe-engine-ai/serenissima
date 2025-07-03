import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FaTimes } from 'react-icons/fa';

interface JournalFile {
  name: string;
  content: string;
  last_modified: string;
  // Add other fields if necessary, e.g., path, size
}

interface JournalViewerPanelProps {
  file: JournalFile | null;
  onClose: () => void;
}

const JournalViewerPanel: React.FC<JournalViewerPanelProps> = ({ file, onClose }) => {
  if (!file) return null;

  // Helper function to format journal file name (consistent with CitizenInfoColumn)
  const formatJournalFileName = (fileName: string): string => {
    if (!fileName) return 'Untitled Entry';
    const nameWithoutExtension = fileName.substring(0, fileName.lastIndexOf('.')) || fileName;
    return nameWithoutExtension
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  const formatKinOSDate = (dateString: string): string => {
    if (!dateString) return 'Unknown date';
    try {
      const date = new Date(dateString);
      // Assuming KinOS dates are UTC. Display in user's local time or a fixed one.
      // For now, just format it. Renaissance adjustment might not be appropriate here.
      return date.toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        timeZoneName: 'short'
      });
    } catch (e) {
      console.error("Error formatting KinOS date:", e);
      return dateString; // Return original string if formatting fails
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[100] p-4 sm:p-8 md:p-12 lg:p-16"
      onClick={onClose} // Close on backdrop click
    >
      <div 
        className="bg-amber-50 text-amber-900 rounded-lg shadow-2xl w-full max-w-4xl h-[90vh] max-h-[800px] flex flex-col overflow-hidden border-2 border-amber-700"
        onClick={(e) => e.stopPropagation()} // Prevent close when clicking inside panel
      >
        {/* Header */}
        <div className="flex justify-between items-center p-4 sm:p-5 border-b border-amber-300 bg-amber-100">
          <div className="flex items-center">
            <span className="text-2xl mr-3">📜</span>
            <div>
              <h2 className="text-xl sm:text-2xl font-serif text-amber-800 truncate italic" title={formatJournalFileName(file.name)}>
                {formatJournalFileName(file.name)}
              </h2>
              <p className="text-xs text-amber-600">
                Last Modified: {formatKinOSDate(file.last_modified)}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="text-amber-600 hover:text-amber-800 p-2 rounded-full hover:bg-amber-200 transition-colors"
            aria-label="Close journal viewer"
          >
            <FaTimes size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6 flex-grow overflow-y-auto custom-scrollbar">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({node, ...props}) => <h1 className="text-2xl font-serif text-amber-800 border-b border-amber-300 pb-2 mb-4 mt-2" {...props} />,
              h2: ({node, ...props}) => <h2 className="text-xl font-serif text-amber-800 border-b border-amber-200 pb-1 mb-3 mt-4" {...props} />,
              h3: ({node, ...props}) => <h3 className="text-lg font-semibold text-amber-700 mb-2 mt-3" {...props} />,
              p: ({node, ...props}) => <p className="mb-3 leading-relaxed text-sm" {...props} />,
              ul: ({node, ...props}) => <ul className="list-disc list-inside mb-3 pl-4 text-sm" {...props} />,
              ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-3 pl-4 text-sm" {...props} />,
              li: ({node, ...props}) => <li className="mb-1" {...props} />,
              blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-amber-300 pl-4 italic text-amber-700 my-3" {...props} />,
              code: ({node, className, children, ...props}) => {
                const match = /language-(\w+)/.exec(className || '');
                return match ? (
                  <pre className="bg-amber-100 p-3 rounded-md overflow-x-auto text-xs my-3 custom-scrollbar">
                    <code className={`language-${match[1]}`} {...props}>
                      {String(children).replace(/\n$/, '')}
                    </code>
                  </pre>
                ) : (
                  <code className="bg-amber-100 text-amber-700 px-1 py-0.5 rounded-sm text-xs" {...props}>
                    {children}
                  </code>
                )
              },
              table: ({node, ...props}) => <table className="min-w-full border border-amber-200 my-4 text-xs" {...props} />,
              thead: ({node, ...props}) => <thead className="bg-amber-100" {...props} />,
              th: ({node, ...props}) => <th className="border border-amber-200 px-3 py-2 text-left font-semibold" {...props} />,
              td: ({node, ...props}) => <td className="border border-amber-200 px-3 py-2" {...props} />,
              a: ({node, ...props}) => <a className="text-sky-600 hover:text-sky-800 underline hover:no-underline" {...props} />,
            }}
          >
            {file.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
};

export default JournalViewerPanel;
