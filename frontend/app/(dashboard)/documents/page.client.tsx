'use client';

import { useState, useEffect, useCallback } from 'react';
import DocumentUpload from '@/components/document-upload/document-upload';
import { Session } from 'next-auth';

interface Document {
    id: number;
    filename: string;
    status: string;
    created_at: string;
    error_message?: string;
}

interface DocumentsPageClientProps {
    session: Session;
}

export default function DocumentsPageClient({ session }: DocumentsPageClientProps) {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);

    // Get access token from session
    const accessToken = (session?.user as any)?.accessToken;

    const fetchDocuments = useCallback(async () => {
        if (!accessToken) {
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents`,
                {
                    headers: {
                        Authorization: `Bearer ${accessToken}`,
                    },
                }
            );

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
    }, [accessToken]);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    const handleUploadSuccess = (_file?: File) => {
        fetchDocuments(); // Refresh the document list after upload
    };

    return (
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            <div className="px-4 py-6 sm:px-0">
                <h1 className="text-2xl font-bold text-gray-900">Your Documents</h1>

                <div className="my-8">
                    <DocumentUpload onUploadSuccess={handleUploadSuccess} accessToken={accessToken} />
                </div>

                <div className="mt-10">
                    <h2 className="text-xl font-semibold text-gray-800">Uploaded Documents</h2>

                    {loading ? (
                        <p className="mt-4 text-gray-600">Loading documents...</p>
                    ) : documents.length === 0 ? (
                        <p className="mt-4 text-gray-600">No documents uploaded yet.</p>
                    ) : (
                        <div className="mt-4 space-y-4">
                            {documents.map((doc) => (
                                <div
                                    key={doc.id}
                                    className="p-4 border rounded-lg flex justify-between items-center bg-white shadow-sm"
                                >
                                    <div>
                                        <h3 className="font-medium text-gray-900">{doc.filename}</h3>
                                        <p className="text-sm text-gray-500">
                                            Status:{' '}
                                            <span
                                                className={`font-medium ${
                                                    doc.status === 'completed'
                                                        ? 'text-green-600'
                                                        : doc.status === 'processing'
                                                            ? 'text-blue-600'
                                                            : 'text-red-600'
                                                }`}
                                            >
                                                {doc.status}
                                            </span>
                                            {doc.error_message && (
                                                <span className="block text-sm text-red-500">{doc.error_message}</span>
                                            )}
                                        </p>
                                    </div>
                                    <div className="text-sm text-gray-500">
                                        {new Date(doc.created_at).toLocaleDateString()}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
