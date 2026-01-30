import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/NavBar';
import SupervisorNavbar from './components/SupervisorNavbar'; // Add this import
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import NewOrder from './pages/NewOrder';
import { MyOrders } from './pages/MyOrders';
import { StoresList } from './pages/StoresList';
import { OrderHistory } from './pages/OrderHistory';
import { AuthProvider, useAuth } from './context/AuthContext';
import SupervisorDashboard from './pages/SupervisorDashboard';
import SupervisorOrders from './pages/SupervisorOrders';
import SupervisorPrinters from './pages/SupervisorPrinters'; // Add these imports
// import SupervisorAlerts from './pages/SupervisorAlerts';
import SupervisorActivityLogs from './pages/SupervisorActivityLogs';
import SupervisorQueries from './pages/SupervisorQueries';
import SupervisorProfile from './pages/SupervisorProfile';

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/" />;
};

function AppContent() {
  const { isAuthenticated, userRole } = useAuth();

  return (
    <Router>
      <div className="min-h-screen bg-gray-50 pt-12">
        {/* Conditional Navbar based on user role */}
        {isAuthenticated && userRole === 'supervisor' ? (
          <SupervisorNavbar />
        ) : (
          <Navbar />
        )}
        
        <Routes>
          <Route path="/" element={<Home />} />
          
          {/* Customer Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/new-order"
            element={
              <ProtectedRoute>
                <NewOrder />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-orders"
            element={
              <ProtectedRoute>
                <MyOrders />
              </ProtectedRoute>
            }
          />
          <Route
            path="/orders/:orderId/history"
            element={
              <ProtectedRoute>
                <OrderHistory />
              </ProtectedRoute>
            }
          />
          <Route path="/stores" element={<StoresList />} />
          
          {/* Supervisor Routes */}
          <Route
            path="/supervisor/dashboard"
            element={
              <ProtectedRoute>
                <SupervisorDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/supervisor/orders"
            element={
              <ProtectedRoute>
                <SupervisorOrders />
              </ProtectedRoute>
            }
          />
          <Route
            path="/supervisor/printers"
            element={
              <ProtectedRoute>
                <SupervisorPrinters />
              </ProtectedRoute>
            }
          />
          {/* <Route
            path="/supervisor/alerts"
            element={
              <ProtectedRoute>
                <SupervisorAlerts />
              </ProtectedRoute>
            }
          /> */}
          <Route
            path="/supervisor/activity-logs"
            element={
              <ProtectedRoute>
                <SupervisorActivityLogs />
              </ProtectedRoute>
            }
          />
          <Route
            path="/supervisor/queries"
            element={
              <ProtectedRoute>
                <SupervisorQueries />
              </ProtectedRoute>
            }
          />
          <Route
            path="/supervisor/profile"
            element={
              <ProtectedRoute>
                <SupervisorProfile />
              </ProtectedRoute>
            }
          />
        </Routes>
      </div>
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;