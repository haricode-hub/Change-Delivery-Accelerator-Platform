import React, { useState } from 'react';
import './App.css';

function App() {
  const [requirement, setRequirement] = useState('');
  const [documentType, setDocumentType] = useState('functionDoc');
  const [testCaseType, setTestCaseType] = useState('stdcif');
  const [testCaseCount, setTestCaseCount] = useState(10);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [codeResult, setCodeResult] = useState(null);
  const [copySuccess, setCopySuccess] = useState(false);

  // Base URL for API - change this to match your backend
  const API_BASE_URL = 'http://127.0.0.1:8080';

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if ((documentType !== 'dataGeneration') && !requirement.trim()) {
      setError('Please enter your requirement');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess(false);
    setCopySuccess(false);
    
    if (documentType !== 'codeGen') {
      setCodeResult(null);
    }

    try {
      let endpoint;
      let isFileDownload = true;
      let requestBody = { text: requirement };
      
      // Fixed endpoint mapping
      if (documentType === 'functionDoc') {
        endpoint = `${API_BASE_URL}/generate-doc`;
      } else if (documentType === 'testCases') {
        endpoint = `${API_BASE_URL}/generate-test-cases`; // Fixed endpoint name
      } else if (documentType === 'dataGeneration') {
        if (testCaseType === 'stdcif') {
          endpoint = `${API_BASE_URL}/generate-stdcif`;
        } else {
          endpoint = `${API_BASE_URL}/generate-stdcusac`;
        }
        requestBody = { count: testCaseCount };
      } else if (documentType === 'codeGen') {
        endpoint = `${API_BASE_URL}/generate-code`;
        isFileDownload = false;
      }
      
      console.log(`Sending request to: ${endpoint}`);
      console.log('Request body:', requestBody);
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          throw new Error(errorData.error || `Failed to generate ${documentType === 'codeGen' ? 'code' : 'document'}`);
        } else {
          const textError = await response.text();
          throw new Error(`Server error: ${response.status} - ${textError.substring(0, 100)}...`);
        }
      }

      if (isFileDownload) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        
        let filename;
        if (documentType === 'functionDoc') {
          filename = 'function_specification.docx';
        } else if (documentType === 'testCases') {
          filename = 'test_cases.xlsx';
        } else if (documentType === 'dataGeneration') {
          filename = testCaseType === 'stdcif' ? 'STDCIF_Cases.xlsx' : 'STDCUSAC_Cases.xlsx';
        }
        
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
        
        // Clean up the URL object
        window.URL.revokeObjectURL(url);
      } else {
        const data = await response.json();
        console.log("Code generation response:", data);
        if (data.success && data.result) {
          setCodeResult(data.result);
        } else {
          throw new Error('Invalid response format from server');
        }
      }
      
      setSuccess(true);
    } catch (err) {
      console.error('Error:', err);
      setError(`An error occurred: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const getButtonText = () => {
    if (documentType === 'functionDoc') return 'Generate Document';
    if (documentType === 'testCases') return 'Generate Test Cases';
    if (documentType === 'dataGeneration') return 'Generate Data';
    return 'Generate Code';
  };

  const getButtonIcon = () => {
    if (documentType === 'functionDoc') return '📄';
    if (documentType === 'testCases' || documentType === 'dataGeneration') return '📊';
    return '💻';
  };

  const handleDocumentTypeChange = (newType) => {
    setDocumentType(newType);
    setError('');
    setSuccess(false);
    setCopySuccess(false);
    
    if (documentType === 'codeGen') {
      setCodeResult(null);
    }
  };

  const handleCopyCode = async () => {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(codeResult);
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
        return;
      }
      
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = codeResult;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        const successful = document.execCommand('copy');
        if (successful) {
          setCopySuccess(true);
          setTimeout(() => setCopySuccess(false), 2000);
        } else {
          throw new Error('Copy command failed');
        }
      } finally {
        document.body.removeChild(textArea);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
      setError('Failed to copy code to clipboard. Please copy manually from the text area.');
      
      // Alternative: Select the text for manual copy
      const codeBlock = document.querySelector('.code-block');
      if (codeBlock) {
        const range = document.createRange();
        range.selectNodeContents(codeBlock);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }
  };

  return (
    <div className="app-container">
      <div className="app-card">
        <header className="app-header">
          <div className="logo-container">
            <img src="/jmr logo.jpg" alt="Company Logo" className="image-logo" />
          </div>
          <h1>Change Delivery Accelerator Platform</h1>
          <p className="subtitle">Generate detailed documents and code from your requirements</p>
        </header>
        
        <main className="app-main">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>
                <span className="label-text">Select Generation Type:</span>
              </label>
              <div className="radio-group">
                <label className="radio-option">
                  <input
                    type="radio"
                    value="functionDoc"
                    checked={documentType === 'functionDoc'}
                    onChange={() => handleDocumentTypeChange('functionDoc')}
                  />
                  <span className="radio-label">Functional Specification Document</span>
                </label>
                <label className="radio-option">
                  <input
                    type="radio"
                    value="testCases"
                    checked={documentType === 'testCases'}
                    onChange={() => handleDocumentTypeChange('testCases')}
                  />
                  <span className="radio-label">Test Cases (Excel)</span>
                </label>
                <label className="radio-option">
                  <input
                    type="radio"
                    value="dataGeneration"
                    checked={documentType === 'dataGeneration'}
                    onChange={() => handleDocumentTypeChange('dataGeneration')}
                  />
                  <span className="radio-label">Test Data Generation (Excel)</span>
                </label>
                <label className="radio-option">
                  <input
                    type="radio"
                    value="codeGen"
                    checked={documentType === 'codeGen'}
                    onChange={() => handleDocumentTypeChange('codeGen')}
                  />
                  <span className="radio-label">PL/SQL Code Generation</span>
                </label>
              </div>
            </div>

            {documentType === 'dataGeneration' && (
              <div className="form-group">
                <label>
                  <span className="label-text">Select Type of Test Data:</span>
                </label>
                <div className="radio-group">
                  <label className="radio-option">
                    <input
                      type="radio"
                      value="stdcif"
                      checked={testCaseType === 'stdcif'}
                      onChange={() => setTestCaseType('stdcif')}
                    />
                    <span className="radio-label">STDCIF (Customer Information)</span>
                  </label>
                  <label className="radio-option">
                    <input
                      type="radio"
                      value="stdcusac"
                      checked={testCaseType === 'stdcusac'}
                      onChange={() => setTestCaseType('stdcusac')}
                    />
                    <span className="radio-label">STDCUSAC (Customer Account)</span>
                  </label>
                </div>
              </div>
            )}

            {documentType === 'dataGeneration' && (
              <div className="form-group">
                <label htmlFor="testCaseCount">
                  <span className="label-text">Number of Records:</span>
                </label>
                <input
                  type="number"
                  id="testCaseCount"
                  value={testCaseCount}
                  onChange={(e) => setTestCaseCount(Math.max(1, parseInt(e.target.value) || 1))}
                  className="count-input"
                  disabled={isLoading}
                  min="1"
                  max="1000"
                />
              </div>
            )}

            {documentType !== 'dataGeneration' && (
              <div className="form-group">
                <label htmlFor="requirement">
                  <span className="label-text">Enter Your Requirement:</span>
                  <span className="label-hint">
                    {documentType === 'codeGen' 
                      ? 'Describe the logging code requirements in detail' 
                      : documentType === 'testCases'
                        ? 'Describe the test case requirements in detail'
                        : 'Please describe the requirement in detail'}
                  </span>
                </label>
                <textarea
                  id="requirement"
                  value={requirement}
                  onChange={(e) => setRequirement(e.target.value)}
                  rows="10"
                  placeholder={documentType === 'codeGen' 
                    ? "Describe your PL/SQL logging requirements in detail..."
                    : documentType === 'testCases'
                      ? "Describe your test case requirements in detail..."
                      : "Describe your business requirement in detail..."}
                  disabled={isLoading}
                />
              </div>
            )}
            
            {error && <div className="message error-message">{error}</div>}
            {success && !codeResult && (
              <div className="message success-message">
                <span className="success-icon">✓</span> 
                {documentType === 'functionDoc' 
                  ? 'Document generated successfully! Check your downloads folder.'
                  : documentType === 'testCases'
                    ? 'Test cases generated successfully! Check your downloads folder.'
                    : documentType === 'dataGeneration'
                      ? `${testCaseType.toUpperCase()} data generated successfully! Check your downloads folder.`
                      : 'Code generated successfully!'}
              </div>
            )}
            
            <div className="button-container">
              <button type="submit" disabled={isLoading} className="submit-button">
                {isLoading ? (
                  <>
                    <span className="spinner"></span>
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <span className="button-icon">{getButtonIcon()}</span>
                    <span>{getButtonText()}</span>
                  </>
                )}
              </button>
            </div>
          </form>
          
          {documentType === 'codeGen' && (
            <div className="code-section">
              {isLoading && (
                <div className="code-loading">
                  <p>Generating your PL/SQL code...</p>
                  <div className="code-spinner"></div>
                </div>
              )}
              
              {codeResult && (
                <div className="code-result-container">
                  <h3>Generated PL/SQL Code:</h3>
                  <div className="code-actions">
                    <button 
                      className="copy-button"
                      onClick={handleCopyCode}
                      disabled={!codeResult}
                    >
                      {copySuccess ? 'Copied!' : 'Copy Code'}
                    </button>
                  </div>
                  <pre className="code-block">{codeResult}</pre>
                </div>
              )}
              
              {success && codeResult && (
                <div className="message success-message code-success">
                  <span className="success-icon">✓</span> 
                  Code generated successfully!
                </div>
              )}
            </div>
          )}
        </main>
        
        <footer className="app-footer">
          <p>© 2025–2026 JMR Infotech. All rights reserved. Powered by AI Team</p>
        </footer>
      </div>
    </div>
  );
}

export default App;