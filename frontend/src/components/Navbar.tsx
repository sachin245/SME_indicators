import { NavLink } from 'react-router-dom'
import { BarChart3, Building2, FileText, LayoutDashboard } from 'lucide-react'
import clsx from 'clsx'

const links = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/companies', label: 'Companies', icon: Building2 },
  { to: '/filings', label: 'Filings', icon: FileText },
]

export default function Navbar() {
  return (
    <nav className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
      <div className="container mx-auto px-4 max-w-7xl flex items-center gap-8 h-14">
        <div className="flex items-center gap-2 font-semibold text-indigo-400 shrink-0">
          <BarChart3 size={20} />
          <span>SME Indicators</span>
        </div>
        <div className="flex items-center gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-indigo-600/30 text-indigo-300'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                )
              }
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  )
}
