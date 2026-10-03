import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/tokens.css';
import './styles/global.css';
import { initTelegram } from './lib/telegram';
import { Today } from './screens/Today';

initTelegram();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div className="app">
      <Today />
    </div>
  </StrictMode>,
);
