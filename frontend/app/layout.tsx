import './globals.css'

export const metadata = {
  title: 'GraphToG',
  description: 'Knowledge Graph-based Document Processing and Q&A System',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}