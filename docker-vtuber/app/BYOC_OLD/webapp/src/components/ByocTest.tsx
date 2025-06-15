import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { useSettings } from '../hooks/useSettings';

const ByocTest: React.FC = () => {
  // Access base API URL from settings
  const {
    settings: { apiBaseUrl },
  } = useSettings();

  const [prompt, setPrompt] = useState<string>('Hello BYOC!');
  const [responseText, setResponseText] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const sendRequest = async () => {
    setIsLoading(true);
    setError(null);
    setResponseText('');

    try {
      // Hit the BYOC worker health endpoint routed via Caddy (/worker/*)
      const res = await fetch(`${apiBaseUrl}/worker/v1/byoc-test`, {
        method: 'GET',
      });

      if (!res.ok) {
        throw new Error(`Server responded with status ${res.status}`);
      }

      const data = await res.json();
      // Expecting { message: string }
      setResponseText(data.message ?? JSON.stringify(data));
    } catch (err: any) {
      console.error('BYOC test request failed:', err);
      setError(err.message || 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg shadow-md mt-6">
      <h2 className="text-lg font-semibold mb-2">BYOC Echo Test</h2>

      <div className="mb-4">
        <label htmlFor="byocPrompt" className="block text-sm font-medium text-gray-700 mb-1">
          Prompt
        </label>
        <input
          id="byocPrompt"
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          disabled={isLoading}
        />
      </div>

      <button
        onClick={sendRequest}
        disabled={!prompt.trim() || isLoading}
        className={`flex items-center px-4 py-2 rounded-md ${
          !prompt.trim() || isLoading ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 text-white'
        }`}
      >
        {isLoading ? (
          <>
            <Loader2 size={18} className="mr-2 animate-spin" />
            Sending...
          </>
        ) : (
          <>
            <Send size={18} className="mr-2" />
            Send
          </>
        )}
      </button>

      {/* Response */}
      {error && <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-md">{error}</div>}

      {responseText && !error && (
        <div className="mt-4 p-3 bg-green-100 text-green-700 rounded-md whitespace-pre-wrap break-words">
          {responseText}
        </div>
      )}
    </div>
  );
};

export default ByocTest; 