// frontend/src/components/DataSourcesDisplay.jsx
import React, { useState } from 'react';
import { FaChevronRight, FaDatabase, FaEye, FaSearch, FaInfoCircle } from 'react-icons/fa';

const DataSourcesDisplay = ({ dataSources, queryAnalysis }) => {
  const [expandedSource, setExpandedSource] = useState(null);
  const [viewingDataset, setViewingDataset] = useState(null);
  const [datasetData, setDatasetData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const viewDataset = async (datasetName) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/dataset/${datasetName}?per_page=100`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setDatasetData(data);
      setViewingDataset(datasetName);
    } catch (err) {
      setError(`Error al cargar ${datasetName}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const closeDatasetView = () => {
    setViewingDataset(null);
    setDatasetData(null);
    setError(null);
  };

  const getRelevanceColor = (score) => {
    if (score >= 0.7) return 'bg-green-100 text-green-800 border-green-200';
    if (score >= 0.4) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-blue-100 text-blue-800 border-blue-200';
  };

  const getRelevanceText = (score) => {
    if (score >= 0.7) return 'Alta relevancia';
    if (score >= 0.4) return 'Relevancia media';
    return 'Relevancia baja';
  };

  if (!dataSources || dataSources.length === 0) {
    return null;
  }

  // Dataset viewing modal
  if (viewingDataset && datasetData) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
          <div className="p-4 border-b border-gray-200 flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{datasetData.filename}</h3>
              <p className="text-sm text-gray-600">{datasetData.description}</p>
              <p className="text-xs text-gray-500 mt-1">
                {datasetData.total_rows.toLocaleString()} filas, {datasetData.columns.length} columnas
              </p>
            </div>
            <button
              onClick={closeDatasetView}
              className="text-gray-400 hover:text-gray-600 text-xl font-bold"
            >
              ×
            </button>
          </div>

          <div className="p-4 overflow-auto flex-1">
            <div className="mb-4">
              <h4 className="font-medium text-gray-900 mb-2">Columnas:</h4>
              <div className="flex flex-wrap gap-2">
                {datasetData.columns.map((col, idx) => (
                  <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                    {col}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">Datos (primeras 100 filas):</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs border border-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {datasetData.columns.map((col, idx) => (
                        <th key={idx} className="px-2 py-1 text-left font-medium text-gray-700 border-b">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {datasetData.data.slice(0, 50).map((row, idx) => (
                      <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        {datasetData.columns.map((col, colIdx) => (
                          <td key={colIdx} className="px-2 py-1 border-b text-gray-600 max-w-xs truncate">
                            {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {datasetData.data.length > 50 && (
                <p className="text-xs text-gray-500 mt-2">
                  Mostrando 50 de {datasetData.total_rows.toLocaleString()} filas
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4 pt-3 border-t border-gray-200/50">
      <details className="text-sm">
        <summary className="cursor-pointer text-indigo-500 hover:text-indigo-700 flex items-center list-none">
          <FaChevronRight className="text-xs mr-1 transform transition-transform duration-200 group-open:rotate-90" />
          <FaDatabase className="text-xs mr-2" />
          <span className="group-open:font-medium">
            Ver fuentes de datos relevantes ({dataSources.length})
          </span>
        </summary>

        <div className="mt-3 space-y-3">
          {queryAnalysis && (
            <div className="p-3 bg-blue-50 rounded-lg text-xs text-blue-800 border border-blue-200">
              <div className="flex items-center mb-1">
                <FaInfoCircle className="mr-1" />
                <span className="font-medium">Análisis de consulta</span>
              </div>
              <p>{queryAnalysis}</p>
            </div>
          )}

          {dataSources.map((source, index) => (
            <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="p-3 bg-gray-50">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <h4 className="font-medium text-gray-900 text-sm">{source.filename}</h4>
                    <span className={`px-2 py-1 rounded-full text-xs border ${getRelevanceColor(source.relevance_score)}`}>
                      {getRelevanceText(source.relevance_score)}
                    </span>
                  </div>
                  <button
                    onClick={() => viewDataset(source.dataset)}
                    disabled={loading}
                    className="flex items-center space-x-1 px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors text-xs disabled:opacity-50"
                  >
                    <FaEye className="text-xs" />
                    <span>{loading && viewingDataset === source.dataset ? 'Cargando...' : 'Ver datos'}</span>
                  </button>
                </div>

                <p className="text-xs text-gray-600 mb-2">{source.description}</p>
                <p className="text-xs text-gray-500">{source.contains}</p>

                <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                  <span>{source.rows.toLocaleString()} filas</span>
                  <span>{source.columns} columnas</span>
                  <span>Relevancia: {(source.relevance_score * 100).toFixed(0)}%</span>
                </div>
              </div>

              <button
                onClick={() => setExpandedSource(expandedSource === index ? null : index)}
                className="w-full px-3 py-2 text-left text-xs text-gray-600 hover:bg-gray-50 transition-colors flex items-center justify-between"
              >
                <span>Detalles técnicos</span>
                <FaChevronRight className={`text-xs transform transition-transform ${expandedSource === index ? 'rotate-90' : ''}`} />
              </button>

              {expandedSource === index && (
                <div className="px-3 pb-3 bg-gray-50 border-t border-gray-200">
                  <div className="text-xs text-gray-600 space-y-1">
                    <p><span className="font-medium">Dataset interno:</span> {source.dataset}</p>
                    <p><span className="font-medium">Puntuación de relevancia:</span> {source.relevance_score.toFixed(3)}</p>
                  </div>
                </div>
              )}
            </div>
          ))}

          {error && (
            <div className="p-3 bg-red-50 text-red-800 rounded-lg text-xs border border-red-200">
              <p>{error}</p>
            </div>
          )}
        </div>
      </details>
    </div>
  );
};

export default DataSourcesDisplay;