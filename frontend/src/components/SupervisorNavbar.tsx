import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  FileText, 
  Printer, 
  User, 
  ClipboardList, 
  MessageSquare,
  LogOut,
  AlertTriangle
} from 'lucide-react';

const SupervisorNavbar: React.FC = () => {
  const { user, signout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleSignout = () => {
    signout();
    navigate('/');
  };

  const navItems = [
    { path: '/supervisor/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/supervisor/orders', icon: FileText, label: 'Orders' },
    { path: '/supervisor/printers', icon: Printer, label: 'Printers' },
    // { path: '/supervisor/alerts', icon: AlertTriangle, label: 'Alerts' },
    { path: '/supervisor/activity-logs', icon: ClipboardList, label: 'Activity Logs' },
    { path: '/supervisor/queries', icon: MessageSquare, label: 'Query Management' },
    { path: '/supervisor/profile', icon: User, label: 'Profile' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="bg-white shadow-lg border-b fixed top-0 left-0 right-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and Brand */}
          <div className="flex items-center">
            <Link to="/supervisor/dashboard" className="flex items-center space-x-2">
              <Printer className="h-8 w-8 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">Supervisor Portal</span>
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition ${
                    isActive(item.path)
                      ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>

          {/* User Info and Logout */}
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-700">
              <div className="font-medium">{user?.username}</div>
              <div className="text-gray-500">Supervisor</div>
            </div>
            <button
              onClick={handleSignout}
              className="flex items-center space-x-1 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition"
            >
              <LogOut className="h-4 w-4" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default SupervisorNavbar;