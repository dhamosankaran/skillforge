import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { motion, useInView } from "framer-motion";
import { ScanLine, Brain, Target, ShieldCheck, BookOpen, UserCheck, Zap } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { capture } from "@/utils/posthog";

/* ═══════════════════════════════════════════════════════════════
   SKILLFORGE LANDING PAGE — "Midnight Forge" Theme

   Conversion architecture:
   1. Hero → immediate value prop + CTA (scan free)
   2. The Loop → visual showing scan→gaps→study→ace
   3. Social proof → "Engineers from Google, Meta..."
   4. Three engines → Lens, Forge, Mission
   5. How it works → 3 steps, animated
   6. Pricing → Free vs Pro
   7. Final CTA → urgency
   ═══════════════════════════════════════════════════════════════ */

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } }
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } }
};

export default function LandingPage() {
  const { user } = useAuth();
  const ctaTo = user ? "/study" : "/login";

  // Acquisition funnel entry point. Fires once per mount.
  useEffect(() => {
    capture('landing_page_viewed');
  }, []);

  return (
    <div style={{
      background: "var(--sf-bg-primary)",
      color: "var(--sf-text-primary)",
      fontFamily: "var(--sf-font-body)",
      overflow: "hidden",
    }}>
      <LandingNavbar ctaTo={ctaTo} />
      <Hero ctaTo={ctaTo} />
      <LogoBar />
      <TheLoop />
      <ThreeEngines />
      <HowItWorks />
      <Pricing ctaTo={ctaTo} />
      <Trust />
      <FinalCTA ctaTo={ctaTo} />
      <Footer />
    </div>
  );
}

/* ── NAVBAR ── */

function LandingNavbar({ ctaTo }: { ctaTo: string }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <nav style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      zIndex: 100,
      padding: "0 24px",
      height: 64,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      background: scrolled ? "rgba(6,6,10,0.85)" : "transparent",
      backdropFilter: scrolled ? "blur(20px) saturate(180%)" : "none",
      borderBottom: scrolled ? "1px solid var(--sf-border-subtle)" : "1px solid transparent",
      transition: "all 300ms ease",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: "var(--sf-gradient-cta)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14, fontWeight: 700, color: "var(--sf-text-on-accent)",
        }}>S</div>
        <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.03em", fontFamily: "var(--sf-font-display)" }}>
          SkillForge
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
        <a href="#how" style={{ color: "var(--sf-text-secondary)", textDecoration: "none", fontSize: 14, fontWeight: 500 }}>How it works</a>
        <a href="#pricing" style={{ color: "var(--sf-text-secondary)", textDecoration: "none", fontSize: 14, fontWeight: 500 }}>Pricing</a>
        <Link to="/login" style={{ color: "var(--sf-text-secondary)", textDecoration: "none", fontSize: 14, fontWeight: 500 }}>Log in</Link>
        <Link
          to={ctaTo}
          className="sf-btn-primary"
          style={{ padding: "8px 20px", fontSize: 13 }}
          onClick={() => capture('cta_clicked', { button: 'hero' })}
        >
          Start Free
        </Link>
      </div>
    </nav>
  );
}

/* ── HERO ── */

