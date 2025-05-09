import { useState } from 'react';
import { Settings as SettingsIcon, Wallet as WalletIcon } from 'lucide-react';
import WalletConnect from './components/WalletConnect';
import Settings from './components/Settings';
import { useWallet } from './hooks/useWallet';
import { useSettings } from './hooks/useSettings';
import ByocTest from './components/ByocTest';
import TextEcho from './components/TextEcho';

function App() {
  const { wallet, connectWallet, disconnectWallet } = useWallet();
  const { settings, updateSettings, clearEthAddress } = useSettings();
  
  const [isWalletModalOpen, setIsWalletModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  
  // Sync wallet address with settings when wallet connects/disconnects
  if (wallet.isConnected && wallet.address && settings.ethAddress !== wallet.address) {
    updateSettings({ ethAddress: wallet.address });
  } else if (!wallet.isConnected && settings.ethAddress) {
    clearEthAddress();
  }

  return (
    <div className="min-h-screen bg-slate-100 p-4 sm:p-6 selection:bg-sky-200 selection:text-sky-900">
      <header className="flex justify-between items-center mb-8 pb-4 border-b border-slate-300">
        <h1 className="text-3xl font-bold text-sky-700">Vtuber Manager</h1>
        
        <div className="flex space-x-3">
          <button
            onClick={() => setIsSettingsModalOpen(true)}
            className="p-2 bg-white rounded-lg shadow-md hover:bg-slate-50 text-slate-600 hover:text-sky-600 transition-colors duration-150"
            aria-label="Settings"
          >
            <SettingsIcon size={22} />
          </button>
          
          <button
            onClick={() => setIsWalletModalOpen(true)}
            className={`p-2 rounded-lg shadow-md flex items-center transition-all duration-150 ${
              wallet.isConnected 
                ? 'bg-emerald-500 text-white hover:bg-emerald-600' 
                : 'bg-white hover:bg-slate-50 text-slate-600 hover:text-sky-600'
            }`}
            aria-label="Wallet"
          >
            <WalletIcon size={22} />
            {wallet.isConnected && (
              <span className="ml-2 text-xs font-medium hidden sm:inline">
                {wallet.address?.substring(0, 6)}...{wallet.address?.substring(wallet.address.length - 4)}
              </span>
            )}
          </button>
        </div>
      </header>
      
      <main className="max-w-3xl mx-auto space-y-6">
        <TextEcho />
        <ByocTest />
      </main>
      
      {/* Wallet Modal */}
      {isWalletModalOpen && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl p-6 sm:p-8 max-w-md w-full">
            <WalletConnect
              wallet={wallet}
              onConnect={connectWallet}
              onDisconnect={disconnectWallet}
              onClose={() => setIsWalletModalOpen(false)}
            />
          </div>
        </div>
      )}
      
      {/* Settings Modal */}
      {isSettingsModalOpen && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl p-6 sm:p-8 max-w-md w-full">
            <Settings
              settings={settings}
              onUpdateSettings={updateSettings}
              onClose={() => setIsSettingsModalOpen(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
