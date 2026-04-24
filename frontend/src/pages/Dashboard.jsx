import React, { useState, useEffect } from 'react';
import { dataAPI } from '../services/api';

export default function Dashboard() {
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchInsights = async () => {
            try {
                // ค้นหาข้อมูลผลลัพธ์ขั้นสุดท้าย (Stage 4) จาก MongoDB[cite: 4]
                const response = await dataAPI.searchInsights({
                    stage: "4_VISUALIZE",
                    limit: 10
                });
                setInsights(response.data.data);
            } catch (error) {
                console.error("Failed to fetch insights", error);
            } finally {
                setLoading(false);
            }
        };
        fetchInsights();
    }, []);

    return (
        <div className="p-8">
            <h1 className="text-3xl font-bold mb-6 text-gray-800">📈 AI Insights Dashboard</h1>
            
            {loading ? (
                <p>กำลังโหลดข้อมูล...</p>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {insights.map((insight) => (
                        <div key={insight._id} className="bg-white rounded-lg shadow p-6 border-t-4 border-blue-500">
                            <div className="flex justify-between items-center mb-4">
                                <h2 className="text-xl font-bold text-gray-800">{insight.asset_ticker || 'N/A'}</h2>
                                <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                                    insight.insight_type === 'Bullish' ? 'bg-green-100 text-green-800' : 
                                    insight.insight_type === 'Bearish' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                                }`}>
                                    Confidence: {(insight.confidence_score * 100).toFixed(0)}%
                                </span>
                            </div>
                            <p className="text-gray-600 mb-4">{insight.summary_text || insight.content}</p>
                            <div className="text-sm text-gray-400">
                                วิเคราะห์เมื่อ: {new Date(insight.created_at).toLocaleString('th-TH')}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}