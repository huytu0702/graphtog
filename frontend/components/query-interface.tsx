'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface QueryResult {
  id?: number;
  query: string;
  answer: string;
  citations: string[];
  entities_found: string[];
  status: string;
  error?: string;
}

interface Document {
  id: number;
  filename: string;
  status: string;
}

interface QueryInterfaceProps {
  accessToken?: string;
  documents?: Document[];
}

export default function QueryInterface({ accessToken, documents = [] }: QueryInterfaceProps) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);

  // Auto-select the most recent completed document
  const completedDocs = documents.filter(doc => doc.status === 'completed');
  if (completedDocs.length > 0 && selectedDocumentId === null) {
    setSelectedDocumentId(completedDocs[0].id);
  }

  const handleQuerySubmit = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/queries`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          query: query,
          hop_limit: 1,
          document_id: selectedDocumentId
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult(data);
      } else {
        setResult({
          query: query,
          answer: '',
          citations: [],
          entities_found: [],
          status: 'error',
          error: data.detail || 'An error occurred'
        });
      }
    } catch (error) {
      console.error('Query error:', error);
      setResult({
        query: query,
        answer: '',
        citations: [],
        entities_found: [],
        status: 'error',
        error: 'Failed to connect to the server'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div className="space-y-6">
        {completedDocs.length > 0 && (
          <div>
            <label htmlFor="document-select" className="block text-sm font-medium text-gray-700 mb-1">
              Select document:
            </label>
            <select
              id="document-select"
              value={selectedDocumentId || ''}
              onChange={(e) => setSelectedDocumentId(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            >
              {completedDocs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-1">
            Ask a question about your documents:
          </label>
          <Textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your question here..."
            rows={4}
            className="w-full"
            disabled={loading}
          />
        </div>

        <div className="flex justify-center">
          <Button
            onClick={handleQuerySubmit}
            disabled={loading || !query.trim()}
            className="w-full sm:w-auto"
          >
            {loading ? 'Processing...' : 'Ask Question'}
          </Button>
        </div>

        {result && (
          <div className="mt-6 p-4 bg-white rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Answer</h3>

            {result.status === 'error' ? (
              <div className="text-red-600">
                <p className="font-medium">Error:</p>
                <p>{result.error}</p>
              </div>
            ) : (
              <>
                <div className="prose max-w-none mb-4">
                  <p>{result.answer || 'No answer generated.'}</p>
                </div>

                {result.entities_found && result.entities_found.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-700">Entities Found:</p>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {result.entities_found.map((entity, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                        >
                          {entity}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {result.citations && result.citations.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700">Citations:</p>
                    <ul className="mt-1 list-disc list-inside text-sm text-gray-600">
                      {result.citations.map((citation, index) => (
                        <li key={index}>{citation}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}