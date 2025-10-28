import { getServerSession } from 'next-auth';

import { authOptions } from '@/lib/auth';

import DashboardHomeClient from './page.client';

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    return null;
  }

  return <DashboardHomeClient session={session} />;
}
