import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { useSettings } from '../hooks/useSettings';
import { getProcessToken, processText } from '../services/textEcho';

const TextEcho: React.FC = () => {
  const { wallet } = useWallet();
  const { settings } = useSettings();
  const [text, setText] = useState('Hello world');
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    if (!wallet.isConnected || !wallet.address || !wallet.signer) {
      setError('Please connect your wallet first.');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      // 1. Token
      const token = await getProcessToken(
        settings.apiBaseUrl,
        wallet.address,
        async (msg: Uint8Array) => wallet.signer!.signMessage(msg),
      );

      // 2. Process
      const result = await processText(
        settings.apiBaseUrl,
        token,
        text,
        wallet.address,
        async (msg: Uint8Array) => wallet.signer!.signMessage(msg),
      );

      setResponse(JSON.stringify(result));
    } catch (err: any) {
      console.error('Text echo failed', err);
      setError(err.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg shadow-md">
      <h2 className="text-lg font-semibold mb-2">Text Echo</h2>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 mb-3"
        disabled={loading}
      />

      <button
        onClick={handleSend}
        disabled={loading || !text.trim()}
        className={`flex items-center px-4 py-2 rounded-md ${
          loading || !text.trim()
            ? 'bg-gray-300 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 text-white'
        }`}
      >
        {loading ? (
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

      {error && <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-md">{error}</div>}
      {response && !error && (
        <div className="mt-4 p-3 bg-green-100 text-green-700 rounded-md whitespace-pre-wrap break-words">
          {response}
        </div>
      )}
    </div>
  );
};

export default TextEcho; 