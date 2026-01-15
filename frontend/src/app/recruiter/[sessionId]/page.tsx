"use client";

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { Loader2, Download, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function RecruiterDetail() {
    const params = useParams();
    const sessionId = params.sessionId as string;
    const [interview, setInterview] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (sessionId) {
            api.get(`/recruiter/interviews/${sessionId}`)
                .then(res => setInterview(res.data))
                .catch(console.error)
                .finally(() => setLoading(false));
        }
    }, [sessionId]);

    if (loading) return <div className="text-white p-10 flex justify-center"><Loader2 className="animate-spin" /></div>;
    if (!interview) return <div className="text-white p-10">Interview not found</div>;

    return (
        <div className="min-h-screen bg-black text-white p-6 font-sans">
            <Link href="/recruiter" className="inline-flex items-center text-gray-400 hover:text-white mb-6">
                <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
            </Link>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[calc(100vh-100px)]">
                {/* Left: Video */}
                <div className="lg:col-span-2 bg-gray-900 rounded-2xl overflow-hidden border border-gray-800 flex flex-col">
                    <div className="p-4 border-b border-gray-800">
                        <h1 className="text-xl font-bold">{interview.candidate_name}</h1>
                        <p className="text-sm text-gray-400">{interview.candidate_email}</p>
                    </div>
                    <div className="flex-1 bg-black flex items-center justify-center relative">
                        {interview.video_url ? (
                            <div className="relative w-full h-full">
                                <video
                                    src={interview.video_url}
                                    controls
                                    className="w-full h-full object-contain"
                                />
                                {/* Overlay Secure Token Info if needed */}
                            </div>
                        ) : (
                            <div className="text-gray-500">Video Processing / Not Available</div>
                        )}
                    </div>
                </div>

                {/* Right: Analysis */}
                <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6 overflow-y-auto">
                    <h2 className="text-lg font-bold mb-4 text-blue-400 uppercase tracking-widest">AI Assessment</h2>

                    {/* Overall Recommendation */}
                    {interview.scores && interview.scores.overall && (
                        <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl mb-6">
                            <span className="block text-xs uppercase text-blue-400 font-bold">Recommendation</span>
                            <span className="text-2xl font-bold text-white">{interview.scores.overall.recommendation || "N/A"}</span>
                            <p className="text-sm text-gray-300 mt-2">{interview.scores.overall.summary}</p>
                        </div>
                    )}

                    {/* Scores JSON Dump (Formatted) */}
                    <div className="space-y-4">
                        <h3 className="font-bold text-gray-400 text-sm">Detailed Scoring Data</h3>
                        <pre className="bg-black/50 p-4 rounded-lg text-xs text-green-400 overflow-x-auto font-mono">
                            {JSON.stringify(interview.scores, null, 2)}
                        </pre>
                    </div>

                    {/* Transcript */}
                    <div className="mt-8">
                        <h3 className="font-bold text-gray-400 text-sm mb-2">Transcript</h3>
                        <div className="text-sm text-gray-300 leading-relaxed space-y-2">
                            {interview.transcript_text ? (
                                interview.transcript_text.split('\n').map((line: string, i: number) => (
                                    <p key={i}>{line}</p>
                                ))
                            ) : (
                                <p className="italic text-gray-500">Transcript generation in progress...</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
