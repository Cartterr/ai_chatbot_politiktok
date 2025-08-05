import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api.js';

const ChatContext = createContext();
export const useChatContext = () => useContext(ChatContext);

export const ChatProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  // Default to a known model ID, ensure it matches backend/Ollama if possible
  const [selectedModel, setSelectedModel] = useState('Qwen2.5-Coder:32B');
  const [error, setError] = useState(null);

  // Load messages from localStorage on initial render
  useEffect(() => {
    const savedMessages = localStorage.getItem('chatMessages');
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (e) {
        console.error('Failed to parse saved messages:', e);
      }
    }

    // Fetch available models on initial load
    fetchModels();
  }, []); // Empty dependency array means this runs once on mount

  // Save messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('chatMessages', JSON.stringify(messages));
  }, [messages]);

  const fetchModels = async () => {
    try {
      const url = `${API_BASE_URL}/models`; // Use API configuration
      console.log("Fetching models from:", url);
      const response = await axios.get(url);

      if (response.data && response.data.models && Array.isArray(response.data.models)) {
        const fetchedModels = response.data.models.map(model => ({
          name: model.name, // Assuming backend provides 'name'
          id: model.model  // Assuming backend provides 'model' as the identifier
        }));

        setAvailableModels(fetchedModels);

         // Ensure the default/selected model exists in the fetched list
         if (fetchedModels.length > 0 && !fetchedModels.some(m => m.id === selectedModel)) {
             // If the current selected model isn't available, default to the first one
             setSelectedModel(fetchedModels[0].id);
         } else if (fetchedModels.length === 0) {
             // Handle case where no models are returned
             setSelectedModel(''); // Or keep the default if you prefer
             // ---> TRANSLATED ERROR <---
             setError('No hay modelos disponibles desde el backend.');
             setAvailableModels([
               // ---> TRANSLATED DEFAULT NAME <---
               { name: 'Qwen2.5-Coder 32B (Predet.)', id: 'Qwen2.5-Coder:32B' }
             ]);
         }
      } else {
          // Handle case where response is okay but data format is wrong
           // ---> TRANSLATED ERROR <---
           setError('Se recibieron datos de modelos inválidos desde el backend.');
           setAvailableModels([
             // ---> TRANSLATED DEFAULT NAME <---
             { name: 'Qwen2.5-Coder 32B (Predet.)', id: 'Qwen2.5-Coder:32B' }
           ]);
      }
    } catch (error) {
        console.error('Error fetching models:', error);
        setError('Fallo al obtener los modelos disponibles. ¿Está el backend funcionando?');
        setAvailableModels([ { name: 'Qwen2.5-Coder 32B (Predet.)', id: 'Qwen2.5-Coder:32B' } ]);
    }
  };

  const sendMessage = async (content, generateVisualization = false, visualizationType = null) => {
    if (!content.trim()) {
        return;
    }

    const userMessage = {
      id: Date.now() + Math.random().toString(36).substring(7),
      sender: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages(prevMessages => [...prevMessages, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const url = `${API_BASE_URL}/chat`; // Use API configuration
      console.log("Posting chat to:", url, "with model:", selectedModel);
      const response = await axios.post(url, {
        query: content,
        generate_visualization: generateVisualization,
        visualization_type: visualizationType,
        model: selectedModel
      });

      const botMessage = {
        id: Date.now() + Math.random().toString(36).substring(7),
        sender: 'bot',
        content: response.data.answer || 'No se recibió respuesta', // Default fallback text
        timestamp: new Date().toISOString(),
        relevantData: response.data.relevant_data, // Pass relevant data if needed
        dataSources: response.data.data_sources, // Pass data sources information
        queryAnalysis: response.data.query_analysis, // Pass query analysis
      };

      // If visualization was requested and provided
      if (generateVisualization && response.data.visualization) {
        botMessage.visualization = response.data.visualization;
      }

      // If there was a visualization error from the backend
      if (response.data.visualization_error) {
        botMessage.visualizationError = response.data.visualization_error;
      }

      setMessages(prevMessages => [...prevMessages, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      // Add a fallback error message to the chat
      setMessages(prevMessages => [...prevMessages, {
        id: Date.now() + Math.random().toString(36).substring(7),
        sender: 'bot',
        content: 'Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta nuevamente.',
        timestamp: new Date().toISOString(),
        isError: true
      }]);

      // Set error state for potential UI display
      setError(
        error.response?.data?.detail ||
        'Fallo al obtener respuesta. Por favor, verifica si el servidor backend está funcionando.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const clearMessages = () => {
    setMessages([]);
    localStorage.removeItem('chatMessages');
  };

  // Provide all the necessary values/functions to consuming components
  const contextValue = {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    availableModels,
    selectedModel,
    setSelectedModel
  };

  return (
    <ChatContext.Provider value={contextValue}>
      {children}
    </ChatContext.Provider>
  );
};