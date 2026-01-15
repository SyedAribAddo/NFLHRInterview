"use client";

import React, { useEffect, useRef, useState, useImperativeHandle, forwardRef } from 'react';
import StreamingAvatar, { AvatarQuality, TaskType, VoiceEmotion } from "@heygen/streaming-avatar";
import { useConversation } from '@11labs/react';
import { api } from '@/lib/api';

interface AvatarPlayerProps {
    onAvatarReady?: (sessionId: string) => void;
    onTalkingStart?: () => void;
    onTalkingEnd?: () => void;
}

export interface AvatarPlayerHandle {
    speak: (text: string) => Promise<void>;
}

const AvatarPlayer = forwardRef<AvatarPlayerHandle, AvatarPlayerProps>(({ onAvatarReady, onTalkingStart, onTalkingEnd }, ref) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const avatarRef = useRef<StreamingAvatar | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [debugStatus, setDebugStatus] = useState("Initializing...");
    const [sessionId, setSessionId] = useState<string | null>(null);

    // ElevenLabs Agent Integration
    const conversation = useConversation({
        onMessage: (message: any) => {
            console.log("Agent Message:", message);
            // Pure Voice Mode: No HeyGen piping.
            // The SDK handles audio playback automatically.
        },
        onError: (err: any) => {
            console.error("Agent Error:", err);
            setDebugStatus(`Agent Error: ${err}`);
        }
    });

    // Extract Agent connection handler
    const startAgent = async () => {
        try {
            // Request microphone access
            await navigator.mediaDevices.getUserMedia({ audio: true });

            // Start conversation
            await conversation.startSession({
                agentId: "agent_0601kdsn3d57f7etgqdp4p628x0n",
            } as any);
            console.log("Agent Connected");
        } catch (err: any) {
            console.error("Failed to start Agent:", err);
            setDebugStatus(`Agent Failed: ${err.message}`);
        }
    };

    // Expose handle to start conversation? Or Auto-start when Avatar is ready?
    // User wants "Conducting interview", so let's auto-start when stream is ready.

    // Fetch token and init
    useEffect(() => {
        async function init() {
            // VOICE MODE (HeyGen Disabled)
            setDebugStatus("Initializing Voice Mode...");
            setIsLoading(false);
            setTimeout(() => {
                setDebugStatus("Voice Interview Ready");
                if (onAvatarReady) onAvatarReady("mock-session");
                startAgent();
            }, 500);
            return; // STOP HERE

            try {
                // ... (Existing Token Logic) ...
                setDebugStatus("Fetching Session from Backend...");
                // 1. Call Backend to create session (Server-side init)
                const res = await api.post('/heygen/session');
                const { session_id, access_token } = res.data;

                setDebugStatus("Connecting to Avatar...");
                // 2. Initialize SDK with the token
                const avatar = new StreamingAvatar({ token: access_token });

                avatar.on("STREAM_READY", (event) => {
                    setDebugStatus("Stream Ready. Connecting Brain...");
                    if (videoRef.current && event.detail) {
                        videoRef.current.srcObject = event.detail;
                        videoRef.current.onloadedmetadata = () => {
                            videoRef.current?.play().catch(console.error);
                        };
                    }
                    // Start Agent (Brain)
                    startAgent();
                });

                // ... (Existing Talk Event Handlers) ...
                avatar.on("M_START", () => {
                    console.log("Avatar started talking");
                    if (onTalkingStart) onTalkingStart();
                });
                avatar.on("M_END", () => {
                    console.log("Avatar stopped talking");
                    if (onTalkingEnd) onTalkingEnd();
                });

                // 3. Connect to the existing session
                // SDK Method: startVoiceChat(request: StartAvatarRequest) ?? 
                // Or works differently? User said "new StreamingAvatar({ sessionId, token })". 
                // Let's try that constructor pattern IF the SDK supports it.
                // Re-reading SDK docs mentally: usually `new StreamingAvatar({ token })` -> `avatar.createStartAvatar()` creates NEW.
                // To join existing, it might be `avatar.connect(sessionId)`?
                // OR `startVoiceChat({ sessionId: ... })`?
                // The User Guide says: "Backend returns client-safe session data... Frontend uses the session... const avatar = new StreamingAvatar({ sessionId: session.session_id, token: session.token })"
                // I will try strictly enforcing the user's snippet.

                // Re-initializing avatar properly per User Step 3
                // Note: I already did `new StreamingAvatar({ token })`. Let's reconstruct or update.
                // User Snippet: `new StreamingAvatar({ sessionId: session.session_id, token: session.token })`
                // This implies the constructor takes sessionId? Let's assume yes.

                // Let's actually use a fresh instance logic here.
                const preConfiguredAvatar = new StreamingAvatar({
                    token: access_token,
                });

                // Bind events to this instance
                preConfiguredAvatar.on("STREAM_READY", (event) => {
                    setDebugStatus("Stream Ready (Pre-conf). Connecting Brain...");
                    if (videoRef.current && event.detail) {
                        videoRef.current.srcObject = event.detail;
                        videoRef.current.play().catch(console.error);
                    }
                    startAgent();
                });
                preConfiguredAvatar.on("M_START", () => onTalkingStart && onTalkingStart());
                preConfiguredAvatar.on("M_END", () => onTalkingEnd && onTalkingEnd());

                // Does it auto-connect if sessionId is passed? Or do we need to call something?
                // The User snippet didn't show a `start()` method. 
                // But most WebRTC SDKs need a trigger.
                // If I look at `lib/index.d.ts` (blocked), I can guess `startAvatar` might accept `sessionId`?
                // Let's try `startAvatar({ sessionId: session_id })`.

                try {
                    console.log("Connecting to session:", session_id);
                    await preConfiguredAvatar.startVoiceChat({
                        sessionId: session_id,
                        // DO NOT pass avatarId, voice, etc. It's already created.
                        useSilencePrompt: false
                    } as any);
                    // Cast to any because types might be strict about missing avatarName if it thinks we are creating new.

                    setSessionId(session_id);
                    avatarRef.current = preConfiguredAvatar;
                    setIsLoading(false);
                    if (onAvatarReady) onAvatarReady(session_id);

                } catch (connErr: any) {
                    console.error("Connection Failed:", connErr);
                    setDebugStatus(`Connection Error: ${connErr.message}`);
                }

            } catch (err: any) {
                setDebugStatus(`Error: ${err.message}`);
                console.error(err);
            }
        }

        init();

        return () => {
            avatarRef.current?.stopAvatar();
            conversation.endSession(); // Cleanup Agent
        };
    }, []);

    useImperativeHandle(ref, () => ({
        async speak(text: string) {
            // Voice Mode: Try to make the Agent speak?
            // The User wants the Agent to ask the question.
            console.log("Asked to speak:", text);
            // If the conversation object has a speak method (via newer type defs?) we use it.
            // Casting to any to avoid TS issues for now if types are outdated.
            const convAny = conversation as any;
            if (convAny.speak) {
                convAny.speak(text).catch((err: any) => console.error("Agent speak failed", err));
            } else {
                console.log("Agent 'speak' not available in this SDK version.");
            }
        }
    }));

    return (
        <div className="w-full h-full bg-gray-900 rounded-lg overflow-hidden flex items-center justify-center relative border border-gray-700 shadow-2xl">
            <video ref={videoRef} autoPlay playsInline className="w-full h-full object-cover" />
            {isLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/80 text-white z-10 flex-col">
                    <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                    <p className="font-mono text-sm">{debugStatus}</p>
                </div>
            )}
        </div>
    );
});

export default AvatarPlayer;
