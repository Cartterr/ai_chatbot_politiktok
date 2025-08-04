import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  FaSpinner,
  FaExclamationTriangle,
  FaFilter,
  FaSearch,
  FaDownload,
  FaClock,
  FaUsers,
  FaChartLine,
  FaEye,
  FaEyeSlash,
  FaRedo
} from 'react-icons/fa';
import * as d3 from 'd3';
import { API_BASE_URL } from '../../config/api.js';

// Debounce hook for performance optimization
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

const WordAnalysisViz = () => {
  // State management
  const [data, setData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Visualization controls
  const [xAxisMode, setXAxisMode] = useState('tiempo'); // 'tiempo', 'creador', 'metricas'
  const [selectedFamilies, setSelectedFamilies] = useState(new Set());
  const [selectedCreators, setSelectedCreators] = useState(new Set());
  const [timeRange, setTimeRange] = useState([null, null]);
  const [searchTerm, setSearchTerm] = useState('');

  // Visualization state
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, data: null });
  const [selectedWords, setSelectedWords] = useState(new Set());

  // Refs
  const svgRef = useRef();
  const containerRef = useRef();
  const animationFrameRef = useRef();

  // Debounce search term to prevent excessive filtering
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  // Constants
  const CREATOR_CATEGORIES = [
    'izquierda', 'derecha', 'LGBTQIA+', 'feminista',
    'discapacidad', 'derechos-indigenas', 'otros'
  ];

  const COLOR_SCHEME = d3.schemeCategory10;

  // Load data on component mount
  useEffect(() => {
    loadWordData();
  }, []);

  // Memoized filtered data to prevent unnecessary recalculations
  const filteredData = useMemo(() => {
    let filtered = data.filter(word => {
      // Family filter
      if (selectedFamilies.size > 0 && !selectedFamilies.has(word.familiaEtim)) {
        return false;
      }

      // Creator filter
      if (selectedCreators.size > 0 && !selectedCreators.has(word.tipoCreador)) {
        return false;
      }

      // Time range filter
      if (timeRange[0] && word.timestamp < timeRange[0]) return false;
      if (timeRange[1] && word.timestamp > timeRange[1]) return false;

      // Search filter
      if (debouncedSearchTerm && !word.texto.toLowerCase().includes(debouncedSearchTerm.toLowerCase())) {
        return false;
      }

      return true;
    });

    // Sample data if too large to prevent performance issues
    if (filtered.length > 1000) {
      // Sort by frequency and take top items plus random sample
      filtered.sort((a, b) => b.frecuencia - a.frecuencia);
      const topItems = filtered.slice(0, 500);
      const remaining = filtered.slice(500);
      const sampleSize = Math.min(500, remaining.length);
      const sampledRemaining = [];

      for (let i = 0; i < sampleSize; i++) {
        const randomIndex = Math.floor(Math.random() * remaining.length);
        sampledRemaining.push(remaining.splice(randomIndex, 1)[0]);
      }

      filtered = [...topItems, ...sampledRemaining];
    }

    return filtered;
  }, [data, selectedFamilies, selectedCreators, timeRange, debouncedSearchTerm]);

  // Optimized visualization update with requestAnimationFrame
  const updateVisualization = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    animationFrameRef.current = requestAnimationFrame(() => {
      if (!svgRef.current || filteredData.length === 0) return;

      const svg = d3.select(svgRef.current);

      // Use efficient clearing instead of selectAll("*").remove()
      svg.selectAll("g").remove();

      const margin = { top: 20, right: 30, bottom: 60, left: 60 };
      const width = 800 - margin.left - margin.right;
      const height = 600 - margin.top - margin.bottom;

      const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

      // Batch DOM operations
      const fragment = document.createDocumentFragment();

      // Create scales based on X-axis mode
      let xScale;
      if (xAxisMode === 'tiempo') {
        xScale = d3.scaleTime()
          .domain(d3.extent(filteredData, d => d.timestamp))
          .range([0, width]);
      } else if (xAxisMode === 'creador') {
        xScale = d3.scaleBand()
          .domain(CREATOR_CATEGORIES)
          .range([0, width])
          .padding(0.1);
      } else if (xAxisMode === 'metricas') {
        xScale = d3.scaleLinear()
          .domain([0, d3.max(filteredData, d => d.metricas.valorEngagement)])
          .range([0, width]);
      }

      const yScale = d3.scaleLinear()
        .domain(d3.extent(filteredData, d => d.valorAfectivo))
        .range([height, 0]);

      const colorScale = d3.scaleOrdinal()
        .domain([...new Set(filteredData.map(d => d.familiaEtim))])
        .range(COLOR_SCHEME);

      const sizeScale = d3.scaleSqrt()
        .domain([0, d3.max(filteredData, d => d.frecuencia)])
        .range([3, 15]);

      // Add axes with minimal DOM operations
      const xAxis = g.append("g")
        .attr("transform", `translate(0,${height})`);

      const yAxis = g.append("g");

      // Defer axis rendering to next frame to split work
      setTimeout(() => {
        xAxis.call(d3.axisBottom(xScale));
        yAxis.call(d3.axisLeft(yScale));

        // Add axis labels
        xAxis.append("text")
          .attr("x", width / 2)
          .attr("y", 40)
          .attr("fill", "black")
          .style("text-anchor", "middle")
          .text(getXAxisLabel());

        yAxis.append("text")
          .attr("transform", "rotate(-90)")
          .attr("y", -40)
          .attr("x", -height / 2)
          .attr("fill", "black")
          .style("text-anchor", "middle")
          .text("Valor Afectivo");
      }, 0);

      // Use efficient data binding with enter/update/exit pattern
      const circles = g.selectAll(".word-circle")
        .data(filteredData, d => d.id);

      // Remove old elements
      circles.exit().remove();

      // Add new elements
      const circlesEnter = circles.enter()
        .append("circle")
        .attr("class", "word-circle")
        .style("cursor", "pointer")
        .attr("opacity", 0);

      // Merge enter and update selections
      const circlesMerged = circlesEnter.merge(circles);

      // Batch attribute updates
      circlesMerged
        .attr("cx", d => {
          if (xAxisMode === 'tiempo') return xScale(d.timestamp);
          if (xAxisMode === 'creador') return xScale(d.tipoCreador) + xScale.bandwidth() / 2;
          if (xAxisMode === 'metricas') return xScale(d.metricas.valorEngagement);
        })
        .attr("cy", d => yScale(d.valorAfectivo))
        .attr("r", d => sizeScale(d.frecuencia))
        .attr("fill", d => colorScale(d.familiaEtim))
        .attr("stroke", "#fff")
        .attr("stroke-width", 1)
        .transition()
        .duration(300)
        .attr("opacity", 0.7);

      // Add event listeners only to new elements
      circlesEnter
        .on("mouseover", handleMouseOver)
        .on("mouseout", handleMouseOut)
        .on("click", handleWordClick);

      // Add legend with minimal DOM operations
      setTimeout(() => {
        addLegend(g, colorScale, width);
      }, 100);
    });
  }, [filteredData, xAxisMode]);

  // Update visualization when filtered data or axis mode changes
  useEffect(() => {
    if (filteredData.length > 0) {
      updateVisualization();
    }
  }, [filteredData, xAxisMode, updateVisualization]);

  // Cleanup animation frame on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const loadWordData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/data/summary`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();

      // Generate mock word data based on your data structure
      const mockWordData = generateMockWordData(data);
      setData(mockWordData);

      // Initialize selected families and creators
      const families = [...new Set(mockWordData.map(d => d.familiaEtim))];
      const creators = [...new Set(mockWordData.map(d => d.tipoCreador))];
      setSelectedFamilies(new Set(families));
      setSelectedCreators(new Set(creators));

    } catch (err) {
      console.error('Error loading word data:', err);
      setError('Error al cargar los datos de palabras');
    } finally {
      setIsLoading(false);
    }
  };

  const generateMockWordData = (summaryData) => {
    // Generate realistic mock data based on your specifications
    const words = [];
    const families = ['política', 'justicia', 'diversidad', 'derechos', 'social', 'juventud'];
    const sentiments = [-1, -0.5, 0, 0.5, 1];

    for (let i = 0; i < 500; i++) {
      const timestamp = new Date(2023, Math.floor(Math.random() * 12), Math.floor(Math.random() * 28));
      const word = {
        id: i,
        texto: `palabra_${i}`,
        timestamp: timestamp,
        frecuencia: Math.floor(Math.random() * 100) + 1,
        metricas: {
          likes: Math.floor(Math.random() * 10000),
          comentarios: Math.floor(Math.random() * 1000),
          compartidos: Math.floor(Math.random() * 500),
          valorEngagement: Math.random() * 100
        },
        familiaEtim: families[Math.floor(Math.random() * families.length)],
        tipoCreador: CREATOR_CATEGORIES[Math.floor(Math.random() * CREATOR_CATEGORIES.length)],
        valorAfectivo: sentiments[Math.floor(Math.random() * sentiments.length)]
      };
      words.push(word);
    }

    return words;
  };

  const getXAxisLabel = () => {
    switch (xAxisMode) {
      case 'tiempo': return 'Tiempo';
      case 'creador': return 'Tipo de Creador';
      case 'metricas': return 'Engagement';
      default: return 'Eje X';
    }
  };

  const addLegend = (g, colorScale, width) => {
    const legend = g.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(${width - 150}, 20)`);

    const legendItems = legend.selectAll(".legend-item")
      .data(colorScale.domain())
      .enter()
      .append("g")
      .attr("class", "legend-item")
      .attr("transform", (d, i) => `translate(0, ${i * 20})`);

    legendItems.append("circle")
      .attr("r", 6)
      .attr("fill", d => colorScale(d));

    legendItems.append("text")
      .attr("x", 12)
      .attr("y", 4)
      .text(d => d)
      .style("font-size", "12px");
  };

  const handleMouseOver = (event, d) => {
    const [x, y] = d3.pointer(event, containerRef.current);
    setTooltip({
      visible: true,
      x: x + 10,
      y: y - 10,
      data: d
    });
  };

  const handleMouseOut = () => {
    setTooltip({ visible: false, x: 0, y: 0, data: null });
  };

  const handleWordClick = (event, d) => {
    const newSelected = new Set(selectedWords);
    if (newSelected.has(d.id)) {
      newSelected.delete(d.id);
    } else {
      newSelected.add(d.id);
    }
    setSelectedWords(newSelected);
  };

  const toggleFamily = (family) => {
    const newSelected = new Set(selectedFamilies);
    if (newSelected.has(family)) {
      newSelected.delete(family);
    } else {
      newSelected.add(family);
    }
    setSelectedFamilies(newSelected);
  };

  const toggleCreator = (creator) => {
    const newSelected = new Set(selectedCreators);
    if (newSelected.has(creator)) {
      newSelected.delete(creator);
    } else {
      newSelected.add(creator);
    }
    setSelectedCreators(newSelected);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50">
        <FaSpinner className="text-indigo-600 text-4xl animate-spin mb-4" />
        <p className="text-gray-600">Cargando análisis de palabras...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50">
        <FaExclamationTriangle className="text-red-500 text-4xl mb-4" />
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Error</h2>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={loadWordData}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          <FaRedo className="inline mr-2" />
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 h-full bg-gray-50">
      <div className="max-w-7xl mx-auto h-full flex flex-col">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">
            Análisis de Palabras en TikTok
          </h1>
          <p className="text-gray-600">
            Visualización de palabras individuales con clasificación de creadores y familias etimológicas
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* X-Axis Mode Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Modo del Eje X
              </label>
              <select
                value={xAxisMode}
                onChange={(e) => setXAxisMode(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="tiempo">Línea de Tiempo</option>
                <option value="creador">Clasificación de Creadores</option>
                <option value="metricas">Métricas de Engagement</option>
              </select>
            </div>

            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Buscar Palabra
              </label>
              <div className="relative">
                <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Buscar..."
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* Stats */}
            <div className="lg:col-span-2">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-indigo-50 p-3 rounded-lg">
                  <div className="text-sm text-indigo-600">Palabras Mostradas</div>
                  <div className="text-xl font-bold text-indigo-800">{filteredData.length}</div>
                </div>
                <div className="bg-purple-50 p-3 rounded-lg">
                  <div className="text-sm text-purple-600">Familias Activas</div>
                  <div className="text-xl font-bold text-purple-800">{selectedFamilies.size}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Family Filters */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Familias Etimológicas
            </label>
            <div className="flex flex-wrap gap-2">
              {[...new Set(data.map(d => d.familiaEtim))].map(family => (
                <button
                  key={family}
                  onClick={() => toggleFamily(family)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedFamilies.has(family)
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {selectedFamilies.has(family) ? <FaEye className="inline mr-1" /> : <FaEyeSlash className="inline mr-1" />}
                  {family}
                </button>
              ))}
            </div>
          </div>

          {/* Creator Filters */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tipos de Creadores
            </label>
            <div className="flex flex-wrap gap-2">
              {CREATOR_CATEGORIES.map(creator => (
                <button
                  key={creator}
                  onClick={() => toggleCreator(creator)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedCreators.has(creator)
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {selectedCreators.has(creator) ? <FaEye className="inline mr-1" /> : <FaEyeSlash className="inline mr-1" />}
                  {creator}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Visualization */}
        <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div ref={containerRef} className="relative w-full h-full">
            <svg
              ref={svgRef}
              width="100%"
              height="600"
              className="w-full"
            />

            {/* Tooltip */}
            {tooltip.visible && tooltip.data && (
              <div
                className="absolute bg-gray-800 text-white p-3 rounded-lg shadow-lg pointer-events-none z-10"
                style={{ left: tooltip.x, top: tooltip.y }}
              >
                <div className="font-semibold">{tooltip.data.texto}</div>
                <div className="text-sm">Familia: {tooltip.data.familiaEtim}</div>
                <div className="text-sm">Creador: {tooltip.data.tipoCreador}</div>
                <div className="text-sm">Frecuencia: {tooltip.data.frecuencia}</div>
                <div className="text-sm">Valor Afectivo: {tooltip.data.valorAfectivo}</div>
                <div className="text-sm">Engagement: {tooltip.data.metricas.valorEngagement.toFixed(2)}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WordAnalysisViz;