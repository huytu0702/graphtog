'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return null; // Will be redirected by useEffect
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">GraphToG Dashboard</h1>
            </div>
            <nav className="flex space-x-4">
              <Link href="/dashboard" className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-gray-900">
                Documents
              </Link>
              <Link href="/query" className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-gray-900">
                Query
              </Link>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  // Sign out and redirect
                  await fetch('/api/auth/signout', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({}),
                  });
                  router.push('/login');
                }}
              >
                <Button type="submit" variant="outline" size="sm">
                  Sign out
                </Button>
              </form>
            </nav>
          </div>
        </div>
      </header>
      <main>
        {children}
      </main>
    </div>
  );
}