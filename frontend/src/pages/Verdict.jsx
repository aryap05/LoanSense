import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import api from '../api/client';

export default function Verdict() {
  const { applicantId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const fetchVerdict = async () => {
    try {
      setLoading(true);
      setError(null);
      setNotFound(false);
      
      const response = await api.get(`/applicants/${applicantId}`);
      setData(response.data);
    } catch (err) {
      if (err.response && err.response.status === 404) {
        setNotFound(true);
      } else if (err.request) {
        setError('Network error: Unable to connect to backend.');
      } else {
        setError(`Failed to fetch verdict: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVerdict();
  }, [applicantId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500 mb-4" />
        <p className="text-gray-500">Retrieving AI Verdict...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="max-w-3xl mx-auto mt-12 text-center">
        <XCircle className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Applicant Not Found</h2>
        <p className="text-gray-600 mb-6">We couldn't find an applicant with ID {applicantId}.</p>
        <Link to="/assess" className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700">
          Start New Assessment
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto mt-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-red-800 mb-2">Connection Error</h2>
          <p className="text-red-600 mb-6">{error}</p>
          <button 
            onClick={fetchVerdict}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700"
          >
            Retry Fetch
          </button>
        </div>
      </div>
    );
  }

  const { decision, confidence_score, reasons, rbi_flags, contradiction_detected, contradiction_score, name, pan_hash } = data;

  const getConfig = () => {
    switch (decision) {
      case 'APPROVE':
        return {
          color: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800',
          icon: <ShieldCheck className="h-10 w-10 text-green-600" />,
          title: 'Approved'
        };
      case 'FLAG_FOR_REVIEW':
        return {
          color: 'bg-amber-50',
          borderColor: 'border-amber-200',
          textColor: 'text-amber-800',
          icon: <ShieldAlert className="h-10 w-10 text-amber-600" />,
          title: 'Flagged for Review'
        };
      case 'REJECT':
      default:
        return {
          color: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          icon: <XCircle className="h-10 w-10 text-red-600" />,
          title: 'Rejected'
        };
    }
  };

  const conf = getConfig();

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      
      {/* Banner */}
      <div className={`rounded-xl border ${conf.borderColor} ${conf.color} p-6 sm:p-8 flex items-start sm:items-center flex-col sm:flex-row shadow-sm`}>
        <div className="mr-6 mb-4 sm:mb-0">
          {conf.icon}
        </div>
        <div className="flex-1">
          <h1 className={`text-3xl font-bold ${conf.textColor} mb-1`}>{conf.title}</h1>
          <p className={`text-sm ${conf.textColor} opacity-80 font-medium`}>
            Applicant: {name} | PAN Hash: {pan_hash?.substring(0, 8)}...
          </p>
        </div>
        <div className="mt-4 sm:mt-0 text-center bg-white/50 rounded-lg px-4 py-3 border border-white/20">
          <div className={`text-2xl font-bold ${conf.textColor}`}>{(confidence_score * 100).toFixed(0)}%</div>
          <div className="text-xs uppercase font-semibold text-gray-500">Confidence</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Basis of Decision */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4 border-b pb-2">Primary Reasons</h2>
          {reasons && reasons.length > 0 ? (
            <ul className="space-y-3">
              {reasons.map((reason, idx) => (
                <li key={idx} className="flex items-start">
                  <div className="flex-shrink-0 h-5 w-5 rounded-full bg-blue-100 flex items-center justify-center mt-0.5">
                    <span className="text-blue-600 text-xs font-bold">{idx + 1}</span>
                  </div>
                  <p className="ml-3 text-sm text-gray-700">{reason}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500 italic">No specific reasons provided.</p>
          )}
        </div>

        {/* RBI Compliance & ML Drift */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
          
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-4 border-b pb-2">RBI Compliance Flags</h2>
            {rbi_flags && rbi_flags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {rbi_flags.map((flag, idx) => (
                  <span key={idx} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200">
                    {flag}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-green-600 font-medium flex items-center">
                <CheckCircle2 className="h-4 w-4 mr-1.5" /> No RBI compliance issues detected.
              </p>
            )}
          </div>

          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-4 border-b pb-2">Fraud & Contradiction</h2>
            {contradiction_detected ? (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-800 font-semibold mb-1 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1.5" />
                  High Risk of Contradiction
                </p>
                <p className="text-xs text-red-600">Model contradiction score: {(contradiction_score * 100).toFixed(1)}%</p>
              </div>
            ) : (
              <p className="text-sm text-gray-600">
                Contradiction Score: <span className="font-semibold">{(contradiction_score * 100).toFixed(1)}%</span> (Normal)
              </p>
            )}
          </div>

        </div>
      </div>
      
      <div className="flex justify-end pt-4">
        <Link to="/audit" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
          View Full Audit Log &rarr;
        </Link>
      </div>

    </div>
  );
}
