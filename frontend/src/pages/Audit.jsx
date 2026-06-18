import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Search, Clock, FileSearch, Shield, Server, Bot, AlertCircle } from 'lucide-react';
import api from '../api/client';

export default function Audit() {
  const location = useLocation();
  const [applicantId, setApplicantId] = useState(location.state?.applicantId || '');
  const [auditLog, setAuditLog] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    if (location.state?.applicantId) {
      // Create a synthetic event or just call the logic
      executeSearch(location.state.applicantId);
    }
  }, [location.state]);

  const executeSearch = async (id) => {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    setAuditLog(null);

    try {
      const response = await api.get(`/audit/${id.trim()}`);
      setAuditLog(response.data.audit_trail);
    } catch (err) {
      if (err.response && err.response.status === 404) {
        setAuditLog([]);
      } else {
        setError('Error fetching audit log. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    executeSearch(applicantId);
  };

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'RECEIVED_APPLICATION':
        return <FileSearch className="h-5 w-5 text-blue-500" />;
      case 'ML_MODELS_EXECUTED':
        return <Server className="h-5 w-5 text-purple-500" />;
      case 'AGENT_REASONING':
        return <Bot className="h-5 w-5 text-amber-500" />;
      case 'VERDICT_GENERATED':
        return <Shield className="h-5 w-5 text-green-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
        <p className="mt-1 text-sm text-gray-500">Search the immutable audit trail for any applicant.</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-4">
        <div className="flex-1 relative">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <Search className="h-5 w-5 text-gray-400" aria-hidden="true" />
          </div>
          <input
            type="text"
            className="block w-full rounded-md border-0 py-2.5 pl-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
            placeholder="Enter Applicant ID (UUID)"
            value={applicantId}
            onChange={(e) => setApplicantId(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !applicantId.trim()}
          className="rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50"
        >
          Search Logs
        </button>
      </form>

      {error && (
        <div className="rounded-md bg-red-50 p-4 border border-red-200">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3 text-sm text-red-700">{error}</div>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-12">
          <Clock className="h-8 w-8 text-blue-500 animate-spin" />
        </div>
      )}

      {searched && !loading && !error && auditLog?.length === 0 && (
        <div className="text-center py-16 bg-white rounded-lg border border-dashed border-gray-300">
          <FileSearch className="mx-auto h-12 w-12 text-gray-300" />
          <h3 className="mt-2 text-sm font-semibold text-gray-900">No logs found</h3>
          <p className="mt-1 text-sm text-gray-500">No audit trail exists for this applicant ID.</p>
        </div>
      )}

      {searched && !loading && !error && auditLog?.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flow-root">
            <ul role="list" className="-mb-8">
              {auditLog.map((event, eventIdx) => (
                <li key={eventIdx}>
                  <div className="relative pb-8">
                    {eventIdx !== auditLog.length - 1 ? (
                      <span className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true" />
                    ) : null}
                    <div className="relative flex space-x-3">
                      <div>
                        <span className="h-8 w-8 rounded-full bg-gray-50 flex items-center justify-center ring-8 ring-white border border-gray-200">
                          {getEventIcon(event.event_type)}
                        </span>
                      </div>
                      <div className="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
                        <div>
                          <p className="text-sm text-gray-900 font-medium">{event.event_type.replace(/_/g, ' ')}</p>
                          <div className="mt-1 text-sm text-gray-500 bg-gray-50 rounded-md p-3 border border-gray-100 font-mono text-xs overflow-x-auto">
                            <pre>{JSON.stringify(event.details, null, 2)}</pre>
                          </div>
                        </div>
                        <div className="whitespace-nowrap text-right text-xs text-gray-500">
                          {new Date(event.timestamp).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
