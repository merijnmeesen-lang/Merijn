import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { Overview } from './pages/Overview'
import { Products } from './pages/Products'
import { StockCount } from './pages/StockCount'
import { WasteLog } from './pages/WasteLog'

function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/" element={<StockCount />} />
          <Route path="/derving" element={<WasteLog />} />
          <Route path="/overzicht" element={<Overview />} />
          <Route path="/producten" element={<Products />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </Router>
  )
}

export default App
