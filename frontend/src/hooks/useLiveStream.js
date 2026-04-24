import { useState, useEffect } from 'react';

export function useLiveStream(ticker) {
    const [liveData, setLiveData] = useState(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        // เปลี่ยน URL เป็น WebSocket Server ของคุณเมื่อพร้อม
        const ws = new WebSocket(`ws://localhost:8001/ws/stream/${ticker}`);

        ws.onopen = () => setIsConnected(true);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setLiveData(data);
        };

        ws.onclose = () => setIsConnected(false);

        return () => ws.close(); // Cleanup เมื่อเปลี่ยนหน้า
    }, [ticker]);

    return { liveData, isConnected };
}