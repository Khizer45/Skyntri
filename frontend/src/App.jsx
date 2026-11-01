import { Route, Routes } from 'react-router-dom'
import AdminRoute from './components/AdminRoute.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import AdminOrders from './pages/AdminOrders.jsx'
import AdminProducts from './pages/AdminProducts.jsx'
import Cart from './pages/Cart.jsx'
import AIAssistant from './pages/AIAssistant.jsx'
import Contact from './pages/Contact.jsx'
import Dashboard from './pages/Dashboard.jsx'
import ForgotPassword from './pages/ForgotPassword.jsx'
import History from './pages/History.jsx'
import IngredientScanner from './pages/IngredientScanner.jsx'
import LandingPage from './pages/LandingPage.jsx'
import Login from './pages/Login.jsx'
import NotFound from './pages/NotFound.jsx'
import Orders from './pages/Orders.jsx'
import ProductDetail from './pages/ProductDetail.jsx'
import Profile from './pages/Profile.jsx'
import ProgressChecker from './pages/ProgressChecker.jsx'
import Reports from './pages/Reports.jsx'
import ResetPassword from './pages/ResetPassword.jsx'
import Settings from './pages/Settings.jsx'
import Shop from './pages/Shop.jsx'
import Signup from './pages/Signup.jsx'
import SkinAnalysis from './pages/SkinAnalysis.jsx'

export default function App() {
  return (
    <Routes>
      {/* Public Landing Page */}
      <Route path="/" element={<LandingPage />} />

      {/* Authentication */}
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Protected Dashboard */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/skin-analysis"
        element={
          <ProtectedRoute>
            <SkinAnalysis />
          </ProtectedRoute>
        }
      />

      <Route
        path="/ingredient-scanner"
        element={
          <ProtectedRoute>
            <IngredientScanner />
          </ProtectedRoute>
        }
      />

      <Route
        path="/progress-checker"
        element={
          <ProtectedRoute>
            <ProgressChecker />
          </ProtectedRoute>
        }
      />

      <Route
        path="/assistant"
        element={
          <ProtectedRoute>
            <AIAssistant />
          </ProtectedRoute>
        }
      />

      <Route
        path="/history"
        element={
          <ProtectedRoute>
            <History />
          </ProtectedRoute>
        }
      />

      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <Reports />
          </ProtectedRoute>
        }
      />

      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />

      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />

      <Route
        path="/contact"
        element={
          <ProtectedRoute>
            <Contact />
          </ProtectedRoute>
        }
      />

      {/* Shop */}
      <Route path="/shop" element={<ProtectedRoute><Shop /></ProtectedRoute>} />
      <Route path="/shop/:productId" element={<ProtectedRoute><ProductDetail /></ProtectedRoute>} />
      <Route path="/cart" element={<ProtectedRoute><Cart /></ProtectedRoute>} />
      <Route path="/orders" element={<ProtectedRoute><Orders /></ProtectedRoute>} />

      {/* Administration (server also enforces the admin role) */}
      <Route path="/admin/products" element={<AdminRoute><AdminProducts /></AdminRoute>} />
      <Route path="/admin/orders" element={<AdminRoute><AdminOrders /></AdminRoute>} />

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}