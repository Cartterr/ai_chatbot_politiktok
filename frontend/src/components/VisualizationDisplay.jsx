// frontend/src/components/VisualizationDisplay.jsx

import React from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, LabelList
} from 'recharts';
import { FaExpand } from 'react-icons/fa'; // Import fullscreen icon

// Consistent color palette
const COLORS = ['#4f46e5', '#7c3aed', '#0ea5e9', '#06b6d4', '#10b981', '#84cc16', '#f97316', '#eab308', '#ef4444', '#ec4899'];
const POSITIVE_COLOR = '#10b981'; // Green
const NEGATIVE_COLOR = '#ef4444'; // Red
const NEUTRAL_COLOR = '#9ca3af'; // Gray

// --- Helper Functions ---

// Format numbers with commas (or 'K'/'M' for large numbers if desired)
const formatNumber = (num) => {
  if (num === null || num === undefined) return 'N/A';
  return num.toLocaleString('es-CL'); // Use Chilean Spanish locale for formatting
};

// Custom label for Pie charts - attempts to fit inside or just outside
const RADIAN = Math.PI / 180;
const renderCustomizedPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, name, value }) => {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5; // Position label halfway in slice
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  const percentage = (percent * 100).toFixed(0);

  // Don't render label for very small slices to avoid clutter
  if (percent < 0.03) {
    return null;
  }

  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize="10px" fontWeight="bold">
      {`${name} (${percentage}%)`}
    </text>
  );
};

// --- Specific Chart Components ---

