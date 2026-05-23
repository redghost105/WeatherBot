import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { TopNav } from '@/components/TopNav'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Polymarket Trading Dashboard',
  description:
    'Real-time trading dashboard for Kalshi weather prediction markets',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="h-full bg-canvas text-body flex flex-col">
        <TopNav />
        <main className="flex-1 overflow-auto">{children}</main>
      </body>
    </html>
  )
}
