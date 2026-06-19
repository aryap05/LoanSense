import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Users, ShieldAlert, FileText, Server, AlertTriangle } from 'lucide-react';
import api from '../api/client';

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recentAssessments, setRecentAssessments] = useState([]);
  const [loadingRecent, setLoadingRecent] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [healthRes, recentRes] = await Promise.all([
          api.get('/health'),
          api.get('/verdicts/recent')
        ]);
        setHealth(healthRes.data);
        setRecentAssessments(recentRes.data);
      } catch (err) {
        setError('Unable to connect to LoanSense backend.');
      } finally {
        setLoading(false);
        setLoadingRecent(false);
      }
    };
    fetchData();
  }, []);

  const stats = [
    { name: 'Total Processed', value: '1,234', icon: Users, color: 'text-blue-500', bg: 'bg-blue-100' },
    { name: 'Avg Turnaround', value: '1.2s', icon: Activity, color: 'text-green-500', bg: 'bg-green-100' },
    { name: 'Auto-Approved', value: '68%', icon: FileText, color: 'text-purple-500', bg: 'bg-purple-100' },
    { name: 'Flagged / Rejected', value: '32%', icon: ShieldAlert, color: 'text-amber-500', bg: 'bg-amber-100' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">Overview of the Agentic Underwriting System.</p>
        </div>
        <Link 
          to="/assess"
          className="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          New Assessment
        </Link>
      </div>

      {/* Drift Alert Banner */}
      {!loading && !error && health?.models?.distribution_drift_detected && (
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <AlertTriangle className="h-5 w-5 text-amber-400" aria-hidden="true" />
            </div>
            <div className="ml-3">
              <p className="text-sm text-amber-700 font-medium">
                Data Drift Detected
              </p>
              <p className="text-sm text-amber-600 mt-1">
                The ML models have detected a shift in incoming application distributions compared to the training baseline. Consider reviewing recent rejections.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((item) => (
          <div key={item.name} className="relative overflow-hidden rounded-lg bg-white px-4 pb-12 pt-5 shadow sm:px-6 sm:pt-6 border border-gray-100">
            <dt>
              <div className={`absolute rounded-md ${item.bg} p-3`}>
                <item.icon className={`h-6 w-6 ${item.color}`} aria-hidden="true" />
              </div>
              <p className="ml-16 truncate text-sm font-medium text-gray-500">{item.name}</p>
            </dt>
            <dd className="ml-16 flex items-baseline pb-6 sm:pb-7">
              <p className="text-2xl font-semibold text-gray-900">{item.value}</p>
            </dd>
          </div>
        ))}
      </div>

      {/* Recent Assessments Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h3 className="text-lg font-medium leading-6 text-gray-900 flex items-center">
            <FileText className="h-5 w-5 mr-2 text-gray-500" />
            Recent Assessments
          </h3>
          <Link to="/assess" className="text-sm font-medium text-blue-600 hover:text-blue-500">
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Applicant</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loadingRecent ? (
                <tr>
                  <td colSpan="4" className="px-6 py-4 text-center text-sm text-gray-500">Loading...</td>
                </tr>
              ) : recentAssessments.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-6 py-4 text-center text-sm text-gray-500">No recent assessments found.</td>
                </tr>
              ) : (
                recentAssessments.map((assessment) => (
                  <tr key={assessment.applicant_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="text-sm font-medium text-gray-900">{assessment.name}</div>
                      </div>
                      <div className="text-xs text-gray-500 font-mono mt-1">ID: {assessment.applicant_id.substring(0, 8)}...</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        assessment.decision === 'APPROVE' ? 'bg-green-100 text-green-800' :
                        assessment.decision === 'FLAG_FOR_REVIEW' ? 'bg-amber-100 text-amber-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {assessment.decision.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(assessment.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link to={`/verdict/${assessment.applicant_id}`} className="text-blue-600 hover:text-blue-900 mr-4">
                        Verdict
                      </Link>
                      <Link to="/audit" state={{ applicantId: assessment.applicant_id }} className="text-gray-600 hover:text-gray-900">
                        Audit
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* System Status Panel */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-5 border-b border-gray-200">
          <h3 className="text-lg font-medium leading-6 text-gray-900 flex items-center">
            <Server className="h-5 w-5 mr-2 text-gray-400" />
            Backend Status
          </h3>
        </div>
        <div className="px-6 py-5">
          {loading ? (
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-4 py-1">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          ) : error ? (
            <div className="text-sm text-red-600 flex items-center">
              <div className="h-3 w-3 bg-red-500 rounded-full mr-2"></div>
              {error}
            </div>
          ) : (
            <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">API Status</dt>
                <dd className="mt-1 text-sm text-gray-900 flex items-center">
                  <div className={`h-2.5 w-2.5 rounded-full mr-2 ${health.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  {health.status === 'healthy' ? 'Healthy' : 'Degraded'}
                </dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Models Loaded</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {health.models?.loaded_models || 0}
                </dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">LLM Provider</dt>
                <dd className="mt-1 text-sm text-gray-900">Groq (Llama-3.3-70b)</dd>
              </div>
            </dl>
          )}
        </div>
      </div>
    </div>
  );
}
