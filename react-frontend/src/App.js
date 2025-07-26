import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const App = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [scenario, setScenario] = useState('');
  const [dashboardData, setDashboardData] = useState(null);

  const handleLogin = async () => {
    try {
      const response = await axios.post(`${process.env.REACT_APP_API_BASE_URL}/api/v1/auth/login`, {
        username,
        password,
      });
      alert('Login successful!');
    } catch (error) {
      alert('Login failed!');
    }
  };

  const handleScenarioSelection = async (selectedScenario) => {
    setScenario(selectedScenario);
    try {
      const response = await axios.post(`${process.env.REACT_APP_API_BASE_URL}/api/v1/scenario`, {
        scenario: selectedScenario,
      });
      alert('Scenario selected successfully!');
    } catch (error) {
      alert('Scenario selection failed!');
    }
  };

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/api/v1/financial-dashboard/demo_user`);
      setDashboardData(response.data);
    } catch (error) {
      alert('Failed to fetch dashboard data!');
    }
  };

  return (
    <div className="App">
      <h1>AvestoAI React Frontend</h1>

      {/* Login Section */}
      <div>
        <h2>Login</h2>
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button onClick={handleLogin}>Login</button>
      </div>

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
        <button onClick={fetchDashboardData}>Fetch Dashboard Data</button>
        {dashboardData && (
          <pre>{JSON.stringify(dashboardData, null, 2)}</pre>
        )}
      </div>
    </div>
  );
};

export default App;
