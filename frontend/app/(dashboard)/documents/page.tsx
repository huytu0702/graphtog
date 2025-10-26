import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import DocumentsPageClient from './page.client';

// Ensure dynamic rendering for this page
export const dynamic = 'force-dynamic';

export default async function DocumentsPage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    return null; // Will be caught by layout middleware
  }

  return <DocumentsPageClient session={session} />;
}