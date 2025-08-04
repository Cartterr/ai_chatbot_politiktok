import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  FaSpinner,
  FaExclamationTriangle,
  FaNetworkWired,
  FaUsers,
  FaHashtag,
  FaPlay,
  FaPause,
  FaRedo,
  FaExpand,
  FaCompress,
  FaFilter,
  FaDownload
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

const NetworkViz = () => {
  // State management
  const [data, setData] = useState({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSimulationRunning, setIsSimulationRunning] = useState(true);
  
  // Visualization controls
  const [networkType, setNetworkType] = useState('creator-word'); // 'creator-word', 'word-sentiment', 'creator-engagement'
  const [nodeFilter, setNodeFilter] = useState('all'); // 'all', 'creators', 'words'
  const [linkStrengthThreshold, setLinkStrengthThreshold] = useState(0.1);
  const [selectedNode, setSelectedNode] = useState(null);
  
  // Visualization state
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, data: null });
  const [zoomLevel, setZoomLevel] = useState(1);
  
  // Refs
  const svgRef = useRef();
  const simulationRef = useRef();
  const containerRef = useRef();
  const animationFrameRef = useRef();

  // Debounce threshold changes to prevent excessive updates
  const debouncedThreshold = useDebounce(linkStrengthThreshold, 200);

  // Constants
  const NODE_TYPES = {
    CREATOR: 'creator',
    WORD: 'word',
    SENTIMENT: 'sentiment'
  };

  const CREATOR_CATEGORIES = [
    'izquierda', 'derecha', 'LGBTQIA+', 'feminista', 
    'discapacidad', 'derechos-indigenas', 'otros'
  ];

  // Load data on component mount
  useEffect(() => {
    loadNetworkData();
  }, []);

  // Memoized filtered data to prevent unnecessary recalculations
  const filteredNetworkData = useMemo(() => {
    // Filter nodes based on current filter
    let filteredNodes = data.nodes;
    if (nodeFilter === 'creators') {
      filteredNodes = data.nodes.filter(n => n.type === NODE_TYPES.CREATOR);
    } else if (nodeFilter === 'words') {
      filteredNodes = data.nodes.filter(n => n.type === NODE_TYPES.WORD);
    }

    // Sample nodes if too many to prevent performance issues
    if (filteredNodes.length > 100) {
      // Keep important nodes (high size/engagement) and sample others
      filteredNodes.sort((a, b) => (b.size || 0) - (a.size || 0));
      const importantNodes = filteredNodes.slice(0, 50);
      const remaining = filteredNodes.slice(50);
      const sampleSize = Math.min(50, remaining.length);
      const sampledNodes = [];
      
      for (let i = 0; i < sampleSize; i++) {
        const randomIndex = Math.floor(Math.random() * remaining.length);
        sampledNodes.push(remaining.splice(randomIndex, 1)[0]);
      }
      
      filteredNodes = [...importantNodes, ...sampledNodes];
    }

    // Filter links based on strength threshold and filtered nodes
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    let filteredLinks = data.links.filter(l => 
      l.strength >= debouncedThreshold && 
      nodeIds.has(l.source.id || l.source) && 
      nodeIds.has(l.target.id || l.target)
    );

    // Sample links if too many
    if (filteredLinks.length > 200) {
      filteredLinks.sort((a, b) => b.strength - a.strength);
      filteredLinks = filteredLinks.slice(0, 200);
    }

    return { nodes: filteredNodes, links: filteredLinks };
  }, [data, nodeFilter, debouncedThreshold, NODE_TYPES]);

  // Optimized network update with requestAnimationFrame
  const updateNetwork = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    animationFrameRef.current = requestAnimationFrame(() => {
      if (!svgRef.current || filteredNetworkData.nodes.length === 0) return;

      const svg = d3.select(svgRef.current);
      
      // Efficient clearing
      svg.selectAll("g").remove();

      const width = 800;
      const height = 600;

      // Create zoom behavior
      const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
          setZoomLevel(event.transform.k);
        });

      svg.call(zoom);

      const g = svg.append("g");

      // Create force simulation with reduced iterations for performance
      const simulation = d3.forceSimulation(filteredNetworkData.nodes)
        .force("link", d3.forceLink(filteredNetworkData.links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(d => d.size + 5))
        .alphaDecay(0.05) // Faster convergence
        .velocityDecay(0.8); // More damping

      simulationRef.current = simulation;

      // Create links with batched operations
      const linkGroup = g.append("g").attr("class", "links");
      const links = linkGroup.selectAll("line")
        .data(filteredNetworkData.links)
        .enter()
        .append("line")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", d => Math.sqrt(d.strength * 10));

      // Create nodes with batched operations
      const nodeGroup = g.append("g").attr("class", "nodes");
      const nodes = nodeGroup.selectAll("circle")
        .data(filteredNetworkData.nodes)
        .enter()
        .append("circle")
        .attr("r", d => d.size)
        .attr("fill", d => getNodeColor(d))
        .attr("stroke", "#fff")
        .attr("stroke-width", 2)
        .style("cursor", "pointer")
        .call(d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended))
        .on("mouseover", handleNodeMouseOver)
        .on("mouseout", handleNodeMouseOut)
        .on("click", handleNodeClick);

      // Add labels with reduced frequency updates
      const labelGroup = g.append("g").attr("class", "labels");
      const labels = labelGroup.selectAll("text")
        .data(filteredNetworkData.nodes.filter(d => d.size > 20)) // Only show labels for larger nodes
        .enter()
        .append("text")
        .text(d => d.label)
        .style("font-size", "12px")
        .style("text-anchor", "middle")
        .style("pointer-events", "none")
        .attr("dy", 4);

      // Throttled tick function for better performance
      let tickCount = 0;
      simulation.on("tick", () => {
        tickCount++;
        // Only update every 3rd tick for better performance
        if (tickCount % 3 === 0) {
          links
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

          nodes
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

          labels
            .attr("x", d => d.x)
            .attr("y", d => d.y);
        }
      });

      // Stop simulation after reasonable time to prevent infinite running
      setTimeout(() => {
        if (simulation) {
          simulation.stop();
        }
      }, 5000);

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    });
  }, [filteredNetworkData]);

  // Update network when type changes
  useEffect(() => {
    if (filteredNetworkData.nodes.length > 0) {
      updateNetwork();
    }
  }, [filteredNetworkData, networkType, updateNetwork]);

  // Cleanup animation frame on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const loadNetworkData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/data/summary`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      
      // Generate network data based on the type
      const networkData = generateNetworkData(data);
      setData(networkData);
      
    } catch (err) {
      console.error('Error loading network data:', err);
      setError('Error al cargar los datos de red');
    } finally {
      setIsLoading(false);
    }
  };

  const generateNetworkData = (summaryData) => {
    const nodes = [];
    const links = [];
    
    // Generate creator nodes
    CREATOR_CATEGORIES.forEach((category, index) => {
      nodes.push({
        id: `creator_${category}`,
        type: NODE_TYPES.CREATOR,
        label: category,
        category: category,
        size: Math.random() * 50 + 20,
        engagement: Math.random() * 100,
        followers: Math.floor(Math.random() * 100000),
        x: Math.random() * 400,
        y: Math.random() * 400
      });
    });

    // Generate word nodes
    const words = ['política', 'justicia', 'diversidad', 'derechos', 'social', 'juventud', 'cambio', 'futuro'];
    words.forEach((word, index) => {
      nodes.push({
        id: `word_${word}`,
        type: NODE_TYPES.WORD,
        label: word,
        frequency: Math.floor(Math.random() * 100) + 10,
        sentiment: (Math.random() - 0.5) * 2, // -1 to 1
        size: Math.random() * 30 + 10,
        x: Math.random() * 400,
        y: Math.random() * 400
      });
    });

    // Generate sentiment nodes
    const sentiments = ['positivo', 'neutral', 'negativo'];
    sentiments.forEach((sentiment, index) => {
      nodes.push({
        id: `sentiment_${sentiment}`,
        type: NODE_TYPES.SENTIMENT,
        label: sentiment,
        value: Math.random(),
        size: Math.random() * 40 + 15,
        x: Math.random() * 400,
        y: Math.random() * 400
      });
    });

    // Generate links based on network type
    if (networkType === 'creator-word') {
      // Connect creators to words they use frequently
      nodes.filter(n => n.type === NODE_TYPES.CREATOR).forEach(creator => {
        nodes.filter(n => n.type === NODE_TYPES.WORD).forEach(word => {
          if (Math.random() > 0.6) { // 40% chance of connection
            links.push({
              source: creator.id,
              target: word.id,
              strength: Math.random(),
              type: 'uses'
            });
          }
        });
      });
    } else if (networkType === 'word-sentiment') {
      // Connect words to sentiments
      nodes.filter(n => n.type === NODE_TYPES.WORD).forEach(word => {
        nodes.filter(n => n.type === NODE_TYPES.SENTIMENT).forEach(sentiment => {
          if (Math.random() > 0.5) {
            links.push({
              source: word.id,
              target: sentiment.id,
              strength: Math.random(),
              type: 'expresses'
            });
          }
        });
      });
    } else if (networkType === 'creator-engagement') {
      // Connect creators based on similar engagement patterns
      const creators = nodes.filter(n => n.type === NODE_TYPES.CREATOR);
      for (let i = 0; i < creators.length; i++) {
        for (let j = i + 1; j < creators.length; j++) {
          if (Math.random() > 0.7) {
            links.push({
              source: creators[i].id,
              target: creators[j].id,
              strength: Math.random(),
              type: 'similar_engagement'
            });
          }
        }
      }
    }

    return { nodes, links };
  };

  const getNodeColor = (node) => {
    switch (node.type) {
      case NODE_TYPES.CREATOR:
        const creatorColors = {
          'izquierda': '#ef4444',
          'derecha': '#3b82f6',
          'LGBTQIA+': '#8b5cf6',
          'feminista': '#ec4899',
          'discapacidad': '#10b981',
          'derechos-indigenas': '#f59e0b',
          'otros': '#6b7280'
        };
        return creatorColors[node.category] || '#6b7280';
      case NODE_TYPES.WORD:
        return d3.interpolateRdYlBu(node.sentiment * 0.5 + 0.5);
      case NODE_TYPES.SENTIMENT:
        const sentimentColors = {
          'positivo': '#10b981',
          'neutral': '#6b7280',
          'negativo': '#ef4444'
        };
        return sentimentColors[node.label] || '#6b7280';
      default:
        return '#6b7280';
    }
  };

  const handleNodeMouseOver = (event, d) => {
    const [x, y] = d3.pointer(event, containerRef.current);
    setTooltip({
      visible: true,
      x: x + 10,
      y: y - 10,
      data: d
    });
  };

  const handleNodeMouseOut = () => {
    setTooltip({ visible: false, x: 0, y: 0, data: null });
  };

  const handleNodeClick = (event, d) => {
    setSelectedNode(d);
    // Highlight connected nodes
    if (simulationRef.current) {
      const connectedNodes = new Set();
      data.links.forEach(link => {
        if (link.source.id === d.id || link.source === d.id) {
          connectedNodes.add(link.target.id || link.target);
        }
        if (link.target.id === d.id || link.target === d.id) {
          connectedNodes.add(link.source.id || link.source);
        }
      });
      
      // Update node styles to highlight connections
      d3.selectAll("circle")
        .style("opacity", node => 
          node.id === d.id || connectedNodes.has(node.id) ? 1 : 0.3
        );
    }
  };

  const toggleSimulation = () => {
    if (simulationRef.current) {
      if (isSimulationRunning) {
        simulationRef.current.stop();
      } else {
        simulationRef.current.restart();
      }
      setIsSimulationRunning(!isSimulationRunning);
    }
  };

  const resetNetwork = () => {
    if (simulationRef.current) {
      simulationRef.current.alpha(1).restart();
    }
    setSelectedNode(null);
    d3.selectAll("circle").style("opacity", 1);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50">
        <FaSpinner className="text-indigo-600 text-4xl animate-spin mb-4" />
        <p className="text-gray-600">Cargando red de conexiones...</p>
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
          onClick={loadNetworkData}
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
            Red de Conexiones TikTok
          </h1>
          <p className="text-gray-600">
            Visualización de relaciones entre creadores, palabras y sentimientos
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            {/* Network Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tipo de Red
              </label>
              <select
                value={networkType}
                onChange={(e) => setNetworkType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="creator-word">Creadores - Palabras</option>
                <option value="word-sentiment">Palabras - Sentimientos</option>
                <option value="creator-engagement">Creadores - Engagement</option>
              </select>
            </div>

            {/* Node Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filtro de Nodos
              </label>
              <select
                value={nodeFilter}
                onChange={(e) => setNodeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="all">Todos</option>
                <option value="creators">Solo Creadores</option>
                <option value="words">Solo Palabras</option>
              </select>
            </div>

            {/* Link Strength */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Fuerza de Conexión: {linkStrengthThreshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={linkStrengthThreshold}
                onChange={(e) => setLinkStrengthThreshold(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>

            {/* Controls */}
            <div className="flex flex-col space-y-2">
              <button
                onClick={toggleSimulation}
                className="flex items-center justify-center px-3 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                {isSimulationRunning ? <FaPause className="mr-2" /> : <FaPlay className="mr-2" />}
                {isSimulationRunning ? 'Pausar' : 'Reanudar'}
              </button>
              <button
                onClick={resetNetwork}
                className="flex items-center justify-center px-3 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
              >
                <FaRedo className="mr-2" />
                Reset
              </button>
            </div>

            {/* Stats */}
            <div>
              <div className="bg-indigo-50 p-3 rounded-lg">
                <div className="text-sm text-indigo-600">Zoom</div>
                <div className="text-xl font-bold text-indigo-800">{(zoomLevel * 100).toFixed(0)}%</div>
              </div>
            </div>
          </div>
        </div>

        {/* Selected Node Info */}
        {selectedNode && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-blue-800 mb-2">Nodo Seleccionado</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Tipo:</span> {selectedNode.type}
              </div>
              <div>
                <span className="font-medium">Etiqueta:</span> {selectedNode.label}
              </div>
              {selectedNode.type === NODE_TYPES.CREATOR && (
                <>
                  <div>
                    <span className="font-medium">Categoría:</span> {selectedNode.category}
                  </div>
                  <div>
                    <span className="font-medium">Engagement:</span> {selectedNode.engagement?.toFixed(2)}
                  </div>
                </>
              )}
              {selectedNode.type === NODE_TYPES.WORD && (
                <>
                  <div>
                    <span className="font-medium">Frecuencia:</span> {selectedNode.frequency}
                  </div>
                  <div>
                    <span className="font-medium">Sentimiento:</span> {selectedNode.sentiment?.toFixed(2)}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

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
                <div className="font-semibold">{tooltip.data.label}</div>
                <div className="text-sm">Tipo: {tooltip.data.type}</div>
                {tooltip.data.type === NODE_TYPES.CREATOR && (
                  <>
                    <div className="text-sm">Categoría: {tooltip.data.category}</div>
                    <div className="text-sm">Engagement: {tooltip.data.engagement?.toFixed(2)}</div>
                  </>
                )}
                {tooltip.data.type === NODE_TYPES.WORD && (
                  <>
                    <div className="text-sm">Frecuencia: {tooltip.data.frequency}</div>
                    <div className="text-sm">Sentimiento: {tooltip.data.sentiment?.toFixed(2)}</div>
                  </>
                )}
              </div>
            )}

            {/* Legend */}
            <div className="absolute top-4 right-4 bg-white p-3 rounded-lg shadow-lg border">
              <h4 className="font-semibold mb-2">Leyenda</h4>
              <div className="space-y-1 text-sm">
                <div className="flex items-center">
                  <div className="w-4 h-4 rounded-full bg-red-500 mr-2"></div>
                  <span>Creadores</span>
                </div>
                <div className="flex items-center">
                  <div className="w-4 h-4 rounded-full bg-blue-500 mr-2"></div>
                  <span>Palabras</span>
                </div>
                <div className="flex items-center">
                  <div className="w-4 h-4 rounded-full bg-green-500 mr-2"></div>
                  <span>Sentimientos</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkViz; 