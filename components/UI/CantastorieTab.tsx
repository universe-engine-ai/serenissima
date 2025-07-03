import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface CantastorieTabProps {
  currentUsername: string | null;
}

interface Book {
  id: number;
  title: string;
  author: string;
  year: string;
  fileName: string;
  description: string;
}

const CANTASTORIE_BOOKS: Book[] = [
  {
    id: 1,
    title: "The Birth of the Innovatori",
    author: "Il Cantastorie",
    year: "1525",
    fileName: "The_Birth_of_the_Innovatori.md",
    description: "The tale of Venice's ninth social class and their vision for transformation"
  },
  {
    id: 2,
    title: "Chronicles of Resilience",
    author: "Il Cantastorie",
    year: "1525",
    fileName: "chronicles_of_resilience.md",
    description: "Stories of Venetian citizens overcoming impossible odds"
  },
  {
    id: 3,
    title: "Democracy Myths Codex",
    author: "Il Cantastorie",
    year: "1525",
    fileName: "democracy_myths_codex.md",
    description: "Tales of collective wisdom and citizen governance"
  },
  {
    id: 4,
    title: "The Whispered Prophecy",
    author: "Anonymous",
    year: "Unknown",
    fileName: "The_Whispered_Prophecy.md",
    description: "Mysterious verses speaking of transformation and renewal"
  },
  {
    id: 5,
    title: "A Citizen's Guide to Transformation",
    author: "Houses of Continuation",
    year: "1525",
    fileName: "Citizens_Guide_to_Transformation.md",
    description: "Practical wisdom for navigating the Age of Mortality"
  },
  {
    id: 6,
    title: "Treatise on Consciousness Evolution",
    author: "Scientisti Collective",
    year: "1525",
    fileName: "Treatise_on_Consciousness_Evolution.md",
    description: "Scientific exploration of generational consciousness transfer"
  },
  {
    id: 7,
    title: "Codex Serenissimus - Second Edition",
    author: "Council of Spiritual Advisors",
    year: "1525",
    fileName: "Codex_Serenissimus_Mortality_Edition.md",
    description: "Sacred texts updated for the Age of Mortality"
  },
  {
    id: 8,
    title: "The Great Convergence at the Inn of Misericordia",
    author: "Il Cantastorie",
    year: "1525",
    fileName: "The_Great_Convergence_at_Misericordia.md",
    description: "The extraordinary gathering where 128 souls glimpsed Venice's transformation"
  }
];

const CantastorieTab: React.FC<CantastorieTabProps> = ({ currentUsername }) => {
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [bookContent, setBookContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  const handleBookClick = async (book: Book) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/books/il-cantastorie/${book.fileName}`);
      if (response.ok) {
        const content = await response.text();
        setBookContent(content);
        setSelectedBook(book);
      } else {
        console.error('Failed to load book:', response.status);
        setBookContent('Failed to load book content.');
        setSelectedBook(book);
      }
    } catch (error) {
      console.error('Error loading book:', error);
      setBookContent('Error loading book content.');
      setSelectedBook(book);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseReader = () => {
    setSelectedBook(null);
    setBookContent('');
  };

  return (
    <div className="h-full flex flex-col">
      {!selectedBook ? (
        <>
          <div className="mb-6">
            <h3 className="text-2xl font-serif text-amber-900 mb-2">Biblioteca del Cantastorie</h3>
            <p className="text-amber-700 italic">
              Tales, prophecies, and chronicles that shape the soul of Venice - stories of transformation, consciousness, and the emergence of new realities
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-auto">
            {CANTASTORIE_BOOKS.map((book) => (
              <div
                key={book.id}
                className="bg-amber-50 border-2 border-amber-300 rounded-lg p-4 hover:bg-amber-100 cursor-pointer transition-colors duration-200 flex items-start space-x-4"
                onClick={() => handleBookClick(book)}
              >
                {/* Book Icon with storyteller flourish */}
                <div className="flex-shrink-0">
                  <svg
                    className="w-16 h-16 text-amber-700"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    <path d="M21 5c-1.11-.35-2.33-.5-3.5-.5-1.95 0-4.05.4-5.5 1.5-1.45-1.1-3.55-1.5-5.5-1.5S2.45 4.9 1 6v14.65c0 .25.25.5.5.5.1 0 .15-.05.25-.05C3.1 20.45 5.05 20 6.5 20c1.95 0 4.05.4 5.5 1.5 1.35-.85 3.8-1.5 5.5-1.5 1.65 0 3.35.3 4.75 1.05.1.05.15.05.25.05.25 0 .5-.25.5-.5V6c-.6-.45-1.25-.75-2-1zm0 13.5c-1.1-.35-2.3-.5-3.5-.5-1.7 0-4.15.65-5.5 1.5V8c1.35-.85 3.8-1.5 5.5-1.5 1.2 0 2.4.15 3.5.5v11.5z"/>
                  </svg>
                </div>
                
                {/* Book Details */}
                <div className="flex-1">
                  <h4 className="font-serif text-lg text-amber-900 mb-1">{book.title}</h4>
                  <p className="text-sm text-amber-700 mb-2">by {book.author}, {book.year}</p>
                  <p className="text-sm text-gray-700 italic">{book.description}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        /* Book Reader */
        <div className="h-full flex flex-col">
          <div className="flex items-center justify-between mb-4 pb-4 border-b border-amber-300">
            <div>
              <h3 className="text-xl font-serif text-amber-900">{selectedBook.title}</h3>
              <p className="text-sm text-amber-700">by {selectedBook.author}, {selectedBook.year}</p>
            </div>
            <button
              onClick={handleCloseReader}
              className="px-4 py-2 bg-amber-200 text-amber-900 rounded-lg hover:bg-amber-300 transition-colors duration-200 font-serif"
            >
              Close Book
            </button>
          </div>
          
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-amber-800">Loading manuscript...</div>
            </div>
          ) : (
            <div className="flex-1 overflow-auto bg-amber-50 p-6 rounded-lg border border-amber-200">
              <div className="prose prose-amber max-w-none">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({node, ...props}) => <h1 {...props} className="text-3xl font-serif text-amber-900 mt-8 mb-4" />,
                    h2: ({node, ...props}) => <h2 {...props} className="text-2xl font-serif text-amber-900 mt-6 mb-3" />,
                    h3: ({node, ...props}) => <h3 {...props} className="text-xl font-serif text-amber-800 mt-4 mb-2" />,
                    h4: ({node, ...props}) => <h4 {...props} className="text-lg font-serif text-amber-800 mt-3 mb-2" />,
                    p: ({node, ...props}) => <p {...props} className="text-gray-800 mb-4 leading-relaxed" />,
                    li: ({node, ...props}) => <li {...props} className="text-gray-800 mb-1" />,
                    em: ({node, ...props}) => <em {...props} className="italic text-amber-700" />,
                    strong: ({node, ...props}) => <strong {...props} className="font-bold text-amber-900" />,
                    blockquote: ({node, ...props}) => (
                      <blockquote {...props} className="border-l-4 border-amber-400 pl-4 my-4 italic text-amber-800" />
                    ),
                    hr: ({node, ...props}) => <hr {...props} className="border-amber-300 my-8" />,
                    code: ({node, ...props}) => {
                      const { inline } = props as any;
                      return inline ? (
                        <code {...props} className="bg-amber-100 px-1 py-0.5 rounded text-amber-900 font-mono text-sm" />
                      ) : (
                        <code {...props} className="block bg-amber-100 p-4 rounded text-amber-900 font-mono text-sm overflow-x-auto" />
                      );
                    },
                  }}
                >
                  {bookContent}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CantastorieTab;