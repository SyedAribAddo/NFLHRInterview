"use client";

import React, { useRef, useEffect, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';

interface AvatarProps {
    audioRef: React.RefObject<HTMLAudioElement | null>;
    isSpeaking: boolean;
}

function Avatar({ audioRef, isSpeaking }: AvatarProps) {
    const { scene } = useGLTF('/avatar/interviewer.glb');
    const headRef = useRef<THREE.SkinnedMesh | null>(null);
    const morphTargetDictRef = useRef<Record<string, number>>({});
    const analyserRef = useRef<AnalyserNode | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const lastAudioRef = useRef<HTMLAudioElement | null>(null);

    // Smooth animation values
    const currentMouthOpen = useRef(0);
    const currentVisemeBlend = useRef({ aa: 0, E: 0, O: 0, I: 0 });

    // Find the head mesh with morph targets
    useEffect(() => {
        scene.traverse((child) => {
            if (child instanceof THREE.SkinnedMesh && child.morphTargetDictionary) {
                const keys = Object.keys(child.morphTargetDictionary);
                if (keys.some(k => k.toLowerCase().includes('viseme') || k.toLowerCase().includes('mouth'))) {
                    headRef.current = child;
                    morphTargetDictRef.current = child.morphTargetDictionary;
                    console.log('Avatar morph targets found:', keys.length);
                }
            }
        });
    }, [scene]);

    // Setup audio analysis - reconnect when audio element changes
    useEffect(() => {
        const audio = audioRef.current;
        if (!audio || !isSpeaking) return;

        // Check if this is a different audio element
        if (audio === lastAudioRef.current && analyserRef.current) {
            return; // Same audio, already connected
        }

        console.log('Connecting audio for lip sync...');
        lastAudioRef.current = audio;

        try {
            // Create fresh AudioContext
            if (audioContextRef.current) {
                audioContextRef.current.close().catch(() => { });
            }

            audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
            const source = audioContextRef.current.createMediaElementSource(audio);
            analyserRef.current = audioContextRef.current.createAnalyser();
            analyserRef.current.fftSize = 256;
            analyserRef.current.smoothingTimeConstant = 0.4;

            source.connect(analyserRef.current);
            analyserRef.current.connect(audioContextRef.current.destination);

            console.log('Audio connected for lip sync!');
        } catch (e: any) {
            console.log('Audio setup:', e.message);
        }
    }, [audioRef.current, isSpeaking]);

    // Lip sync animation with smooth, natural movement
    useFrame((_, delta) => {
        if (!headRef.current || !headRef.current.morphTargetInfluences) return;

        const morphDict = morphTargetDictRef.current;
        const influences = headRef.current.morphTargetInfluences;
        const smoothSpeed = 8 * delta;

        let targetMouth = 0;
        let targetAA = 0, targetE = 0, targetO = 0, targetI = 0;

        if (isSpeaking && analyserRef.current) {
            const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
            analyserRef.current.getByteFrequencyData(dataArray);

            // Voice frequency analysis
            const bass = dataArray.slice(0, 4).reduce((a, b) => a + b, 0) / 4 / 255;
            const mid = dataArray.slice(4, 16).reduce((a, b) => a + b, 0) / 12 / 255;
            const high = dataArray.slice(16, 40).reduce((a, b) => a + b, 0) / 24 / 255;
            const overall = (bass + mid * 2 + high) / 4;

            if (overall > 0.03) {
                targetMouth = Math.min(0.7, overall * 2);

                // Natural viseme variation based on frequencies
                if (bass > mid * 0.8) {
                    // Low sounds: O, U
                    targetO = targetMouth * 0.8;
                    targetAA = targetMouth * 0.3;
                } else if (high > mid * 1.2) {
                    // High sounds: E, I, S
                    targetE = targetMouth * 0.7;
                    targetI = targetMouth * 0.5;
                } else {
                    // Mid sounds: A, mixed
                    targetAA = targetMouth * 0.8;
                    targetE = targetMouth * 0.2;
                }
            }
        }

        // Smooth interpolation
        currentMouthOpen.current += (targetMouth - currentMouthOpen.current) * smoothSpeed;
        currentVisemeBlend.current.aa += (targetAA - currentVisemeBlend.current.aa) * smoothSpeed;
        currentVisemeBlend.current.E += (targetE - currentVisemeBlend.current.E) * smoothSpeed;
        currentVisemeBlend.current.O += (targetO - currentVisemeBlend.current.O) * smoothSpeed;
        currentVisemeBlend.current.I += (targetI - currentVisemeBlend.current.I) * smoothSpeed;

        // Apply visemes
        const applyMorph = (name: string, value: number) => {
            const idx = morphDict[name];
            if (idx !== undefined && influences[idx] !== undefined) {
                influences[idx] = Math.max(0, Math.min(1, value));
            }
        };

        applyMorph('viseme_aa', currentVisemeBlend.current.aa);
        applyMorph('viseme_E', currentVisemeBlend.current.E);
        applyMorph('viseme_O', currentVisemeBlend.current.O);
        applyMorph('viseme_I', currentVisemeBlend.current.I);
        applyMorph('viseme_U', currentVisemeBlend.current.O * 0.5);

        // Mouth open blend shape
        applyMorph('mouthOpen', currentMouthOpen.current * 0.4);
        applyMorph('jawOpen', currentMouthOpen.current * 0.3);

        // Subtle idle animation when speaking stops
        if (!isSpeaking && currentMouthOpen.current < 0.02) {
            applyMorph('viseme_sil', 0.1);
        }
    });

    return (
        <primitive
            object={scene}
            scale={3.5}
            position={[0, -5.5, 0]}
            rotation={[0, 0, 0]}
        />
    );
}

interface TalkingAvatarProps {
    audioRef: React.RefObject<HTMLAudioElement | null>;
    isSpeaking: boolean;
}

export default function TalkingAvatar({ audioRef, isSpeaking }: TalkingAvatarProps) {
    return (
        <div className="w-full h-full bg-gradient-to-br from-slate-800 via-slate-900 to-slate-950">
            <Canvas
                camera={{ position: [0, 0.2, 2.5], fov: 28 }}
                gl={{ antialias: true, alpha: true }}
            >
                <ambientLight intensity={1.2} />
                <directionalLight position={[2, 2, 5]} intensity={1.5} />
                <directionalLight position={[-2, 1, 3]} intensity={0.8} />
                <pointLight position={[0, 1, 2]} intensity={0.6} />

                <Suspense fallback={null}>
                    <Avatar audioRef={audioRef} isSpeaking={isSpeaking} />
                </Suspense>

                <OrbitControls
                    enableZoom={false}
                    enablePan={false}
                    enableRotate={false}
                    target={[0, 0.2, 0]}
                />
            </Canvas>
        </div>
    );
}
