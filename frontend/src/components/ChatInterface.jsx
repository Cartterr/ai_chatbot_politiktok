// frontend/src/components/ChatInterface.jsx
import React, { useState, useRef, useEffect } from 'react';
import { FaPaperPlane, FaRobot, FaUser, FaTrash, FaChartBar, FaRegCopy, FaChevronRight } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import { useChatContext } from '../contexts/ChatContext';
import VisualizationDisplay from './VisualizationDisplay'; // Assuming this component exists

const MessageItem = ({ message, openFullscreen }) => {
  const isUser = message.sender === 'user';
  const formattedDate = new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); // Simplified time
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`relative p-4 md:p-6 my-4 rounded-xl shadow-sm max-w-xl md:max-w-3xl message-fade-in ${ // Adjusted padding/max-width
      isUser
        ? 'ml-auto bg-gradient-to-r from-indigo-500 to-purple-600 text-white'
        : 'mr-auto bg-white border border-gray-100 text-gray-800' // Ensure text color contrast
    }`}>
      <div className="flex items-start gap-3 mb-2">
        <div className={`p-2 rounded-full flex items-center justify-center text-lg ${ // Slightly larger icon
          isUser
            ? 'bg-indigo-700 text-white'
            : 'bg-gradient-to-r from-indigo-400 to-purple-500 text-white'
        }`}>
          {isUser ? <FaUser /> : <FaRobot />}
        </div>

        <div>
          <div className="flex items-center flex-wrap"> {/* Allow wrapping */}
            <p className={`font-medium mr-2 ${isUser ? 'text-white' : 'text-gray-900'}`}>
              {isUser ? 'Tú' : 'Asistente IA'} {/* Spanish Names */}
            </p>
            <p className={`text-xs ${isUser ? 'text-indigo-100' : 'text-gray-400'}`}>
              {formattedDate}
            </p>
          </div>
        </div>

        {!isUser && (
          <button
            onClick={copyToClipboard}
            className="ml-auto text-gray-400 hover:text-indigo-500 transition-colors p-1" // Added padding
            title={copied ? "¡Copiado!" : "Copiar respuesta"} // Spanish title
          >
            {copied ? 'Copiado!' : <FaRegCopy />}
          </button>
        )}
      </div>

      {/* Use prose for better markdown defaults if Tailwind typography is installed */}
      <div className={`prose prose-sm max-w-none mt-3 ${isUser ? 'prose-invert' : ''} markdown-content`}>
        <ReactMarkdown
           components={{ // Optional: Render links to open in new tab
             a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" />
           }}
        >{message.content}</ReactMarkdown>
      </div>

      {message.visualization && (
        <div className="mt-4 border-t border-gray-200/50 pt-4">
          <VisualizationDisplay
            visualization={message.visualization}
            openFullscreen={openFullscreen}
            isFullscreen={false}
          />
        </div>
      )}

      {message.visualizationError && (
        <div className="mt-2 p-3 bg-red-100 text-red-700 rounded-lg text-sm">
          <p><span className="font-medium">Error al visualizar:</span> {message.visualizationError}</p>
        </div>
      )}

      {message.relevantData && Object.keys(message.relevantData).length > 1 && ( // Check if relevantData has more than just summary/status
        <div className="mt-4 pt-3 border-t border-gray-200/50">
          <details className="text-sm">
            <summary className="cursor-pointer text-indigo-500 hover:text-indigo-700 flex items-center list-none"> {/* Remove default marker */}
               <FaChevronRight className="text-xs mr-1 transform transition-transform duration-200 group-open:rotate-90" /> {/* Simple rotate */}
              <span className="group-open:font-medium"> {/* Highlight when open */}
                 Ver fuentes de datos relevantes {/* Spanish */}
              </span>
            </summary>
            <div className="mt-2 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
              {/* Simple list of relevant data keys found */}
              Datos considerados: {Object.entries(message.relevantData)
                 .filter(([key, value]) => Array.isArray(value) && value.length > 0)
                 .map(([key]) => key)
                 .join(', ') || 'Resumen general'}
              {/* You could make this more detailed if needed */}
            </div>
          </details>
        </div>
      )}
    </div>
  );
};


