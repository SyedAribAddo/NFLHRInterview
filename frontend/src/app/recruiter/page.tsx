"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Loader2, PlayCircle, FileText } from 'lucide-react';

export default function RecruiterDashboard() {
    const [interviews, setInterviews] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get('/recruiter/interviews')
            .then(res => setInterviews(res.data))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="text-white p-10 flex justify-center"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="min-h-screen bg-gray-950 text-white p-8 font-sans">
            <h1 className="text-3xl font-bold mb-6 text-blue-400">Recruiter Dashboard</h1>

            <div className="overflow-x-auto bg-gray-900 rounded-lg border border-gray-800">
                <table className="w-full text-left">
                    <thead className="bg-gray-800 text-gray-400 uppercase text-xs">
                        <tr>
                            <th className="p-4">Candidate</th>
                            <th className="p-4">Status</th>
                            <th className="p-4">Date</th>
                            <th className="p-4">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                        {interviews.map((i) => (
                            <tr key={i.id} className="hover:bg-gray-800/50 transition">
                                <td className="p-4">
                                    <div className="font-bold text-white">{i.candidate_name}</div>
                                    <div className="text-xs text-gray-500">{i.candidate_email}</div>
                                </td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded text-xs font-bold uppercase
                                        ${i.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                                            i.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' :
                                                'bg-blue-500/20 text-blue-400'}`}>
                                        {i.status}
                                    </span>
                                </td>
                                <td className="p-4 text-gray-400 text-sm">
                                    {new Date(i.created_at).toLocaleDateString()}
                                </td>
                                <td className="p-4">
                                    <Link href={`/recruiter/${i.id}`} className="inline-flex items-center text-blue-400 hover:text-white">
                                        View <PlayCircle className="w-4 h-4 ml-1" />
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
