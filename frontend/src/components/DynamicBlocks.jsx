import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  LineChart, Line, BarChart, Bar, AreaChart, Area, 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend 
} from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

// ==========================================
// 1. Text & Markdown Block
// ==========================================
export const MarkdownBlock = ({ payload }) => (
  <div className="prose prose-sm sm:prose-base max-w-none text-gray-800 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {payload.content}
    </ReactMarkdown>
  </div>
);

// ==========================================
// 2. Metric / Label-Value Block
// ==========================================
export const MetricBlock = ({ payload }) => {
  const { label, value, trend, color = 'blue', suffix = '' } = payload;
  
  // จัดการสีและไอคอนตาม Trend
  const colorMap = {
    green: 'text-emerald-600 bg-emerald-50',
    red: 'text-rose-600 bg-rose-50',
    blue: 'text-blue-600 bg-blue-50',
    gray: 'text-gray-600 bg-gray-50'
  };

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-emerald-500' : trend === 'down' ? 'text-rose-500' : 'text-gray-400';

  return (
    <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
      <h3 className="text-sm font-medium text-gray-500">{label}</h3>
      <div className="flex items-end justify-between mt-2">
        <div className="flex items-baseline space-x-1">
          <span className={`text-3xl font-bold ${colorMap[color]?.split(' ')[0] || 'text-gray-900'}`}>
            {value}
          </span>
          {suffix && <span className="text-sm font-medium text-gray-500">{suffix}</span>}
        </div>
        {trend && (
          <div className={`flex items-center space-x-1 text-sm font-medium ${trendColor}`}>
            <TrendIcon size={16} />
          </div>
        )}
      </div>
    </div>
  );
};

// ==========================================
// 3. Table Block
// ==========================================
export const TableBlock = ({ payload }) => {
  const { columns, data } = payload;
  if (!data || data.length === 0) return null;

  // ถ้าไม่มีการระบุ columns ให้ดึง key จาก data แถวแรกมาใช้
  const tableCols = columns || Object.keys(data[0]).map(key => ({ key, label: key.toUpperCase() }));

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {tableCols.map((col, idx) => (
                <th key={idx} className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-gray-50 transition-colors">
                {tableCols.map((col, colIdx) => (
                  <td key={colIdx} className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ==========================================
// 4. Graph / Chart Block (Recharts)
// ==========================================
export const ChartBlock = ({ payload }) => {
  const { subType = 'line', data, config } = payload;
  const { xAxisKey = 'name', lines = [] } = config || {};

  // กำหนดสีมาตรฐานของกราฟ
  const colors = ['#6366f1', '#10b981', '#f43f5e', '#f59e0b', '#8b5cf6'];

  const renderChart = () => {
    switch (subType) {
      case 'bar':
        return (
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey={xAxisKey} tick={{fontSize: 12}} tickLine={false} axisLine={false} />
            <YAxis tick={{fontSize: 12}} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
            {lines.map((line, idx) => (
              <Bar key={line.dataKey} dataKey={line.dataKey} name={line.name || line.dataKey} fill={line.color || colors[idx % colors.length]} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        );
      case 'area':
        return (
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey={xAxisKey} tick={{fontSize: 12}} tickLine={false} axisLine={false} />
            <YAxis tick={{fontSize: 12}} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
            {lines.map((line, idx) => (
              <Area key={line.dataKey} type="monotone" dataKey={line.dataKey} name={line.name || line.dataKey} stroke={line.color || colors[idx % colors.length]} fill={line.color || colors[idx % colors.length]} fillOpacity={0.1} strokeWidth={2} />
            ))}
          </AreaChart>
        );
      case 'line':
      default:
        return (
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey={xAxisKey} tick={{fontSize: 12}} tickLine={false} axisLine={false} />
            <YAxis tick={{fontSize: 12}} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
            {lines.map((line, idx) => (
              <Line key={line.dataKey} type="monotone" dataKey={line.dataKey} name={line.name || line.dataKey} stroke={line.color || colors[idx % colors.length]} strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
            ))}
          </LineChart>
        );
    }
  };

  return (
    <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
      {payload.title && <h3 className="text-lg font-bold text-gray-800 mb-4">{payload.title}</h3>}
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          {renderChart()}
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// ==========================================
// 5. Media & Embed Block
// ==========================================
export const EmbedBlock = ({ payload }) => {
  const { provider, url, title } = payload;
  
  if (provider === 'youtube') {
    // Extract Video ID
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    const videoId = (match && match[2].length === 11) ? match[2] : null;

    if (!videoId) return <div className="text-red-500 text-sm">Invalid YouTube URL</div>;

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="relative pt-[56.25%] w-full">
          <iframe 
            className="absolute top-0 left-0 w-full h-full"
            src={`https://www.youtube.com/embed/${videoId}`} 
            title={title || "YouTube video player"}
            frameBorder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowFullScreen
          ></iframe>
        </div>
      </div>
    );
  }

  // รองรับ Image ชั่วคราว (เผื่อส่งรูปภาพมาจาก AI)
  if (provider === 'image') {
    return (
      <div className="rounded-xl overflow-hidden shadow-sm border border-gray-100">
        <img src={url} alt={title || 'Embedded image'} className="w-full h-auto object-cover" />
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl text-center text-sm text-gray-500">
      Unsupported embed provider: <span className="font-bold">{provider}</span>
      <br/>
      <a href={url} target="_blank" rel="noreferrer" className="text-blue-500 underline mt-2 block">Open Link</a>
    </div>
  );
};