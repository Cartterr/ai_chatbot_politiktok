import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  FaSpinner,
  FaExclamationTriangle,
  FaProjectDiagram,
  FaFilter,
  FaSearch,
  FaDownload,
  FaClock,
  FaChartLine,
  FaEye,
  FaEyeSlash,
  FaRedo,
  FaLanguage,
  FaHeart,
  FaBrain,
  FaCalculator
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

const EtymologicalFamiliesViz = () => {
  // State management
  const [data, setData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Visualization controls
  const [xAxisMode, setXAxisMode] = useState('timeline'); // 'timeline', 'metrics'
  const [aggregationMethod, setAggregationMethod] = useState('weighted_average'); // 'sum', 'weighted_average', 'correlation'
  const [sentimentThreshold, setSentimentThreshold] = useState(0.3);
  const [frequencyThreshold, setFrequencyThreshold] = useState(5);
  const [selectedFamilies, setSelectedFamilies] = useState(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [scalingMethod, setScalingMethod] = useState('sqrt'); // 'linear', 'sqrt', 'log'
  const [outlierHandling, setOutlierHandling] = useState('winsorize'); // 'none', 'winsorize', 'log_scale'

  // Visualization state
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, data: null });
  const [selectedFamily, setSelectedFamily] = useState(null);
  const [hoveredBubble, setHoveredBubble] = useState(null);

  // Refs
  const svgRef = useRef();
  const containerRef = useRef();
  const animationFrameRef = useRef();

  // Debounce search term and thresholds
  const debouncedSearchTerm = useDebounce(searchTerm, 300);
  const debouncedSentimentThreshold = useDebounce(sentimentThreshold, 200);
  const debouncedFrequencyThreshold = useDebounce(frequencyThreshold, 200);

  // Constants
  const ETYMOLOGICAL_FAMILIES = [
    { id: 'politica', label: 'Política', color: '#ef4444', description: 'Palabras relacionadas con política y gobierno' },
    { id: 'justicia', label: 'Justicia', color: '#3b82f6', description: 'Términos de justicia y derecho' },
    { id: 'diversidad', label: 'Diversidad', color: '#8b5cf6', description: 'Palabras sobre diversidad e inclusión' },
    { id: 'derechos', label: 'Derechos', color: '#10b981', description: 'Términos de derechos humanos' },
    { id: 'social', label: 'Social', color: '#f59e0b', description: 'Palabras del ámbito social' },
    { id: 'juventud', label: 'Juventud', color: '#ec4899', description: 'Términos relacionados con jóvenes' },
    { id: 'cambio', label: 'Cambio', color: '#06b6d4', description: 'Palabras sobre transformación' },
    { id: 'identidad', label: 'Identidad', color: '#84cc16', description: 'Términos de identidad personal/colectiva' }
  ];

  const SENTIMENT_LEXICON = {
    // Positive words
    'amor': 1, 'paz': 1, 'justicia': 1, 'libertad': 1, 'igualdad': 1, 'respeto': 1,
    'dignidad': 1, 'esperanza': 1, 'futuro': 1, 'progreso': 1, 'unidad': 1, 'solidaridad': 1,
    'inclusión': 1, 'diversidad': 1, 'tolerancia': 1, 'democracia': 1, 'derechos': 1,
    
    // Negative words
    'odio': -1, 'violencia': -1, 'discriminación': -1, 'injusticia': -1, 'opresión': -1,
    'exclusión': -1, 'racismo': -1, 'machismo': -1, 'homofobia': -1, 'xenofobia': -1,
    'corrupción': -1, 'desigualdad': -1, 'pobreza': -1, 'represión': -1, 'censura': -1
  };

  // Load data on component mount
  useEffect(() => {
    loadEtymologicalData();
  }, []);

  // Helper function to handle outliers - moved before useMemo
  const handleOutliers = (data) => {
    if (outlierHandling === 'winsorize') {
      const frequencies = data.map(d => d.totalFrequency).sort((a, b) => a - b);
      const p5 = frequencies[Math.floor(frequencies.length * 0.05)];
      const p95 = frequencies[Math.floor(frequencies.length * 0.95)];
      
      return data.map(d => ({
        ...d,
        totalFrequency: Math.max(p5, Math.min(p95, d.totalFrequency))
      }));
    } else if (outlierHandling === 'log') {
      return data.map(d => ({
        ...d,
        totalFrequency: Math.log(d.totalFrequency + 1)
      }));
    }
    return data;
  };

  // Helper functions moved before useMemo
  const calculateBubbleSize = (frequency, allData) => {
    const minFreq = Math.min(...allData.map(d => d.totalFrequency));
    const maxFreq = Math.max(...allData.map(d => d.totalFrequency));
    
    const minRadius = 15;
    const maxRadius = 60;
    
    switch (scalingMethod) {
      case 'linear':
        const linearNorm = (frequency - minFreq) / (maxFreq - minFreq);
        return minRadius + (linearNorm * (maxRadius - minRadius));
      
      case 'sqrt':
        const sqrtMin = Math.sqrt(minFreq);
        const sqrtMax = Math.sqrt(maxFreq);
        const sqrtValue = Math.sqrt(frequency);
        const sqrtNorm = (sqrtValue - sqrtMin) / (sqrtMax - sqrtMin);
        return minRadius + (sqrtNorm * (maxRadius - minRadius));
      
      case 'log':
        const logMin = Math.log(Math.max(1, minFreq));
        const logMax = Math.log(Math.max(1, maxFreq));
        const logValue = Math.log(Math.max(1, frequency));
        const logNorm = (logValue - logMin) / (logMax - logMin);
        return minRadius + (logNorm * (maxRadius - minRadius));
      
      default:
        return minRadius;
    }
  };

  const calculateXPosition = (family) => {
    if (xAxisMode === 'timeline') {
      return family.timelinePosition;
    } else {
      return family.metricsValue;
    }
  };

  const getXAxisLabel = () => {
    return xAxisMode === 'timeline' ? 'Posición Temporal Ponderada' : 'Métricas de Video Agregadas';
  };

  const addLegend = (g, width) => {
    const legend = g.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(${width + 20}, 20)`);

    const legendItems = legend.selectAll(".legend-item")
      .data(ETYMOLOGICAL_FAMILIES.filter(f => selectedFamilies.has(f.id)))
      .enter()
      .append("g")
      .attr("class", "legend-item")
      .attr("transform", (d, i) => `translate(0, ${i * 25})`);

    legendItems.append("circle")
      .attr("r", 8)
      .attr("fill", d => d.color);

    legendItems.append("text")
      .attr("x", 15)
      .attr("y", 4)
      .text(d => d.label)
      .style("font-size", "12px");
  };

  const handleBubbleMouseOver = (event, d) => {
    const [x, y] = d3.pointer(event, containerRef.current);
    setTooltip({
      visible: true,
      x: x + 10,
      y: y - 10,
      data: d
    });
    setHoveredBubble(d);
  };

  const handleBubbleMouseOut = () => {
    setTooltip({ visible: false, x: 0, y: 0, data: null });
    setHoveredBubble(null);
  };

  const handleBubbleClick = (event, d) => {
    setSelectedFamily(d);
  };

  // Memoized processed data with etymological analysis
  const processedData = useMemo(() => {
    if (data.length === 0) return [];

    // Step 1: Filter by sentiment threshold and frequency
    let filteredData = data.filter(family => {
      const avgSentiment = Math.abs(family.netAffectiveValue / family.totalFrequency);
      return avgSentiment >= debouncedSentimentThreshold && 
             family.totalFrequency >= debouncedFrequencyThreshold;
    });

    // Step 2: Filter by selected families
    if (selectedFamilies.size > 0) {
      filteredData = filteredData.filter(family => selectedFamilies.has(family.id));
    }

    // Step 3: Filter by search term
    if (debouncedSearchTerm) {
      filteredData = filteredData.filter(family => 
        family.label.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) ||
        family.words.some(word => word.toLowerCase().includes(debouncedSearchTerm.toLowerCase()))
      );
    }

    // Step 4: Handle outliers in metrics
    if (outlierHandling !== 'none') {
      filteredData = handleOutliers(filteredData);
    }

    // Step 5: Calculate positions and sizes
    return filteredData.map(family => ({
      ...family,
      bubbleSize: calculateBubbleSize(family.totalFrequency, filteredData),
      xPosition: calculateXPosition(family),
      yPosition: family.netAffectiveValue,
      opacity: hoveredBubble && hoveredBubble.id !== family.id ? 0.3 : 1
    }));
  }, [data, debouncedSentimentThreshold, debouncedFrequencyThreshold, selectedFamilies, 
      debouncedSearchTerm, outlierHandling, xAxisMode, aggregationMethod, hoveredBubble]);

  // Optimized visualization update
  const updateVisualization = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    animationFrameRef.current = requestAnimationFrame(() => {
      if (!svgRef.current || processedData.length === 0) return;

      const svg = d3.select(svgRef.current);
      svg.selectAll("g").remove();

      const margin = { top: 20, right: 120, bottom: 60, left: 80 };
      const width = 900 - margin.left - margin.right;
      const height = 600 - margin.top - margin.bottom;

      const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

      // Create scales
      const xExtent = d3.extent(processedData, d => d.xPosition);
      const yExtent = d3.extent(processedData, d => d.yPosition);
      
      const xScale = d3.scaleLinear()
        .domain(xExtent)
        .range([0, width]);

      const yScale = d3.scaleLinear()
        .domain(yExtent)
        .range([height, 0]);

      // Add zero line for affective values
      g.append("line")
        .attr("x1", 0)
        .attr("x2", width)
        .attr("y1", yScale(0))
        .attr("y2", yScale(0))
        .attr("stroke", "#666")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "5,5");

      // Add axes
      setTimeout(() => {
        const xAxis = g.append("g")
          .attr("transform", `translate(0,${height})`);
        
        const yAxis = g.append("g");

        xAxis.call(d3.axisBottom(xScale));
        yAxis.call(d3.axisLeft(yScale));

        // Add axis labels
        xAxis.append("text")
          .attr("x", width / 2)
          .attr("y", 50)
          .attr("fill", "black")
          .style("text-anchor", "middle")
          .text(getXAxisLabel());

        yAxis.append("text")
          .attr("transform", "rotate(-90)")
          .attr("y", -60)
          .attr("x", -height / 2)
          .attr("fill", "black")
          .style("text-anchor", "middle")
          .text("Valor Afectivo Neto");
      }, 0);

      // Create bubbles
      const bubbles = g.selectAll(".family-bubble")
        .data(processedData, d => d.id);

      const bubblesEnter = bubbles.enter()
        .append("circle")
        .attr("class", "family-bubble")
        .style("cursor", "pointer")
        .attr("opacity", 0);

      const bubblesMerged = bubblesEnter.merge(bubbles);

      bubblesMerged
        .attr("cx", d => xScale(d.xPosition))
        .attr("cy", d => yScale(d.yPosition))
        .attr("r", d => d.bubbleSize)
        .attr("fill", d => d.color)
        .attr("stroke", "#fff")
        .attr("stroke-width", 2)
        .transition()
        .duration(300)
        .attr("opacity", d => d.opacity);

      // Add event listeners
      bubblesEnter
        .on("mouseover", handleBubbleMouseOver)
        .on("mouseout", handleBubbleMouseOut)
        .on("click", handleBubbleClick);

      // Add family labels
      setTimeout(() => {
        g.selectAll(".family-label")
          .data(processedData.filter(d => d.bubbleSize > 15))
          .enter()
          .append("text")
          .attr("class", "family-label")
          .attr("x", d => xScale(d.xPosition))
          .attr("y", d => yScale(d.yPosition) + 5)
          .attr("text-anchor", "middle")
          .style("font-size", "12px")
          .style("font-weight", "bold")
          .style("pointer-events", "none")
          .text(d => d.label)
          .attr("opacity", 0)
          .transition()
          .duration(300)
          .attr("opacity", 1);
      }, 100);

      // Add legend
      setTimeout(() => {
        addLegend(g, width);
      }, 200);
    });
  }, [processedData, xAxisMode]);

  // Update visualization when data changes
  useEffect(() => {
    if (processedData.length > 0) {
      updateVisualization();
    }
  }, [processedData, updateVisualization]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const loadEtymologicalData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/data/summary`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();

      // Process etymological families
      const familiesData = await processEtymologicalFamilies(data);
      setData(familiesData);

      // Initialize selected families
      setSelectedFamilies(new Set(ETYMOLOGICAL_FAMILIES.map(f => f.id)));

    } catch (err) {
      console.error('Error loading etymological data:', err);
      setError('Error al cargar los datos de familias etimológicas');
    } finally {
      setIsLoading(false);
    }
  };

  const processEtymologicalFamilies = async (summaryData) => {
    // Generate mock data based on etymological families
    const familiesData = [];

    for (const family of ETYMOLOGICAL_FAMILIES) {
      // Generate words for this family
      const words = generateWordsForFamily(family.id);
      
      // Calculate metrics for the family
      const familyMetrics = calculateFamilyMetrics(words, family);
      
      familiesData.push({
        id: family.id,
        label: family.label,
        color: family.color,
        description: family.description,
        words: words.map(w => w.word),
        totalFrequency: familyMetrics.totalFrequency,
        netAffectiveValue: familyMetrics.netAffectiveValue,
        averageSentiment: familyMetrics.averageSentiment,
        timelinePosition: familyMetrics.timelinePosition,
        metricsValue: familyMetrics.metricsValue,
        correlationScore: familyMetrics.correlationScore,
        wordCount: words.length,
        topWords: words.slice(0, 5),
        sentimentDistribution: familyMetrics.sentimentDistribution,
        temporalDistribution: familyMetrics.temporalDistribution
      });
    }

    return familiesData;
  };

  const generateWordsForFamily = (familyId) => {
    const wordsByFamily = {
      politica: ['política', 'gobierno', 'estado', 'poder', 'democracia', 'elecciones', 'partido', 'candidato'],
      justicia: ['justicia', 'derecho', 'ley', 'tribunal', 'juez', 'legal', 'constitución', 'norma'],
      diversidad: ['diversidad', 'inclusión', 'multicultural', 'tolerancia', 'pluralidad', 'diferencia', 'variedad'],
      derechos: ['derechos', 'libertad', 'igualdad', 'dignidad', 'humanos', 'civil', 'fundamental'],
      social: ['social', 'sociedad', 'comunidad', 'colectivo', 'público', 'ciudadano', 'pueblo'],
      juventud: ['juventud', 'joven', 'adolescente', 'estudiante', 'generación', 'futuro', 'nuevo'],
      cambio: ['cambio', 'transformación', 'revolución', 'reforma', 'evolución', 'progreso', 'innovación'],
      identidad: ['identidad', 'género', 'sexual', 'cultural', 'étnico', 'personal', 'individual']
    };

    const familyWords = wordsByFamily[familyId] || [];
    
    return familyWords.map(word => ({
      word,
      frequency: Math.floor(Math.random() * 100) + 10,
      sentiment: getSentimentValue(word),
      timestamps: generateTimestamps(),
      videoMetrics: generateVideoMetrics()
    }));
  };

  const getSentimentValue = (word) => {
    // Check sentiment lexicon first
    if (SENTIMENT_LEXICON[word] !== undefined) {
      return SENTIMENT_LEXICON[word];
    }
    
    // Apply ML-based sentiment analysis simulation
    const positiveWords = ['amor', 'paz', 'justicia', 'libertad', 'igualdad', 'respeto', 'dignidad', 'esperanza'];
    const negativeWords = ['odio', 'violencia', 'discriminación', 'injusticia', 'opresión', 'exclusión'];
    
    if (positiveWords.some(pw => word.includes(pw))) return 1;
    if (negativeWords.some(nw => word.includes(nw))) return -1;
    
    // Random assignment for neutral words (filtered out by threshold)
    return (Math.random() - 0.5) * 2;
  };

  const generateTimestamps = () => {
    const timestamps = [];
    const startDate = new Date('2023-01-01');
    const endDate = new Date('2023-12-31');
    
    for (let i = 0; i < Math.floor(Math.random() * 50) + 10; i++) {
      const randomTime = startDate.getTime() + Math.random() * (endDate.getTime() - startDate.getTime());
      timestamps.push(new Date(randomTime));
    }
    
    return timestamps.sort((a, b) => a - b);
  };

  const generateVideoMetrics = () => {
    return {
      likes: Math.floor(Math.random() * 10000),
      comments: Math.floor(Math.random() * 1000),
      shares: Math.floor(Math.random() * 500),
      views: Math.floor(Math.random() * 100000)
    };
  };

  const calculateFamilyMetrics = (words, family) => {
    const totalFrequency = words.reduce((sum, w) => sum + w.frequency, 0);
    
    // Calculate net affective value (frequency × sentiment)
    const netAffectiveValue = words.reduce((sum, w) => sum + (w.frequency * w.sentiment), 0);
    
    // Calculate average sentiment
    const averageSentiment = netAffectiveValue / totalFrequency;
    
    // Calculate weighted timeline position
    const timelinePosition = calculateWeightedTimelinePosition(words);
    
    // Calculate aggregated metrics value
    const metricsValue = calculateAggregatedMetrics(words);
    
    // Calculate correlation score
    const correlationScore = calculateCorrelationScore(words);
    
    return {
      totalFrequency,
      netAffectiveValue,
      averageSentiment,
      timelinePosition,
      metricsValue,
      correlationScore,
      sentimentDistribution: calculateSentimentDistribution(words),
      temporalDistribution: calculateTemporalDistribution(words)
    };
  };

  const calculateWeightedTimelinePosition = (words) => {
    let weightedTimeTotal = 0;
    let totalFrequency = 0;
    
    words.forEach(word => {
      word.timestamps.forEach(timestamp => {
        const numericTime = timestamp.getTime();
        weightedTimeTotal += numericTime * word.frequency;
        totalFrequency += word.frequency;
      });
    });
    
    return totalFrequency > 0 ? weightedTimeTotal / totalFrequency : Date.now();
  };

  const calculateAggregatedMetrics = (words) => {
    switch (aggregationMethod) {
      case 'sum':
        return words.reduce((sum, w) => sum + w.videoMetrics.likes + w.videoMetrics.comments + w.videoMetrics.shares, 0);
      
      case 'weighted_average':
        let weightedTotal = 0;
        let totalFrequency = 0;
        words.forEach(w => {
          const metrics = w.videoMetrics.likes + w.videoMetrics.comments + w.videoMetrics.shares;
          weightedTotal += metrics * w.frequency;
          totalFrequency += w.frequency;
        });
        return totalFrequency > 0 ? weightedTotal / totalFrequency : 0;
      
      case 'correlation':
        // Simplified correlation calculation
        return Math.random() * 100; // Placeholder for actual correlation
      
      default:
        return 0;
    }
  };

  const calculateCorrelationScore = (words) => {
    // Simplified Pearson correlation between frequency and engagement
    const frequencies = words.map(w => w.frequency);
    const engagements = words.map(w => w.videoMetrics.likes + w.videoMetrics.comments);
    
    if (frequencies.length < 2) return 0;
    
    const meanFreq = frequencies.reduce((a, b) => a + b) / frequencies.length;
    const meanEng = engagements.reduce((a, b) => a + b) / engagements.length;
    
    let numerator = 0;
    let denomFreq = 0;
    let denomEng = 0;
    
    for (let i = 0; i < frequencies.length; i++) {
      const freqDiff = frequencies[i] - meanFreq;
      const engDiff = engagements[i] - meanEng;
      numerator += freqDiff * engDiff;
      denomFreq += freqDiff * freqDiff;
      denomEng += engDiff * engDiff;
    }
    
    const denominator = Math.sqrt(denomFreq * denomEng);
    return denominator !== 0 ? numerator / denominator : 0;
  };

  const calculateSentimentDistribution = (words) => {
    const positive = words.filter(w => w.sentiment > 0).length;
    const negative = words.filter(w => w.sentiment < 0).length;
    const neutral = words.filter(w => w.sentiment === 0).length;
    
    return { positive, negative, neutral };
  };

  const calculateTemporalDistribution = (words) => {
    const allTimestamps = words.flatMap(w => w.timestamps);
    const months = {};
    
    allTimestamps.forEach(timestamp => {
      const month = timestamp.getMonth();
      months[month] = (months[month] || 0) + 1;
    });
    
    return months;
  };

  const toggleFamily = (familyId) => {
    const newSelected = new Set(selectedFamilies);
    if (newSelected.has(familyId)) {
      newSelected.delete(familyId);
    } else {
      newSelected.add(familyId);
    }
    setSelectedFamilies(newSelected);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50">
        <FaSpinner className="text-indigo-600 text-4xl animate-spin mb-4" />
        <p className="text-gray-600">Procesando familias etimológicas...</p>
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
          onClick={loadEtymologicalData}
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
            <FaProjectDiagram className="inline mr-3" />
            Familias Etimológicas TikTok
          </h1>
          <p className="text-gray-600">
            Visualización de familias de palabras por valores afectivos, frecuencias y métricas de interacción
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* X-Axis Mode */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <FaClock className="inline mr-1" />
                Eje X
              </label>
              <select
                value={xAxisMode}
                onChange={(e) => setXAxisMode(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="timeline">Línea de Tiempo</option>
                <option value="metrics">Métricas de Video</option>
              </select>
            </div>

            {/* Aggregation Method */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <FaCalculator className="inline mr-1" />
                Agregación
              </label>
              <select
                value={aggregationMethod}
                onChange={(e) => setAggregationMethod(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="sum">Suma</option>
                <option value="weighted_average">Promedio Ponderado</option>
                <option value="correlation">Correlación</option>
              </select>
            </div>

            {/* Scaling Method */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Escalado de Burbujas
              </label>
              <select
                value={scalingMethod}
                onChange={(e) => setScalingMethod(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="linear">Lineal</option>
                <option value="sqrt">Raíz Cuadrada</option>
                <option value="log">Logarítmico</option>
              </select>
            </div>

            {/* Outlier Handling */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Manejo de Atípicos
              </label>
              <select
                value={outlierHandling}
                onChange={(e) => setOutlierHandling(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="none">Ninguno</option>
                <option value="winsorize">Winsorización</option>
                <option value="log_scale">Escala Logarítmica</option>
              </select>
            </div>
          </div>

          {/* Thresholds */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <FaBrain className="inline mr-1" />
                Umbral de Sentimiento: {sentimentThreshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={sentimentThreshold}
                onChange={(e) => setSentimentThreshold(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Umbral de Frecuencia: {frequencyThreshold}
              </label>
              <input
                type="range"
                min="1"
                max="50"
                step="1"
                value={frequencyThreshold}
                onChange={(e) => setFrequencyThreshold(parseInt(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <FaSearch className="inline mr-1" />
                Buscar Familia
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Family Filters */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <FaLanguage className="inline mr-1" />
              Familias Etimológicas
            </label>
            <div className="flex flex-wrap gap-2">
              {ETYMOLOGICAL_FAMILIES.map(family => (
                <button
                  key={family.id}
                  onClick={() => toggleFamily(family.id)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedFamilies.has(family.id)
                      ? 'text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                  style={{
                    backgroundColor: selectedFamilies.has(family.id) ? family.color : undefined
                  }}
                  title={family.description}
                >
                  {selectedFamilies.has(family.id) ? <FaEye className="inline mr-1" /> : <FaEyeSlash className="inline mr-1" />}
                  {family.label}
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
                height="650"
                className="w-full"
              />

              {/* Tooltip */}
              {tooltip.visible && tooltip.data && (
                <div
                  className="absolute bg-gray-800 text-white p-3 rounded-lg shadow-lg pointer-events-none z-10 max-w-xs"
                  style={{ left: tooltip.x, top: tooltip.y }}
                >
                  <div className="font-semibold">{tooltip.data.label}</div>
                  <div className="text-sm">Palabras: {tooltip.data.wordCount}</div>
                  <div className="text-sm">Frecuencia Total: {tooltip.data.totalFrequency}</div>
                  <div className="text-sm">Valor Afectivo: {tooltip.data.netAffectiveValue.toFixed(2)}</div>
                  <div className="text-sm">Sentimiento Promedio: {tooltip.data.averageSentiment.toFixed(2)}</div>
                  <div className="text-sm">Correlación: {tooltip.data.correlationScore.toFixed(2)}</div>
                  <div className="text-xs mt-1 text-gray-300">{tooltip.data.description}</div>
                </div>
              )}
            </div>
          </div>

          {/* Details Panel */}
          {selectedFamily && (
            <div className="w-80 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-800 mb-4">
                <FaHeart className="inline mr-2" style={{ color: selectedFamily.color }} />
                {selectedFamily.label}
              </h3>
              
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Información General</h4>
                  <div className="space-y-1 text-sm">
                    <div>Palabras: <span className="font-medium">{selectedFamily.wordCount}</span></div>
                    <div>Frecuencia Total: <span className="font-medium">{selectedFamily.totalFrequency}</span></div>
                    <div>Valor Afectivo Neto: <span className="font-medium">{selectedFamily.netAffectiveValue.toFixed(2)}</span></div>
                    <div>Sentimiento Promedio: <span className="font-medium">{selectedFamily.averageSentiment.toFixed(2)}</span></div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Palabras Principales</h4>
                  <div className="space-y-1">
                    {selectedFamily.topWords.map((wordData, index) => (
                      <div key={index} className="flex justify-between text-sm">
                        <span>{wordData.word}</span>
                        <span className="font-medium">{wordData.frequency}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Distribución de Sentimiento</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-green-600">Positivo:</span>
                      <span className="font-medium">{selectedFamily.sentimentDistribution.positive}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Neutral:</span>
                      <span className="font-medium">{selectedFamily.sentimentDistribution.neutral}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-red-600">Negativo:</span>
                      <span className="font-medium">{selectedFamily.sentimentDistribution.negative}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Métricas</h4>
                  <div className="space-y-1 text-sm">
                    <div>Correlación: <span className="font-medium">{selectedFamily.correlationScore.toFixed(3)}</span></div>
                    <div>Valor de Métricas: <span className="font-medium">{selectedFamily.metricsValue.toFixed(0)}</span></div>
                  </div>
                </div>

                <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                  {selectedFamily.description}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EtymologicalFamiliesViz; 