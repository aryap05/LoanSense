import { Link, Outlet, useLocation } from 'react-router-dom';
import { Shield, Home, FileText, Activity } from 'lucide-react';

export default function Layout() {
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'All Assessments', href: '/assessments', icon: FileText },
    { name: 'New Assessment', href: '/assess', icon: FileText },
    { name: 'Audit Logs', href: '/audit', icon: Activity },
  ];

  return (
    <div className="flex h-screen bg-lightBg font-sans">
      {/* Sidebar */}
      <div className="w-64 bg-darkSidebar text-white flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-gray-800">
          <Shield className="h-8 w-8 text-blue-500 mr-3" />
          <span className="text-xl font-bold tracking-tight">LoanSense</span>
        </div>
        <nav className="flex-1 px-4 py-6 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                {item.name}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 text-xs text-gray-500 text-center border-t border-gray-800">
          Agentic Underwriting System
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
