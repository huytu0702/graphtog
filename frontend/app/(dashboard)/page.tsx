import { auth } from '@/app/api/auth/[...nextauth]/route';

export default async function DashboardPage() {
  const session = await auth();
  
  if (!session) {
    // This page will be redirected by the layout component
    return null;
  }

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="border-4 border-dashed border-gray-200 rounded-lg h-96 flex items-center justify-center">
          <h2 className="text-2xl font-bold text-gray-800">
            Welcome to GraphToG, {session.user?.name || session.user?.email}!
          </h2>
        </div>
      </div>
    </div>
  );
}