const TimeSeriesVisualization = ({ data, openFullscreen, isFullscreen }) => {
  if (!data?.data?.length && !data?.views_data?.length) return <p className="text-center text-gray-500 py-4">No hay datos temporales disponibles</p>;
  // Merge data for combined chart
  const combinedData = data.data.map(countEntry => {
      const viewEntry = data.views_data?.find(v => v.date === countEntry.date);
      return {
          ...countEntry,
          avg_views: viewEntry?.avg_views // Add avg_views if found
      };
  });

  return (
    <div className="relative group"> {/* Added relative/group for button positioning */}
        {!isFullscreen && ( // Show button only if not already fullscreen
             <button onClick={() => openFullscreen(data)} className="absolute top-2 right-2 z-10 p-1.5 bg-gray-100/50 text-gray-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-200 hover:text-gray-700" title="Ver en pantalla completa">
                <FaExpand className="w-3 h-3" />
             </button>
        )}
        <div className="space-y-6">
            <h3 className="text-lg font-semibold text-gray-800 pr-8">{data.title || 'Análisis Temporal'}</h3>
            <ResponsiveContainer width="100%" height={isFullscreen ? 450 : 300}>
                <AreaChart data={combinedData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <defs>
                        <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1"> <stop offset="5%" stopColor={COLORS[0]} stopOpacity={0.8}/> <stop offset="95%" stopColor={COLORS[0]} stopOpacity={0.1}/> </linearGradient>
                        <linearGradient id="colorViews" x1="0" y1="0" x2="0" y2="1"> <stop offset="5%" stopColor={COLORS[4]} stopOpacity={0.8}/> <stop offset="95%" stopColor={COLORS[4]} stopOpacity={0.1}/> </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="left" stroke={COLORS[0]} tick={{ fontSize: 11 }} tickFormatter={formatNumber} label={{ value: 'Videos', angle: -90, position: 'insideLeft', style: {textAnchor: 'middle', fontSize: '12px', fill: COLORS[0]}, dx: -15 }}/>
                    {data.views_data?.length > 0 && (
                        <YAxis yAxisId="right" orientation="right" stroke={COLORS[4]} tick={{ fontSize: 11 }} tickFormatter={formatNumber} label={{ value: 'Vistas Prom.', angle: 90, position: 'insideRight', style: {textAnchor: 'middle', fontSize: '12px', fill: COLORS[4]}, dx: 15 }} />
                    )}
                    <Tooltip formatter={(value, name) => [formatNumber(value), name === 'count' ? 'Videos' : 'Vistas Prom.']} />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Area type="monotone" dataKey="count" stroke={COLORS[0]} fillOpacity={0.6} fill="url(#colorCount)" name="Videos" yAxisId="left" activeDot={{ r: 6 }} />
                    {data.views_data?.length > 0 && (
                        <Area type="monotone" dataKey="avg_views" stroke={COLORS[4]} fillOpacity={0.4} fill="url(#colorViews)" name="Vistas Prom." yAxisId="right" />
                    )}
                </AreaChart>
            </ResponsiveContainer>
            {/* Stats */}
            {data.stats && Object.keys(data.stats).length > 0 && (
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                    {Object.entries(data.stats).map(([key, value]) => (
                         <div key={key} className="bg-gray-100 p-3 rounded-md border border-gray-200">
                            <p className="font-medium text-gray-600 capitalize">{key.replace('_', ' ')}:</p>
                            <p className="text-lg font-semibold text-indigo-700">{typeof value === 'number' ? formatNumber(Math.round(value * 10)/10) : value}</p>
                         </div>
                    ))}
                </div>
            )}
        </div>
    </div>
  );
};


const ComparisonVisualization = ({ data, openFullscreen, isFullscreen }) => {
  const hasData = data && Object.values(data).some(val => Array.isArray(val) && val.length > 0);
  if (!hasData) return <p className="text-center text-gray-500 py-4">No hay datos de comparación disponibles</p>;

  return (
    <div className="relative group">
         {!isFullscreen && ( <button onClick={() => openFullscreen(data)} className="absolute top-2 right-2 z-10 p-1.5 bg-gray-100/50 text-gray-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-200 hover:text-gray-700" title="Ver en pantalla completa"> <FaExpand className="w-3 h-3" /> </button> )}
         <div className="space-y-8">
            <h3 className="text-lg font-semibold text-gray-800 pr-8">{data.title || 'Comparación'}</h3>
            {/* Followers Bar */}
            {data.follower_comparison?.length > 0 && (
                <div>
                    <h4 className="text-md font-medium mb-3 text-gray-700">por Seguidores</h4>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data.follower_comparison} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
                            <YAxis dataKey="name" type="category" width={140} tick={{ fontSize: 11 }} interval={0} />
                            <Tooltip formatter={(value) => formatNumber(value)} cursor={{ fill: '#f9fafb' }}/>
                            <Bar dataKey="value" fill={COLORS[0]} name="Seguidores"> <LabelList dataKey="value" position="right" formatter={formatNumber} style={{ fontSize: 10, fill: '#374151' }}/> </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
            {/* Perspective Pie */}
            {data.perspective_comparison?.length > 0 && (
                <div>
                    <h4 className="text-md font-medium mb-3 text-gray-700">por Perspectiva Política</h4>
                    <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                            <Pie data={data.perspective_comparison} cx="50%" cy="50%" outerRadius={85} innerRadius={45} fill="#8884d8" dataKey="value" nameKey="name" paddingAngle={2}>
                                {data.perspective_comparison.map((entry, index) => (<Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />))}
                            </Pie>
                            <Tooltip formatter={(value, name) => [formatNumber(value), name]} />
                            <Legend wrapperStyle={{ fontSize: '12px', marginTop: '10px' }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            )}
            {/* Themes Bar */}
             {data.theme_comparison?.length > 0 && (
                 <div>
                     <h4 className="text-md font-medium mb-3 text-gray-700">por Temas (Top 10)</h4>
                     <ResponsiveContainer width="100%" height={300}>
                          <BarChart data={data.theme_comparison} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                              <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
                              <YAxis dataKey="name" type="category" width={160} tick={{ fontSize: 11 }} interval={0} />
                              <Tooltip formatter={(value) => formatNumber(value)} cursor={{ fill: '#f9fafb' }}/>
                              <Bar dataKey="value" fill={COLORS[4]} name="Menciones"> <LabelList dataKey="value" position="right" formatter={formatNumber} style={{ fontSize: 10, fill: '#374151' }}/> </Bar>
                          </BarChart>
                     </ResponsiveContainer>
                 </div>
             )}
            {/* Views Bar */}
            {data.views_comparison?.length > 0 && (
                <div>
                    <h4 className="text-md font-medium mb-3 text-gray-700">por Vistas Promedio (Top 10 Creadores)</h4>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data.views_comparison} margin={{ top: 5, right: 5, left: 5, bottom: 50 }}> {/* Increased bottom margin */}
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis dataKey="username" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={60} interval={0} /> {/* Angle labels */}
                            <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber}/>
                            <Tooltip formatter={(value) => formatNumber(value)} cursor={{ fill: '#f9fafb' }}/>
                            <Legend wrapperStyle={{ fontSize: '12px' }} />
                            <Bar dataKey="avg_views" fill={COLORS[1]} name="Vistas Prom.">
                               <LabelList dataKey="avg_views" position="top" formatter={v => formatNumber(Math.round(v))} style={{ fontSize: 9, fill: '#374151' }}/>
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
         </div>
    </div>
  );
};


const DistributionVisualization = ({ data }) => {
  const hasData = data && Object.values(data).some(val => Array.isArray(val) && val.length > 0);
  if (!hasData) {
    return <p className="text-center text-gray-500 py-4">No hay datos de distribución disponibles</p>;
  }

  return (
    <div className="space-y-8">
      <h3 className="text-lg font-semibold text-gray-800">{data.title || 'Distribución'}</h3>

      {/* Perspective Pie */}
      {data.perspective_distribution?.length > 0 && (
        <div>
          <h4 className="text-md font-medium mb-3 text-gray-700">Distribución por Perspectiva Política</h4>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={data.perspective_distribution} cx="50%" cy="50%" outerRadius={85} innerRadius={45} fill="#8884d8" dataKey="count" nameKey="category" paddingAngle={2}>
                {data.perspective_distribution.map((entry, index) => (<Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />))}
              </Pie>
              <Tooltip formatter={(value, name) => [formatNumber(value), name]} />
              <Legend wrapperStyle={{ fontSize: '12px', marginTop: '10px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Age Bar */}
      {data.age_distribution?.length > 0 && (
        <div>
          <h4 className="text-md font-medium mb-3 text-gray-700">Distribución por Edad</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.age_distribution} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb"/>
              <XAxis dataKey="category" tick={{ fontSize: 11 }}/>
              <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber}/>
              <Tooltip formatter={(value) => formatNumber(value)} cursor={{ fill: '#f3f4f6' }}/>
              <Bar dataKey="count" fill={COLORS[2]} name="Cuentas">
                 <LabelList dataKey="count" position="top" formatter={formatNumber} style={{ fontSize: 10, fill: '#374151' }}/>
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Theme Bar (Vertical) */}
      {data.theme_distribution?.length > 0 && (
        <div>
          <h4 className="text-md font-medium mb-3 text-gray-700">Distribución por Temas (Top 15)</h4>
          <ResponsiveContainer width="100%" height={400}> {/* Increased height */}
            <BarChart data={data.theme_distribution} margin={{ top: 5, right: 20, left: 5, bottom: 5 }} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb"/>
              <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={formatNumber}/>
              <YAxis dataKey="category" type="category" width={160} tick={{ fontSize: 11 }} interval={0}/>
              <Tooltip formatter={(value) => formatNumber(value)} cursor={{ fill: '#f3f4f6' }}/>
              <Bar dataKey="count" fill={COLORS[4]} name="Menciones">
                 <LabelList dataKey="count" position="right" formatter={formatNumber} style={{ fontSize: 10, fill: '#374151' }}/>
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Views Bar */}
      {data.views_distribution?.length > 0 && (
        <div>
          <h4 className="text-md font-medium mb-3 text-gray-700">Distribución por Rango de Vistas</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.views_distribution} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb"/>
              <XAxis dataKey="category" tick={{ fontSize: 11 }}/>
              <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber}/>
              <Tooltip formatter={(value) => formatNumber(value)} cursor={{ fill: '#f3f4f6' }}/>
              <Bar dataKey="count" fill={COLORS[6]} name="Videos">
                 <LabelList dataKey="count" position="top" formatter={formatNumber} style={{ fontSize: 10, fill: '#374151' }}/>
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Sentiment Pie */}
      {data.sentiment_distribution?.length > 0 && (
        <div>
          <h4 className="text-md font-medium mb-3 text-gray-700">Distribución por Sentimiento (Palabras)</h4>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={data.sentiment_distribution.map(item => ({
                  name: item.category === 1.0 ? 'Positivo' : item.category === -1.0 ? 'Negativo' : 'Neutral', // Map numeric category to name
                  value: item.count
                }))}
                cx="50%" cy="50%" outerRadius={85} innerRadius={45} fill="#8884d8" dataKey="value" nameKey="name" paddingAngle={2}>
                {data.sentiment_distribution.map((entry, index) => {
                   let color = NEUTRAL_COLOR;
                   if (entry.category === 1.0) color = POSITIVE_COLOR;
                   if (entry.category === -1.0) color = NEGATIVE_COLOR;
                   return <Cell key={`cell-${index}`} fill={color} />;
                })}
              </Pie>
              <Tooltip formatter={(value, name) => [formatNumber(value), name]} />
              <Legend wrapperStyle={{ fontSize: '12px', marginTop: '10px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};


const SentimentVisualization = ({ data }) => {
  // Combine checks for both data arrays
  const hasData = (data?.data?.length > 0) || (data?.by_user?.length > 0);
  if (!hasData) {
    return <p className="text-center text-gray-500 py-4">No hay datos de sentimiento disponibles</p>;
  }

  return (
    <div className="space-y-8">
      <h3 className="text-lg font-semibold text-gray-800">{data.title || 'Análisis de Sentimiento'}</h3>

      {/* Avg Sentiment by User Bar Chart */}
      {data.by_user?.length > 0 && (
        <div>
          <h4 className="text-md font-medium mb-3 text-gray-700">Sentimiento Promedio por Usuario</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={data.by_user.slice(0, 15)} // Show top 15 users by avg sentiment
              margin={{ top: 5, right: 5, left: 5, bottom: 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb"/>
              <XAxis dataKey="username" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} interval={0} />
              <YAxis domain={[-1, 1]} tick={{ fontSize: 11 }} allowDataOverflow={true}/>
              <Tooltip formatter={(value) => value.toFixed(2)} cursor={{ fill: '#f3f4f6' }}/>
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="avg_sentiment" name="Sentimiento Prom." >
                {data.by_user.slice(0, 15).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.avg_sentiment >= 0 ? POSITIVE_COLOR : NEGATIVE_COLOR} />
                ))}
                 {/* <LabelList dataKey="avg_sentiment" position="top" formatter={(v) => v.toFixed(1)} style={{ fontSize: 9, fill: '#374151' }}/> */}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Detailed Table */}
      {data.data?.length > 0 && (
        <div>
            <h4 className="text-md font-medium mt-4 mb-2 text-gray-700">Detalles por Video (Top 50 por Ratio)</h4>
            <div className="bg-gray-50 p-3 rounded-lg max-h-80 overflow-y-auto border border-gray-200"> {/* Increased height */}
            <table className="min-w-full divide-y divide-gray-200 text-xs">
                <thead className="bg-gray-100 sticky top-0"> {/* Sticky header */}
                <tr>
                    <th className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider">Usuario</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider">Pos</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider">Neg</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider">Ratio</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider">URL (si existe)</th>
                </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                {data.data.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-3 py-2 whitespace-nowrap">{item.username}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-center">{item.positive_words}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-center">{item.negative_words}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-center">
                        <span
                        className={`px-2 py-0.5 inline-flex leading-4 font-semibold rounded-full ${
                            item.sentiment_ratio > 0.1 ? 'bg-green-100 text-green-800' :
                            item.sentiment_ratio < -0.1 ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                        }`}
                        >
                        {item.sentiment_ratio.toFixed(2)}
                        </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap truncate max-w-xs">
                        {item.url ? (
                            <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-800 hover:underline">
                                Ver Video
                            </a>
                        ) : '-'}
                    </td>
                    </tr>
                ))}
                </tbody>
            </table>
            </div>
        </div>
       )}
    </div>
  );
};


const SummaryVisualization = ({ data }) => {
  const hasData = (data?.charts?.length > 0) || (data?.stats && Object.keys(data.stats).length > 0);
  if (!hasData) {
    return <p className="text-center text-gray-500 py-4">No hay datos de resumen disponibles</p>;
  }

  return (
    <div className="space-y-8">
      <h3 className="text-lg font-semibold text-gray-800">{data.title || 'Resumen de Datos'}</h3>

      {/* Stats Overview */}
      {data.stats && Object.keys(data.stats).length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Dynamically create stat cards */}
            {Object.entries(data.stats).map(([key, value]) => {
                let label = key.replace(/_/g, ' ').replace('total ', '').replace(' analyzed', '');
                label = label.charAt(0).toUpperCase() + label.slice(1); // Capitalize
                 if (label.includes('subtitles')) label = 'Con Subtítulos';
                 if (label.includes('words')) label = 'Palabras Léxico';
                 if (label.includes('accounts')) label = 'Cuentas';
                 if (label.includes('videos')) label = 'Videos';

                return (
                <div key={key} className="bg-gradient-to-br from-indigo-50 to-purple-50 p-4 rounded-lg shadow-sm border border-indigo-100 text-center">
                    <p className="text-xs text-indigo-700 font-medium uppercase tracking-wider">{label}</p>
                    <p className="text-2xl font-bold text-indigo-900 mt-1">{formatNumber(value)}</p>
                </div>
                );
            })}
        </div>
      )}

      {/* Grid for Charts */}
      {data.charts?.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {data.charts.map((chart, idx) => (
            <div key={chart.id || idx} className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
              <h4 className="text-md font-semibold mb-4 text-gray-700">{chart.title}</h4>

              {/* Render correct chart type */}
              <ResponsiveContainer width="100%" height={280}>
                {chart.type === 'pie' ? (
                  <PieChart>
                    <Pie data={chart.data} cx="50%" cy="50%" outerRadius={80} innerRadius={40} fill="#8884d8" dataKey="value" nameKey="name" paddingAngle={2}>
                      {chart.data.map((entry, index) => (<Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />))}
                    </Pie>
                    <Tooltip formatter={(value, name) => [formatNumber(value), name]} />
                    <Legend wrapperStyle={{ fontSize: '11px', marginTop: '5px' }} layout="horizontal" verticalAlign="bottom" align="center"/>
                  </PieChart>
                ) : chart.type === 'line' ? (
                  <LineChart data={chart.data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb"/>
                    <XAxis dataKey="date" tick={{ fontSize: 10 }}/>
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber}/>
                    <Tooltip formatter={(value) => formatNumber(value)} />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                    <Line type="monotone" dataKey="value" stroke={COLORS[idx % COLORS.length]} name="Valor" dot={false} strokeWidth={2}/>
                  </LineChart>
                ) : ( // Default to Bar Chart (handles horizontal/vertical based on data length)
                  <BarChart
                    data={chart.data}
                    layout={chart.data.length > 6 ? "vertical" : "horizontal"} // Switch layout based on items
                    margin={chart.data.length > 6 ? { top: 5, right: 20, left: 20, bottom: 5 } : { top: 5, right: 5, left: 5, bottom: 40 } }
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb"/>
                    {chart.data.length > 6 ? ( // Vertical layout axes
                       <>
                         <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={formatNumber}/>
                         <YAxis dataKey="name" type="category" width={140} tick={{ fontSize: 10 }} interval={0}/>
                       </>
                    ) : ( // Horizontal layout axes
                       <>
                         <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={50} interval={0}/>
                         <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber}/>
                       </>
                    )}
                    <Tooltip formatter={(value, name) => [formatNumber(value), name]} cursor={{ fill: '#f9fafb' }}/>
                    <Bar dataKey="value" fill={COLORS[idx % COLORS.length]} name="Valor" barSize={chart.data.length > 6 ? 15 : undefined}>
                        {/* Add labels only if few bars, otherwise too cluttered */}
                        {chart.data.length <= 10 && <LabelList dataKey="value" position={chart.data.length > 6 ? "right" : "top"} formatter={formatNumber} style={{ fontSize: 9, fill: '#4b5563' }} />}
                    </Bar>
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};


// --- Main Display Component ---
const VisualizationDisplay = ({ visualization, openFullscreen, isFullscreen = false }) => {
  if (!visualization) {
    return <div className="p-6 bg-gray-100 rounded-lg border border-gray-200 text-center text-gray-500"><p>No hay visualización para mostrar.</p></div>;
  }
  if (visualization.error) {
       return <div className="p-6 bg-red-50 text-red-700 rounded-lg border border-red-200"><p className="font-semibold mb-1">Error al generar visualización:</p><p className="text-sm">{visualization.error}</p></div>;
  }

  // Pass openFullscreen and isFullscreen down to the specific components
  switch (visualization.type) {
    case 'time_series': return <TimeSeriesVisualization data={visualization} openFullscreen={openFullscreen} isFullscreen={isFullscreen} />;
    case 'comparison': return <ComparisonVisualization data={visualization} openFullscreen={openFullscreen} isFullscreen={isFullscreen} />;
    case 'distribution': return <DistributionVisualization data={visualization} openFullscreen={openFullscreen} isFullscreen={isFullscreen} />;
    case 'network': return <div className="p-4 text-center text-gray-500">Visualización de Red no implementada.</div>; // Placeholder
    case 'sentiment': return <SentimentVisualization data={visualization} openFullscreen={openFullscreen} isFullscreen={isFullscreen} />;
    case 'summary': return <SummaryVisualization data={visualization} openFullscreen={openFullscreen} isFullscreen={isFullscreen} />; // Pass props
    default:
      return (
        <div className="p-6 bg-yellow-50 rounded-lg border border-yellow-200 text-center text-yellow-700">
          <p className="font-semibold">Tipo de visualización no soportado: {visualization.type || 'Desconocido'}</p>
          <pre className="text-xs text-left mt-2 overflow-auto max-h-40 bg-white p-2 rounded">{JSON.stringify(visualization, null, 2)}</pre>
        </div>
      );
  }
};

export default VisualizationDisplay;