'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Upload } from 'lucide-react';

interface DocumentUploadProps {
  onUploadSuccess?: (file?: File) => void;
  accessToken?: string;
}

export default function DocumentUpload({ onUploadSuccess, accessToken }: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ success: boolean; message: string } | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setUploading(true);
    setUploadStatus(null);

    if (!accessToken) {
      setUploadStatus({ success: false, message: 'Authentication required before uploading.' });
      setUploading(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);

      const headers: HeadersInit = {
        Authorization: `Bearer ${accessToken}`,
      };

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents/upload`,
        {
          method: 'POST',
          headers,
          body: formData,
        }
      );

      if (response.ok) {
        await response.json();
        setUploadStatus({ success: true, message: `Document "${file.name}" uploaded successfully!` });
        onUploadSuccess?.(file);
      } else {
        const error = await response.json();
        // Handle token expiration specifically
        if (response.status === 401 && error.detail === 'Invalid token') {
          setUploadStatus({
            success: false,
            message: 'Session expired. Please refresh the page and log in again.'
          });
        } else {
          setUploadStatus({ success: false, message: error.detail || 'Upload failed' });
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus({ success: false, message: 'An error occurred during upload' });
    } finally {
      setUploading(false);
    }
  }, [onUploadSuccess, accessToken]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/markdown': ['.md'],
      'text/x-markdown': ['.md']
    },
    maxFiles: 1,
    multiple: false
  });

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
          }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        {isDragActive ? (
          <p className="mt-2 text-lg font-medium text-gray-900">Drop the file here ...</p>
        ) : (
          <p className="mt-2 text-lg font-medium text-gray-900">
            Drag & drop a Markdown file here, or click to select
          </p>
        )}
        <p className="mt-1 text-sm text-gray-500">
          Supports Markdown (.md) files only (Max 1 file at a time)
        </p>
      </div>

      {uploading && (
        <div className="mt-4 text-center">
          <p className="text-blue-600">Uploading document...</p>
        </div>
      )}

      {uploadStatus && (
        <div className={`mt-4 p-3 rounded-md text-center ${uploadStatus.success
          ? 'bg-green-50 text-green-800'
          : 'bg-red-50 text-red-800'
          }`}>
          {uploadStatus.message}
        </div>
      )}

      <div className="mt-6">
        <Button
          type="button"
          className="w-full"
          disabled={uploading}
        >
          {uploading ? 'Uploading...' : 'Upload Document'}
        </Button>
      </div>
    </div>
  );
}
