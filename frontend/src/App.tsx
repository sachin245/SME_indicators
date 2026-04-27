import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Overview from './pages/Overview'
import SectorDetail from './pages/SectorDetail'
import CompanyBrowser from './pages/CompanyBrowser'
import CompanyDetail from './pages/CompanyDetail'
import FilingsBrowser from './pages/FilingsBrowser'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 container mx-auto px-4 py-6 max-w-7xl">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/sectors/:sector" element={<SectorDetail />} />
          <Route path="/companies" element={<CompanyBrowser />} />
          <Route path="/companies/:code" element={<CompanyDetail />} />
          <Route path="/filings" element={<FilingsBrowser />} />
        </Routes>
      </main>
    </div>
  )
}
