// frontend/src/components/Visualizations.jsx

import React, { useState, useEffect } from 'react';
import {
  FaSearch,
  FaChartLine,
  FaChartBar,
  FaChartPie,
  FaNetworkWired,
  FaSmile,
  FaSpinner
} from 'react-icons/fa';
import VisualizationDisplay from './VisualizationDisplay'; // Assuming this component exists and renders based on type
import axios from 'axios';

// --- VizTypeButton Component ---
// Button for selecting a specific visualization type for generation
const VizTypeButton = ({ icon, label, value, selected, onClick }) => (
  <button
    type="button" // Prevent form submission
    onClick={() => onClick(value)}
    className={`flex items-center p-2 md:p-3 text-xs md:text-sm rounded-lg border transition-colors duration-150 ${
      selected
        ? 'bg-indigo-100 border-indigo-500 text-indigo-700 font-medium'
        : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50 hover:border-gray-400'
    }`}
    title={`Seleccionar tipo: ${label}`} // Accessibility Title (Spanish)
  >
    {icon}
    <span className="ml-2">{label}</span>
  </button>
);

// --- VizCard Component ---
// Card displaying a previously generated visualization in the list
const VizCard = ({ vizInfo, isActive, onClick }) => {
  // Determine icon based on visualization type
  let icon;
  const vizType = vizInfo?.visualization?.type; // Safely access type
  switch (vizType) {
    case 'time_series': icon = <FaChartLine className="text-indigo-600 mr-2" />; break;
    case 'comparison': icon = <FaChartBar className="text-indigo-600 mr-2" />; break;
    case 'distribution': icon = <FaChartPie className="text-indigo-600 mr-2" />; break;
    case 'network': icon = <FaNetworkWired className="text-indigo-600 mr-2" />; break;
    case 'sentiment': icon = <FaSmile className="text-indigo-600 mr-2" />; break;
    case 'summary': icon = <FaChartBar className="text-indigo-600 mr-2" />; break; // Re-use icon for summary
    default: icon = <FaChartBar className="text-gray-500 mr-2" />; // Fallback icon
  }

  const title = vizInfo?.visualization?.title || 'Visualización Sin Título'; // Safely access title

  return (
    <button // Make it a button for better semantics/accessibility
      type="button"
      className={`text-left w-full p-4 rounded-lg border transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-indigo-300 ${
        isActive
          ? 'border-indigo-500 bg-indigo-50 shadow-md ring-1 ring-indigo-500' // Clearer active state
          : 'border-gray-200 bg-white hover:shadow-sm hover:border-gray-300'
      }`}
      onClick={() => onClick(vizInfo)} // Pass the whole vizInfo back
      aria-pressed={isActive} // Indicate active state for screen readers
    >
      <div className="flex items-center">
        {icon}
        <h4 className={`font-medium truncate ${isActive ? 'text-indigo-700' : 'text-gray-700'}`}>
          {title}
        </h4>
      </div>
      <p className="text-xs text-gray-500 mt-2">
        {/* Format timestamp */}
        {new Date(vizInfo.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short'})}
      </p>
    </button>
  );
};


// --- Main Visualizations Component ---
const Visualizations = ({ visualization, messages }) => {
  const [query, setQuery] = useState('');
  const [selectedGenType, setSelectedGenType] = useState(''); // Type for *generating* new viz
  // State to hold the currently displayed visualization's data and its origin message ID (or null if newly generated)
  const [activeViz, setActiveViz] = useState({ id: null, data: visualization });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- Effect to update the active viz if the initial prop changes ---
  // (e.g., generated in Chat tab, then user switches to Visualization tab)
  useEffect(() => {
      // Only update if the incoming prop is different from the current data
      // This prevents unnecessary re-renders if the prop reference changes but data is same
      // Note: Deep comparison could be used here if needed, but often reference check is sufficient
      if (visualization !== activeViz.data) {
           setActiveViz({ id: null, data: visualization }); // Assume incoming prop is new/not from history
      }
  }, [visualization]); // Rerun only when the `visualization` prop changes

  // --- Extract and Sort Previous Visualizations from Messages ---
  const messageVisualizations = React.useMemo(() => {
      return messages
        .filter(m => m.visualization) // Only messages with visualizations
        .map(m => ({
            id: m.id, // Keep the message ID
            title: m.visualization.title || 'Visualización', // Use title from data
            type: m.visualization.type,
            visualization: m.visualization, // The actual viz data
            timestamp: m.timestamp
        }))
        // Sort by timestamp descending (newest first)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  }, [messages]); // Recalculate only when messages change

  // --- Handler for Visualization Type Button Click ---
  const handleTypeButtonClick = (typeValue) => {
      // If clicking the already selected type, deselect it (back to auto-detect)
      setSelectedGenType(prevType => (prevType === typeValue ? '' : typeValue));
  };

  // --- Handler for Submitting a New Visualization Request ---
  const handleQuerySubmit = async (e) => {
    e.preventDefault();
    // No API_BASE_URL check needed here anymore
    if (!query.trim()) {
        // Maybe add a visual cue instead of just returning?
        return;
    }

    setIsLoading(true);
    setError(null);
    setActiveViz({ id: null, data: null }); // Clear previous viz while loading

    try {
      const url = '/api/visualize'; // Use relative path for the proxy
      console.log(`Requesting visualization: POST ${url} | Type: ${selectedGenType || 'auto'}`);
      const response = await axios.post(url, {
        query,
        visualization_type: selectedGenType || undefined // Send undefined if empty string for auto-detect
      });

      if (response.data && response.data.visualization) {
        // Set the newly generated viz data, ID is null as it's not from history
        setActiveViz({ id: null, data: response.data.visualization });
      } else {
        // Handle case where backend responded but didn't include visualization data
        setError('La respuesta del servidor no incluyó una visualización válida.'); // Spanish
        setActiveViz({ id: null, data: null });
      }
    } catch (err) {
      console.error('Error generating visualization:', err);
      // Set error message from backend response or provide a generic one
      setError(
        err.response?.data?.detail || // Use FastAPI error detail if available
        'Error al generar la visualización. Verifica la conexión o la consulta.' // Spanish generic error
      );
      setActiveViz({ id: null, data: null }); // Clear viz on error
    } finally {
      setIsLoading(false);
    }
  };

  // --- Handler for Selecting a Previous Visualization ---
  const selectVisualization = (vizInfo) => {
      // Set the active visualization using the ID and data from the selected history item
    setActiveViz({ id: vizInfo.id, data: vizInfo.visualization });
    setError(null); // Clear any previous errors
    // Optional: Clear the generation query/type when selecting from history?
    // setQuery('');
    // setSelectedGenType('');
  };


  // --- Render Logic ---
  return (
    <div className="h-full flex flex-col bg-gray-100"> {/* Changed background */}

      {/* --- Search and Filter Area --- */}
      <div className="bg-white border-b border-gray-200 p-4 md:p-6 shadow-sm">
        <form onSubmit={handleQuerySubmit} className="flex flex-col space-y-4 max-w-4xl mx-auto">
          {/* Input Field */}
          <div className="flex shadow-sm rounded-lg">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Escribe una consulta para generar una visualización..." // Spanish
              className="flex-1 p-3 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 z-10" // Ensure input is above button focus ring
              disabled={isLoading}
              aria-label="Consulta para visualización" // Accessibility label
            />
            {/* Submit Button */}
            <button
              type="submit"
              className={`relative inline-flex items-center justify-center px-4 py-3 border border-transparent font-medium rounded-r-lg text-white transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                isLoading || !query.trim()
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
              disabled={isLoading || !query.trim()}
              title="Generar Visualización" // Spanish
            >
              {isLoading ? <FaSpinner className="animate-spin h-5 w-5" /> : <FaSearch className="h-5 w-5" />}
            </button>
          </div>

          {/* Visualization Type Buttons */}
          <div className="flex flex-wrap justify-center gap-2">
            <VizTypeButton icon={<FaChartLine />} label="Serie Temporal" value="time_series" selected={selectedGenType === 'time_series'} onClick={handleTypeButtonClick} />
            <VizTypeButton icon={<FaChartBar />} label="Comparación" value="comparison" selected={selectedGenType === 'comparison'} onClick={handleTypeButtonClick} />
            <VizTypeButton icon={<FaChartPie />} label="Distribución" value="distribution" selected={selectedGenType === 'distribution'} onClick={handleTypeButtonClick} />
            <VizTypeButton icon={<FaNetworkWired />} label="Red" value="network" selected={selectedGenType === 'network'} onClick={handleTypeButtonClick} />
            <VizTypeButton icon={<FaSmile />} label="Sentimientos" value="sentiment" selected={selectedGenType === 'sentiment'} onClick={handleTypeButtonClick} />
            <VizTypeButton icon={<FaChartBar />} label="Resumen" value="summary" selected={selectedGenType === 'summary'} onClick={handleTypeButtonClick} />
          </div>
        </form>
      </div>

      {/* --- Main Display Area --- */}
      <div className="flex-1 p-4 md:p-6 overflow-y-auto">
        {/* Loading State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center text-center h-64 p-4">
            <FaSpinner className="text-indigo-500 text-3xl animate-spin mb-4" />
            <p className="text-gray-600 font-medium">Generando visualización...</p> {/* Spanish */}
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="max-w-2xl mx-auto p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 shadow-sm">
            <p className="font-semibold mb-1">Error al generar visualización</p> {/* Spanish */}
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Display Current Visualization State */}
        {!isLoading && !error && activeViz.data && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-lg p-4 md:p-6 mb-8 max-w-5xl mx-auto">
            <VisualizationDisplay visualization={activeViz.data} />
          </div>
        )}

        {/* Default/Empty State (when no viz is loaded/selected) */}
        {!isLoading && !error && !activeViz.data && (
          <div className="flex flex-col items-center justify-center text-center h-64 p-4 text-gray-500">
            <div className="p-5 rounded-full bg-gray-200 mb-4">
              <FaChartBar className="text-4xl text-gray-400" />
            </div>
            <h2 className="text-xl font-semibold mb-2 text-gray-700">No hay visualización seleccionada</h2> {/* Spanish */}
            <p className="text-center text-gray-600 max-w-md">
              Usa el buscador para generar una nueva o selecciona una de las visualizaciones previas. {/* Spanish */}
            </p>
          </div>
        )}

        {/* --- List of Previously Generated Visualizations --- */}
        {messageVisualizations.length > 0 && (
          <div className="mt-10 max-w-5xl mx-auto">
            <h3 className="text-lg font-semibold mb-4 text-gray-800 px-1">Visualizaciones Previas</h3> {/* Spanish */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {messageVisualizations.map((vizInfo) => (
                <VizCard
                  key={vizInfo.id} // Use the unique message ID
                  vizInfo={vizInfo}
                  // Highlight if the ID matches the active visualization's ID
                  isActive={activeViz.id === vizInfo.id}
                  onClick={selectVisualization} // Pass the handler
                />
              ))}
            </div>
          </div>
        )}
      </div> {/* End Main Display Area */}
    </div> // End Component Root Div
  );
};

export default Visualizations;