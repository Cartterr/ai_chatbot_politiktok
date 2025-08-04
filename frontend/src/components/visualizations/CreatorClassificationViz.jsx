import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  FaSpinner,
  FaExclamationTriangle,
  FaUsers,
  FaChartPie,
  FaChartBar,
  FaFilter,
  FaSearch,
  FaDownload,
  FaRedo,
  FaEye,
  FaEyeSlash,
  FaSortAmountDown,
  FaSortAmountUp
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

const CreatorClassificationViz = () => {
  // State management
  const [data, setData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Visualization controls
  const [viewType, setViewType] = useState('overview'); // 'overview', 'detailed', 'comparison'
  const [chartType, setChartType] = useState('pie'); // 'pie', 'bar', 'treemap', 'sunburst'
  const [metricType, setMetricType] = useState('count'); // 'count', 'engagement', 'followers', 'videos'
  const [sortBy, setSortBy] = useState('count');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategories, setSelectedCategories] = useState(new Set());
  const [minThreshold, setMinThreshold] = useState(0);
  
  // Visualization state
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, data: null });
  const [selectedCreator, setSelectedCreator] = useState(null);
  const [hoveredSegment, setHoveredSegment] = useState(null);
  
  // Refs
  const svgRef = useRef();
  const containerRef = useRef();
  const animationFrameRef = useRef();

  // Debounce search and threshold to prevent excessive filtering
  const debouncedSearchTerm = useDebounce(searchTerm, 300);
  const debouncedThreshold = useDebounce(minThreshold, 200);

  // Constants
  const CREATOR_CATEGORIES = [
    { id: 'izquierda', label: 'Izquierda', color: '#ef4444' },
    { id: 'derecha', label: 'Derecha', color: '#3b82f6' },
    { id: 'LGBTQIA+', label: 'LGBTQIA+', color: '#8b5cf6' },
    { id: 'feminista', label: 'Feminista', color: '#ec4899' },
    { id: 'discapacidad', label: 'Discapacidad', color: '#10b981' },
    { id: 'derechos-indigenas', label: 'Derechos Indígenas', color: '#f59e0b' },
    { id: 'otros', label: 'Otros', color: '#6b7280' }
  ];

  const METRICS = {
    count: { label: 'Número de Creadores', format: d => d },
    engagement: { label: 'Engagement Promedio', format: d => d.toFixed(2) },
    followers: { label: 'Seguidores Promedio', format: d => d.toLocaleString() },
    videos: { label: 'Videos Totales', format: d => d.toLocaleString() }
  };

  // Load data on component mount
  useEffect(() => {
    loadCreatorData();
  }, []);

  // Memoized filtered and sorted data
  const filteredAndSortedData = useMemo(() => {
    let filtered = data.filter(d => {
      // Category filter
      if (selectedCategories.size > 0 && !selectedCategories.has(d.id)) {
        return false;
      }
      
      // Search filter
      if (debouncedSearchTerm && !d.label.toLowerCase().includes(debouncedSearchTerm.toLowerCase())) {
        return false;
      }
      
      // Threshold filter
      if (d[metricType] < debouncedThreshold) {
        return false;
      }
      
      return true;
    });

    // Sort data
    filtered.sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      const multiplier = sortOrder === 'asc' ? 1 : -1;
      return (aVal - bVal) * multiplier;
    });

    return filtered;
  }, [data, selectedCategories, debouncedSearchTerm, debouncedThreshold, metricType, sortBy, sortOrder]);

  // Optimized visualization update with requestAnimationFrame
  const updateVisualization = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    animationFrameRef.current = requestAnimationFrame(() => {
      if (!svgRef.current || filteredAndSortedData.length === 0) return;

      const svg = d3.select(svgRef.current);
      
      // Efficient clearing
      svg.selectAll("g").remove();

      // Defer rendering based on chart type to split work
      setTimeout(() => {
        switch (chartType) {
          case 'pie':
            renderPieChart(svg, filteredAndSortedData);
            break;
          case 'bar':
            renderBarChart(svg, filteredAndSortedData);
            break;
          case 'treemap':
            renderTreemap(svg, filteredAndSortedData);
            break;
          case 'sunburst':
            renderSunburst(svg, filteredAndSortedData);
            break;
          default:
            renderPieChart(svg, filteredAndSortedData);
        }
      }, 0);
    });
  }, [filteredAndSortedData, chartType, metricType]);

  // Update visualization when data or controls change
  useEffect(() => {
    if (filteredAndSortedData.length > 0) {
      updateVisualization();
    }
  }, [filteredAndSortedData, viewType, chartType, updateVisualization]);

  // Cleanup animation frame on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const loadCreatorData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/data/summary`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      
      // Generate creator classification data
      const creatorData = generateCreatorData(data);
      setData(creatorData);
      
      // Initialize selected categories
      setSelectedCategories(new Set(CREATOR_CATEGORIES.map(c => c.id)));
      
    } catch (err) {
      console.error('Error loading creator data:', err);
      setError('Error al cargar los datos de clasificación de creadores');
    } finally {
      setIsLoading(false);
    }
  };

  const generateCreatorData = (summaryData) => {
    return CREATOR_CATEGORIES.map(category => {
      const baseCount = Math.floor(Math.random() * 50) + 10;
      const baseEngagement = Math.random() * 100;
      const baseFollowers = Math.floor(Math.random() * 100000) + 1000;
      const baseVideos = Math.floor(Math.random() * 500) + 50;
      
      return {
        id: category.id,
        label: category.label,
        color: category.color,
        count: baseCount,
        engagement: baseEngagement,
        followers: baseFollowers,
        videos: baseVideos,
        avgViews: Math.floor(Math.random() * 50000) + 5000,
        avgLikes: Math.floor(Math.random() * 5000) + 500,
        avgComments: Math.floor(Math.random() * 500) + 50,
        avgShares: Math.floor(Math.random() * 200) + 20,
        topWords: generateTopWords(),
        sentiment: (Math.random() - 0.5) * 2, // -1 to 1
        growthRate: (Math.random() - 0.5) * 0.4, // -20% to +20%
        activeHours: generateActiveHours(),
        demographics: generateDemographics()
      };
    });
  };

  const generateTopWords = () => {
    const words = ['política', 'justicia', 'diversidad', 'derechos', 'social', 'juventud', 'cambio', 'futuro'];
    return words.slice(0, Math.floor(Math.random() * 5) + 3).map(word => ({
      word,
      frequency: Math.floor(Math.random() * 100) + 10
    }));
  };

  const generateActiveHours = () => {
    return Array.from({ length: 24 }, (_, i) => ({
      hour: i,
      activity: Math.random() * 100
    }));
  };

  const generateDemographics = () => {
    return {
      ageGroups: [
        { range: '13-17', percentage: Math.random() * 30 },
        { range: '18-24', percentage: Math.random() * 40 },
        { range: '25-34', percentage: Math.random() * 20 },
        { range: '35+', percentage: Math.random() * 10 }
      ],
      gender: {
        male: Math.random() * 60,
        female: Math.random() * 60,
        other: Math.random() * 10
      }
    };
  };

  const renderPieChart = (svg, chartData) => {
    const width = 600;
    const height = 400;
    const radius = Math.min(width, height) / 2 - 40;

    const g = svg.append("g")
      .attr("transform", `translate(${width / 2},${height / 2})`);

    const pie = d3.pie()
      .value(d => d[metricType])
      .sort(null);

    const arc = d3.arc()
      .innerRadius(0)
      .outerRadius(radius);

    const arcs = g.selectAll(".arc")
      .data(pie(chartData))
      .enter()
      .append("g")
      .attr("class", "arc");

    // Batch path creation
    arcs.append("path")
      .attr("d", arc)
      .attr("fill", d => d.data.color)
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .attr("opacity", 0)
      .transition()
      .duration(300)
      .attr("opacity", 1)
      .on("end", function(d, i) {
        // Add event listeners after animation
        if (i === 0) {
          arcs.selectAll("path")
            .on("mouseover", handleMouseOver)
            .on("mouseout", handleMouseOut)
            .on("click", handleSegmentClick);
        }
      });

    // Defer label rendering
    setTimeout(() => {
      // Add labels
      arcs.append("text")
        .attr("transform", d => `translate(${arc.centroid(d)})`)
        .attr("text-anchor", "middle")
        .style("font-size", "12px")
        .style("font-weight", "bold")
        .text(d => d.data.label)
        .attr("opacity", 0)
        .transition()
        .duration(300)
        .attr("opacity", 1);

      // Add percentage labels
      arcs.append("text")
        .attr("transform", d => {
          const centroid = arc.centroid(d);
          return `translate(${centroid[0]}, ${centroid[1] + 15})`;
        })
        .attr("text-anchor", "middle")
        .style("font-size", "10px")
        .text(d => {
          const total = d3.sum(chartData, item => item[metricType]);
          const percentage = ((d.data[metricType] / total) * 100).toFixed(1);
          return `${percentage}%`;
        })
        .attr("opacity", 0)
        .transition()
        .duration(300)
        .attr("opacity", 1);
    }, 100);
  };

  const renderBarChart = (svg, chartData) => {
    const margin = { top: 20, right: 30, bottom: 60, left: 80 };
    const width = 600 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const xScale = d3.scaleBand()
      .domain(chartData.map(d => d.label))
      .range([0, width])
      .padding(0.1);

    const yScale = d3.scaleLinear()
      .domain([0, d3.max(chartData, d => d[metricType])])
      .range([height, 0]);

    // Defer axis rendering
    setTimeout(() => {
      // Add axes
      g.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(xScale))
        .selectAll("text")
        .style("text-anchor", "end")
        .attr("dx", "-.8em")
        .attr("dy", ".15em")
        .attr("transform", "rotate(-45)");

      g.append("g")
        .call(d3.axisLeft(yScale));
    }, 0);

    // Add bars with animation
    const bars = g.selectAll(".bar")
      .data(chartData)
      .enter()
      .append("rect")
      .attr("class", "bar")
      .attr("x", d => xScale(d.label))
      .attr("width", xScale.bandwidth())
      .attr("y", height)
      .attr("height", 0)
      .attr("fill", d => d.color)
      .style("cursor", "pointer");

    // Animate bars
    bars.transition()
      .duration(500)
      .attr("y", d => yScale(d[metricType]))
      .attr("height", d => height - yScale(d[metricType]))
      .on("end", function(d, i) {
        // Add event listeners after animation
        if (i === 0) {
          bars
            .on("mouseover", handleMouseOver)
            .on("mouseout", handleMouseOut)
            .on("click", handleSegmentClick);
        }
      });

    // Defer value labels
    setTimeout(() => {
      g.selectAll(".label")
        .data(chartData)
        .enter()
        .append("text")
        .attr("class", "label")
        .attr("x", d => xScale(d.label) + xScale.bandwidth() / 2)
        .attr("y", d => yScale(d[metricType]) - 5)
        .attr("text-anchor", "middle")
        .style("font-size", "12px")
        .style("font-weight", "bold")
        .text(d => METRICS[metricType].format(d[metricType]))
        .attr("opacity", 0)
        .transition()
        .duration(300)
        .attr("opacity", 1);
    }, 200);
  };

  const renderTreemap = (svg, chartData) => {
    const width = 600;
    const height = 400;

    const root = d3.hierarchy({ children: chartData })
      .sum(d => d[metricType])
      .sort((a, b) => b.value - a.value);

    d3.treemap()
      .size([width, height])
      .padding(2)(root);

    const g = svg.append("g");

    const leaf = g.selectAll("g")
      .data(root.leaves())
      .enter()
      .append("g")
      .attr("transform", d => `translate(${d.x0},${d.y0})`);

    leaf.append("rect")
      .attr("width", d => d.x1 - d.x0)
      .attr("height", d => d.y1 - d.y0)
      .attr("fill", d => d.data.color)
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .on("mouseover", handleMouseOver)
      .on("mouseout", handleMouseOut)
      .on("click", handleSegmentClick);

    leaf.append("text")
      .attr("x", 4)
      .attr("y", 14)
      .style("font-size", "12px")
      .style("font-weight", "bold")
      .text(d => d.data.label);

    leaf.append("text")
      .attr("x", 4)
      .attr("y", 28)
      .style("font-size", "10px")
      .text(d => METRICS[metricType].format(d.data[metricType]));
  };

  const renderSunburst = (svg, chartData) => {
    const width = 600;
    const height = 400;
    const radius = Math.min(width, height) / 2 - 40;

    const g = svg.append("g")
      .attr("transform", `translate(${width / 2},${height / 2})`);

    // Create hierarchical data structure
    const root = d3.hierarchy({
      children: chartData.map(d => ({
        ...d,
        children: d.topWords.map(w => ({ ...w, parent: d }))
      }))
    })
    .sum(d => d[metricType] || d.frequency || 1);

    const partition = d3.partition()
      .size([2 * Math.PI, radius]);

    partition(root);

    const arc = d3.arc()
      .startAngle(d => d.x0)
      .endAngle(d => d.x1)
      .innerRadius(d => d.y0)
      .outerRadius(d => d.y1);

    g.selectAll("path")
      .data(root.descendants())
      .enter()
      .append("path")
      .attr("d", arc)
      .attr("fill", d => d.data.color || d.parent?.data.color || "#ccc")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1)
      .style("cursor", "pointer")
      .on("mouseover", handleMouseOver)
      .on("mouseout", handleMouseOut)
      .on("click", handleSegmentClick);
  };

  const handleMouseOver = (event, d) => {
    const [x, y] = d3.pointer(event, containerRef.current);
    setTooltip({
      visible: true,
      x: x + 10,
      y: y - 10,
      data: d.data || d
    });
    setHoveredSegment(d.data || d);
  };

  const handleMouseOut = () => {
    setTooltip({ visible: false, x: 0, y: 0, data: null });
    setHoveredSegment(null);
  };

  const handleSegmentClick = (event, d) => {
    setSelectedCreator(d.data || d);
  };

  const toggleCategory = (categoryId) => {
    const newSelected = new Set(selectedCategories);
    if (newSelected.has(categoryId)) {
      newSelected.delete(categoryId);
    } else {
      newSelected.add(categoryId);
    }
    setSelectedCategories(newSelected);
  };

  const toggleSortOrder = () => {
    setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50">
        <FaSpinner className="text-indigo-600 text-4xl animate-spin mb-4" />
        <p className="text-gray-600">Cargando clasificación de creadores...</p>
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
          onClick={loadCreatorData}
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
            Clasificación de Creadores TikTok
          </h1>
          <p className="text-gray-600">
            Análisis detallado de diferentes tipos de creadores y sus características
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-6 gap-4">
            {/* Chart Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tipo de Gráfico
              </label>
              <select
                value={chartType}
                onChange={(e) => setChartType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="pie">Gráfico Circular</option>
                <option value="bar">Gráfico de Barras</option>
                <option value="treemap">Mapa de Árbol</option>
                <option value="sunburst">Sunburst</option>
              </select>
            </div>

            {/* Metric Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Métrica
              </label>
              <select
                value={metricType}
                onChange={(e) => setMetricType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {Object.entries(METRICS).map(([key, metric]) => (
                  <option key={key} value={key}>{metric.label}</option>
                ))}
              </select>
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ordenar Por
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {Object.entries(METRICS).map(([key, metric]) => (
                  <option key={key} value={key}>{metric.label}</option>
                ))}
              </select>
            </div>

            {/* Sort Order */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Orden
              </label>
              <button
                onClick={toggleSortOrder}
                className="w-full flex items-center justify-center px-3 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                {sortOrder === 'desc' ? <FaSortAmountDown className="mr-2" /> : <FaSortAmountUp className="mr-2" />}
                {sortOrder === 'desc' ? 'Descendente' : 'Ascendente'}
              </button>
            </div>

            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Buscar
              </label>
              <div className="relative">
                <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Buscar categoría..."
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* Threshold */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Umbral Mínimo: {minThreshold}
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={minThreshold}
                onChange={(e) => setMinThreshold(parseInt(e.target.value))}
                className="w-full"
              />
            </div>
          </div>

          {/* Category Filters */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Categorías de Creadores
            </label>
            <div className="flex flex-wrap gap-2">
              {CREATOR_CATEGORIES.map(category => (
                <button
                  key={category.id}
                  onClick={() => toggleCategory(category.id)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedCategories.has(category.id)
                      ? 'text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                  style={{
                    backgroundColor: selectedCategories.has(category.id) ? category.color : undefined
                  }}
                >
                  {selectedCategories.has(category.id) ? <FaEye className="inline mr-1" /> : <FaEyeSlash className="inline mr-1" />}
                  {category.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1 flex gap-6">
          {/* Main Visualization */}
          <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div ref={containerRef} className="relative w-full h-full">
              <svg
                ref={svgRef}
                width="100%"
                height="450"
                className="w-full"
              />
              
              {/* Tooltip */}
              {tooltip.visible && tooltip.data && (
                <div
                  className="absolute bg-gray-800 text-white p-3 rounded-lg shadow-lg pointer-events-none z-10"
                  style={{ left: tooltip.x, top: tooltip.y }}
                >
                  <div className="font-semibold">{tooltip.data.label}</div>
                  <div className="text-sm">{METRICS[metricType].label}: {METRICS[metricType].format(tooltip.data[metricType])}</div>
                  <div className="text-sm">Engagement: {tooltip.data.engagement?.toFixed(2)}</div>
                  <div className="text-sm">Seguidores: {tooltip.data.followers?.toLocaleString()}</div>
                </div>
              )}
            </div>
          </div>

          {/* Details Panel */}
          {selectedCreator && (
            <div className="w-80 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-800 mb-4">Detalles del Creador</h3>
              
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Información General</h4>
                  <div className="space-y-1 text-sm">
                    <div>Categoría: <span className="font-medium">{selectedCreator.label}</span></div>
                    <div>Creadores: <span className="font-medium">{selectedCreator.count}</span></div>
                    <div>Videos: <span className="font-medium">{selectedCreator.videos.toLocaleString()}</span></div>
                    <div>Engagement: <span className="font-medium">{selectedCreator.engagement.toFixed(2)}</span></div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Métricas Promedio</h4>
                  <div className="space-y-1 text-sm">
                    <div>Vistas: <span className="font-medium">{selectedCreator.avgViews.toLocaleString()}</span></div>
                    <div>Likes: <span className="font-medium">{selectedCreator.avgLikes.toLocaleString()}</span></div>
                    <div>Comentarios: <span className="font-medium">{selectedCreator.avgComments.toLocaleString()}</span></div>
                    <div>Compartidos: <span className="font-medium">{selectedCreator.avgShares.toLocaleString()}</span></div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Palabras Más Usadas</h4>
                  <div className="space-y-1">
                    {selectedCreator.topWords.slice(0, 5).map((word, index) => (
                      <div key={index} className="flex justify-between text-sm">
                        <span>{word.word}</span>
                        <span className="font-medium">{word.frequency}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Análisis</h4>
                  <div className="space-y-1 text-sm">
                    <div>Sentimiento: <span className={`font-medium ${selectedCreator.sentiment > 0 ? 'text-green-600' : selectedCreator.sentiment < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                      {selectedCreator.sentiment > 0 ? 'Positivo' : selectedCreator.sentiment < 0 ? 'Negativo' : 'Neutral'} ({selectedCreator.sentiment.toFixed(2)})
                    </span></div>
                    <div>Crecimiento: <span className={`font-medium ${selectedCreator.growthRate > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {(selectedCreator.growthRate * 100).toFixed(1)}%
                    </span></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CreatorClassificationViz; 