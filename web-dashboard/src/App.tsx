import { Routes, Route } from 'react-router-dom'
import { Box } from '@mui/material'

import Layout from './components/Layout/Layout'
import Dashboard from './pages/Dashboard/Dashboard'
import Catalog from './pages/Catalog/Catalog'
import Products from './pages/Products/Products'
import Suppliers from './pages/Suppliers/Suppliers'
import Analytics from './pages/Analytics/Analytics'
import Reports from './pages/Reports/Reports'
import Settings from './pages/Settings/Settings'

function App() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/products" element={<Products />} />
          <Route path="/suppliers" element={<Suppliers />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Box>
  )
}

export default App
