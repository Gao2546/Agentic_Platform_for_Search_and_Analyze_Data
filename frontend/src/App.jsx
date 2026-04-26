import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ScopeList from './pages/ScopeList'; // เปลี่ยนจาก ScopeManager
import ScopeDetail from './pages/ScopeDetail'; // เพิ่มหน้าใหม่
import ScheduleFlow from './pages/ScheduleFlow';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        {/* Navigation Bar */}
        <nav className="bg-blue-800 text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <div className="flex space-x-8">
                <span className="font-bold text-xl tracking-wider">Agentic Platform</span>
                <div className="flex space-x-4">
                  <Link to="/" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition">
                    Dashboard
                  </Link>
                  <Link to="/scopes" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition">
                    Scopes
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/scopes" element={<ScopeList />} />
            <Route path="/scopes/:scopeId" element={<ScopeDetail />} />
            <Route path="/scopes/:scopeId/schedules/:scheduleId/flow" element={<ScheduleFlow />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;