import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FaSpinner, FaExpand, FaCompress } from 'react-icons/fa';
import InfoIcon from './InfoIcon'; // Assurez-vous que ce chemin est correct

interface CitizenCorrespondanceColumnProps {
  citizen: any;
  messages: any[];
  isLoadingHistory: boolean;
  messagesFetchFailed: boolean;
  isTyping: boolean;
  inputValue: string;
  setInputValue: (value: string) => void;
  sendMessage: (content: string) => Promise<void>;
  isCorrespondanceFullScreen: boolean;
  setIsCorrespondanceFullScreen: (value: boolean) => void;
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

const CitizenCorrespondanceColumn: React.FC<CitizenCorrespondanceColumnProps> = ({
  citizen,
  messages,
  isLoadingHistory,
  messagesFetchFailed,
  isTyping,
  inputValue,
  setInputValue,
  sendMessage,
  isCorrespondanceFullScreen,
  setIsCorrespondanceFullScreen,
  messagesEndRef,
}) => {

  // Add a function to filter system messages
  const isSystemMessage = (message: any): boolean => {
    return message.content && typeof message.content === 'string' && message.content.includes('[SYSTEM]');
  };

  return (
    <div className="flex flex-col h-full"> {/* Ensure column takes full height */}
      <div className="flex items-center flex-shrink-0">
        <h3 className="text-lg font-serif text-amber-800 mb-2 border-b border-amber-200 pb-1 flex-grow">Correspondance</h3>
        <InfoIcon tooltipText="Direct messages exchanged with this citizen. Use this to negotiate, gather information, or build relationships." />
        <button 
          onClick={() => setIsCorrespondanceFullScreen(!isCorrespondanceFullScreen)} 
          className="text-amber-600 hover:text-amber-700 ml-2 p-1 flex-shrink-0"
          title={isCorrespondanceFullScreen ? "Exit full screen" : "Full screen"}
        >
          {isCorrespondanceFullScreen ? <FaCompress size={16} /> : <FaExpand size={16} />}
        </button>
      </div>
      
      {/* Messages area */}
      <div 
        className="flex-grow overflow-y-auto p-3 bg-amber-50 bg-opacity-80 rounded-lg mb-3 custom-scrollbar min-h-[300px]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100' height='100' filter='url(%23noise)' opacity='0.05'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'repeat'
        }}
      >
        {isLoadingHistory ? (
          <div className="flex justify-center items-center h-full">
            <div className="bg-yellow-500 text-white p-3 rounded-lg rounded-bl-none inline-block">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-yellow-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-yellow-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-yellow-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-8">
            {messagesFetchFailed ? (
              <div className="text-gray-500 italic">
                Unable to load conversation history with {citizen.firstName}.
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-amber-700 italic">
                No correspondence yet. Send a message to begin.
              </div>
            )}
          </div>
        ) : (
          <>
            {messages.filter(message => !isSystemMessage(message)).map((message) => (
              <div 
                key={message.id || `msg-${Date.now()}-${Math.random()}`} 
                className={`mb-3 ${
                  message.role === 'user' 
                    ? 'text-right' 
                    : 'text-left'
                }`}
              >
                <div 
                  className={`inline-block p-3 rounded-lg max-w-[80%] ${
                    message.role === 'user'
                      ? 'bg-amber-100 text-amber-900 rounded-br-none'
                      : 'bg-amber-700 text-white rounded-bl-none'
                  }`}
                >
                  <div className="markdown-content relative z-10 text-sm">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        a: ({node, ...props}) => <a {...props} className="text-amber-300 underline hover:text-amber-100" target="_blank" rel="noopener noreferrer" />,
                        code: ({node, ...props}) => <code {...props} className="bg-amber-800 px-1 py-0.5 rounded text-sm font-mono" />,
                        pre: ({node, ...props}) => <pre {...props} className="bg-amber-800 p-2 rounded my-2 overflow-x-auto text-sm font-mono" />,
                        ul: ({node, ...props}) => <ul {...props} className="list-disc pl-5 my-1" />,
                        ol: ({node, ...props}) => <ol {...props} className="list-decimal pl-5 my-1" />,
                        li: ({node, ...props}) => <li {...props} className="my-0.5" />,
                        blockquote: ({node, ...props}) => <blockquote {...props} className="border-l-4 border-amber-500 pl-3 italic my-2" />,
                        h1: ({node, ...props}) => <h1 {...props} className="text-lg font-bold my-2" />,
                        h2: ({node, ...props}) => <h2 {...props} className="text-md font-bold my-2" />,
                        h3: ({node, ...props}) => <h3 {...props} className="text-sm font-bold my-1" />,
                        p: ({node, ...props}) => <p {...props} className="my-1" />
                      }}
                    >
                      {message.content || "No content available"}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="text-left mb-3" key="typing-indicator">
                <div className="inline-block p-3 rounded-lg max-w-[80%] bg-yellow-500 text-white rounded-bl-none">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-yellow-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-yellow-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-yellow-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      
      <form 
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage(inputValue);
        }} 
        className="flex flex-shrink-0 items-end"
      >
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={`Message ${citizen.firstName}... (Shift+Enter for new line)`} 
          className="flex-1 p-2 border border-amber-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-amber-500 resize-none"
          rows={3}
          disabled={isTyping}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (!isTyping && inputValue.trim()) {
                sendMessage(inputValue);
              }
            }
          }}
          style={{ maxHeight: '120px' }}
        />
        <button 
          type="submit"
          className={`px-4 rounded-r-lg transition-colors self-stretch ${
            isTyping || !inputValue.trim()
              ? 'bg-gray-400 text-white cursor-not-allowed'
              : 'bg-amber-700 text-white hover:bg-amber-600'
          }`}
          disabled={isTyping || !inputValue.trim()}
        >
          {isTyping ? <FaSpinner className="animate-spin text-yellow-400" /> : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default CitizenCorrespondanceColumn;
