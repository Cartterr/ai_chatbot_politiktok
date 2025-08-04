// frontend/src/components/DataSummary.jsx
import React, { useState, useEffect } from 'react';
import {
  FaSpinner,
  FaDatabase,
  FaUser,
  FaVideo,
  FaComment,
  FaHashtag,
  FaExclamationTriangle,
  FaBrain,
  FaChartLine,
  FaHeart,
  FaUsers,
  FaFire,
  FaRedo
} from 'react-icons/fa';
import { API_BASE_URL } from '../config/api.js';

const InsightCard = ({ insight, index }) => {
  const iconMap = {
    'overview': <FaDatabase className="text-xl" />,
    'trends': <FaChartLine className="text-xl" />,
    'sentiment': <FaHeart className="text-xl" />,
    'demographics': <FaUsers className="text-xl" />,
    'engagement': <FaFire className="text-xl" />
  };

  const colorMap = {
    'overview': 'bg-indigo-500',
    'trends': 'bg-purple-500',
    'sentiment': 'bg-pink-500',
    'demographics': 'bg-blue-500',
    'engagement': 'bg-orange-500'
  };

  const category = insight.category || 'overview';
  
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
      <div className="flex items-start space-x-4">
        <div className={`p-3 rounded-full ${colorMap[category]} text-white flex-shrink-0`}>
          {iconMap[category]}
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 mb-2">{insight.title}</h3>
          <p className="text-gray-600 mb-3 leading-relaxed">{insight.description}</p>
          {insight.metric && (
            <div className="bg-gray-50 px-3 py-2 rounded-md">
              <span className="text-sm font-medium text-gray-700">📊 {insight.metric}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const InsightTypeSelector = ({ selectedType, onTypeChange, isLoading }) => {
  const types = [
    { id: 'overview', label: 'Resumen General', icon: <FaDatabase /> },
    { id: 'trends', label: 'Tendencias', icon: <FaChartLine /> },
    { id: 'sentiment', label: 'Sentimientos', icon: <FaHeart /> },
    { id: 'demographics', label: 'Demografía', icon: <FaUsers /> },
    { id: 'engagement', label: 'Engagement', icon: <FaFire /> }
  ];

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {types.map((type) => (
        <button
          key={type.id}
          onClick={() => onTypeChange(type.id)}
          disabled={isLoading}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            selectedType === type.id
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          {type.icon}
          <span>{type.label}</span>
        </button>
      ))}
    </div>
  );
};

const DataSummary = ({ data, isLoading: dataLoading }) => {
  const [insights, setInsights] = useState([]);
  const [summary, setSummary] = useState('');
  const [dataUsed, setDataUsed] = useState({});
  const [selectedInsightType, setSelectedInsightType] = useState('overview');
  const [focusArea, setFocusArea] = useState('');
  const [isGeneratingInsights, setIsGeneratingInsights] = useState(false);
  const [error, setError] = useState(null);

  const generateInsights = async () => {
    if (!data) return;
    
    setIsGeneratingInsights(true);
    try {
      const response = await fetch(`${API_BASE_URL}/data/insights`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          data_summary: data,
          focus_areas: ['trends', 'patterns', 'anomalies']
        })
      });

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      setInsights(result.insights || []);
      setSummary(result.summary || '');
      setDataUsed(result.data_used || {});
    } catch (err) {
      console.error('Error generating insights:', err);
      setError(err.message);
      setInsights([]);
      setSummary('');
    } finally {
      setIsGeneratingInsights(false);
    }
  };

  useEffect(() => {
    if (!dataLoading && data) {
      generateInsights();
    }
  }, [dataLoading, data]);

  const handleInsightTypeChange = (newType) => {
    setSelectedInsightType(newType);
    generateInsights();
  };

  const handleFocusAreaChange = (e) => {
    setFocusArea(e.target.value);
  };

  const handleRefresh = () => {
    generateInsights();
  };

  if (dataLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50">
        <FaSpinner className="text-indigo-600 text-4xl animate-spin mb-4" />
        <p className="text-gray-600">Cargando datos...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 text-gray-500">
        <div className="p-4 rounded-full bg-red-100 text-red-500 mb-4">
          <FaExclamationTriangle className="text-4xl" />
        </div>
        <h2 className="text-2xl font-semibold mb-2 text-gray-700">No se pudieron cargar los datos</h2>
        <p className="text-center max-w-md text-gray-600">
          Verifica que el servidor backend esté funcionando y los datos estén disponibles.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 overflow-y-auto h-full bg-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <FaBrain className="text-indigo-500 text-2xl mr-3" />
            <h2 className="text-2xl font-bold text-gray-800">Insights Inteligentes</h2>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isGeneratingInsights}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <FaRedo className={isGeneratingInsights ? 'animate-spin' : ''} />
            <span>Actualizar</span>
          </button>
        </div>

        {/* Data Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center">
              <FaUser className="text-indigo-500 text-xl mr-3" />
              <div>
                <p className="text-sm text-gray-600">Cuentas</p>
                <p className="text-xl font-bold text-gray-800">{dataUsed.accounts_count || 0}</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center">
              <FaVideo className="text-purple-500 text-xl mr-3" />
              <div>
                <p className="text-sm text-gray-600">Videos</p>
                <p className="text-xl font-bold text-gray-800">{dataUsed.videos_count || 0}</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center">
              <FaComment className="text-blue-500 text-xl mr-3" />
              <div>
                <p className="text-sm text-gray-600">Subtítulos</p>
                <p className="text-xl font-bold text-gray-800">{dataUsed.subtitles_count || 0}</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center">
              <FaHashtag className="text-green-500 text-xl mr-3" />
              <div>
                <p className="text-sm text-gray-600">Palabras</p>
                <p className="text-xl font-bold text-gray-800">{dataUsed.words_count || 0}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Configurar Análisis</h3>
          
          <InsightTypeSelector 
            selectedType={selectedInsightType}
            onTypeChange={handleInsightTypeChange}
            isLoading={isGeneratingInsights}
          />

          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Área de Enfoque (Opcional)
              </label>
              <input
                type="text"
                value={focusArea}
                onChange={handleFocusAreaChange}
                placeholder="ej: política juvenil, diversidad, justicia social..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={() => generateInsights()}
                disabled={isGeneratingInsights}
                className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isGeneratingInsights ? 'Generando...' : 'Generar'}
              </button>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isGeneratingInsights && (
          <div className="flex flex-col items-center justify-center py-12">
            <FaSpinner className="text-indigo-600 text-3xl animate-spin mb-4" />
            <p className="text-gray-600">Generando insights inteligentes...</p>
            <p className="text-sm text-gray-500 mt-2">Esto puede tomar unos momentos</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <FaExclamationTriangle className="text-red-500 text-xl mr-3" />
              <div>
                <h3 className="text-red-800 font-semibold">Error al generar insights</h3>
                <p className="text-red-600">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Summary */}
        {summary && !isGeneratingInsights && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-indigo-800 mb-3">Resumen del Análisis</h3>
            <p className="text-indigo-700 leading-relaxed">{summary}</p>
          </div>
        )}

        {/* Insights */}
        {insights.length > 0 && !isGeneratingInsights && (
          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-800">Insights Generados</h3>
            <div className="grid gap-6">
              {insights.map((insight, index) => (
                <InsightCard key={index} insight={insight} index={index} />
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {insights.length === 0 && !isGeneratingInsights && !error && (
          <div className="text-center py-12">
            <FaBrain className="text-gray-300 text-5xl mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No hay insights disponibles</h3>
            <p className="text-gray-500">Selecciona un tipo de análisis y haz clic en "Generar" para comenzar.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DataSummary;