"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Mic, Loader2, RefreshCw, MessageCircle, SkipForward } from 'lucide-react';
import { api } from '@/lib/api';
import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues with Three.js
const TalkingAvatar = dynamic(() => import('./TalkingAvatar'), { ssr: false });

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api';

const QUESTIONS = [
    { id: 1, text: "Walk me through your sales experience and the types of products you've sold." },
    { id: 2, text: "Describe a time you missed target — what did you change afterward?" },
    { id: 3, text: "Why National Foods, and why this sales role?" }
];

export default function InterviewSession({ sessionId }: { sessionId: string }) {
    const router = useRouter();
    const videoRef = useRef<HTMLVideoElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioRecorderRef = useRef<MediaRecorder | null>(null); // Separate audio-only recorder
    const chunksRef = useRef<Blob[]>([]); // Full video interview
    const audioChunksRef = useRef<Blob[]>([]); // Audio-only for analysis

    // --- State ---
    const [phase, setPhase] = useState<'init' | 'intro' | 'question' | 'analysing' | 'outro' | 'uploading' | 'upload-error'>('init');
    const [subState, setSubState] = useState<'speaking' | 'listening' | 'processing'>('speaking');
    const [qIndex, setQIndex] = useState(0);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [debugLog, setDebugLog] = useState<string[]>([]);
    const [avatarSpeaking, setAvatarSpeaking] = useState(false);
    const ttsAudioRef = useRef<HTMLAudioElement | null>(null);

    // --- Refs ---
    const audioContextRef = useRef<AudioContext | null>(null);
    const silenceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const subStateRef = useRef(subState);
    const initializedRef = useRef(false);
    const qIndexRef = useRef(0);
    const currentAttemptRef = useRef(0);
    const isAnalyzingRef = useRef(false);

    // Debug helper
    const log = (msg: string) => {
        console.log(`[Interview] ${msg}`);
        setDebugLog(prev => [...prev.slice(-4), msg]);
    };

    useEffect(() => { subStateRef.current = subState; }, [subState]);

    // --- Init ---
    useEffect(() => {
        if (initializedRef.current) return;
        initializedRef.current = true;

        async function start() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                if (videoRef.current) videoRef.current.srcObject = stream;

                initVAD(stream);
                initRecorders(stream);

                setPhase('intro');
                playAudio('intro', () => advanceToQuestion(0));

            } catch (e) {
                console.error("Setup failed", e);
                alert("Please enable camera/microphone.");
            }
        }
        start();

        return () => {
            if (audioContextRef.current) audioContextRef.current.close();
            if (audioRef.current) { audioRef.current.pause(); }
        };
    }, []);

    // --- VAD ---
    const initVAD = (stream: MediaStream) => {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = ctx;
        const source = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        const data = new Uint8Array(analyser.frequencyBinCount);

        const loop = () => {
            analyser.getByteFrequencyData(data);
            const vol = data.reduce((a, b) => a + b, 0) / data.length;

            if (vol > 40) { // Lowered threshold for better detection
                setIsSpeaking(true);
                if (silenceTimeoutRef.current) {
                    clearTimeout(silenceTimeoutRef.current);
                    silenceTimeoutRef.current = null;
                }
            } else {
                setIsSpeaking(false);
                // 3s Silence -> Analyze
                if (subStateRef.current === 'listening' && !silenceTimeoutRef.current && !isAnalyzingRef.current) {
                    silenceTimeoutRef.current = setTimeout(() => {
                        log("Silence detected -> Analyzing...");
                        triggerAnalysis();
                    }, 3000);
                }
            }
            requestAnimationFrame(loop);
        };
        loop();
    };

    const initRecorders = (stream: MediaStream) => {
        // Video recorder (full interview)
        const videoRec = new MediaRecorder(stream, { mimeType: 'video/webm' });
        videoRec.ondataavailable = (e) => {
            if (e.data.size > 0) chunksRef.current.push(e.data);
        };
        videoRec.start(1000);
        mediaRecorderRef.current = videoRec;

        // Audio-only recorder for analysis (cleaner data)
        const audioTrack = stream.getAudioTracks()[0];
        const audioStream = new MediaStream([audioTrack]);
        const audioRec = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
        audioRec.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };
        audioRec.start(500);
        audioRecorderRef.current = audioRec;
    };

    // Start fresh audio capture for this answer
    const startAudioCapture = () => {
        audioChunksRef.current = [];
        log("Audio capture started");
    };

    // --- Smart Logic ---
    const triggerAnalysis = async () => {
        if (isAnalyzingRef.current || subStateRef.current !== 'listening') return;
        isAnalyzingRef.current = true;

        // Flush audio recorder
        audioRecorderRef.current?.requestData();

        // Small delay to ensure data is flushed
        await new Promise(r => setTimeout(r, 100));

        setSubState('processing');
        setPhase('analysing');

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        log(`Audio blob size: ${audioBlob.size} bytes`);

        if (audioBlob.size < 500) {
            log("Empty audio -> Nudging");
            isAnalyzingRef.current = false;
            handleAction('nudge');
            return;
        }

        const formData = new FormData();
        formData.append('file', audioBlob, 'answer.webm');
        formData.append('question_text', QUESTIONS[qIndexRef.current].text);
        formData.append('attempt', currentAttemptRef.current.toString());

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 8000);

            const res = await api.post('/interview/analyze', formData, { signal: controller.signal });
            clearTimeout(timeoutId);

            const action = res.data.action || 'next';
            const transcript = res.data.transcript || '';
            log(`Analysis: "${transcript}" -> ${action}`);

            handleAction(action);

        } catch (e: any) {
            log(`Analysis error: ${e.message} -> Next`);
            handleAction('next');
        } finally {
            isAnalyzingRef.current = false;
        }
    };

    const handleAction = (action: string) => {
        if (action === 'nudge' || action === 'rephrase') {
            if (currentAttemptRef.current >= 1) {
                log("Max attempts -> Next");
                nextQuestion();
            } else {
                currentAttemptRef.current++;
                playDynamicResponse(action as 'nudge' | 'rephrase');
            }
        } else {
            nextQuestion();
        }
    };

    const playDynamicResponse = async (action: 'nudge' | 'rephrase') => {
        setPhase('question');
        setSubState('speaking');
        setAvatarSpeaking(true); // Start avatar animation

        const text = action === 'nudge'
            ? "Could you elaborate a bit more on that? I'd love to hear more details."
            : "Let me rephrase that question for you. " + QUESTIONS[qIndexRef.current].text;

        log(`Playing ${action}: "${text.substring(0, 30)}..."`);

        try {
            const response = await fetch(`${API_URL}/interview/synthesize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            if (!response.ok) throw new Error("TTS Error");

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.crossOrigin = "anonymous"; // Required for Web Audio API

            // Set both refs for lip sync
            ttsAudioRef.current = audio;
            audioRef.current = audio;

            audio.onended = () => {
                setAvatarSpeaking(false);
                startAudioCapture();
                setSubState('listening');
            };
            audio.onerror = () => {
                setAvatarSpeaking(false);
                log("TTS playback error");
                startAudioCapture();
                setSubState('listening');
            };
            audio.play().catch(() => {
                setAvatarSpeaking(false);
                startAudioCapture();
                setSubState('listening');
            });

        } catch (e) {
            setAvatarSpeaking(false);
            log(`Dynamic TTS Error: ${e}`);
            startAudioCapture();
            setSubState('listening');
        }
    };

    // --- Manual Controls ---
    const manualNudge = () => {
        if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
        currentAttemptRef.current++;
        playDynamicResponse('nudge');
    };

    const manualRephrase = () => {
        if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
        currentAttemptRef.current++;
        playDynamicResponse('rephrase');
    };

    const manualSkip = () => {
        if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
        nextQuestion();
    };

    // --- Navigation ---
    const playAudio = (key: string, onEnded: () => void) => {
        if (ttsAudioRef.current) { ttsAudioRef.current.pause(); ttsAudioRef.current.onended = null; }
        const audio = new Audio(`${API_URL}/interview/audio/${key}`);
        audio.crossOrigin = "anonymous"; // Required for Web Audio API analysis
        ttsAudioRef.current = audio;
        audioRef.current = audio; // For compatibility

        setAvatarSpeaking(true);

        audio.onended = () => {
            setAvatarSpeaking(false);
            onEnded();
        };
        audio.onerror = () => {
            setAvatarSpeaking(false);
            log("Audio load failed -> Skip");
            onEnded();
        };
        audio.play().catch(e => {
            setAvatarSpeaking(false);
            log(`Play failed: ${e.name}`);
            if (e.name !== 'AbortError') onEnded();
        });
    };

    const advanceToQuestion = (idx: number) => {
        if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);

        setQIndex(idx);
        qIndexRef.current = idx;
        currentAttemptRef.current = 0;
        isAnalyzingRef.current = false;

        setPhase('question');
        setSubState('speaking');

        log(`Question ${idx + 1}`);

        playAudio(QUESTIONS[idx].id.toString(), () => {
            startAudioCapture(); // Start fresh capture AFTER question audio ends
            setSubState('listening');
        });
    };

    const nextQuestion = () => {
        const next = qIndexRef.current + 1;
        if (next < QUESTIONS.length) {
            advanceToQuestion(next);
        } else {
            startOutro();
        }
    };

    const startOutro = () => {
        setPhase('outro');
        setSubState('speaking');
        playAudio('outro', finishInterview);
    };

    const finishInterview = async () => {
        if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
        if (audioRecorderRef.current?.state === 'recording') audioRecorderRef.current.stop();
        setPhase('uploading');

        const blob = new Blob(chunksRef.current, { type: 'video/webm' });
        const formData = new FormData();
        formData.append('file', blob);

        try {
            await api.post(`/interview/${sessionId}/complete`, formData, {
                onUploadProgress: (ev) => setUploadProgress(Math.round((ev.loaded * 100) / (ev.total || blob.size)))
            });
            router.push(`/recruiter/${sessionId}`);
        } catch (e) {
            setPhase('upload-error');
        }
    };

    // --- Render ---
    return (
        <div className="flex flex-col h-screen bg-gray-900 text-white font-sans">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center">
                <h1 className="text-xl font-bold text-blue-400">National Foods AI Interview</h1>
                <div className="text-red-500 font-bold text-xs animate-pulse">● REC</div>
            </div>

            <div className="flex-1 flex flex-col md:flex-row">
                {/* Left: 3D Avatar */}
                <div className="flex-1 relative bg-gradient-to-br from-slate-800 via-slate-900 to-slate-950">
                    <TalkingAvatar
                        audioRef={ttsAudioRef}
                        isSpeaking={avatarSpeaking}
                    />

                    {/* Candidate Webcam - Picture in Picture */}
                    <div className="absolute bottom-4 right-4 w-40 h-32 md:w-48 md:h-36 rounded-xl overflow-hidden border-2 border-blue-500/50 shadow-lg shadow-blue-500/20">
                        <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                    </div>

                    {/* Debug Log */}
                    <div className="absolute bottom-4 left-4 bg-black/70 px-3 py-2 rounded text-xs space-y-1 max-w-xs">
                        <div className="text-gray-400 text-xs">{sessionId}</div>
                        {debugLog.slice(-2).map((msg, i) => (
                            <div key={i} className="text-green-400 text-xs truncate">{msg}</div>
                        ))}
                    </div>

                    {/* Speaking Indicator */}
                    {avatarSpeaking && (
                        <div className="absolute top-4 left-4 flex items-center gap-2 bg-blue-500/20 backdrop-blur-sm px-3 py-1 rounded-full">
                            <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                            <span className="text-blue-300 text-sm">Salman is speaking...</span>
                        </div>
                    )}
                </div>

                <div className="flex-1 p-8 flex flex-col justify-center items-center text-center space-y-6">
                    {phase === 'init' && <Loader2 className="w-10 h-10 animate-spin" />}
                    {phase === 'intro' && <div className="text-xl text-blue-200">Starting Interview...</div>}

                    {phase === 'analysing' && (
                        <div className="flex flex-col items-center space-y-3">
                            <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
                            <div className="text-blue-300">Analyzing your response...</div>
                        </div>
                    )}

                    {phase === 'question' && (
                        <div className="max-w-xl space-y-6">
                            <div className="text-blue-500 font-bold text-sm uppercase tracking-wide">
                                Question {qIndex + 1} of {QUESTIONS.length}
                            </div>
                            <h2 className={`text-2xl leading-relaxed transition-colors ${subState === 'speaking' ? 'text-white' : 'text-gray-400'}`}>
                                "{QUESTIONS[qIndex].text}"
                            </h2>

                            {subState === 'listening' && (
                                <div className="space-y-6">
                                    <div className="flex items-center justify-center space-x-2 text-green-400">
                                        <Mic className={`w-6 h-6 ${isSpeaking ? 'animate-bounce' : 'animate-pulse'}`} />
                                        <span className="text-lg">{isSpeaking ? "I hear you..." : "Listening..."}</span>
                                    </div>

                                    {/* Fallback Controls */}
                                    <div className="flex flex-wrap justify-center gap-3">
                                        <button
                                            onClick={manualNudge}
                                            className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg text-sm font-medium transition-colors"
                                        >
                                            <MessageCircle className="w-4 h-4" />
                                            Nudge Me
                                        </button>
                                        <button
                                            onClick={manualRephrase}
                                            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-medium transition-colors"
                                        >
                                            <RefreshCw className="w-4 h-4" />
                                            Rephrase
                                        </button>
                                        <button
                                            onClick={manualSkip}
                                            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
                                        >
                                            <SkipForward className="w-4 h-4" />
                                            Skip
                                        </button>
                                    </div>
                                    <p className="text-xs text-gray-500">Smart detection will auto-respond after 3s silence, or use buttons above.</p>
                                </div>
                            )}
                        </div>
                    )}

                    {phase === 'outro' && <div className="text-green-400 text-2xl font-bold">Interview Complete!</div>}
                    {phase === 'uploading' && <div className="text-blue-400">Uploading... {uploadProgress}%</div>}
                    {phase === 'upload-error' && <div className="text-red-500">Upload Failed. Please refresh.</div>}
                </div>
            </div>
        </div>
    );
}
