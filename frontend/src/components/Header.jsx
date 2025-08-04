// frontend/src/components/Header.jsx
import React, { useState } from 'react';
import { FaRobot, FaInfoCircle } from 'react-icons/fa';
import { useChatContext } from '../contexts/ChatContext';

const Header = ({ activeTab }) => {
  const [showInfo, setShowInfo] = useState(false);
  const { availableModels, selectedModel, setSelectedModel } = useChatContext();

  // Helper to get Spanish titles
  const getTitle = (tab) => {
    switch(tab) {
      case 'chat': return 'Chat con Asistente de Investigación TikTok';
      case 'data': return 'Resumen de Datos';
      case 'visualizations': return 'Visualizaciones';
      default: return 'Investigación TikTok';
    }
  }

  return (
    <header className="bg-white border-b border-gray-200 py-4 px-6 flex items-center justify-between">
       {/* Use helper function for title */}
      <h1 className="text-xl font-bold text-gray-800">
        {getTitle(activeTab)}
      </h1>

      <div className="flex items-center space-x-4">
        {availableModels.length > 0 && (
          <div>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="border border-gray-300 rounded-md py-1 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              // Add title for accessibility
              title="Seleccionar modelo de IA"
            >
              {availableModels.map(model => (
                // Use model.name which might be fetched from backend
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <button
          onClick={() => setShowInfo(!showInfo)}
          className="flex items-center text-gray-500 hover:text-indigo-600 transition-colors"
          // Changed title
          title="Acerca del proyecto"
        >
          <FaInfoCircle className="text-xl" />
        </button>
      </div>

      {showInfo && (
        <div className="absolute top-16 right-4 bg-white text-gray-800 shadow-xl rounded-lg p-6 z-10 max-w-md border border-gray-100">
          <div className="flex items-center mb-3">
            <FaRobot className="text-indigo-500 mr-2 text-xl" />
            {/* Changed title */}
            <h2 className="text-lg font-semibold text-gray-800">
              Acerca del Proyecto
            </h2>
          </div>

          {/* Ensure content is in Spanish */}
          <p className="mb-3 text-gray-700">
            Este chatbot analiza la producción de espacios de educación política y alfabetizaciones
            políticas digitales creadas por jóvenes chilenos en sus cuentas públicas de TikTok.
          </p>
          <p className="text-sm text-gray-600">
            El proyecto examina cómo los jóvenes discuten política formal y temas de diversidad y justicia social,
            analiza los repertorios afectivos, y estudia las prácticas pedagógicas en estos espacios digitales.
          </p>
          <button
            onClick={() => setShowInfo(false)}
            className="mt-4 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          >
             {/* Changed text */}
            Cerrar
          </button>
        </div>
      )}
    </header>
  );
};

export default Header;