function Hero({ ctaTo }: { ctaTo: string }) {
  return (
    <section style={{
      position: "relative",
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      padding: "120px 24px 80px",
    }}>
      {/* Background glow */}
      <div style={{
        position: "absolute",
        top: "-20%",
        left: "50%",
        transform: "translateX(-50%)",
        width: "120%",
        height: "80%",
        background: "radial-gradient(ellipse at center, rgba(0,212,255,0.08) 0%, rgba(123,97,255,0.04) 40%, transparent 70%)",
        pointerEvents: "none",
      }} />

      {/* Grid overlay */}
      <div style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `
          linear-gradient(rgba(148,148,168,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(148,148,168,0.03) 1px, transparent 1px)
        `,
        backgroundSize: "60px 60px",
        maskImage: "radial-gradient(ellipse at center, black 30%, transparent 70%)",
        WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 70%)",
        pointerEvents: "none",
      }} />

      <motion.div
        initial="hidden"
        animate="visible"
        variants={stagger}
        style={{ position: "relative", maxWidth: 800 }}
      >
        <motion.div variants={fadeUp}>
          <span className="sf-badge sf-badge-cyan" style={{ marginBottom: 24, display: "inline-flex" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--sf-accent-primary)", animation: "sfPulse 2s infinite" }} />
            NOW IN BETA
          </span>
        </motion.div>

        <motion.h1 variants={fadeUp} style={{
          fontSize: "clamp(40px, 6vw, 72px)",
          fontWeight: 800,
          lineHeight: 1.05,
          letterSpacing: "-0.04em",
          fontFamily: "var(--sf-font-display)",
          margin: "0 0 24px",
        }}>
          Ace your next{" "}
          <span className="sf-gradient-text">
            engineering interview
          </span>
        </motion.h1>

        <motion.p variants={fadeUp} style={{
          fontSize: "clamp(16px, 2vw, 20px)",
          color: "var(--sf-text-secondary)",
          lineHeight: 1.6,
          maxWidth: 580,
          margin: "0 auto 40px",
        }}>
          Scan your resume, study your gaps with AI-powered spaced repetition, and walk into every interview prepared.
        </motion.p>

        <motion.div variants={fadeUp} style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <Link
            to={ctaTo}
            className="sf-btn-primary"
            style={{ fontSize: 16, padding: "14px 36px", textDecoration: "none" }}
            onClick={() => capture('cta_clicked', { button: 'hero' })}
          >
            Start Free →
          </Link>
          <a
            href="#how"
            className="sf-btn-secondary"
            style={{ fontSize: 16, padding: "14px 36px" }}
            onClick={() => capture('cta_clicked', { button: 'how_it_works' })}
          >
            See how it works
          </a>
        </motion.div>

        <motion.p variants={fadeUp} style={{
          fontSize: 13,
          color: "var(--sf-text-tertiary)",
          marginTop: 16,
        }}>
          Join 500+ engineers studying smarter. No credit card required.
        </motion.p>
      </motion.div>

      <style>{`@keyframes sfPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }`}</style>
    </section>
  );
}

/* ── LOGO BAR ── */

function LogoBar() {
  const logos = ["Google", "Meta", "Amazon", "Microsoft", "Stripe", "Netflix"];
  return (
    <section style={{
      padding: "40px 24px",
      textAlign: "center",
      borderTop: "1px solid var(--sf-border-subtle)",
      borderBottom: "1px solid var(--sf-border-subtle)",
    }}>
      <p style={{ fontSize: 13, color: "var(--sf-text-tertiary)", marginBottom: 24, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600 }}>
        Engineers from these companies trust SkillForge
      </p>
      <div style={{ display: "flex", justifyContent: "center", gap: 48, flexWrap: "wrap", opacity: 0.35 }}>
        {logos.map(name => (
          <span key={name} style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--sf-font-display)", color: "var(--sf-text-primary)", letterSpacing: "-0.02em" }}>
            {name}
          </span>
        ))}
      </div>
    </section>
  );
}

/* ── THE LOOP (core value prop visual) ── */

