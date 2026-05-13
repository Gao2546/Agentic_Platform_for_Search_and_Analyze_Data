import React from 'react';

// 🧊 Skeleton สำหรับการ์ด Schedule (หน้า ScopeDetail)
export const ScheduleSkeleton = () => {
    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col justify-between h-auto animate-pulse">
            <div>
                {/* Badge Skeletons */}
                <div className="flex items-center justify-between mb-4">
                    <div className="h-5 bg-gray-200 rounded-full w-24"></div>
                    <div className="h-5 bg-purple-100 rounded w-20"></div>
                </div>
                
                {/* Title Skeleton */}
                <div className="h-6 bg-gray-300 rounded w-3/4 mb-3"></div>
                
                {/* Subtitle / Details Skeleton */}
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-5"></div>
                
                {/* List Items Skeletons */}
                <div className="space-y-2 mt-4">
                    <div className="h-3 bg-gray-200 rounded w-full"></div>
                    <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                </div>
            </div>

            {/* AI Loading Indicator (ป้ายบอกว่า AI กำลังคิด) */}
            <div className="mt-6 pt-4 border-t border-gray-100 flex items-center justify-center space-x-2">
                <div className="w-4 h-4 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0s' }}></div>
                <div className="w-4 h-4 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-4 h-4 rounded-full bg-indigo-600 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                <span className="text-sm font-bold text-indigo-600 ml-2">AI is crafting schedules...</span>
            </div>
        </div>
    );
};

// 🧊 Skeleton สำหรับกล่อง Task (หน้า ScheduleFlow / Pipeline Builder)
export const TaskSkeleton = () => {
    return (
        <div className="bg-white border-2 border-dashed border-indigo-300 rounded-lg p-4 w-[160px] text-center animate-pulse shadow-sm">
            <div className="h-3 bg-gray-200 rounded w-1/2 mx-auto mb-2"></div>
            <div className="h-5 bg-indigo-200 rounded w-3/4 mx-auto mb-3"></div>
            <div className="flex justify-center space-x-1 mt-2">
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></div>
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse delay-75"></div>
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse delay-150"></div>
            </div>
        </div>
    );
};