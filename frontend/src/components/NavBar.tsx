'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const LINKS = [
  { href: '/',             label: 'Dashboard'    },
  { href: '/experiments',  label: 'Experiments'  },
  { href: '/injection',    label: 'Injection'     },
]

export default function NavBar() {
  const pathname = usePathname()

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-8">
      <span className="font-bold text-gray-900 text-lg tracking-tight">
        EvalForge
      </span>
      <div className="flex gap-6">
        {LINKS.map(({ href, label }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              className={
                active
                  ? 'text-indigo-600 font-semibold border-b-2 border-indigo-600 pb-0.5'
                  : 'text-gray-500 hover:text-gray-800 transition-colors'
              }
            >
              {label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
