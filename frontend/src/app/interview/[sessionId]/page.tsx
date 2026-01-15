"use client";

import React from 'react';
import { useParams } from 'next/navigation';
import InterviewSession from '@/components/InterviewSession';

export default function InterviewPage() {
    const params = useParams();
    const sessionId = params.sessionId as string;

    return <InterviewSession sessionId={sessionId} />;
}
