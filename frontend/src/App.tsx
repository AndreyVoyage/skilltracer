import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Home } from './pages/Home';
import { DayDetail } from './pages/DayDetail';
import { PublicReport } from './pages/PublicReport';
import { useTelegram } from './hooks/useTelegram';

function App() {
  useTelegram();
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/day/:date" element={<DayDetail />} />
        <Route path="/report/:token" element={<PublicReport />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
