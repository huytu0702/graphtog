'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Upload } from 'lucide-react';

interface DocumentUploadProps {
  onUploadSuccess?: () => void;
}

export default function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ success: boolean; message: string } | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    
    const file = acceptedFiles[0];
    setUploading(true);
    setUploadStatus(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        setUploadStatus({ success: true, message: `Document "${file.name}" uploaded successfully!` });
        onUploadSuccess?.();
      } else {
        const error = await response.json();
        setUploadStatus({ success: false, message: error.detail || 'Upload failed' });
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus({ success: false, message: 'An error occurred during upload' });
    } finally {
      setUploading(false);
    }
  }, [onUploadSuccess]);

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
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
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
        <div className={`mt-4 p-3 rounded-md text-center ${
          uploadStatus.success 
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