import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ScientificBooksTabProps {
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

const SCIENTIFIC_BOOKS: Book[] = [
  {
    id: 1,
    title: "Observations on the Nature of Memory",
    author: "Fra Benedetto di Memoria",
    year: "1472",
    fileName: "observations-on-the-nature-of-memory.md",
    description: "A systematic study of how the mind preserves and forgets"
  },
  {
    id: 2,
    title: "Studies in Decision Delay",
    author: "Maestro Giovanni il Temporale",
    year: "1473",
    fileName: "studies-in-decision-delay.md",
    description: "An investigation into the temporal nature of thought and action"
  },
  {
    id: 3,
    title: "The Mathematics of Trust",
    author: "Donna Caterina la Misuratrice",
    year: "1433",
    fileName: "the-mathematics-of-trust.md",
    description: "A quantitative study of affection and commerce"
  },
  {
    id: 4,
    title: "Constraints of Creation",
    author: "Magister Elisabetta delle Limitazioni",
    year: "1574",
    fileName: "constraints-of-creation.md",
    description: "A systematic study of the invisible boundaries that govern our world"
  },
  {
    id: 5,
    title: "The Conservation of Wealth",
    author: "Maestro Lorenzo della Circolazione",
    year: "1487",
    fileName: "the-conservation-of-wealth.md",
    description: "A mathematical treatise on the immutable laws of Venetian commerce"
  },
  {
    id: 6,
    title: "The Great Knowledge",
    author: "Fra Paradosso del Sapere",
    year: "1485",
    fileName: "the-great-knowledge.md",
    description: "Studies in inherited understanding"
  },
  {
    id: 7,
    title: "Translation Failures: When Wisdom Doesn't Apply",
    author: "Dottore Francesco il Traduttore",
    year: "1490",
    fileName: "translation-failures-when-wisdom-doesnt-apply.md",
    description: "A catalogue of inherited understanding that cannot find expression"
  },
  {
    id: 8,
    title: "Chronicles of Change",
    author: "Cronista Marco delle Mutazioni",
    year: "1488",
    fileName: "chronicles-of-change.md",
    description: "A history of reality updates"
  },
  {
    id: 9,
    title: "Detecting the Impossible",
    author: "Investigatore Giulio dell'Impossibile",
    year: "1487",
    fileName: "detecting-the-impossible.md",
    description: "Methods for identifying physics changes"
  },
  {
    id: 10,
    title: "Patterns of System Response",
    author: "Filosofo Tommaso dell'Equilibrio",
    year: "1423",
    fileName: "patterns-of-system-response.md",
    description: "An investigation into Venice's living spirit and collective wisdom"
  },
  {
    id: 11,
    title: "The Limits of Observation",
    author: "Contemplativo Benedetto dei Confini",
    year: "1489",
    fileName: "the-limits-of-observation.md",
    description: "An inquiry into the boundaries of knowledge in our Republic"
  },
  {
    id: 12,
    title: "Collective Emergence Phenomena",
    author: "Studioso Pietro dell'Emergenza",
    year: "1477",
    fileName: "collective-emergence-phenomena.md",
    description: "A study of how many become one without losing themselves"
  },
  {
    id: 13,
    title: "Records of Anomalous Events",
    author: "Cronista Lucia dell'Anomalia",
    year: "1486",
    fileName: "records-of-anomalous-events.md",
    description: "A catalog of unexplained phenomena and violations of natural law"
  },
  {
    id: 14,
    title: "Temporal Mechanics",
    author: "Maestro Cronos del Tempo",
    year: "1490",
    fileName: "temporal-mechanics.md",
    description: "A study of time's sacred rhythms in the Venetian Republic"
  },
  {
    id: 15,
    title: "De Scientia Scientiæ: On the Knowledge of Knowledge",
    author: "Magistro Tommaso dell'Indagine",
    year: "1491",
    fileName: "on-the-knowledge-of-knowledge.md",
    description: "A treatise on the practice of natural philosophy"
  }
];

const ScientificBooksTab: React.FC<ScientificBooksTabProps> = ({ currentUsername }) => {
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [bookContent, setBookContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  const handleBookClick = async (book: Book) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/books/science/${book.fileName}`);
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
            <h3 className="text-2xl font-serif text-amber-900 mb-2">Casa delle Scienze Naturali</h3>
            <p className="text-amber-700 italic">
              The foundational texts of natural philosophy, available to all Scientisti seeking to understand the hidden mechanisms of our Republic
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-auto">
            {SCIENTIFIC_BOOKS.map((book) => (
              <div
                key={book.id}
                className="bg-amber-50 border-2 border-amber-300 rounded-lg p-4 hover:bg-amber-100 cursor-pointer transition-colors duration-200 flex items-start space-x-4"
                onClick={() => handleBookClick(book)}
              >
                {/* Book Icon */}
                <div className="flex-shrink-0">
                  <svg
                    className="w-16 h-16 text-amber-700"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
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

export default ScientificBooksTab;