function TheLoop() {
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const steps = [
    { icon: "📄", label: "Scan", desc: "Upload your resume", color: "var(--sf-accent-primary)" },
    { icon: "🔍", label: "Gaps", desc: "AI finds weak spots", color: "var(--sf-accent-secondary)" },
    { icon: "🧠", label: "Study", desc: "FSRS spaced repetition", color: "var(--sf-accent-warm)" },
    { icon: "🎯", label: "Ace", desc: "Interview ready", color: "var(--sf-accent-success)" },
  ];

  return (
    <section ref={ref} style={{ padding: "96px 24px", textAlign: "center" }}>
      <motion.div initial="hidden" animate={isInView ? "visible" : "hidden"} variants={stagger}>
        <motion.p variants={fadeUp} className="sf-badge sf-badge-purple" style={{ margin: "0 auto 16px", display: "inline-flex" }}>
          THE SKILLFORGE LOOP
        </motion.p>
        <motion.h2 variants={fadeUp} style={{
          fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 800,
          fontFamily: "var(--sf-font-display)", letterSpacing: "-0.03em",
          margin: "0 0 16px",
        }}>
          One loop. Zero gaps.
        </motion.h2>
        <motion.p variants={fadeUp} style={{ color: "var(--sf-text-secondary)", maxWidth: 500, margin: "0 auto 56px", fontSize: 17 }}>
          Most platforms stop at scanning. We close the entire loop from resume to offer letter.
        </motion.p>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 24,
          maxWidth: 720,
          margin: "0 auto",
        }}>
          {steps.map((step, i) => (
            <motion.div key={step.label} variants={fadeUp} className="sf-card" style={{
              padding: "32px 20px",
              textAlign: "center",
              position: "relative",
            }}>
              {i < steps.length - 1 && (
                <div style={{
                  position: "absolute", right: -16, top: "50%", transform: "translateY(-50%)",
                  color: "var(--sf-text-tertiary)", fontSize: 20, zIndex: 2,
                }} className="sf-loop-arrow">→</div>
              )}
              <div style={{ fontSize: 32, marginBottom: 12 }}>{step.icon}</div>
              <div style={{ fontWeight: 700, fontSize: 18, fontFamily: "var(--sf-font-display)", marginBottom: 4 }}>{step.label}</div>
              <div style={{ fontSize: 13, color: "var(--sf-text-secondary)" }}>{step.desc}</div>
              <div style={{
                position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%)",
                width: "60%", height: 2, borderRadius: 1,
                background: step.color, opacity: 0.5,
              }} />
            </motion.div>
          ))}
        </div>
      </motion.div>

      <style>{`
        @media (max-width: 640px) { .sf-loop-arrow { display: none !important; } }
        @media (min-width: 641px) { .sf-loop-arrow { display: block; } }
      `}</style>
    </section>
  );
}

/* ── THREE ENGINES ── */

