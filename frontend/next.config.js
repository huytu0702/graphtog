/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return {
      beforeFiles: [
        // Forward backend API routes to FastAPI backend
        // Exclude /api/auth/* which is handled by NextAuth.js
        // Exclude /api/tog/* which uses custom route handlers with extended timeout
        {
          source: '/api/documents/:path*',
          destination: 'http://localhost:8000/api/documents/:path*',
        },
        {
          source: '/api/queries/:path*',
          destination: 'http://localhost:8000/api/queries/:path*',
        },
        {
          source: '/api/communities/:path*',
          destination: 'http://localhost:8000/api/communities/:path*',
        },
        {
          source: '/api/visualize/:path*',
          destination: 'http://localhost:8000/api/visualize/:path*',
        },
        {
          source: '/api/admin/:path*',
          destination: 'http://localhost:8000/api/admin/:path*',
        },
        {
          source: '/api/extract/:path*',
          destination: 'http://localhost:8000/api/extract/:path*',
        },
        {
          source: '/api/cache/:path*',
          destination: 'http://localhost:8000/api/cache/:path*',
        },
        {
          source: '/api/analyze/:path*',
          destination: 'http://localhost:8000/api/analyze/:path*',
        },
      ],
    }
  },
}

module.exports = nextConfig