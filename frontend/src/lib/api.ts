import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api';

export const api = axios.create({
    baseURL: API_URL,
});

export const createSession = async (name: string, email: string) => {
    // New Endpoint: POST /interview/start
    const res = await api.post('/interview/start', { name, email });
    return res.data; // { sessionId: "..." }
};

// Deprecated / Legacy endpoints
export const startHeyGenSession = async () => {
    const res = await api.post('/heygen/session');
    return res.data;
};

export const speakText = async (sessionId: string, text: string) => {
    const res = await api.post('/heygen/speak', { session_id: sessionId, text });
    return res.data;
};
