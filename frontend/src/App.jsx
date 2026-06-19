import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Assess from './pages/Assess';
import Assessments from './pages/Assessments';
import Verdict from './pages/Verdict';
import Audit from './pages/Audit';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="assess" element={<Assess />} />
          <Route path="assessments" element={<Assessments />} />
          <Route path="verdict/:applicantId" element={<Verdict />} />
          <Route path="audit" element={<Audit />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
