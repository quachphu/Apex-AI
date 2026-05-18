import { useEffect, useRef } from 'react';
import { ArrowRight, Phone, Globe, X } from 'lucide-react';

const VIDEO_SOURCE =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260328_115001_bcdaa3b4-03de-47e7-ad63-ae3e392c32d4.mp4';

const FADE_DURATION_MS = 500;
const FADE_OUT_SECONDS_REMAINING = 0.55;

const navLinks = [
  { label: 'Features', href: '#features' },
  { label: 'Pricing',  href: '#pricing'  },
  { label: 'About',    href: '#about'    },
];

export default function LandingPage({ onLogin }) {
  const videoRef    = useRef(null);
  const frameRef    = useRef(null);
  const fadingOutRef = useRef(false);

  const cancelFade = () => {
    if (frameRef.current !== null) {
      window.cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }
  };

  const fadeVideoTo = (targetOpacity) => {
    const video = videoRef.current;
    if (!video) return;
    cancelFade();
    const startOpacity = parseFloat(video.style.opacity || '0');
    const startTime    = performance.now();
    const animate = (now) => {
      const progress    = Math.min((now - startTime) / FADE_DURATION_MS, 1);
      video.style.opacity = String(startOpacity + (targetOpacity - startOpacity) * progress);
      if (progress < 1) frameRef.current = window.requestAnimationFrame(animate);
      else { video.style.opacity = String(targetOpacity); frameRef.current = null; }
    };
    frameRef.current = window.requestAnimationFrame(animate);
  };

  const playVideo = async () => {
    try { await videoRef.current?.play(); } catch { /* blocked */ }
  };

  const startFromBeginning = () => {
    const video = videoRef.current;
    if (!video) return;
    cancelFade();
    video.style.opacity = '0';
    window.setTimeout(() => {
      if (!videoRef.current) return;
      videoRef.current.currentTime = 0;
      fadingOutRef.current = false;
      void playVideo();
      fadeVideoTo(1);
    }, 100);
  };

  const handleLoadedData = () => {
    if (!videoRef.current) return;
    videoRef.current.style.opacity = '0';
    fadingOutRef.current = false;
    void playVideo();
    fadeVideoTo(1);
  };

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (!video || !Number.isFinite(video.duration)) return;
    const remaining = video.duration - video.currentTime;
    if (remaining <= FADE_OUT_SECONDS_REMAINING && !fadingOutRef.current) {
      fadingOutRef.current = true;
      fadeVideoTo(0);
    }
  };

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.style.opacity = '0';
      void playVideo();
    }
    return () => cancelFade();
  }, []);

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-black text-white">
      {/* Background video */}
      <video
        ref={videoRef}
        className="absolute inset-0 h-full w-full translate-y-[17%] object-cover"
        src={VIDEO_SOURCE}
        muted
        autoPlay
        playsInline
        preload="auto"
        onLoadedData={handleLoadedData}
        onTimeUpdate={handleTimeUpdate}
        onEnded={startFromBeginning}
      />

      {/* Overlays */}
      <div className="absolute inset-0 bg-black/35" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.2)_45%,rgba(0,0,0,0.78)_100%)]" />
      <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black via-black/25 to-transparent" />

      {/* Nav */}
      <div className="relative z-20 px-6 py-6">
        <nav className="liquid-glass mx-auto flex max-w-5xl items-center justify-between rounded-full px-6 py-3">
          <div className="flex items-center gap-8">
            <a href="#home" className="flex items-center gap-2 text-lg font-semibold text-white">
              <Phone size={20} aria-hidden="true" />
              <span>Apex</span>
            </a>
            <div className="hidden items-center gap-8 md:flex">
              {navLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  className="text-sm font-medium text-white/80 transition-colors hover:text-white"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              className="text-sm font-medium text-white transition-colors hover:text-white/80"
              type="button"
              onClick={onLogin}
            >
              Sign Up
            </button>
            <button
              className="liquid-glass rounded-full px-6 py-2 text-sm font-medium text-white transition-all hover:bg-white/10"
              type="button"
              onClick={onLogin}
            >
              Login
            </button>
          </div>
        </nav>
      </div>

      {/* Hero */}
      <section className="relative z-10 flex flex-1 -translate-y-[20%] flex-col items-center justify-center px-6 py-12 text-center">
        {/* Pill badge */}
        <div className="liquid-glass mb-6 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium text-white/70">
          <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
          Built for the YC Call My Agent Hackathon · May 2026
        </div>

        <h1
          className="mb-4 text-5xl tracking-tight text-white md:text-6xl lg:text-7xl"
          style={{ fontFamily: "'Instrument Serif', serif" }}
        >
          Your AI Agent Receptionist
        </h1>

        <p className="mb-10 max-w-xl text-base text-white/60 leading-relaxed">
          Apex calls your leads, qualifies them, handles objections in real time,
          and closes with a payment link — all without lifting a finger.
        </p>

        <div className="flex flex-col items-center gap-4 w-full max-w-md">
          <button
            type="button"
            onClick={onLogin}
            className="w-full liquid-glass flex items-center justify-center gap-3 rounded-full py-3.5 px-8 text-base font-semibold text-white transition-all hover:bg-white/10 hover:scale-[1.02]"
          >
            Launch Demo
            <ArrowRight size={18} />
          </button>

          <p className="text-xs text-white/40">
            No setup needed · Powered by Gemini 2.5 · AgentPhone · Stripe
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 flex justify-center gap-4 pb-10">
        <a
          href="https://twitter.com"
          aria-label="X (Twitter)"
          className="liquid-glass rounded-full p-4 text-white/70 transition-all hover:bg-white/5 hover:text-white"
        >
          <X size={18} aria-hidden="true" />
        </a>
        <a
          href="https://github.com"
          aria-label="Website"
          className="liquid-glass rounded-full p-4 text-white/70 transition-all hover:bg-white/5 hover:text-white"
        >
          <Globe size={18} aria-hidden="true" />
        </a>
      </footer>
    </main>
  );
}
