import React, { useState, useEffect } from 'react';
import { FaSearch, FaHashtag, FaHeart, FaFrown, FaMeh, FaFilter, FaTag } from 'react-icons/fa';
import { API_BASE_URL } from '../config/api.js';

const WordList = () => {
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSentiment, setSelectedSentiment] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState({});
  const [sortBy, setSortBy] = useState('');
  const [sortOrder, setSortOrder] = useState('asc');
  const [filterBy, setFilterBy] = useState('');
  const [filterValue, setFilterValue] = useState('');

  const itemsPerPage = 25;

  useEffect(() => {
    fetchWords();
  }, [currentPage, searchTerm, selectedSentiment, sortBy, sortOrder, filterBy, filterValue]);

  const fetchWords = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: itemsPerPage.toString(),
        ...(searchTerm && { search: searchTerm }),
        ...(sortBy && { sort_by: sortBy }),
        ...(sortOrder && { sort_order: sortOrder }),
        ...(filterBy && { filter_by: filterBy }),
        ...(filterValue && { filter_value: filterValue })
      });

      const response = await fetch(`${API_BASE_URL}/data/words?${params}`);
      if (!response.ok) {
        throw new Error('Error al cargar datos de palabras');
      }
      
      const data = await response.json();
      setWords(data.words || []);
      setPagination(data.pagination || {});
    } catch (err) {
      setError(err.message);
      setWords([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const handleSentimentFilter = (e) => {
    setSelectedSentiment(e.target.value);
    setCurrentPage(1);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  const getSentimentIcon = (sentiment) => {
    switch (sentiment) {
      case 'Positivo':
        return <FaHeart className="h-4 w-4 text-green-500" />;
      case 'Negativo':
        return <FaFrown className="h-4 w-4 text-red-500" />;
      case 'Neutral':
        return <FaMeh className="h-4 w-4 text-gray-500" />;
      default:
        return <FaMeh className="h-4 w-4 text-gray-500" />;
    }
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'Positivo':
        return 'bg-green-100 text-green-800';
      case 'Negativo':
        return 'bg-red-100 text-red-800';
      case 'Neutral':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatFrequency = (frequency) => {
    if (frequency >= 1000) {
      return `${(frequency / 1000).toFixed(1)}K`;
    }
    return frequency.toString();
  };

  const formatFamily = (family) => {
    if (!family || family === 'Sin clasificar') return 'Sin clasificar';
    // Clean up family names for display
    return family.replace(/familia_palabras_\d+_/, '').replace(/_/g, ' ');
  };

  const getEngagementColor = (score) => {
    if (score >= 1000) return 'text-green-600 bg-green-50';
    if (score >= 500) return 'text-yellow-600 bg-yellow-50';
    if (score >= 100) return 'text-orange-600 bg-orange-50';
    return 'text-red-600 bg-red-50';
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Cargando palabras...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <div className="text-red-400">
              <FaHashtag className="h-5 w-5" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error al cargar datos</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Lista de Palabras</h1>
        
        {/* Search and Filter Controls */}
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="relative flex-1">
            <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar palabras..."
              value={searchTerm}
              onChange={handleSearch}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div className="relative">
            <FaFilter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <select
              value={selectedSentiment}
              onChange={handleSentimentFilter}
              className="pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todos los sentimientos</option>
              <option value="positive">Positivo</option>
              <option value="negative">Negativo</option>
              <option value="neutral">Neutral</option>
            </select>
          </div>
        </div>

        {/* Results Summary */}
        <div className="text-sm text-gray-600 mb-4">
          Mostrando {words.length} de {pagination.total || 0} palabras
          {searchTerm && ` (filtrado por: "${searchTerm}")`}
          {selectedSentiment && ` (sentimiento: ${selectedSentiment})`}
        </div>
      </div>

      {/* Words Table */}
      <div className="bg-white shadow-sm rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Palabra
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Frecuencia
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Sentimiento
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Familia 1
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Familia 2
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Engagement
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {words.map((word, index) => (
                <tr key={`${word.word}-${index}`} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-8 w-8">
                        <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                          <FaHashtag className="h-3 w-3 text-blue-600" />
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {word.word}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {formatFrequency(word.frequency)}
                    </div>
                    <div className="text-xs text-gray-500">
                      apariciones
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {getSentimentIcon(word.sentiment_label)}
                      <span className={`ml-2 inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSentimentColor(word.sentiment_label)}`}>
                        {word.sentiment_label}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Score: {word.sentiment_score.toFixed(2)}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 max-w-xs">
                    <div className="flex items-center">
                      <FaTag className="h-3 w-3 text-gray-400 mr-1" />
                      <span className="truncate" title={word.family_1}>
                        {formatFamily(word.family_1)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 max-w-xs">
                    <div className="flex items-center">
                      <FaTag className="h-3 w-3 text-gray-400 mr-1" />
                      <span className="truncate" title={word.family_2}>
                        {formatFamily(word.family_2)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getEngagementColor(word.engagement_score)}`}>
                      {Math.round(word.engagement_score)}
                    </span>
                    <div className="text-xs text-gray-500 mt-1">
                      {word.videos_count} videos
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {words.length === 0 && !loading && (
          <div className="text-center py-12">
            <FaHashtag className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No se encontraron palabras</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm || selectedSentiment ? 'Intenta con otros términos de búsqueda.' : 'No hay datos disponibles.'}
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {pagination.pages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Página {pagination.page} de {pagination.pages}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Anterior
            </button>
            
            {/* Page numbers */}
            {Array.from({ length: Math.min(5, pagination.pages) }, (_, i) => {
              const pageNum = Math.max(1, Math.min(pagination.pages - 4, currentPage - 2)) + i;
              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`px-3 py-2 text-sm font-medium rounded-md ${
                    pageNum === currentPage
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-500 bg-white border border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= pagination.pages}
              className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default WordList; 