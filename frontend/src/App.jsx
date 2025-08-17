// frontend/src/App.jsx

import React, { useState, useEffect } from 'react';
import {
  FaChartBar,
  FaDatabase,
  FaHome,
  FaExpand, // Icon for fullscreen button
  FaTimes,   // Icon for close button
  FaWordpress, // For word analysis
  FaNetworkWired, // For network visualization
  FaChartLine, // For timeline analysis
  FaUsers, // For creator classification
  FaBrain,
  FaComments,
  FaHashtag,
  FaProjectDiagram
} from 'react-icons/fa';
import ChatInterface from './components/ChatInterface';
import DataSummary from './components/DataSummary';     // Assuming you created/imported this
import Visualizations from './components/Visualizations'; // Assuming you created/imported this
import Header from './components/Header';             // Assuming you created/imported this
import { useChatContext } from './contexts/ChatContext';
import VisualizationDisplay from './components/VisualizationDisplay'; // Import for modal

// Import new visualization components
import WordAnalysisViz from './components/visualizations/WordAnalysisViz';
import NetworkViz from './components/visualizations/NetworkViz';
import TimelineViz from './components/visualizations/TimelineViz';
import CreatorClassificationViz from './components/visualizations/CreatorClassificationViz';
import EtymologicalFamiliesViz from './components/visualizations/EtymologicalFamiliesViz';
import CreatorList from './components/CreatorList';
import VideoList from './components/VideoList';
import WordList from './components/WordList';

// 1. Import the logo image
import politiktokLogo from './assets/politiktok_logo.png'; // Adjust path if needed

