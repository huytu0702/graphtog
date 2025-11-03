'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Session } from 'next-auth';
import { AlertCircle, CheckCircle2, Compass, FileText, Loader2, Plus, Settings2, UploadCloud } from 'lucide-react';

import DocumentUpload from '@/components/document-upload/document-upload';
import QueryInterface from '@/components/query-interface';
import ToGQueryInterface from '@/components/tog-query-interface';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface Document {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  updated_at: string;
  version: number;
  last_processed_at?: string | null;
  content_hash?: string | null;
  error_message?: string | null;
}

interface StatusMeta {
  label: string;
  description: string;
  badgeClass: string;
}

type UploadFeedback = {
  type: 'success' | 'error';
  message: string;
};

const STATUS_META: Record<string, StatusMeta> = {
  pending: {
    label: 'Chờ xử lý',
    description: 'Nguồn đang chờ được xử lý.',
    badgeClass: 'text-amber-600 bg-amber-100',
  },
  processing: {
    label: 'Đang xử lý',
    description: 'Gemini đang trích xuất thực thể và quan hệ.',
    badgeClass: 'text-blue-600 bg-blue-100',
  },
  completed: {
    label: 'Hoàn tất',
    description: 'Nguồn sẵn sàng cho truy vấn.',
    badgeClass: 'text-emerald-600 bg-emerald-100',
  },
  failed: {
    label: 'Lỗi xử lý',
    description: 'Không thể xử lý nguồn, vui lòng thử lại.',
    badgeClass: 'text-rose-600 bg-rose-100',
  },
};

function getStatusMeta(status: string): StatusMeta {
  return (
    STATUS_META[status] || {
      label: status,
      description: 'Trạng thái không xác định từ hệ thống.',
      badgeClass: 'text-gray-600 bg-gray-100',
    }
  );
}

