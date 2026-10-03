import { useEffect } from 'react';
import { HashRouter, Navigate, Route, Routes, useLocation } from 'react-router';
import { StoreProvider } from './lib/store';
import { TelegramButtonsProvider } from './lib/tgButtons';
import { Today } from './screens/Today';
import { Wizard } from './screens/Wizard';

/**
 * Маршруты — design/05-screens.md. HashRouter: Mini App открывается по одной ссылке
 * и раздаётся как статика, без настройки сервера под history API.
 */
export function App() {
  return (
    <StoreProvider>
      <HashRouter>
        <TelegramButtonsProvider>
          <ScrollToTop />
          <div className="app">
            <Routes>
              <Route path="/today" element={<Today />} />
              <Route path="/new/:step" element={<Wizard />} />
              <Route path="*" element={<Navigate to="/today" replace />} />
            </Routes>
          </div>
        </TelegramButtonsProvider>
      </HashRouter>
    </StoreProvider>
  );
}

/** Каждый новый экран открывается с начала. */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}
