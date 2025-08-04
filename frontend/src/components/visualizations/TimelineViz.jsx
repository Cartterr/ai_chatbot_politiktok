import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  FaSpinner,
  FaExclamationTriangle,
  FaClock,
  FaPlay,
  FaPause,
  FaStepForward,
  FaStepBackward,
  FaCalendarAlt,
  FaChartLine,
  FaFilter,
  FaDownload,
  FaRedo,
  FaExpand
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

const TimelineViz = () => {
  // State management
  const [data, setData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Timeline controls
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date('2023-01-01'));
  const [timeRange, setTimeRange] = useState([new Date('2023-01-01'), new Date('2023-12-31')]);
  const [playbackSpeed, setPlaybackSpeed] = useState(1000); // milliseconds
  const [viewMode, setViewMode] = useState('daily'); // 'daily', 'weekly', 'monthly'
  
  // Visualization controls
  const [metricType, setMetricType] = useState('videos'); // 'videos', 'engagement', 'sentiment'
  const [creatorFilter, setCreatorFilter] = useState('all');
  const [aggregationLevel, setAggregationLevel] = useState('count'); // 'count', 'average', 'sum'
  
  // Visualization state
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, data: null });
  const [selectedPeriod, setSelectedPeriod] = useState(null);
  const [animationFrame, setAnimationFrame] = useState(null);
  
  // Refs
  const svgRef = useRef();
  const containerRef = useRef();
  const intervalRef = useRef();
  const animationFrameRef = useRef();

  // Debounce current time updates to prevent excessive re-renders
  const debouncedCurrentTime = useDebounce(currentTime, 100);

  // Constants
  const CREATOR_CATEGORIES = [
    'izquierda', 'derecha', 'LGBTQIA+', 'feminista', 
    'discapacidad', 'derechos-indigenas', 'otros'
  ];

  const COLORS = {
    videos: '#3b82f6',
    engagement: '#10b981',
    sentiment: '#f59e0b',
    positive: '#10b981',
    neutral: '#6b7280',
    negative: '#ef4444'
  };

  // Load data on component mount
  useEffect(() => {
    loadTimelineData();
  }, []);

  // Helper function to aggregate data - moved above useMemo
  const aggregateData = (data, timeUnit) => {
    const grouped = d3.group(data, d => {
      const date = d.date;
      switch (timeUnit) {
        case 'daily':
          return d3.timeDay.floor(date);
        case 'weekly':
          return d3.timeWeek.floor(date);
        case 'monthly':
          return d3.timeMonth.floor(date);
        default:
          return d3.timeDay.floor(date);
      }
    });

    const aggregated = [];
    grouped.forEach((values, key) => {
      const creatorGroups = d3.group(values, d => d.creator);
      
      creatorGroups.forEach((creatorValues, creator) => {
        let aggregatedValue;
        switch (aggregationLevel) {
          case 'count':
            aggregatedValue = creatorValues.length;
            break;
          case 'average':
            aggregatedValue = d3.mean(creatorValues, d => d[metricType]);
            break;
          case 'sum':
            aggregatedValue = d3.sum(creatorValues, d => d[metricType]);
            break;
          default:
            aggregatedValue = creatorValues.length;
        }

        aggregated.push({
          date: key,
          creator: creator,
          value: aggregatedValue,
          originalData: creatorValues
        });
      });
    });

    return aggregated;
  };

  // Memoized filtered and aggregated data
  const processedData = useMemo(() => {
    // Filter data
    let filteredData = data;
    if (creatorFilter !== 'all') {
      filteredData = data.filter(d => d.creator === creatorFilter);
    }

    // Aggregate data
    let aggregated = aggregateData(filteredData, viewMode);
    
    // Sample data if too large to prevent performance issues
    if (aggregated.length > 500) {
      // Sort by value and keep most important data points
      aggregated.sort((a, b) => b.value - a.value);
      const importantData = aggregated.slice(0, 250);
      const remaining = aggregated.slice(250);
      const sampleSize = Math.min(250, remaining.length);
      const sampledData = [];
      
      for (let i = 0; i < sampleSize; i++) {
        const randomIndex = Math.floor(Math.random() * remaining.length);
        sampledData.push(remaining.splice(randomIndex, 1)[0]);
      }
      
      aggregated = [...importantData, ...sampledData];
      // Re-sort by date for proper line drawing
      aggregated.sort((a, b) => a.date - b.date);
    }
    
    return aggregated;
  }, [data, creatorFilter, viewMode, aggregationLevel, metricType]);

  // Optimized visualization update with requestAnimationFrame
  const updateVisualization = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    animationFrameRef.current = requestAnimationFrame(() => {
      if (!svgRef.current || processedData.length === 0) return;

      const svg = d3.select(svgRef.current);
      
      // Efficient clearing
      svg.selectAll("g").remove();

      const margin = { top: 20, right: 120, bottom: 60, left: 60 };
      const width = 800 - margin.left - margin.right;
      const height = 400 - margin.top - margin.bottom;

      const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

      // Create scales
      const xScale = d3.scaleTime()
        .domain(timeRange)
        .range([0, width]);

      const yScale = d3.scaleLinear()
        .domain([0, d3.max(processedData, d => d.value)])
        .range([height, 0]);

      const colorScale = d3.scaleOrdinal()
        .domain(CREATOR_CATEGORIES)
        .range(d3.schemeCategory10);

      // Add axes with deferred rendering
      const xAxisGroup = g.append("g")
        .attr("transform", `translate(0,${height})`);
      
      const yAxisGroup = g.append("g");

      // Defer axis rendering to next frame
      setTimeout(() => {
        xAxisGroup.call(d3.axisBottom(xScale).tickFormat(d3.timeFormat("%b %Y")));
        yAxisGroup.call(d3.axisLeft(yScale));
        
        // Add axis labels
        yAxisGroup.append("text")
          .attr("transform", "rotate(-90)")
          .attr("y", -40)
          .attr("x", -height / 2)
          .attr("fill", "black")
          .style("text-anchor", "middle")
          .text(getYAxisLabel());

        xAxisGroup.append("text")
          .attr("x", width / 2)
          .attr("y", 50)
          .attr("fill", "black")
          .style("text-anchor", "middle")
          .text("Tiempo");
      }, 0);

      // Group data by creator for line drawing
      const creatorData = d3.group(processedData, d => d.creator);

      // Create line generator
      const line = d3.line()
        .x(d => xScale(d.date))
        .y(d => yScale(d.value))
        .curve(d3.curveMonotoneX);

      // Draw lines and dots with batched operations
      const linesGroup = g.append("g").attr("class", "lines");
      const dotsGroup = g.append("g").attr("class", "dots");

      creatorData.forEach((values, creator) => {
        const sortedValues = values.sort((a, b) => a.date - b.date);
        
        // Add line
        linesGroup.append("path")
          .datum(sortedValues)
          .attr("fill", "none")
          .attr("stroke", colorScale(creator))
          .attr("stroke-width", 2)
          .attr("d", line);

        // Add dots with sampling for performance
        const sampledValues = sortedValues.length > 50 
          ? sortedValues.filter((_, i) => i % Math.ceil(sortedValues.length / 50) === 0)
          : sortedValues;

        dotsGroup.selectAll(`.dot-${creator.replace(/[^a-zA-Z0-9]/g, '')}`)
          .data(sampledValues)
          .enter()
          .append("circle")
          .attr("class", `dot-${creator.replace(/[^a-zA-Z0-9]/g, '')}`)
          .attr("cx", d => xScale(d.date))
          .attr("cy", d => yScale(d.value))
          .attr("r", 4)
          .attr("fill", colorScale(creator))
          .style("cursor", "pointer")
          .on("mouseover", handleMouseOver)
          .on("mouseout", handleMouseOut)
          .on("click", handleDotClick);
      });

      // Add current time indicator
      const currentTimeX = xScale(debouncedCurrentTime);
      g.append("line")
        .attr("class", "current-time-line")
        .attr("x1", currentTimeX)
        .attr("x2", currentTimeX)
        .attr("y1", 0)
        .attr("y2", height)
        .attr("stroke", "#ef4444")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "5,5");

      // Add legend with deferred rendering
      setTimeout(() => {
        const legend = g.append("g")
          .attr("class", "legend")
          .attr("transform", `translate(${width + 20}, 20)`);

        const legendItems = legend.selectAll(".legend-item")
          .data(CREATOR_CATEGORIES)
          .enter()
          .append("g")
          .attr("class", "legend-item")
          .attr("transform", (d, i) => `translate(0, ${i * 20})`);

        legendItems.append("line")
          .attr("x1", 0)
          .attr("x2", 15)
          .attr("y1", 0)
          .attr("y2", 0)
          .attr("stroke", d => colorScale(d))
          .attr("stroke-width", 2);

        legendItems.append("text")
          .attr("x", 20)
          .attr("y", 4)
          .text(d => d)
          .style("font-size", "12px");
      }, 100);
    });
  }, [processedData, debouncedCurrentTime, timeRange]);

  // Update visualization when data or controls change
  useEffect(() => {
    if (processedData.length > 0) {
      updateVisualization();
    }
  }, [processedData, metricType, aggregationLevel, debouncedCurrentTime, updateVisualization]);

  // Cleanup animation frame on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  // Handle playback
  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        setCurrentTime(prevTime => {
          const nextTime = new Date(prevTime.getTime() + getTimeIncrement());
          if (nextTime > timeRange[1]) {
            setIsPlaying(false);
            return timeRange[0]; // Reset to start
          }
          return nextTime;
        });
      }, playbackSpeed);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isPlaying, playbackSpeed, timeRange]);

  const getTimeIncrement = () => {
    switch (viewMode) {
      case 'daily': return 24 * 60 * 60 * 1000; // 1 day
      case 'weekly': return 7 * 24 * 60 * 60 * 1000; // 1 week
      case 'monthly': return 30 * 24 * 60 * 60 * 1000; // 1 month
      default: return 24 * 60 * 60 * 1000;
    }
  };

  const loadTimelineData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/data/summary`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      
      // Generate timeline data
      const timelineData = generateTimelineData(data);
      setData(timelineData);
      
      // Set initial time range
      if (timelineData.length > 0) {
        const dates = timelineData.map(d => d.date);
        const minDate = d3.min(dates);
        const maxDate = d3.max(dates);
        setTimeRange([minDate, maxDate]);
        setCurrentTime(minDate);
      }
      
    } catch (err) {
      console.error('Error loading timeline data:', err);
      setError('Error al cargar los datos de línea de tiempo');
    } finally {
      setIsLoading(false);
    }
  };

  const generateTimelineData = (summaryData) => {
    const data = [];
    const startDate = new Date('2023-01-01');
    const endDate = new Date('2023-12-31');
    
    // Generate daily data points
    for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
      const date = new Date(d);
      
      // Generate data for each creator category
      CREATOR_CATEGORIES.forEach(category => {
        const baseValue = Math.random() * 50 + 10;
        const seasonalFactor = Math.sin((date.getMonth() / 12) * 2 * Math.PI) * 0.3 + 1;
        const weeklyFactor = date.getDay() === 0 || date.getDay() === 6 ? 1.2 : 1; // Weekend boost
        
        data.push({
          date: new Date(date),
          creator: category,
          videos: Math.floor(baseValue * seasonalFactor * weeklyFactor),
          engagement: Math.floor((baseValue * 2) * seasonalFactor * weeklyFactor),
          sentiment: (Math.random() - 0.5) * 2, // -1 to 1
          likes: Math.floor(Math.random() * 10000),
          comments: Math.floor(Math.random() * 1000),
          shares: Math.floor(Math.random() * 500),
          views: Math.floor(Math.random() * 100000)
        });
      });
    }
    
    return data;
  };

  const getYAxisLabel = () => {
    const metricLabels = {
      videos: 'Número de Videos',
      engagement: 'Engagement',
      sentiment: 'Sentimiento Promedio'
    };
    return metricLabels[metricType] || 'Valor';
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

  const handleDotClick = (event, d) => {
    setSelectedPeriod(d);
  };

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  const stepForward = () => {
    setCurrentTime(prevTime => {
      const nextTime = new Date(prevTime.getTime() + getTimeIncrement());
      return nextTime <= timeRange[1] ? nextTime : timeRange[1];
    });
  };

  const stepBackward = () => {
    setCurrentTime(prevTime => {
      const prevTimeNew = new Date(prevTime.getTime() - getTimeIncrement());
      return prevTimeNew >= timeRange[0] ? prevTimeNew : timeRange[0];
    });
  };

  const resetTimeline = () => {
    setCurrentTime(timeRange[0]);
    setIsPlaying(false);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50">
        <FaSpinner className="text-indigo-600 text-4xl animate-spin mb-4" />
        <p className="text-gray-600">Cargando línea de tiempo...</p>
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
          onClick={loadTimelineData}
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
            Línea de Tiempo TikTok
          </h1>
          <p className="text-gray-600">
            Análisis temporal de actividad y tendencias en TikTok
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-6 gap-4">
            {/* View Mode */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Vista Temporal
              </label>
              <select
                value={viewMode}
                onChange={(e) => setViewMode(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="daily">Diaria</option>
                <option value="weekly">Semanal</option>
                <option value="monthly">Mensual</option>
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
                <option value="videos">Videos</option>
                <option value="engagement">Engagement</option>
                <option value="sentiment">Sentimiento</option>
              </select>
            </div>

            {/* Creator Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Creador
              </label>
              <select
                value={creatorFilter}
                onChange={(e) => setCreatorFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="all">Todos</option>
                {CREATOR_CATEGORIES.map(category => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
            </div>

            {/* Aggregation */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Agregación
              </label>
              <select
                value={aggregationLevel}
                onChange={(e) => setAggregationLevel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="count">Conteo</option>
                <option value="average">Promedio</option>
                <option value="sum">Suma</option>
              </select>
            </div>

            {/* Playback Speed */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Velocidad (ms)
              </label>
              <input
                type="range"
                min="100"
                max="2000"
                step="100"
                value={playbackSpeed}
                onChange={(e) => setPlaybackSpeed(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="text-xs text-gray-500 text-center">{playbackSpeed}ms</div>
            </div>

            {/* Current Time Display */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tiempo Actual
              </label>
              <div className="bg-gray-50 p-2 rounded-md text-sm text-center">
                {currentTime.toLocaleDateString()}
              </div>
            </div>
          </div>

          {/* Playback Controls */}
          <div className="flex items-center justify-center space-x-4 mt-4">
            <button
              onClick={stepBackward}
              className="p-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              title="Paso Atrás"
            >
              <FaStepBackward />
            </button>
            <button
              onClick={togglePlayback}
              className="p-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              title={isPlaying ? "Pausar" : "Reproducir"}
            >
              {isPlaying ? <FaPause /> : <FaPlay />}
            </button>
            <button
              onClick={stepForward}
              className="p-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              title="Paso Adelante"
            >
              <FaStepForward />
            </button>
            <button
              onClick={resetTimeline}
              className="p-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              title="Reiniciar"
            >
              <FaRedo />
            </button>
          </div>
        </div>

        {/* Selected Period Info */}
        {selectedPeriod && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-blue-800 mb-2">Período Seleccionado</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="font-medium">Fecha:</span> {selectedPeriod.date.toLocaleDateString()}
              </div>
              <div>
                <span className="font-medium">Creador:</span> {selectedPeriod.creator}
              </div>
              <div>
                <span className="font-medium">Valor:</span> {selectedPeriod.value.toFixed(2)}
              </div>
            </div>
          </div>
        )}

        {/* Visualization */}
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
                <div className="font-semibold">{tooltip.data.date.toLocaleDateString()}</div>
                <div className="text-sm">Creador: {tooltip.data.creator}</div>
                <div className="text-sm">Valor: {tooltip.data.value.toFixed(2)}</div>
                <div className="text-sm">Datos originales: {tooltip.data.originalData?.length || 0}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimelineViz; 