export default function DashboardHomeClient({ session }: { session: Session }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<UploadFeedback | null>(null);

  const apiBaseUrl = useMemo(() => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000', []);

  const fetchDocuments = useCallback(async () => {
    try {
      setLoadingDocuments(true);
      const response = await fetch(`${apiBaseUrl}/api/documents/`, {
        headers: {
          Authorization: `Bearer ${(session?.user as any)?.accessToken}`,
        },
        redirect: 'follow',
      });

      if (response.status === 401) {
        // Token is invalid or expired, sign out and redirect
        await fetch('/api/auth/signout', { method: 'POST' });
        window.location.href = '/login?error=session_expired';
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }

      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      console.error('Error fetching documents:', error);
      setUploadFeedback({
        type: 'error',
        message: 'Không thể tải danh sách nguồn. Vui lòng thử lại.',
      });
    } finally {
      setLoadingDocuments(false);
    }
  }, [apiBaseUrl, session]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUploadSuccess = (file?: File) => {
    setUploadDialogOpen(false);
    setUploadFeedback({
      type: 'success',
      message: file
        ? `Đã tải nguồn "${file.name}" thành công.`
        : 'Đã tải nguồn thành công.',
    });
    fetchDocuments();
  };

  const hasSources = documents.length > 0;

  // Get access token from session
  const accessToken = (session?.user as any)?.accessToken;

  const formatDateTime = (value?: string | null) => {
    if (!value) return '--';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString();
  };

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 py-8 lg:py-10">
        <div className="mb-6">
          <p className="text-sm text-gray-500">Xin chào,</p>
          <h1 className="text-2xl font-semibold text-gray-900">
            {session.user?.name || session.user?.email || 'nhà khai thác'}
          </h1>
        </div>

        {uploadFeedback && (
          <div
            className={`mb-6 flex items-center gap-3 rounded-2xl px-4 py-3 text-sm ${uploadFeedback.type === 'success'
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-rose-50 text-rose-700'
              }`}
          >
            {uploadFeedback.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0" />
            )}
            <span>{uploadFeedback.message}</span>
            <button
              className="ml-auto text-xs uppercase tracking-wide"
              onClick={() => setUploadFeedback(null)}
            >
              Đóng
            </button>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[360px,1fr]">
          <div className="flex flex-col gap-4">
            <div className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Nguồn</h2>
                  <p className="text-sm text-gray-500">Các nguồn đã lưu sẽ xuất hiện ở đây</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setUploadDialogOpen(true)}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Thêm
                  </Button>
                  <Button size="sm" variant="ghost">
                    <Compass className="h-4 w-4" />
                    <span className="ml-2 hidden lg:inline">Khám phá</span>
                  </Button>
                </div>
              </div>

              <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50/60 p-4">
                {loadingDocuments ? (
                  <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-sm text-gray-500">
                    <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                    <p>Đang tải danh sách nguồn...</p>
                  </div>
                ) : hasSources ? (
                  <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                    {documents.map((doc) => {
                      const statusMeta = getStatusMeta(doc.status);
                      return (
                        <div
                          key={doc.id}
                          className="rounded-2xl border border-white bg-white/90 p-4 shadow-sm"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
                              <FileText className="h-4 w-4 text-gray-400" />
                              <span className="truncate">{doc.filename}</span>
                            </div>
                            <span
                              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusMeta.badgeClass}`}
                            >
                              {statusMeta.label}
                            </span>
                          </div>
                          <p className="mt-2 text-xs text-gray-500">{statusMeta.description}</p>
                          <p className="mt-1 text-xs text-gray-400">
                            Version {doc.version} - Last processed {formatDateTime(doc.last_processed_at)}
                          </p>
                          <p className="mt-1 text-[11px] text-gray-400">
                            Created {formatDateTime(doc.created_at)} - Updated {formatDateTime(doc.updated_at)}
                          </p>
                          {doc.error_message && (
                            <p className="mt-2 text-xs text-rose-600">{doc.error_message}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-12 text-center">
                    <FileText className="h-10 w-10 text-gray-300" />
                    <p className="text-base font-medium text-gray-800">Chưa có nguồn nào</p>
                    <p className="text-sm text-gray-500">
                      Nhấp &quot;Thêm&quot; để tải tệp Markdown của bạn lên và bắt đầu xây dựng đồ thị kiến thức.
                    </p>
                    <Button variant="outline" onClick={() => setUploadDialogOpen(true)}>
                      <UploadCloud className="mr-2 h-4 w-4" />
                      Tải nguồn lên
                    </Button>
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-3xl border border-gray-200 bg-white p-4 text-sm text-gray-500 shadow-sm">
              <p className="font-medium text-gray-700">Tải một nguồn lên để bắt đầu</p>
              <p className="mt-1 text-xs text-gray-400">
                Hệ thống hiện hỗ trợ tệp Markdown (.md). Các nguồn đã tải: {documents.length}
              </p>
            </div>
          </div>

          <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Cuộc trò chuyện</h2>
                <p className="text-sm text-gray-500">Truy vấn được ghi lại cùng chuỗi suy luận.</p>
              </div>
              <Button variant="ghost" size="icon" className="text-gray-500">
                <Settings2 className="h-5 w-5" />
              </Button>
            </div>

            {hasSources ? (
              <div className="max-h-[620px] overflow-y-auto pr-1">
                <Tabs defaultValue="graphrag" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="graphrag">GraphRAG</TabsTrigger>
                    <TabsTrigger value="tog">Tree of Graphs (ToG)</TabsTrigger>
                  </TabsList>
                  <TabsContent value="graphrag" className="mt-4">
                    <QueryInterface accessToken={accessToken} documents={documents} />
                  </TabsContent>
                  <TabsContent value="tog" className="mt-4">
                    <ToGQueryInterface accessToken={accessToken} documents={documents} />
                  </TabsContent>
                </Tabs>
              </div>
            ) : (
              <div className="flex h-[500px] flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-gray-200 text-center">
                <UploadCloud className="h-12 w-12 text-gray-300" />
                <div>
                  <p className="text-lg font-medium text-gray-900">Thêm một nguồn để bắt đầu</p>
                  <p className="text-sm text-gray-500">Bạn cần ít nhất một nguồn để khởi tạo cuộc trò chuyện.</p>
                </div>
                <Button onClick={() => setUploadDialogOpen(true)}>
                  Tải nguồn lên
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Tải nguồn Markdown</DialogTitle>
            <DialogDescription>
              Kéo thả hoặc chọn một tệp .md để bắt đầu quá trình trích xuất đồ thị. Bạn có thể theo dõi trạng thái trong bảng Nguồn.
            </DialogDescription>
          </DialogHeader>
          <DocumentUpload onUploadSuccess={handleUploadSuccess} accessToken={accessToken} />
        </DialogContent>
      </Dialog>
    </>
  );
}
