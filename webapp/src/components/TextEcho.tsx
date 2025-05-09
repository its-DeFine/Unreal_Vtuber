import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { useSettings } from '../hooks/useSettings';
import { getProcessToken, processText, NeuroSyncVtuberRequestData } from '../services/textEcho';
import { v4 as uuidv4 } from 'uuid';

const TextEcho: React.FC = () => {
  const { wallet } = useWallet();
  const { settings } = useSettings();
  
  const [prompt, setPrompt] = useState('Hello world');
  const [character, setCharacter] = useState('DefaultCharacter');
  const [knowledgeSourceUrl, setKnowledgeSourceUrl] = useState('http://example.com/kb');
  const [modelTimeSeconds, setModelTimeSeconds] = useState(60);

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
      const token = await getProcessToken(
        settings.apiBaseUrl,
        wallet.address,
        async (msg: Uint8Array) => wallet.signer!.signMessage(msg),
      );

      const requestData: NeuroSyncVtuberRequestData = {
        job_id: uuidv4(),
        character: character,
        prompt: prompt,
        knowledge_source_url: knowledgeSourceUrl,
        model_time_seconds: Number(modelTimeSeconds) || undefined,
      };

      const result = await processText(
        settings.apiBaseUrl,
        token,
        requestData,
        wallet.address,
        async (msg: Uint8Array) => wallet.signer!.signMessage(msg),
      );

      setResponse(JSON.stringify(result, null, 2));
    } catch (err: any) {
      console.error('Text echo failed', err);
      setError(err.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg shadow-md">
      <h2 className="text-lg font-semibold mb-4">VTuber Request Echo</h2>

      <div className="space-y-4 mb-4">
        <div>
          <label htmlFor="character" className="block text-sm font-medium text-gray-700 mb-1">
            Character
          </label>
          <input
            id="character"
            type="text"
            value={character}
            onChange={(e) => setCharacter(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            disabled={loading}
          />
        </div>

        <div>
          <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-1">
            Prompt
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            disabled={loading}
          />
        </div>
        
        <div>
          <label htmlFor="knowledgeSourceUrl" className="block text-sm font-medium text-gray-700 mb-1">
            Knowledge Source URL (Optional)
          </label>
          <input
            id="knowledgeSourceUrl"
            type="text"
            value={knowledgeSourceUrl}
            onChange={(e) => setKnowledgeSourceUrl(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            disabled={loading}
            placeholder="http://example.com/info.txt"
          />
        </div>

        <div>
          <label htmlFor="modelTimeSeconds" className="block text-sm font-medium text-gray-700 mb-1">
            Model Time Seconds (Optional)
          </label>
          <input
            id="modelTimeSeconds"
            type="number"
            value={modelTimeSeconds}
            onChange={(e) => setModelTimeSeconds(parseInt(e.target.value, 10))}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            disabled={loading}
            placeholder="60"
          />
        </div>
      </div>

      <button
        onClick={handleSend}
        disabled={loading || !prompt.trim() || !character.trim()}
        className={`flex items-center px-4 py-2 rounded-md ${
          loading || !prompt.trim() || !character.trim()
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
            Send VTuber Request
          </>
        )}
      </button>

      {error && <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-md">{error}</div>}
      {response && !error && (
        <div className="mt-4 p-3 bg-green-100 text-green-700 rounded-md whitespace-pre-wrap break-words">
          <h3 className="font-semibold mb-1">Echoed Response:</h3>
          <code>{response}</code>
        </div>
      )}
    </div>
  );
};

export default TextEcho; 