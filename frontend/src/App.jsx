import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import PCView from './PCView';
import MobileView from './MobileView';

function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md text-center max-w-md w-full">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Chess Vision Tracker</h1>
        <p className="text-gray-600 mb-8">Select your device role to start the application.</p>
        
        <div className="flex flex-col space-y-4">
          <button 
            onClick={() => navigate('/pc')}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded transition duration-200"
          >
            I am a Computer (Host)
          </button>
          
          <button 
            onClick={() => navigate('/mobile')}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded transition duration-200"
          >
            I am a Phone (Camera)
          </button>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/pc" element={<PCView />} />
        <Route path="/mobile" element={<MobileView />} />
      </Routes>
    </Router>
  );
}

export default App;
