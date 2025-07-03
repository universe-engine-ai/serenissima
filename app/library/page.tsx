'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

interface DocumentInfo {
  name: string;
  path: string;
  type: 'markdown' | 'pdf' | 'tex';
  size: number;
  modified: string;
  category: 'books' | 'papers';
}

interface DocumentsResponse {
  success: boolean;
  documents: DocumentInfo[];
  total: number;
  error?: string;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const getFileIcon = (type: string): string => {
  switch (type) {
    case 'pdf':
      return '📄';
    case 'markdown':
      return '📝';
    case 'tex':
      return '📜';
    default:
      return '📄';
  }
};

const getCategoryIcon = (category: string): string => {
  switch (category) {
    case 'books':
      return '📚';
    case 'papers':
      return '📋';
    default:
      return '📄';
  }
};

export default function LibraryPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<'all' | 'books' | 'papers'>('all');
  const [selectedDocument, setSelectedDocument] = useState<DocumentInfo | null>(null);
  const [documentContent, setDocumentContent] = useState<string | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/documents');
      const data: DocumentsResponse = await response.json();
      
      if (data.success) {
        setDocuments(data.documents);
      } else {
        setError(data.error || 'Failed to fetch documents');
      }
    } catch (err) {
      setError('Network error while fetching documents');
      console.error('Error fetching documents:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDocumentContent = async (doc: DocumentInfo) => {
    if (doc.type === 'pdf') {
      // Open PDF in new tab
      window.open(`/api/documents?action=serve&path=${doc.path}`, '_blank');
      return;
    }

    try {
      setContentLoading(true);
      setSelectedDocument(doc);
      setDocumentContent(null);

      const response = await fetch(`/api/documents?action=serve&path=${doc.path}`);
      
      if (response.ok) {
        const content = await response.text();
        setDocumentContent(content);
      } else {
        setError('Failed to load document content');
      }
    } catch (err) {
      setError('Error loading document content');
      console.error('Error fetching document content:', err);
    } finally {
      setContentLoading(false);
    }
  };

  const filteredDocuments = documents.filter(doc => 
    selectedCategory === 'all' || doc.category === selectedCategory
  );

  const categoryCounts = {
    books: documents.filter(d => d.category === 'books').length,
    papers: documents.filter(d => d.category === 'papers').length,
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-orange-100 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-amber-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading Venice Library...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-orange-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-amber-800 to-orange-800 text-white shadow-lg">
        <div className="max-w-6xl mx-auto px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-3">
                📖 Venice Digital Library
              </h1>
              <p className="text-amber-100 mt-2">
                Historical documents and research papers from La Serenissima
              </p>
            </div>
            <Link 
              href="/"
              className="bg-amber-600 hover:bg-amber-700 px-4 py-2 rounded-lg transition-colors"
            >
              ← Back to Venice
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-8">
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-6 sticky top-8">
              <h2 className="text-xl font-bold text-gray-800 mb-4">Browse Collection</h2>
              
              {/* Category Filter */}
              <div className="space-y-2 mb-6">
                <button
                  onClick={() => setSelectedCategory('all')}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                    selectedCategory === 'all' 
                      ? 'bg-amber-100 text-amber-800 border-l-4 border-amber-600' 
                      : 'hover:bg-gray-100'
                  }`}
                >
                  📚 All Documents ({documents.length})
                </button>
                <button
                  onClick={() => setSelectedCategory('books')}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                    selectedCategory === 'books' 
                      ? 'bg-amber-100 text-amber-800 border-l-4 border-amber-600' 
                      : 'hover:bg-gray-100'
                  }`}
                >
                  📖 Books ({categoryCounts.books})
                </button>
                <button
                  onClick={() => setSelectedCategory('papers')}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                    selectedCategory === 'papers' 
                      ? 'bg-amber-100 text-amber-800 border-l-4 border-amber-600' 
                      : 'hover:bg-gray-100'
                  }`}
                >
                  📋 Research Papers ({categoryCounts.papers})
                </button>
              </div>

              {/* Quick Stats */}
              <div className="border-t pt-4">
                <h3 className="font-semibold text-gray-700 mb-2">Collection Stats</h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <div>Total Documents: {documents.length}</div>
                  <div>Categories: {Object.keys(categoryCounts).length}</div>
                  <div>Last Updated: {documents.length > 0 ? formatDate(Math.max(...documents.map(d => new Date(d.modified).getTime())).toString()) : 'N/A'}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2">
            {!selectedDocument ? (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-2xl font-bold text-gray-800 mb-6">
                  {selectedCategory === 'all' ? 'All Documents' : 
                   selectedCategory === 'books' ? 'Books' : 'Research Papers'}
                </h2>

                {filteredDocuments.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">📚</div>
                    <p className="text-gray-500">No documents found in this category.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {filteredDocuments.map((doc, index) => (
                      <div 
                        key={index}
                        className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => fetchDocumentContent(doc)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-2xl">{getFileIcon(doc.type)}</span>
                              <span className="text-lg">{getCategoryIcon(doc.category)}</span>
                              <h3 className="text-lg font-semibold text-gray-800">{doc.name}</h3>
                            </div>
                            <div className="text-sm text-gray-600 space-y-1">
                              <div>Category: {doc.category}</div>
                              <div>Type: {doc.type.toUpperCase()}</div>
                              <div>Size: {formatFileSize(doc.size)}</div>
                              <div>Modified: {formatDate(doc.modified)}</div>
                            </div>
                          </div>
                          <div className="ml-4">
                            <button className="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg text-sm transition-colors">
                              {doc.type === 'pdf' ? 'Open PDF' : 'Read'}
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                      {getFileIcon(selectedDocument.type)} {selectedDocument.name}
                    </h2>
                    <p className="text-gray-600">
                      {selectedDocument.category} • {selectedDocument.type.toUpperCase()} • {formatFileSize(selectedDocument.size)}
                    </p>
                  </div>
                  <button 
                    onClick={() => setSelectedDocument(null)}
                    className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                  >
                    ← Back to List
                  </button>
                </div>

                {contentLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-amber-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading document...</p>
                  </div>
                ) : documentContent ? (
                  <div className="prose prose-amber max-w-none">
                    {selectedDocument.type === 'markdown' ? (
                      <div className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded-lg overflow-x-auto">
                        {documentContent}
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded-lg overflow-x-auto">
                        {documentContent}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <p className="text-gray-500">Failed to load document content.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}