const ChatInterface = ({ openFullscreen }) => {
  const [message, setMessage] = useState('');
  const [generateVisualization, setGenerateVisualization] = useState(false);
  const [visualizationType, setVisualizationType] = useState(''); // Default empty for auto-detect
  const { messages, isLoading, sendMessage, clearMessages, error } = useChatContext();
  const messagesEndRef = useRef(null);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (message.trim()) {
      sendMessage(message, generateVisualization, visualizationType || null); // Pass null if empty
      setMessage('');
      // Optional: Reset visualization options after sending
      // setGenerateVisualization(false);
      // setVisualizationType('');
    }
  };

  // Scroll to bottom when messages change or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Messages area */}
      <div className="flex-1 p-4 md:p-6 overflow-y-auto">
        {messages.length === 0 && !isLoading ? ( // Only show welcome if not loading initially
          <div className="flex flex-col items-center justify-center h-full text-gray-500 pt-10">
            <div className="p-4 rounded-full bg-gradient-to-r from-indigo-400 to-purple-500 text-white mb-6 shadow-lg">
              <FaRobot className="text-4xl" />
            </div>
            <h2 className="text-2xl font-bold mb-3 text-gray-800">Asistente de Investigación TikTok</h2>
            <p className="text-center max-w-md text-gray-600 mb-8">
              Pregunta sobre los jóvenes chilenos en TikTok, sus discusiones políticas,
              alfabetización digital, o pide visualizaciones de datos.
            </p>

            {/* Example Prompts - Updated styling */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-lg w-full">
              <button onClick={() => setMessage("¿Qué temas son más prevalentes en los videos de TikTok de jóvenes chilenos?")} className="text-left bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-300">
                <div className="flex items-center text-indigo-600 mb-2">
                  <FaRobot className="mr-2" />
                  <span className="font-semibold">Prueba preguntar</span>
                </div>
                <p className="text-gray-700 text-sm">
                  "¿Qué temas son más prevalentes...?"
                </p>
              </button>

              <button onClick={() => { setMessage("Muéstrame la distribución de perspectivas políticas"); setGenerateVisualization(true); }} className="text-left bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-300">
                <div className="flex items-center text-indigo-600 mb-2">
                  <FaChartBar className="mr-2" />
                  <span className="font-semibold">Prueba visualizar</span>
                </div>
                <p className="text-gray-700 text-sm">
                  "Distribución de perspectivas políticas..."
                </p>
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map(msg => (
              <MessageItem
                key={msg.id}
                message={msg}
                openFullscreen={openFullscreen}
              />
            ))}
          </>
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex justify-start p-4 md:p-6 my-4">
             <div className="flex items-center gap-3 mr-auto bg-white border border-gray-100 text-gray-800 rounded-xl shadow-sm p-4 message-fade-in">
                <div className="p-2 rounded-full flex items-center justify-center bg-gradient-to-r from-indigo-400 to-purple-500 text-white">
                    <FaRobot className="text-xl animate-pulse" />
                </div>
                <div className="flex flex-col">
                  <span className="font-medium text-gray-900 mb-1">Asistente IA</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">Pensando</span>
                    <div className="flex items-center space-x-1">
                        <div className="w-2 h-2 rounded-full bg-indigo-400 thinking-dot"></div>
                        <div className="w-2 h-2 rounded-full bg-indigo-500 thinking-dot"></div>
                        <div className="w-2 h-2 rounded-full bg-indigo-600 thinking-dot"></div>
                    </div>
                  </div>
                </div>
             </div>
          </div>
        )}

        {/* Error Display */}
        {error && !isLoading && ( // Only show error if not loading
          <div className="p-4 my-4 bg-red-50 text-red-800 rounded-lg border border-red-200 max-w-xl md:max-w-3xl mx-auto text-sm shadow-sm">
            <p><span className="font-semibold">Error:</span> {error}</p>
          </div>
        )}

        <div ref={messagesEndRef} /> {/* Element to scroll to */}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white p-4 sticky bottom-0"> {/* Make input sticky */}
        <div className="max-w-4xl mx-auto">
             {/* Visualization Options */}
             <div className="flex items-center justify-between mb-3 flex-wrap gap-2"> {/* Allow wrapping */}
                <label className="flex items-center text-sm cursor-pointer text-gray-700">
                <input
                    type="checkbox"
                    checked={generateVisualization}
                    onChange={(e) => setGenerateVisualization(e.target.checked)}
                    className="mr-2 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <FaChartBar className="mr-1.5 text-indigo-500" />
                Generar visualización
                </label>

                {generateVisualization && (
                <select
                    value={visualizationType}
                    onChange={(e) => setVisualizationType(e.target.value)}
                    className="text-sm border border-gray-300 rounded p-1.5 text-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                    title="Tipo de visualización (opcional)"
                >
                    <option value="">Detectar automáticamente</option>
                    <option value="time_series">Serie temporal</option>
                    <option value="comparison">Comparación</option>
                    <option value="distribution">Distribución</option>
                    <option value="network">Red</option>
                    <option value="sentiment">Análisis de sentimiento</option>
                    <option value="summary">Resumen</option>
                </select>
                )}

                {messages.length > 0 && ( // Only show clear button if there are messages
                <button
                    type="button"
                    onClick={clearMessages}
                    className="text-xs text-gray-500 hover:text-red-600 flex items-center transition-colors p-1 rounded hover:bg-red-50"
                    title="Limpiar conversación"
                >
                    <FaTrash className="mr-1" />
                    Limpiar
                </button>
                )}
            </div>

             {/* Text Input Form */}
            <form onSubmit={handleSendMessage} className="flex items-center rounded-lg border border-gray-300 bg-white focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 overflow-hidden">
                <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Escribe tu pregunta aquí..." // Spanish placeholder
                className="flex-1 p-3 text-sm focus:outline-none" // Adjusted padding/text size
                disabled={isLoading}
                />
                <button
                type="submit"
                className={`p-3 transition-colors duration-200 ${
                    isLoading || !message.trim()
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    : 'bg-indigo-600 text-white hover:bg-indigo-700' // Adjusted colors
                }`}
                disabled={isLoading || !message.trim()}
                title="Enviar mensaje" // Spanish title
                >
                <FaPaperPlane className="w-4 h-4" /> {/* Explicit size */}
                </button>
            </form>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;