// --- Fullscreen Modal Component ---
const FullscreenModal = ({ vizData, onClose }) => {
    if (!vizData) return null;

    // Effect to prevent body scroll when modal is open
    useEffect(() => {
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, []);

    return (
        // Overlay
        <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={onClose} // Close on overlay click
        >
            {/* Modal Content */}
            <div
                className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
                onClick={e => e.stopPropagation()} // Prevent closing when clicking inside modal
            >
                {/* Modal Header */}
                <div className="flex justify-between items-center p-4 border-b border-gray-200 bg-gray-50">
                    <h2 className="text-lg font-semibold text-gray-700">{vizData.title || 'Visualización'}</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-200 transition-colors"
                        title="Cerrar"
                        aria-label="Cerrar visualización en pantalla completa"
                    >
                        <FaTimes className="w-5 h-5" />
                    </button>
                </div>
                {/* Modal Body (Scrollable) */}
                <div className="flex-1 overflow-y-auto p-6">
                   {/* Render the visualization using the same component */}
                   <VisualizationDisplay visualization={vizData} isFullscreen={true} />
                </div>
            </div>
        </div>
    );
};


// --- Main App Component ---
const App = () => {
  const [activeTab, setActiveTab] = useState('chat');
  // State for fullscreen mode
  const [fullscreenVizData, setFullscreenVizData] = useState(null); // Holds data for the fullscreen viz

  // --- Context ---
  // Use context safely, checking if it exists
  const context = useChatContext();
  if (!context) {
    return (
      <div className="flex h-screen bg-gray-100 items-center justify-center">
        <div className="text-center p-6 bg-white rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Error</h2>
          <p className="text-gray-600">No se pudo cargar el contexto del chat. Por favor, recarga la página.</p>
        </div>
      </div>
    );
  }
  // Destructure AFTER checking context exists
  const { messages, isLoading: isChatLoading, error: chatError } = context; // Use specific names if needed

  // --- State for Data Summary (Example) ---
  // You would fetch this data similarly to how models are fetched in ChatContext
  const [summaryData, setSummaryData] = useState(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);

   useEffect(() => {
      const fetchSummary = async () => {
          if (activeTab === 'data' && !summaryData) { // Fetch only when tab is active and data not loaded
              setIsSummaryLoading(true);
              try {
                  // Use axios or fetch with relative path to your summary endpoint
                  // const response = await axios.get('/api/data/summary');
                  // setSummaryData(response.data);

                  // Placeholder data for now:
                   await new Promise(resolve => setTimeout(resolve, 500)); // Simulate fetch
                   setSummaryData({
                       accounts: { rows: 150, sample: [{username: '@test', followers: '10K'}], columns: ['username', 'followers'] },
                       videos: { rows: 1200, sample: [{title: 'vid1', views: 5000}], columns: ['title', 'views'] },
                       subtitles: { rows: 800 },
                       words: { rows: 5000 }
                   });

              } catch (error) {
                  console.error("Error fetching summary data:", error);
                  // Handle error state if needed
              } finally {
                  setIsSummaryLoading(false);
              }
          }
      };
      fetchSummary();
   }, [activeTab, summaryData]); // Rerun if tab changes or summaryData is reset


  // --- Fullscreen Handlers ---
  const openFullscreen = (vizData) => {
      if (vizData) {
          console.log("Opening fullscreen for:", vizData.title);
          setFullscreenVizData(vizData);
      }
  };
  const closeFullscreen = () => {
      console.log("Closing fullscreen");
      setFullscreenVizData(null);
  };

  // --- Helper to render main content based on activeTab ---
  const renderMainContent = () => {
    switch(activeTab) {
      case 'chat':
        // Pass openFullscreen function down to ChatInterface -> MessageItem -> VisualizationDisplay
        return <ChatInterface openFullscreen={openFullscreen} />;
      case 'data':
        return <DataSummary data={summaryData} isLoading={isSummaryLoading} />;
      case 'visualizations':
        // Pass openFullscreen function down to Visualizations -> VizCard -> VisualizationDisplay
        // Also pass messages for the history list
        // Pass the *last* generated visualization from messages as initial prop (optional)
        const lastViz = messages.slice().reverse().find(m => m.visualization)?.visualization;
        return <Visualizations visualization={lastViz} messages={messages} openFullscreen={openFullscreen} />;
      case 'word-analysis':
        return <WordAnalysisViz />;
      case 'network-viz':
        return <NetworkViz />;
      case 'timeline-viz':
        return <TimelineViz />;
      case 'creator-classification':
        return <CreatorClassificationViz />;
      case 'etymological-families':
        return <EtymologicalFamiliesViz />;
      case 'creators':
        return <CreatorList />;
      case 'videos':
        return <VideoList />;
      case 'words':
        return <WordList />;
      default:
        return <ChatInterface openFullscreen={openFullscreen} />; // Default to chat
    }
  };

  return (
    <div className="flex h-screen bg-gray-100 font-sans"> {/* Added font-sans */}
      {/* --- Sidebar --- */}
      <aside className="w-16 md:w-20 bg-gradient-to-b from-indigo-700 to-purple-800 text-indigo-100 flex flex-col items-center py-5 shadow-lg">
        <div className="mb-10 mt-1">
          <a 
            href="https://politiktok.cl/" 
            target="_blank" 
            rel="noopener noreferrer"
            className="block hover:opacity-80 transition-opacity duration-200"
            title="Ir a PoliTikTok.cl"
          >
            <img src={politiktokLogo} alt="PoliTikTok Logo" className="w-10 h-10 md:w-12 md:h-12 object-contain"/>
          </a>
        </div>
        <nav className="flex flex-col items-center space-y-5">
          {/* Navigation Buttons */}
          {[
            { id: 'chat', title: 'Chat', icon: FaHome },
            { id: 'data', title: 'Resumen Datos', icon: FaDatabase },
            { id: 'visualizations', title: 'Visualizaciones', icon: FaChartBar },
            { id: 'word-analysis', title: 'Análisis de Palabras', icon: FaWordpress },
            { id: 'network-viz', title: 'Red de Conexiones', icon: FaNetworkWired },
            { id: 'timeline-viz', title: 'Línea de Tiempo', icon: FaChartLine },
            { id: 'creator-classification', title: 'Clasificación Creadores', icon: FaUsers },
            { id: 'etymological-families', title: 'Familias Etimológicas', icon: FaProjectDiagram },
            { id: 'creators', title: 'Creadores', icon: FaUsers },
            { id: 'videos', title: 'Videos', icon: FaComments },
            { id: 'words', title: 'Palabras', icon: FaHashtag }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`p-3 rounded-lg transition-all duration-200 ease-in-out transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:ring-opacity-50 ${
                activeTab === tab.id
                  ? 'bg-white text-indigo-700 shadow-md'
                  : 'text-indigo-200 hover:text-white hover:bg-white/20'
              }`}
              title={tab.title} // Spanish titles
            >
              <tab.icon className="w-5 h-5 md:w-6 md:h-6" />
            </button>
          ))}
        </nav>
      </aside>

      {/* --- Main Content Area --- */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header Component */}
        <Header activeTab={activeTab} />

        {/* Dynamic Main Content */}
        <main className="flex-1 overflow-y-auto bg-gray-50"> {/* Allow scrolling */}
           {renderMainContent()}
        </main>
      </div>

      {/* --- Fullscreen Modal --- */}
      {/* Render the modal conditionally based on fullscreenVizData state */}
      <FullscreenModal vizData={fullscreenVizData} onClose={closeFullscreen} />

    </div>
  );
};

export default App;