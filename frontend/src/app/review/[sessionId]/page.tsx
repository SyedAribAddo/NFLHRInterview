"use client";

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';

export default function SessionDetailPage() {
    const params = useParams();
    const sessionId = params.sessionId as string;
    const [detail, setDetail] = useState<any>(null);

    useEffect(() => {
        if (sessionId) {
            api.get(`/recruiter/sessions/${sessionId}`).then(res => setDetail(res.data));
        }
    }, [sessionId]);

    if (!detail) return <div>Loading...</div>;

    const downloadJson = () => {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(detail, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", `session_${sessionId}.json`);
        document.body.appendChild(downloadAnchorNode); // required for firefox
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    };

    return (
        <div className="min-h-screen bg-gray-100 p-8 text-black">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold">{detail.candidate_name} ({detail.role})</h1>
                    <p className="text-gray-500">{detail.candidate_email}</p>
                </div>
                <button onClick={downloadJson} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
                    Export JSON
                </button>
            </div>

            <div className="space-y-8">
                {detail.answers.map((ans: any, idx: number) => (
                    <div key={idx} className="bg-white p-6 rounded-lg shadow">
                        <h3 className="text-lg font-bold mb-4">Question {ans.question_id}</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <video src={ans.video_url} controls className="w-full rounded bg-black aspect-video" />
                            </div>
                            <div>
                                <div className="mb-4">
                                    <h4 className="font-bold text-gray-700 text-sm upppercase">Transcript</h4>
                                    <p className="text-gray-600 text-sm mt-1">{ans.transcript}</p>
                                </div>

                                {ans.score && (
                                    <div className="bg-gray-50 p-4 rounded border border-gray-200">
                                        <h4 className="font-bold text-gray-700 text-sm uppercase mb-2">AI Scorecard</h4>
                                        <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                                            <div>Clarity: <span className="font-bold text-black">{ans.score.communication_clarity}</span>/5</div>
                                            <div>Mindset: <span className="font-bold text-black">{ans.score.sales_mindset_ownership}</span>/5</div>
                                            <div>Objections: <span className="font-bold text-black">{ans.score.objection_handling}</span>/5</div>
                                            <div>Planning: <span className="font-bold text-black">{ans.score.planning_execution}</span>/5</div>
                                        </div>
                                        <div className="mt-3 pt-3 border-t border-gray-200">
                                            <div className="font-bold">Recommendation: <span className="text-blue-600">{ans.score.recommendation}</span></div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
