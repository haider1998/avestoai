import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [count, setCount] = useState(0);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [scenario, setScenario] = useState('');
  const [dashboardData, setDashboardData] = useState(null);
  const [token, setToken] = useState(null);

  // Configure axios defaults
  axios.interceptors.request.use((config) => {
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  const handleLogin = async () => {
    try {
      console.log('Attempting login with:', { email, password });
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/login`, {
        email,
        password
      });
      console.log('Login successful:', response.data);
      // Store the token
      setToken(response.data.access_token);
      alert('Login successful!');
      // Fetch dashboard data after successful login
      await fetchDashboardData();
    } catch (error) {
      console.error('Login failed:', error);
      if (error.response) {
        // The request was made and the server responded with a status code
        console.log('Error response:', error.response.data);
        alert(`Login failed: ${error.response.data.detail || 'Unknown error'}`);
      } else if (error.request) {
        // The request was made but no response was received
        console.log('Error request:', error.request);
        alert('No response from server. Please try again.');
      } else {
        // Something happened in setting up the request
        console.log('Error message:', error.message);
        alert(`Error: ${error.message}`);
      }
    }
  };

  const handleScenarioSelection = async (selectedScenario) => {
    setScenario(selectedScenario);
    try {
      console.log('Selecting scenario:', selectedScenario);
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/v1/scenario`, {
        scenario: selectedScenario,
      });
      console.log('Scenario selected successfully:', response.data);
      alert('Scenario selected successfully!');
    } catch (error) {
      console.error('Scenario selection failed:', error);
      alert('Scenario selection failed!');
    }
  };

  const fetchDashboardData = async () => {
    try {
      console.log('Fetching dashboard data...');
      const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/v1/financial-dashboard/demo_user`);
      console.log('Dashboard data fetched successfully:', response.data);
      setDashboardData(response.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      alert('Failed to fetch dashboard data!');
    }
  };

  useEffect(() => {
    // Only fetch dashboard data if token exists
    if (token) {
      fetchDashboardData();
    }
  }, [token]);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Welcome to AvestoAI React Frontend</h1>

        {/* Login Section */}
        <div>
          <h2>Login</h2>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button onClick={handleLogin}>Login</button>
        </div>

        {/* Show remaining sections only if logged in */}
        {token && (
          <>
            {/* Scenario Selection Section */}
            <div>
              <h2>Select Scenario</h2>
              <button onClick={() => handleScenarioSelection('balanced')}>Balanced Portfolio</button>
              <button onClick={() => handleScenarioSelection('high_growth')}>High Growth</button>
              <button onClick={() => handleScenarioSelection('sip_investor')}>SIP Investor</button>
              <button onClick={() => handleScenarioSelection('fixed_income')}>Conservative</button>
              <button onClick={() => handleScenarioSelection('debt_heavy')}>Debt Heavy</button>
              <button onClick={() => handleScenarioSelection('starter')}>Starter</button>
            </div>

            {/* Dashboard Section */}
            <div>
              <h2>Dashboard</h2>
              {dashboardData ? (
                <pre>{JSON.stringify(dashboardData, null, 2)}</pre>
              ) : (
                <p>Loading dashboard data...</p>
              )}
            </div>
          </>
        )}

        <p>Edit <code>src/App.jsx</code> and save to test HMR</p>
        <p>
          Click on the Vite and React logos to learn more
        </p>
      </header>
    </div>
  );
}

export default App;
