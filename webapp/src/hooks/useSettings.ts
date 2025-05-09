import { useState, useEffect, useCallback } from 'react';

// Base URL for Caddy; endpoints are routed via Caddy rules (/process/*, /worker/*, etc.)
const DEFAULT_API_BASE_URL = 'http://localhost:8088';
const DEFAULT_CAPABILITY = 'text-echo';
const STORAGE_KEY = 'text-echo-settings';

interface Settings {
  apiBaseUrl: string;
  capability: string;
  ethAddress: string;
}

export function useSettings() {
  const [settings, setSettings] = useState<Settings>(() => {
    // Initialize from localStorage if available
    try {
      const savedSettings = localStorage.getItem(STORAGE_KEY);
      if (savedSettings) {
        return JSON.parse(savedSettings);
      }
    } catch (error) {
      console.error('Failed to parse saved settings:', error);
    }
    
    // Default settings
    return {
      apiBaseUrl: DEFAULT_API_BASE_URL,
      capability: DEFAULT_CAPABILITY,
      ethAddress: '',
    };
  });

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (error) {
      console.error('Failed to save settings to localStorage:', error);
    }
  }, [settings]);

  // Update settings
  const updateSettings = useCallback((newSettings: Partial<Settings>) => {
    setSettings(prevSettings => ({
      ...prevSettings,
      ...newSettings
    }));
  }, []);

  // Clear ethereum address
  const clearEthAddress = useCallback(() => {
    setSettings(prevSettings => ({
      ...prevSettings,
      ethAddress: ''
    }));
  }, []);

  return {
    settings,
    updateSettings,
    clearEthAddress,
    DEFAULT_API_BASE_URL,
    DEFAULT_CAPABILITY,
  };
}