function ThreeEngines() {
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const engines = [
    {
      name: "Lens",
      tagline: "ATS Scanner",
      desc: "Upload your resume. Our AI scores it against real ATS systems, surfaces skill gaps, and tells you exactly what to fix.",
      badge: "FREE",
      badgeClass: "sf-badge-cyan",
      gradient: "linear-gradient(135deg, rgba(0,212,255,0.1) 0%, transparent 60%)",
      border: "rgba(0,212,255,0.2)",
    },
    {
      name: "Forge",
      tagline: "Study Engine",
      desc: "177 expert-crafted flashcards with FSRS spaced repetition. Your gaps become your study plan. 5 cards a day, every day.",
      badge: "CORE",
      badgeClass: "sf-badge-purple",
      gradient: "linear-gradient(135deg, rgba(123,97,255,0.1) 0%, transparent 60%)",
      border: "rgba(123,97,255,0.2)",
    },
    {
      name: "Mission",
      tagline: "Interview Sprint",
      desc: "Set a target date. We build a countdown study plan. Daily targets, streak pressure, and a completion certificate.",
      badge: "PRO",
      badgeClass: "sf-badge-warm",
      gradient: "linear-gradient(135deg, rgba(255,138,80,0.1) 0%, transparent 60%)",
      border: "rgba(255,138,80,0.2)",
    },
  ];

  return (
    <section ref={ref} style={{ padding: "96px 24px", background: "var(--sf-bg-secondary)" }}>
      <motion.div initial="hidden" animate={isInView ? "visible" : "hidden"} variants={stagger} style={{ maxWidth: 1080, margin: "0 auto" }}>
        <motion.div variants={fadeUp} style={{ textAlign: "center", marginBottom: 56 }}>
          <h2 style={{
            fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 800,
            fontFamily: "var(--sf-font-display)", letterSpacing: "-0.03em", margin: "0 0 16px",
          }}>
            Three engines.{" "}
            <span className="sf-gradient-text">One platform.</span>
          </h2>
          <p style={{ color: "var(--sf-text-secondary)", maxWidth: 500, margin: "0 auto", fontSize: 17 }}>
            From scanning to studying to shipping — everything you need to level up.
          </p>
        </motion.div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24 }}>
          {engines.map(engine => (
            <motion.div key={engine.name} variants={fadeUp} style={{
              background: engine.gradient,
              border: `1px solid ${engine.border}`,
              borderRadius: "var(--sf-radius-lg)",
              padding: "36px 28px",
              transition: "all 300ms ease",
            }}>
              <span className={`sf-badge ${engine.badgeClass}`} style={{ marginBottom: 20, display: "inline-flex" }}>
                {engine.badge}
              </span>
              <h3 style={{
                fontSize: 28, fontWeight: 800, fontFamily: "var(--sf-font-display)",
                letterSpacing: "-0.02em", margin: "0 0 4px",
              }}>
                {engine.name}
              </h3>
              <p style={{ fontSize: 14, color: "var(--sf-text-secondary)", fontWeight: 600, marginBottom: 16 }}>
                {engine.tagline}
              </p>
              <p style={{ fontSize: 15, color: "var(--sf-text-secondary)", lineHeight: 1.6, margin: 0 }}>
                {engine.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}

/* ── HOW IT WORKS ── */

function HowItWorks() {
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const steps = [
    { icon: <ScanLine size={24} />, title: "Scan your resume", desc: "Drop your PDF. Our AI runs it through real ATS scoring and surfaces every skill gap — in 30 seconds.", color: "var(--sf-accent-primary)" },
    { icon: <Brain size={24} />, title: "Study your gaps", desc: "Each gap maps to expert flashcards. FSRS schedules reviews at the optimal moment. 5 cards a day builds mastery.", color: "var(--sf-accent-secondary)" },
    { icon: <Target size={24} />, title: "Ace the interview", desc: "Track your progress with skill radar. Set a Mission countdown for your interview date. Show up prepared.", color: "var(--sf-accent-warm)" },
  ];

  return (
    <section ref={ref} id="how" style={{ padding: "96px 24px" }}>
      <motion.div initial="hidden" animate={isInView ? "visible" : "hidden"} variants={stagger} style={{ maxWidth: 800, margin: "0 auto" }}>
        <motion.div variants={fadeUp} style={{ textAlign: "center", marginBottom: 56 }}>
          <p className="sf-badge sf-badge-cyan" style={{ margin: "0 auto 16px", display: "inline-flex" }}>HOW IT WORKS</p>
          <h2 style={{ fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 800, fontFamily: "var(--sf-font-display)", letterSpacing: "-0.03em", margin: 0 }}>
            Three steps to interview-ready
          </h2>
        </motion.div>

        <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
          {steps.map(step => (
            <motion.div key={step.title} variants={fadeUp} style={{
              display: "flex", gap: 24, alignItems: "flex-start",
              padding: "28px",
              borderRadius: "var(--sf-radius-lg)",
              border: "1px solid var(--sf-border-subtle)",
              background: "var(--sf-bg-tertiary)",
            }}>
              <div style={{
                minWidth: 48, height: 48, borderRadius: "var(--sf-radius-md)",
                background: `${step.color}15`,
                border: `1px solid ${step.color}30`,
                display: "flex", alignItems: "center", justifyContent: "center",
                color: step.color,
                flexShrink: 0,
              }}>
                {step.icon}
              </div>
              <div>
                <h3 style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--sf-font-display)", margin: "0 0 8px", letterSpacing: "-0.02em" }}>
                  {step.title}
                </h3>
                <p style={{ fontSize: 15, color: "var(--sf-text-secondary)", lineHeight: 1.6, margin: 0 }}>
                  {step.desc}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}

/* ── PRICING ── */

function Pricing({ ctaTo }: { ctaTo: string }) {
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} id="pricing" style={{ padding: "96px 24px", background: "var(--sf-bg-secondary)" }}>
      <motion.div initial="hidden" animate={isInView ? "visible" : "hidden"} variants={stagger} style={{ maxWidth: 880, margin: "0 auto" }}>
        <motion.div variants={fadeUp} style={{ textAlign: "center", marginBottom: 56 }}>
          <h2 style={{ fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 800, fontFamily: "var(--sf-font-display)", letterSpacing: "-0.03em", margin: "0 0 16px" }}>
            Simple pricing. No surprises.
          </h2>
          <p style={{ color: "var(--sf-text-secondary)", fontSize: 17 }}>
            Start free. Upgrade when you're serious.
          </p>
        </motion.div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 24 }}>
          {/* Free */}
          <motion.div variants={fadeUp} style={{
            padding: "36px 32px",
            borderRadius: "var(--sf-radius-lg)",
            border: "1px solid var(--sf-border-subtle)",
            background: "var(--sf-bg-tertiary)",
          }}>
            <p style={{ fontSize: 14, color: "var(--sf-text-tertiary)", fontWeight: 600, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>Free</p>
            <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginBottom: 24 }}>
              <span style={{ fontSize: 48, fontWeight: 800, fontFamily: "var(--sf-font-display)", letterSpacing: "-0.04em" }}>$0</span>
              <span style={{ color: "var(--sf-text-tertiary)", fontSize: 14 }}>/forever</span>
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 32px", display: "flex", flexDirection: "column", gap: 12 }}>
              {["15 study cards", "1 ATS resume scan", "Daily review", "Basic skill gap report"].map(f => (
                <li key={f} style={{ fontSize: 14, color: "var(--sf-text-secondary)", display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ color: "var(--sf-accent-success)", fontSize: 16 }}>✓</span> {f}
                </li>
              ))}
            </ul>
            <Link
              to={ctaTo}
              className="sf-btn-secondary"
              style={{ display: "block", textAlign: "center", textDecoration: "none" }}
              onClick={() => capture('cta_clicked', { button: 'pricing' })}
            >
              Get started free
            </Link>
          </motion.div>

          {/* Pro */}
          <motion.div variants={fadeUp} style={{
            padding: "36px 32px",
            borderRadius: "var(--sf-radius-lg)",
            border: "2px solid var(--sf-accent-primary)",
            background: "var(--sf-bg-tertiary)",
            position: "relative",
            boxShadow: "var(--sf-glow-accent)",
          }}>
            <span className="sf-badge sf-badge-cyan" style={{
              position: "absolute", top: -12, left: 32,
            }}>MOST POPULAR</span>
            <p style={{ fontSize: 14, color: "var(--sf-text-tertiary)", fontWeight: 600, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>Pro</p>
            <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginBottom: 24 }}>
              <span style={{ fontSize: 48, fontWeight: 800, fontFamily: "var(--sf-font-display)", letterSpacing: "-0.04em" }}>$49</span>
              <span style={{ color: "var(--sf-text-tertiary)", fontSize: 14 }}>/month</span>
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 32px", display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                "Everything in Free",
                "Unlimited study cards",
                "Unlimited ATS scans",
                "Mission Mode — interview countdown",
                "Streak freeze",
                "FSRS spaced repetition (Daily 5)",
                "Skill radar + activity heatmap",
                "Daily email reminders",
              ].map(f => (
                <li key={f} style={{ fontSize: 14, color: "var(--sf-text-secondary)", display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ color: "var(--sf-accent-primary)", fontSize: 16 }}>✓</span> {f}
                </li>
              ))}
            </ul>
            <Link
              to={ctaTo}
              className="sf-btn-primary"
              style={{ display: "block", textAlign: "center", textDecoration: "none", width: "100%", boxSizing: "border-box" }}
              onClick={() => capture('cta_clicked', { button: 'pricing' })}
            >
              Start Pro — $49/mo →
            </Link>
            <p style={{ fontSize: 12, color: "var(--sf-text-tertiary)", textAlign: "center", marginTop: 12 }}>
              Cancel anytime. No contracts.
            </p>
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}

/* ── FINAL CTA ── */

function FinalCTA({ ctaTo }: { ctaTo: string }) {
  return (
    <section style={{
      padding: "96px 24px",
      textAlign: "center",
      position: "relative",
    }}>
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse at center, rgba(123,97,255,0.08) 0%, transparent 60%)",
        pointerEvents: "none",
      }} />
      <div style={{ position: "relative", maxWidth: 600, margin: "0 auto" }}>
        <h2 style={{
          fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 800,
          fontFamily: "var(--sf-font-display)", letterSpacing: "-0.03em",
          margin: "0 0 16px",
        }}>
          Your next interview is{" "}
          <span className="sf-gradient-text">coming.</span>
        </h2>
        <p style={{ fontSize: 17, color: "var(--sf-text-secondary)", marginBottom: 36, lineHeight: 1.6 }}>
          The engineers who get $200K+ offers aren't smarter. They're more prepared. Start your first scan in 30 seconds.
        </p>
        <Link
          to={ctaTo}
          className="sf-btn-primary"
          style={{ fontSize: 17, padding: "16px 40px", textDecoration: "none" }}
          onClick={() => capture('cta_clicked', { button: 'hero' })}
        >
          Start Free →
        </Link>
      </div>
    </section>
  );
}

