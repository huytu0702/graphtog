'use client';

import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Session } from 'next-auth';
import DocumentUpload from '@/components/document-upload/document-upload';
import { Button } from '@/components/ui/button';
import { Loader2, RefreshCw, RotateCcw, UploadCloud } from 'lucide-react';

interface Document {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  updated_at: string;
  version: number;
  content_hash?: string | null;
  last_processed_at?: string | null;
  error_message?: string | null;
}

interface DocumentsPageClientProps {
  session: Session;
}

export default function DocumentsPageClient({ session }: DocumentsPageClientProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionStates, setActionStates] = useState<Record<string, { loading: boolean; message?: string; type?: 'success' | 'error' }>>({});

  // Get access token from session
  const accessToken = (session?.user as any)?.accessToken;
  const apiBaseUrl = useMemo(() => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000', []);
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const updateActionState = useCallback(
    (
      documentId: string,
      partial: Partial<{ loading: boolean; message?: string; type?: 'success' | 'error' }>
    ) => {
      setActionStates((prev) => {
        const prevState = prev[documentId] ?? { loading: false };
        const nextState = { ...prevState };

        if (Object.prototype.hasOwnProperty.call(partial, 'loading')) {
          nextState.loading = Boolean(partial.loading);
        }
        if (Object.prototype.hasOwnProperty.call(partial, 'message')) {
          nextState.message = partial.message;
        }
        if (Object.prototype.hasOwnProperty.call(partial, 'type')) {
          nextState.type = partial.type;
        }

        return { ...prev, [documentId]: nextState };
      });
    },
    []
  );

  const fetchDocuments = useCallback(async () => {
    if (!accessToken) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/api/documents`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (response.status === 401) {
        // Token is invalid or expired, sign out and redirect
        await fetch('/api/auth/signout', { method: 'POST' });
        window.location.href = '/login?error=session_expired';
        return;
      }

      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      } else {
        setDocuments([]);
        console.error('Error fetching documents:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  }, [accessToken, apiBaseUrl]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUploadSuccess = (_file?: File) => {
    fetchDocuments(); // Refresh the document list after upload
  };

  const triggerFileDialog = (documentId: string) => {
    const input = fileInputRefs.current[documentId];
    if (input) {
      input.value = '';
      input.click();
    }
  };

  const handleFileSelection = async (documentId: string, event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!accessToken) {
      updateActionState(documentId, {
        loading: false,
        message: 'Authentication required. Please sign in again.',
        type: 'error',
      });
      return;
    }

    updateActionState(documentId, { loading: true, message: undefined, type: undefined });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${apiBaseUrl}/api/documents/${documentId}/update`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Document update failed');
      }

      updateActionState(documentId, {
        loading: false,
        message: data.message || `Incremental update started (v${data.version ?? ''}).`,
        type: 'success',
      });
      fetchDocuments();
    } catch (error) {
      console.error('Error updating document:', error);
      updateActionState(documentId, {
        loading: false,
        message: error instanceof Error ? error.message : 'Failed to update document',
        type: 'error',
      });
    } finally {
      event.target.value = '';
    }
  };

  const handleReprocess = async (documentId: string, forceFull = false) => {
    if (!accessToken) {
      updateActionState(documentId, {
        loading: false,
        message: 'Authentication required. Please sign in again.',
        type: 'error',
      });
      return;
    }

    updateActionState(documentId, { loading: true, message: undefined, type: undefined });

    try {
      const response = await fetch(
        `${apiBaseUrl}/api/documents/${documentId}/reprocess${forceFull ? '?force_full=true' : ''}`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to reprocess document');
      }

      updateActionState(documentId, {
        loading: false,
        message: data.message || 'Reprocessing started.',
        type: 'success',
      });
      fetchDocuments();
    } catch (error) {
      console.error('Error reprocessing document:', error);
      updateActionState(documentId, {
        loading: false,
        message: error instanceof Error ? error.message : 'Failed to reprocess document',
        type: 'error',
      });
    }
  };

  const formatDate = (value?: string | null) => {
    if (!value) return '--';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString();
  };

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0 space-y-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Your Documents</h1>
        </div>

        <div>
          <DocumentUpload onUploadSuccess={handleUploadSuccess} accessToken={accessToken} />
        </div>

        <div>
          <h2 className="text-xl font-semibold text-gray-800">Uploaded Documents</h2>

          {loading ? (
            <div className="mt-6 flex items-center text-sm text-gray-500">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading documents...
            </div>
          ) : documents.length === 0 ? (
            <p className="mt-4 text-gray-600">No documents uploaded yet.</p>
          ) : (
            <div className="mt-4 space-y-4">
              {documents.map((doc) => {
                const actionState = actionStates[doc.id];
                return (
                  <div
                    key={doc.id}
                    className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">{doc.filename}</h3>
                        <p className="mt-1 text-sm text-gray-600">
                          Status:{' '}
                          <span
                            className={`font-medium ${doc.status === 'completed'
                              ? 'text-green-600'
                              : doc.status === 'processing'
                                ? 'text-blue-600'
                                : doc.status === 'failed'
                                  ? 'text-red-600'
                                  : 'text-gray-600'
                              }`}
                          >
                            {doc.status}
                          </span>
                        </p>
                        <p className="mt-1 text-sm text-gray-500">
                          Version {doc.version} - Last processed: {formatDate(doc.last_processed_at)}
                        </p>
                        <p className="mt-1 text-xs text-gray-400">
                          Created: {formatDate(doc.created_at)} - Updated: {formatDate(doc.updated_at)}
                        </p>
                        {doc.error_message && (
                          <p className="mt-2 text-sm text-red-600">{doc.error_message}</p>
                        )}
                        {doc.content_hash && (
                          <p className="mt-2 text-xs font-mono text-gray-400 break-all">
                            Hash: {doc.content_hash}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-col items-stretch gap-2 md:min-w-[220px]">
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => triggerFileDialog(doc.id)}
                          disabled={actionState?.loading}
                          className="justify-center"
                        >
                          <UploadCloud className="mr-2 h-4 w-4" />
                          Upload new version
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => handleReprocess(doc.id, false)}
                          disabled={actionState?.loading}
                          className="justify-center"
                        >
                          <RefreshCw className="mr-2 h-4 w-4" />
                          Reprocess (incremental)
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => handleReprocess(doc.id, true)}
                          disabled={actionState?.loading}
                          className="justify-center text-red-600 hover:text-red-600"
                        >
                          <RotateCcw className="mr-2 h-4 w-4" />
                          Force full reprocess
                        </Button>
                      </div>
                    </div>

                    <input
                      ref={(el) => {
                        fileInputRefs.current[doc.id] = el;
                      }}
                      type="file"
                      accept=".md,text/markdown"
                      className="hidden"
                      onChange={(event) => handleFileSelection(doc.id, event)}
                    />

                    {actionState?.message && (
                      <div
                        className={`mt-3 rounded-md px-3 py-2 text-sm ${actionState.type === 'success'
                          ? 'bg-green-50 text-green-700'
                          : actionState.type === 'error'
                            ? 'bg-red-50 text-red-700'
                            : 'bg-gray-50 text-gray-600'
                          }`}
                      >
                        {actionState.message}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
