"use client";

import React, { useRef, useState, useEffect } from 'react';
import { Camera, StopCircle, Upload, Play, CheckCircle } from 'lucide-react';

interface VideoRecorderProps {
    onRecordingComplete: (blob: Blob) => void;
    isUploading: boolean;
}

export default function VideoRecorder({ onRecordingComplete, isUploading }: VideoRecorderProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const [isRecording, setIsRecording] = useState(false);
    const [recordedChunks, setRecordedChunks] = useState<Blob[]>([]);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [stream, setStream] = useState<MediaStream | null>(null);

    useEffect(() => {
        // Initialize user media
        async function initCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                setStream(stream);
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
            } catch (err) {
                console.error("Error accessing camera:", err);
            }
        }
        initCamera();
        return () => {
            // Cleanup stream
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, []);

    const startRecording = () => {
        if (!stream) return;
        setRecordedChunks([]);
        setPreviewUrl(null);
        const options = { mimeType: 'video/webm' };
        const mediaRecorder = new MediaRecorder(stream, options);

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                setRecordedChunks((prev) => [...prev, event.data]);
            }
        };

        mediaRecorder.onstop = () => {
            // Blob creation happens in useEffect on recordedChunks? No, synchronously here isn't safe if chunks update async.
            // Better: handle chunks in state or ref.
        };

        mediaRecorderRef.current = mediaRecorder;
        mediaRecorder.start();
        setIsRecording(true);
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            // We need to wait for onstop event or just gather chunks?
            // Actually, ondataavailable might fire one last time.
            // Let's use a small timeout or event based.
            setTimeout(() => {
                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                const url = URL.createObjectURL(blob);
                setPreviewUrl(url);
                onRecordingComplete(blob); // Pass blob up
            }, 500);
            // Note: state `recordedChunks` might not be updated inside this closure efficiently without refs.
            // Fixing: Use a Ref for chunks to avoid closure stale state.
        }
    };

    // Fix for chunks closure issue
    const chunksRef = useRef<Blob[]>([]);
    useEffect(() => {
        chunksRef.current = recordedChunks;
    }, [recordedChunks]);

    const handleStart = () => {
        if (!stream) return;
        chunksRef.current = [];
        setRecordedChunks([]);
        setPreviewUrl(null);

        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                setRecordedChunks(prev => [...prev, e.data]);
            }
        };

        mediaRecorder.start();
        setIsRecording(true);
    };

    const handleStop = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            // Wait slightly for last chunk
            setTimeout(() => {
                const blob = new Blob(chunksRef.current, { type: 'video/webm' });
                setPreviewUrl(URL.createObjectURL(blob));
                onRecordingComplete(blob);
            }, 200);
        }
    };

    return (
        <div className="flex flex-col items-center space-y-4">
            <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden border border-gray-700">
                {!previewUrl ? (
                    <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                ) : (
                    <video src={previewUrl} controls className="w-full h-full object-cover" />
                )}

                {isRecording && (
                    <div className="absolute top-4 right-4 animate-pulse">
                        <div className="w-4 h-4 bg-red-600 rounded-full"></div>
                    </div>
                )}
            </div>

            <div className="flex space-x-4">
                {!isRecording && !previewUrl && (
                    <button onClick={handleStart} className="flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transform transition active:scale-95">
                        <Camera className="w-5 h-5 mr-2" /> Start Answer
                    </button>
                )}

                {isRecording && (
                    <button onClick={handleStop} className="flex items-center px-6 py-3 bg-red-600 hover:bg-red-700 rounded-lg font-semibold animate-pulse">
                        <StopCircle className="w-5 h-5 mr-2" /> Stop Recording
                    </button>
                )}

                {previewUrl && !isUploading && (
                    <button onClick={handleStart} className="flex items-center px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg text-sm">
                        Redo
                    </button>
                )}

                {isUploading && (
                    <div className="flex items-center text-blue-400">
                        <Upload className="w-5 h-5 mr-2 animate-bounce" /> Uploading...
                    </div>
                )}
            </div>
        </div>
    );
}
