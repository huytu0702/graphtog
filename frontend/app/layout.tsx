import './globals.css'
import { ReactNode } from 'react'

export const metadata = {
  title: 'GraphToG',
  description: 'Knowledge Graph-based Document Processing and Q&A System',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}