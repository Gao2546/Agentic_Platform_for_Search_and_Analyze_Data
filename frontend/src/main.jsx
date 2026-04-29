import { StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import './i18n';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Suspense fallback={<div className="h-screen w-screen flex items-center justify-center font-bold text-gray-500">Loading Languages...</div>}>
      <App />
    </Suspense>
  </StrictMode>,
)