/* ── TRUST ── */

function Trust() {
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const items = [
    { icon: <Zap size={24} />, title: "AI-powered spaced repetition", desc: "FSRS algorithm schedules reviews at the optimal moment for long-term retention." },
    { icon: <BookOpen size={24} />, title: "177+ expert-curated cards", desc: "Covering system design, algorithms, behavioral, and more — written by senior engineers." },
    { icon: <UserCheck size={24} />, title: "Personalized to your resume gaps", desc: "Our ATS scanner identifies exactly what you're missing and builds a study plan around it." },
    { icon: <ShieldCheck size={24} />, title: "Built by engineers, for engineers", desc: "We've been through the interview grind. SkillForge is the tool we wished we had." },
  ];

  return (
    <section ref={ref} style={{ padding: "96px 24px" }}>
      <motion.div initial="hidden" animate={isInView ? "visible" : "hidden"} variants={stagger} style={{ maxWidth: 880, margin: "0 auto" }}>
        <motion.div variants={fadeUp} style={{ textAlign: "center", marginBottom: 56 }}>
          <p className="sf-badge sf-badge-purple" style={{ margin: "0 auto 16px", display: "inline-flex" }}>WHY SKILLFORGE</p>
          <h2 style={{
            fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 800,
            fontFamily: "var(--sf-font-display)", letterSpacing: "-0.03em", margin: 0,
          }}>
            Everything you need to{" "}
            <span className="sf-gradient-text">level up</span>
          </h2>
        </motion.div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 24,
        }}>
          {items.map(item => (
            <motion.div key={item.title} variants={fadeUp} style={{
              padding: "28px 24px",
              borderRadius: "var(--sf-radius-lg)",
              border: "1px solid var(--sf-border-subtle)",
              background: "var(--sf-bg-tertiary)",
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: "var(--sf-radius-md)",
                background: "rgba(123,97,255,0.1)",
                border: "1px solid rgba(123,97,255,0.2)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "var(--sf-accent-secondary)",
                marginBottom: 16,
              }}>
                {item.icon}
              </div>
              <h3 style={{
                fontSize: 16, fontWeight: 700, fontFamily: "var(--sf-font-display)",
                letterSpacing: "-0.02em", margin: "0 0 8px",
              }}>
                {item.title}
              </h3>
              <p style={{ fontSize: 14, color: "var(--sf-text-secondary)", lineHeight: 1.6, margin: 0 }}>
                {item.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}

/* ── FOOTER ── */

function Footer() {
  return (
    <footer style={{
      padding: "48px 24px 32px",
      borderTop: "1px solid var(--sf-border-subtle)",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      flexWrap: "wrap",
      gap: 16,
      maxWidth: 1080,
      margin: "0 auto",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          width: 24, height: 24, borderRadius: 6,
          background: "var(--sf-gradient-cta)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 11, fontWeight: 700, color: "var(--sf-text-on-accent)",
        }}>S</div>
        <span style={{ fontSize: 14, fontWeight: 600, fontFamily: "var(--sf-font-display)" }}>SkillForge</span>
      </div>
      <p style={{ fontSize: 13, color: "var(--sf-text-tertiary)", margin: 0 }}>
        © 2026 SkillForge. All rights reserved.
      </p>
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <a href="#how" style={{ color: "var(--sf-text-tertiary)", textDecoration: "none", fontSize: 13 }}>About</a>
        <a href="#pricing" style={{ color: "var(--sf-text-tertiary)", textDecoration: "none", fontSize: 13 }}>Pricing</a>
        <a href="/privacy" style={{ color: "var(--sf-text-tertiary)", textDecoration: "none", fontSize: 13 }}>Privacy</a>
        <a href="/terms" style={{ color: "var(--sf-text-tertiary)", textDecoration: "none", fontSize: 13 }}>Terms</a>
        <a href="mailto:hello@theskillsforge.dev" style={{ color: "var(--sf-text-tertiary)", textDecoration: "none", fontSize: 13 }}>Contact</a>
      </div>
    </footer>
  );
}
