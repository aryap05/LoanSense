import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import api from '../api/client';

export default function Assess() {
  const navigate = useNavigate();
  const panRef = useRef(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  const [formData, setFormData] = useState({
    name: '',
    income: '',
    loan_amount: '',
    loan_term_months: '',
    cibil_score: '',
    existing_emi: '0',
    employment_type: 'salaried_private',
    employer_name: '',
    purpose: 'personal',
    account_age_months: '',
    enquiry_count_30d: '',
    upi_velocity_percentile: '',
    transaction_velocity_30d: '',
    applicant_notes: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear field-specific error when user types
    if (fieldErrors[name]) {
      setFieldErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const hashPAN = async (pan) => {
    const msgBuffer = new TextEncoder().encode(pan);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setGlobalError(null);
    setFieldErrors({});

    try {
      const rawPan = panRef.current?.value;
      if (!rawPan) {
        setFieldErrors(prev => ({ ...prev, pan_number: 'PAN is required' }));
        setIsSubmitting(false);
        return;
      }

      // Hash PAN and clear the DOM node immediately
      const hashed_pan = await hashPAN(rawPan);
      panRef.current.value = '';

      // Prepare payload with explicit type conversions
      const payload = {
        name: formData.name,
        pan_number: hashed_pan,
        income: parseFloat(formData.income),
        loan_amount: parseFloat(formData.loan_amount),
        loan_term_months: parseInt(formData.loan_term_months, 10),
        cibil_score: parseInt(formData.cibil_score, 10),
        existing_emi: parseFloat(formData.existing_emi) || 0.0,
        employment_type: formData.employment_type,
        employer_name: formData.employer_name || null,
        purpose: formData.purpose,
        account_age_months: parseInt(formData.account_age_months, 10),
        enquiry_count_30d: parseInt(formData.enquiry_count_30d, 10),
        upi_velocity_percentile: parseFloat(formData.upi_velocity_percentile),
        transaction_velocity_30d: parseFloat(formData.transaction_velocity_30d),
        applicant_notes: formData.applicant_notes || null
      };

      const response = await api.post('/assess', payload);
      
      // Navigate to verdict page
      navigate(`/verdict/${response.data.applicant_id}`);

    } catch (err) {
      if (err.response) {
        if (err.response.status === 422) {
          // Unprocessable Entity - Validation Errors
          const errors = err.response.data.detail;
          const newFieldErrors = {};
          if (Array.isArray(errors)) {
            errors.forEach(error => {
              const field = error.loc[error.loc.length - 1]; // Last item in loc array is usually the field name
              newFieldErrors[field] = error.msg;
            });
            setFieldErrors(newFieldErrors);
            setGlobalError('Please correct the highlighted errors below.');
          } else {
            setGlobalError('Validation failed. Please check your inputs.');
          }
        } else {
          setGlobalError(`Server Error (${err.response.status}): ${err.response.data.detail || 'Something went wrong.'}`);
        }
      } else if (err.request) {
        setGlobalError('Network Error: Unable to reach the server. Please ensure the backend is running.');
      } else {
        setGlobalError(`Error: ${err.message}`);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">New Assessment</h1>
        <p className="mt-2 text-sm text-gray-600">
          Enter applicant details for AI-driven underwriting. The PAN number is securely hashed before transmission.
        </p>
      </div>

      {globalError && (
        <div className="mb-6 p-4 rounded-md bg-red-50 border border-red-200 flex items-start">
          <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
          <div className="text-sm text-red-800">{globalError}</div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white shadow-sm ring-1 ring-gray-900/5 rounded-xl p-8">
        <div className="space-y-8">
          
          {/* Section: Personal Info */}
          <div>
            <h2 className="text-base font-semibold leading-7 text-gray-900 border-b pb-2 mb-4">Personal Information</h2>
            <div className="grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700">Applicant Name</label>
                <div className="mt-2">
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.name ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.name && <p className="mt-1 text-xs text-red-600">{fieldErrors.name}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">PAN Number</label>
                <div className="mt-2">
                  <input
                    type="password"
                    ref={panRef}
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.pan_number ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                    placeholder="Enter raw PAN (will be hashed)"
                  />
                  {fieldErrors.pan_number && <p className="mt-1 text-xs text-red-600">{fieldErrors.pan_number}</p>}
                </div>
              </div>
            </div>
          </div>

          {/* Section: Loan Details */}
          <div>
            <h2 className="text-base font-semibold leading-7 text-gray-900 border-b pb-2 mb-4">Loan Details</h2>
            <div className="grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">Loan Amount (₹)</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="loan_amount"
                    value={formData.loan_amount}
                    onChange={handleChange}
                    min="1"
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.loan_amount ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.loan_amount && <p className="mt-1 text-xs text-red-600">{fieldErrors.loan_amount}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Loan Term (Months)</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="loan_term_months"
                    value={formData.loan_term_months}
                    onChange={handleChange}
                    min="1"
                    max="360"
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.loan_term_months ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.loan_term_months && <p className="mt-1 text-xs text-red-600">{fieldErrors.loan_term_months}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Purpose</label>
                <div className="mt-2">
                  <select
                    name="purpose"
                    value={formData.purpose}
                    onChange={handleChange}
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.purpose ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  >
                    <option value="personal">Personal</option>
                    <option value="home_renovation">Home Renovation</option>
                    <option value="education">Education</option>
                    <option value="business_capital">Business Capital</option>
                    <option value="medical">Medical</option>
                    <option value="vehicle">Vehicle</option>
                  </select>
                  {fieldErrors.purpose && <p className="mt-1 text-xs text-red-600">{fieldErrors.purpose}</p>}
                </div>
              </div>
            </div>
          </div>

          {/* Section: Financials & Bureau */}
          <div>
            <h2 className="text-base font-semibold leading-7 text-gray-900 border-b pb-2 mb-4">Financials & Bureau</h2>
            <div className="grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">Monthly Income (₹)</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="income"
                    value={formData.income}
                    onChange={handleChange}
                    min="0"
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.income ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.income && <p className="mt-1 text-xs text-red-600">{fieldErrors.income}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Existing EMI (₹)</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="existing_emi"
                    value={formData.existing_emi}
                    onChange={handleChange}
                    min="0"
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.existing_emi ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.existing_emi && <p className="mt-1 text-xs text-red-600">{fieldErrors.existing_emi}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">CIBIL Score</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="cibil_score"
                    value={formData.cibil_score}
                    onChange={handleChange}
                    min="0"
                    max="900"
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.cibil_score ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  <p className="mt-1 text-xs text-gray-500">0 for No File</p>
                  {fieldErrors.cibil_score && <p className="mt-1 text-xs text-red-600">{fieldErrors.cibil_score}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Employment Type</label>
                <div className="mt-2">
                  <select
                    name="employment_type"
                    value={formData.employment_type}
                    onChange={handleChange}
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.employment_type ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  >
                    <option value="salaried_private">Salaried (Private)</option>
                    <option value="salaried_govt">Salaried (Govt)</option>
                    <option value="self_employed">Self Employed</option>
                    <option value="gig_worker">Gig Worker</option>
                  </select>
                  {fieldErrors.employment_type && <p className="mt-1 text-xs text-red-600">{fieldErrors.employment_type}</p>}
                </div>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700">Employer Name</label>
                <div className="mt-2">
                  <input
                    type="text"
                    name="employer_name"
                    value={formData.employer_name}
                    onChange={handleChange}
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.employer_name ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.employer_name && <p className="mt-1 text-xs text-red-600">{fieldErrors.employer_name}</p>}
                </div>
              </div>
            </div>
          </div>

          {/* Section: Advanced Risk Features */}
          <div>
            <h2 className="text-base font-semibold leading-7 text-gray-900 border-b pb-2 mb-4">Digital Footprint & Risk Features</h2>
            <div className="grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Account Age (Months)</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="account_age_months"
                    value={formData.account_age_months}
                    onChange={handleChange}
                    min="0"
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.account_age_months ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.account_age_months && <p className="mt-1 text-xs text-red-600">{fieldErrors.account_age_months}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Bureau Enquiries (30d)</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="enquiry_count_30d"
                    value={formData.enquiry_count_30d}
                    onChange={handleChange}
                    min="0"
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.enquiry_count_30d ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.enquiry_count_30d && <p className="mt-1 text-xs text-red-600">{fieldErrors.enquiry_count_30d}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">UPI Velocity %tile</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="upi_velocity_percentile"
                    value={formData.upi_velocity_percentile}
                    onChange={handleChange}
                    min="0"
                    max="100"
                    step="0.1"
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.upi_velocity_percentile ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.upi_velocity_percentile && <p className="mt-1 text-xs text-red-600">{fieldErrors.upi_velocity_percentile}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Txn Velocity (30d)</label>
                <div className="mt-2">
                  <input
                    type="number"
                    name="transaction_velocity_30d"
                    value={formData.transaction_velocity_30d}
                    onChange={handleChange}
                    min="0"
                    step="0.1"
                    required
                    className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.transaction_velocity_30d ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                  />
                  {fieldErrors.transaction_velocity_30d && <p className="mt-1 text-xs text-red-600">{fieldErrors.transaction_velocity_30d}</p>}
                </div>
              </div>
            </div>
          </div>

          {/* Section: Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Applicant Notes / Interview Context</label>
            <div className="mt-2">
              <textarea
                name="applicant_notes"
                rows={3}
                value={formData.applicant_notes}
                onChange={handleChange}
                className={`block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ${fieldErrors.applicant_notes ? 'ring-red-500 focus:ring-red-500' : 'ring-gray-300 focus:ring-blue-600'} focus:ring-2 sm:text-sm`}
                placeholder="Optional context for the AI Underwriter..."
              />
              {fieldErrors.applicant_notes && <p className="mt-1 text-xs text-red-600">{fieldErrors.applicant_notes}</p>}
            </div>
          </div>
          
        </div>

        <div className="mt-8 flex items-center justify-end gap-x-4 border-t pt-6">
          <button
            type="button"
            className="text-sm font-semibold leading-6 text-gray-900"
            onClick={() => navigate('/')}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center justify-center rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" />
                Processing...
              </>
            ) : (
              <>
                <CheckCircle2 className="-ml-1 mr-2 h-4 w-4" />
                Submit Assessment
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
