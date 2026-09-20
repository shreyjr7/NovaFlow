import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import { setupApiInterceptor } from './services/apiInterceptor';

// Initialize transparent backend routing and tunnel bypass headers
setupApiInterceptor();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

