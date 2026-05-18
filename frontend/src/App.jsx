import { useState, useEffect, useRef } from "react"
import Onboarding from "./Onboarding"
import LandingPage from "./LandingPage"

const API = "http://localhost:8000"

const STATUS_CONFIG = {
  idle:            { color: "text-notion-muted",  dot: "bg-notion-faint",   label: "Ready" },
  calling:         { color: "text-notion-yellow", dot: "bg-notion-yellow",  label: "Dialing…",   blink: true },
  active:          { color: "text-notion-green",  dot: "bg-notion-green",   label: "Live Call",  blink: true },
  ended:           { color: "text-notion-blue",   dot: "bg-notion-blue",    label: "Call Ended" },
  followup_active: { color: "text-notion-purple", dot: "bg-notion-purple",  label: "Follow-up",  blink: true },
}

const INITIAL_SCHEDULE = {
  saturday: {
    label: "Saturday 10:00 AM",
    type: "Beginner Mat",
    capacity: 4,
    enrolled: [],
    status: "open",
  },
  tuesday: {
    label: "Tuesday 6:00 PM",
    type: "Beginner Mat",
    capacity: 6,
    enrolled: [],
    status: "open",
  },
  thursday: {
    label: "Thursday 7:00 PM",
    type: "Reformer Advanced",
    capacity: 6,
    enrolled: [],
    status: "waitlist",
  },
}

// ─── Shared sub-components ────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.idle
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-notion-border bg-white text-xs font-medium ${cfg.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot} ${cfg.blink ? "blink" : ""}`} />
      {cfg.label}
    </div>
  )
}

function Card({ children, className = "" }) {
  return (
    <div className={`bg-white rounded-xl border border-notion-border shadow-notion ${className}`}>
      {children}
    </div>
  )
}

function SectionLabel({ children, right }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <span className="text-[11px] font-semibold text-notion-muted uppercase tracking-widest">{children}</span>
      {right && <span className="text-[11px] text-notion-faint">{right}</span>}
    </div>
  )
}

function PipelineStep({ label, done, index }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-notion-border last:border-0 transition-all duration-500">
      <div className={`w-5 h-5 rounded-md flex items-center justify-center text-[11px] font-bold flex-shrink-0 transition-all duration-500 ${
        done ? "bg-notion-green text-white" : "bg-notion-hover text-notion-faint border border-notion-border"
      }`}>
        {done ? "✓" : index}
      </div>
      <span className={`text-sm flex-1 transition-colors duration-500 ${done ? "text-notion-text" : "text-notion-muted"}`}>
        {label}
      </span>
      {done && (
        <span className="text-[10px] font-medium text-notion-green bg-notion-greenBg px-2 py-0.5 rounded-full">
          Done
        </span>
      )}
    </div>
  )
}

function TranscriptBubble({ turn }) {
  const isAgent = turn.role === "agent"
  return (
    <div className="slide-in flex gap-2.5 mb-3">
      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5 ${
        isAgent ? "bg-notion-greenBg text-notion-green" : "bg-notion-blueBg text-notion-blue"
      }`}>
        {isAgent ? "M" : "S"}
      </div>
      <div className="flex-1 min-w-0">
        <div className={`text-[10px] font-semibold mb-1 uppercase tracking-wider ${
          isAgent ? "text-notion-green" : "text-notion-blue"
        }`}>
          {isAgent ? "Maya" : "Sarah"}
        </div>
        <div className="text-sm text-notion-text leading-relaxed">{turn.text}</div>
      </div>
    </div>
  )
}

function MossEntry({ query }) {
  return (
    <div className="slide-in mb-3 last:mb-0">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-notion-yellow text-xs">⚡</span>
        <span className="text-xs text-notion-text font-medium flex-1 truncate">
          "{query.query.slice(0, 48)}{query.query.length > 48 ? "…" : ""}"
        </span>
        <span className="text-[11px] font-semibold text-notion-green bg-notion-greenBg px-2 py-0.5 rounded-full flex-shrink-0">
          {query.latency_ms}ms
        </span>
      </div>
      <div className="text-xs text-notion-muted leading-relaxed pl-5">
        {query.result.slice(0, 100)}{query.result.length > 100 ? "…" : ""}
      </div>
    </div>
  )
}

function ApiLogLine({ icon, text, color }) {
  return (
    <div className={`slide-in flex items-start gap-2 text-sm py-1.5 border-b border-notion-border last:border-0 ${color}`}>
      <span className="flex-shrink-0 mt-0.5">{icon}</span>
      <span>{text}</span>
    </div>
  )
}

// ─── Main App ────────────────────────────────────────────────────────────────

export default function App() {
  const [showLanding,    setShowLanding]    = useState(true)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [activeTab, setActiveTab]           = useState("live")

  const [status, setStatus]               = useState("idle")
  const [lead, setLead]                   = useState({ name: "Sarah K.", phone: "+17143101206", email: "quachphuwork@gmail.com" })
  const [transcript, setTranscript]       = useState([])
  const [mossQueries, setMossQueries]     = useState([])
  const [pipeline, setPipeline]           = useState({
    call_connected: false,
    objection_handled: false,
    email_sent: false,
    stripe_paid: false,
    memory_saved: false,
  })
  const [stripeEvent, setStripeEvent]     = useState(null)
  const [memoryRecall, setMemoryRecall]   = useState(null)
  const [callDuration, setCallDuration]   = useState(0)
  const [errorMsg, setErrorMsg]           = useState(null)
  const [lastActivity, setLastActivity]   = useState("")
  const [schedule, setSchedule]           = useState(INITIAL_SCHEDULE)
  const [feedbackSent, setFeedbackSent]   = useState(false)

  const transcriptRef = useRef(null)
  const timerRef      = useRef(null)
  const esRef         = useRef(null)

  // ── SSE ──────────────────────────────────────────────────────────────────

  const connectSSE = () => {
    if (esRef.current) esRef.current.close()
    const es = new EventSource(`${API}/api/events`)
    esRef.current = es
    es.onmessage = (e) => { try { handleEvent(JSON.parse(e.data)) } catch {} }
    es.onerror   = () => { es.close(); setTimeout(connectSSE, 2000) }
  }

  useEffect(() => {
    connectSSE()
    return () => { if (esRef.current) esRef.current.close() }
  }, [])

  useEffect(() => {
    if (transcriptRef.current)
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
  }, [transcript])

  const handleEvent = (event) => {
    if (event.type === "ping") return
    setLastActivity(new Date().toLocaleTimeString())
    switch (event.type) {
      case "state":
        setStatus(event.data.status)
        setPipeline(event.data.pipeline || {})
        setTranscript(event.data.transcript || [])
        setMossQueries(event.data.moss_queries || [])
        if (event.data.memory_recall) setMemoryRecall(event.data.memory_recall)
        break
      case "status_change":
        setStatus(event.data.status)
        break
      case "transcript":
        setTranscript(prev => [...prev, event.data])
        break
      case "moss_query":
        setMossQueries(prev => [...prev, event.data])
        break
      case "pipeline_update":
        setPipeline(prev => ({ ...prev, [event.data.key]: event.data.value }))
        break
      case "stripe_paid":
        setStripeEvent(event.data)
        // Auto-enroll Sarah in Saturday class on payment
        setSchedule(prev => ({
          ...prev,
          saturday: {
            ...prev.saturday,
            enrolled: [
              ...prev.saturday.enrolled,
              {
                name: "Sarah K.",
                phone: "+17143101206",
                email: "quachphuwork@gmail.com",
                status: "confirmed",
                paidAt: new Date().toLocaleTimeString(),
              },
            ],
          },
        }))
        break
      case "memory_recall":
        setMemoryRecall(event.data.content)
        break
      case "call_ended":
        setStatus("ended")
        break
    }
  }

  // ── Call timer ────────────────────────────────────────────────────────────

  useEffect(() => {
    if (status === "active" || status === "followup_active") {
      timerRef.current = setInterval(() => setCallDuration(d => d + 1), 1000)
    } else {
      clearInterval(timerRef.current)
      if (status === "idle") setCallDuration(0)
    }
    return () => clearInterval(timerRef.current)
  }, [status])

  const formatTime = (s) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`

  // ── API actions ───────────────────────────────────────────────────────────

  const startCampaign = async () => {
    setTranscript([]); setMossQueries([]); setStripeEvent(null)
    setMemoryRecall(null); setCallDuration(0); setErrorMsg(null)
    setFeedbackSent(false)
    try {
      const res  = await fetch(`${API}/api/start-campaign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead }),
      })
      const data = await res.json()
      if (data.error) { setErrorMsg(data.detail || data.error); setStatus("idle") }
    } catch {
      setErrorMsg("Backend not reachable — is uvicorn running?")
      setStatus("idle")
    }
  }

  const simulatePayment  = () => fetch(`${API}/api/simulate-payment`, { method: "POST" })
  const triggerFollowup  = () => { setMemoryRecall(null); fetch(`${API}/api/followup-call`, { method: "POST" }) }
  const sendFeedback     = async () => {
    await fetch(`${API}/api/send-feedback`, { method: "POST" })
    setFeedbackSent(true)
  }

  const isCallActive   = status === "active" || status === "calling"
  const completedSteps = Object.values(pipeline).filter(Boolean).length

  // ── Sub-views ─────────────────────────────────────────────────────────────

  const TabBar = () => (
    <div className="flex items-center gap-1 border-b border-notion-border mb-5 px-1">
      {[
        { id: "live",     icon: "📞", label: "Live Call" },
        { id: "schedule", icon: "📅", label: "Class Schedule" },
        { id: "leads",    icon: "👥", label: "Leads" },
      ].map(tab => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-all -mb-px ${
            activeTab === tab.id
              ? "border-[#37352f] text-[#37352f]"
              : "border-transparent text-[#9b9a97] hover:text-[#787774]"
          }`}
        >
          <span>{tab.icon}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  )

  const ScheduleTab = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(schedule).map(([key, cls]) => {
          const spotsLeft = cls.capacity - cls.enrolled.length
          const fullness  = cls.enrolled.length / cls.capacity

          return (
            <div key={key} className="bg-white rounded-xl border border-notion-border p-5 shadow-notion">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-semibold text-notion-text text-sm">{cls.label}</div>
                  <div className="text-notion-muted text-xs mt-0.5">{cls.type} · 60 min</div>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  cls.status === "waitlist" ? "bg-notion-yellowBg text-notion-yellow" :
                  spotsLeft === 0           ? "bg-notion-redBg text-notion-red" :
                                             "bg-notion-greenBg text-notion-green"
                }`}>
                  {cls.status === "waitlist" ? "Waitlist" : spotsLeft === 0 ? "Full" : `${spotsLeft} open`}
                </span>
              </div>

              {/* Capacity bar */}
              <div className="mb-4">
                <div className="flex justify-between text-xs text-notion-faint mb-1">
                  <span>Capacity</span>
                  <span>{cls.enrolled.length}/{cls.capacity}</span>
                </div>
                <div className="h-1.5 bg-notion-hover rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      fullness >= 1    ? "bg-notion-red" :
                      fullness >= 0.75 ? "bg-notion-yellow" :
                                        "bg-notion-green"
                    }`}
                    style={{ width: `${Math.min(fullness * 100, 100)}%` }}
                  />
                </div>
              </div>

              {/* Enrolled students */}
              <div className="space-y-0">
                {cls.enrolled.length === 0 ? (
                  <div className="text-notion-faint text-xs text-center py-3">No enrollments yet</div>
                ) : (
                  cls.enrolled.map((student, i) => (
                    <div key={i} className="flex items-center justify-between py-1.5 border-b border-notion-border last:border-0">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-notion-purpleBg flex items-center justify-center text-xs font-semibold text-notion-purple">
                          {student.name[0]}
                        </div>
                        <div>
                          <div className="text-notion-text text-xs font-medium">{student.name}</div>
                          <div className="text-notion-faint text-xs">{student.email}</div>
                        </div>
                      </div>
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        student.status === "confirmed"
                          ? "bg-notion-greenBg text-notion-green"
                          : "bg-notion-yellowBg text-notion-yellow"
                      }`}>
                        {student.status === "confirmed" ? "✓ Paid" : "Pending"}
                      </span>
                    </div>
                  ))
                )}
                {/* Empty spots */}
                {Array.from({ length: Math.max(0, spotsLeft) }).map((_, i) => (
                  <div key={`empty-${i}`} className="py-1.5 border-b border-notion-border last:border-0">
                    <div className="text-notion-faint text-xs italic">Open spot</div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Summary row */}
      <Card className="p-4">
        <div className="grid grid-cols-4 gap-4 text-center">
          {[
            { label: "Total Classes This Week", value: "3" },
            { label: "Total Capacity",          value: "16" },
            {
              label: "Confirmed Bookings",
              value: `${Object.values(schedule).reduce((a, c) => a + c.enrolled.filter(e => e.status === "confirmed").length, 0)}`,
            },
            {
              label: "Revenue This Week",
              value: `$${Object.values(schedule).reduce((a, c) => a + c.enrolled.filter(e => e.status === "confirmed").length * 1, 0)}`,
            },
          ].map(stat => (
            <div key={stat.label}>
              <div className="text-xl font-bold text-notion-text">{stat.value}</div>
              <div className="text-notion-faint text-xs mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )

  const LeadsTab = () => {
    const rows = [
      {
        name:        lead.name,
        phone:       lead.phone,
        email:       lead.email,
        called:      pipeline.call_connected,
        emailSent:   pipeline.email_sent,
        paid:        pipeline.stripe_paid,
        memorySaved: pipeline.memory_saved,
      },
    ]

    return (
      <Card className="overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-notion-border bg-notion-hover">
              {["Lead", "Phone", "Email", "Called", "Email Sent", "Paid", "Memory"].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-notion-faint uppercase tracking-widest">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-notion-border last:border-0 hover:bg-notion-hover transition-colors">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-notion-purpleBg flex items-center justify-center text-xs font-semibold text-notion-purple">
                      {row.name[0]}
                    </div>
                    <span className="font-medium text-notion-text text-sm">{row.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-notion-muted font-mono">{row.phone}</td>
                <td className="px-4 py-3 text-sm text-notion-muted">{row.email}</td>
                {[row.called, row.emailSent, row.paid, row.memorySaved].map((done, j) => (
                  <td key={j} className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      done ? "bg-notion-greenBg text-notion-green" : "bg-notion-hover text-notion-faint"
                    }`}>
                      {done ? "✓ Done" : "Pending"}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    )
  }

  // ── Landing page gate ─────────────────────────────────────────────────────

  if (showLanding) {
    return <LandingPage onLogin={() => { setShowLanding(false); setShowOnboarding(true); }} />
  }

  // ── Onboarding gate ───────────────────────────────────────────────────────

  if (showOnboarding) {
    return <Onboarding onComplete={(data) => {
      if (data?.leads?.length > 0) setLead(data.leads[0])
      setShowOnboarding(false)
    }} />
  }

  // ── Main dashboard ────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-notion-bg" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* ── Top nav ─────────────────────────────────────────────────────── */}
      <nav className="bg-white border-b border-notion-border sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-notion-text flex items-center justify-center text-white font-bold text-sm select-none">A</div>
            <div>
              <div className="text-sm font-semibold text-notion-text leading-none">Apex</div>
              <div className="text-[11px] text-notion-faint leading-none mt-0.5">AI Receptionist Agent · CoreFlow Pilates</div>
            </div>
          </div>

          {/* Pipeline dots */}
          <div className="hidden md:flex items-center gap-1.5">
            {["call_connected","objection_handled","email_sent","stripe_paid","memory_saved"].map(key => (
              <div
                key={key}
                title={key.replace(/_/g, " ")}
                className={`w-2 h-2 rounded-full transition-all duration-500 ${pipeline[key] ? "bg-notion-green" : "bg-notion-border"}`}
              />
            ))}
            <span className="text-[11px] text-notion-muted ml-1 font-medium">{completedSteps} / 5</span>
          </div>

          <div className="flex items-center gap-3">
            {lastActivity && (
              <span className="hidden sm:block text-[11px] text-notion-faint">Last event {lastActivity}</span>
            )}
            <StatusBadge status={status} />
            <button
              onClick={startCampaign}
              disabled={isCallActive}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-notion-text text-white text-sm font-medium transition-all hover:bg-[#1a1a1a] disabled:bg-notion-border disabled:text-notion-faint disabled:cursor-not-allowed"
            >
              {status === "calling" ? "Dialing…" : status === "active" ? "In Progress" : "▶  Start Campaign"}
            </button>
          </div>
        </div>
      </nav>

      {/* ── Error banner ────────────────────────────────────────────────── */}
      {errorMsg && (
        <div className="max-w-7xl mx-auto px-6 pt-4">
          <div className="bg-notion-redBg border border-red-200 rounded-xl px-4 py-3 text-sm text-notion-red flex items-center gap-2">
            <span>⚠</span> {errorMsg}
          </div>
        </div>
      )}

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-6 py-5">
        <TabBar />

        {/* ── Live Call tab ──────────────────────────────────────────────── */}
        {activeTab === "live" && (
          <div className="space-y-4">

            {/* Row 1: Lead Info | Transcript | Pipeline */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

              {/* Lead Queue */}
              <Card className="p-5">
                <SectionLabel right="1 lead">Lead Queue</SectionLabel>

                <div className={`rounded-lg border p-4 transition-all duration-500 ${
                  status !== "idle" ? "border-green-200 bg-notion-greenBg" : "border-notion-border"
                }`}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 transition-all ${
                      status === "active"          ? "bg-notion-green blink" :
                      status === "calling"         ? "bg-notion-yellow blink" :
                      status === "ended"           ? "bg-notion-blue" :
                      status === "followup_active" ? "bg-notion-purple blink" :
                      "bg-notion-border"
                    }`} />
                    <span className="font-semibold text-notion-text text-sm">{lead.name}</span>
                    {pipeline.stripe_paid && (
                      <span className="ml-auto text-[11px] font-semibold text-notion-green bg-notion-greenBg border border-green-200 px-2 py-0.5 rounded-full">
                        Paid ✓
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-notion-muted font-mono space-y-0.5">
                    <div>{lead.phone}</div>
                    <div>{lead.email}</div>
                  </div>
                  <div className="text-[11px] text-notion-faint mt-2">Prospect · Pilates Interest · $1 trial</div>
                  {(status === "active" || status === "followup_active") && (
                    <div className="mt-2 text-xs font-mono font-semibold text-notion-green">⏱ {formatTime(callDuration)}</div>
                  )}
                </div>

                {/* Demo buttons */}
                <div className="mt-4 space-y-2">
                  <div className="text-[11px] font-semibold text-notion-muted uppercase tracking-widest">Demo Controls</div>
                  <button
                    onClick={simulatePayment}
                    className="w-full text-xs py-2 px-3 rounded-lg border border-notion-border hover:bg-notion-hover text-notion-muted hover:text-notion-text transition-colors text-left flex items-center gap-2"
                  >
                    <span>💳</span> Simulate Stripe Payment
                  </button>
                  <button
                    onClick={triggerFollowup}
                    className="w-full text-xs py-2 px-3 rounded-lg border border-notion-border hover:bg-notion-hover text-notion-muted hover:text-notion-text transition-colors text-left flex items-center gap-2"
                  >
                    <span>🧠</span> Trigger Follow-up Call
                  </button>
                </div>

                {/* Tech stack */}
                <div className="mt-4 pt-4 border-t border-notion-border">
                  <div className="text-[11px] font-semibold text-notion-muted uppercase tracking-widest mb-2">Powered By</div>
                  <div className="flex flex-wrap gap-1.5">
                    {["AgentPhone", "Gemini", "Moss", "Supermemory", "AgentMail", "Stripe"].map(t => (
                      <span key={t} className="text-[11px] px-2 py-0.5 rounded-md border border-notion-border text-notion-muted bg-notion-hover font-medium">{t}</span>
                    ))}
                  </div>
                </div>
              </Card>

              {/* Transcript */}
              <Card className="p-5 flex flex-col">
                <SectionLabel right={transcript.length > 0 ? `${transcript.length} turns` : undefined}>
                  {status === "active" ? `Active Call · ${formatTime(callDuration)}` : "Call Transcript"}
                </SectionLabel>

                <div ref={transcriptRef} className="flex-1 overflow-y-auto max-h-72 pr-1">
                  {transcript.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-notion-faint text-sm text-center leading-loose">
                      <div className="text-2xl mb-2 opacity-40">🎙</div>
                      Transcript will appear here<br />during the live call
                    </div>
                  ) : (
                    transcript.map((turn, i) => <TranscriptBubble key={i} turn={turn} />)
                  )}
                </div>

                {status === "active" && (
                  <div className="mt-3 pt-3 border-t border-notion-border flex items-center gap-1">
                    {[...Array(14)].map((_, i) => (
                      <div
                        key={i}
                        className="wave-bar w-0.5 bg-notion-green rounded-full"
                        style={{ height: `${8 + (i % 5) * 4}px`, animationDelay: `${i * 0.07}s` }}
                      />
                    ))}
                    <span className="text-[11px] font-semibold text-notion-green ml-2">Live</span>
                  </div>
                )}
              </Card>

              {/* Pipeline */}
              <Card className="p-5">
                <SectionLabel right={`${completedSteps}/5 complete`}>Sales Pipeline</SectionLabel>

                <div className="h-1.5 bg-notion-border rounded-full overflow-hidden mb-4">
                  <div
                    className="h-full bg-notion-green rounded-full transition-all duration-700"
                    style={{ width: `${(completedSteps / 5) * 100}%` }}
                  />
                </div>

                <div>
                  <PipelineStep index={1} label="Call Connected"             done={pipeline.call_connected} />
                  <PipelineStep index={2} label="Objection Handled (Moss)"   done={pipeline.objection_handled} />
                  <PipelineStep index={3} label="Follow-up Email Sent"       done={pipeline.email_sent} />
                  <PipelineStep index={4} label="Stripe Payment Received"    done={pipeline.stripe_paid} />
                  <PipelineStep index={5} label="Memory Saved (Supermemory)" done={pipeline.memory_saved} />
                </div>

                {/* Stripe success card */}
                {stripeEvent && (
                  <div className="mt-4 rounded-lg border border-green-200 bg-notion-greenBg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-base">💰</span>
                      <span className="text-sm font-semibold text-notion-green">Payment Succeeded</span>
                    </div>
                    <div className="text-xs text-notion-text font-mono">
                      {stripeEvent.customer} · ${typeof stripeEvent.amount === "number" ? stripeEvent.amount.toFixed(2) : stripeEvent.amount} USD
                    </div>
                    <div className="text-[11px] text-notion-muted mt-0.5">CoreFlow Pilates Trial Class</div>
                  </div>
                )}

                {/* Memory recall card */}
                {memoryRecall && (
                  <div className="mt-3 rounded-lg border border-purple-200 bg-notion-purpleBg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-base">🧠</span>
                      <span className="text-xs font-semibold text-notion-purple">Supermemory Recall</span>
                    </div>
                    <div className="text-xs text-notion-text leading-relaxed">
                      {memoryRecall.slice(0, 200)}{memoryRecall.length > 200 ? "…" : ""}
                    </div>
                  </div>
                )}

                {/* Post-class follow-up — shown after payment */}
                {pipeline.stripe_paid && (
                  <div className="mt-4 border border-notion-border rounded-xl overflow-hidden">
                    <div className="px-4 py-3 bg-notion-hover border-b border-notion-border">
                      <div className="text-xs font-semibold text-notion-text uppercase tracking-widest">
                        Post-Class Follow-up
                      </div>
                    </div>
                    <div className="p-4">
                      <p className="text-xs text-notion-muted mb-3 leading-relaxed">
                        After Saturday's class, Sofia will send personalized feedback directly to Sarah.
                      </p>
                      <div className="space-y-2 mb-4 text-xs text-notion-text">
                        <div className="flex items-start gap-2">
                          <span className="text-notion-green mt-0.5">✓</span>
                          <span>What went well in the session</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-notion-green mt-0.5">✓</span>
                          <span>Focus areas and personalized homework</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-notion-green mt-0.5">✓</span>
                          <span>Link to book next class</span>
                        </div>
                      </div>

                      {!feedbackSent ? (
                        <button
                          onClick={sendFeedback}
                          className="w-full py-2 bg-notion-purple hover:bg-[#5a35a0] text-white rounded-lg text-xs font-semibold transition-colors"
                        >
                          📝 Send Instructor Feedback Email
                        </button>
                      ) : (
                        <div className="flex items-center gap-2 py-2 px-3 bg-notion-purpleBg rounded-lg">
                          <span className="text-notion-purple">✓</span>
                          <span className="text-notion-purple text-xs font-medium">
                            Feedback sent to quachphuwork@gmail.com
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </Card>
            </div>

            {/* Row 2: Moss Log | API Activity */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              <Card className="p-5">
                <SectionLabel right={mossQueries.length > 0 ? `${mossQueries.length} ${mossQueries.length === 1 ? "query" : "queries"}` : undefined}>
                  ⚡ Moss Real-Time Retrieval
                </SectionLabel>
                {mossQueries.length === 0 ? (
                  <div className="flex items-center justify-center h-24 text-notion-faint text-sm text-center">
                    Semantic queries fire &lt;10ms when lead asks a question…
                  </div>
                ) : (
                  mossQueries.map((q, i) => <MossEntry key={i} query={q} />)
                )}
              </Card>

              <Card className="p-5">
                <SectionLabel>API Activity Log</SectionLabel>
                <div>
                  {!pipeline.call_connected && status === "idle" ? (
                    <div className="flex items-center justify-center h-24 text-notion-faint text-sm">
                      Waiting for campaign to start…
                    </div>
                  ) : (
                    <>
                      {pipeline.call_connected && (
                        <ApiLogLine icon="📞" color="text-notion-green"
                          text={`AgentPhone · outbound call → ${lead.phone}`} />
                      )}
                      {transcript.length > 0 && (
                        <ApiLogLine icon="✦" color="text-notion-text"
                          text={`Gemini 2.5 Flash · ${transcript.filter(t => t.role === "agent").length} agent responses`} />
                      )}
                      {mossQueries.length > 0 && (
                        <ApiLogLine icon="⚡" color="text-notion-yellow"
                          text={`Moss · ${mossQueries.length} semantic ${mossQueries.length === 1 ? "query" : "queries"} · avg ${Math.round(mossQueries.reduce((a, b) => a + b.latency_ms, 0) / mossQueries.length)}ms`} />
                      )}
                      {pipeline.email_sent && (
                        <ApiLogLine icon="✉" color="text-notion-blue"
                          text={`AgentMail · follow-up → ${lead.email}`} />
                      )}
                      {pipeline.email_sent && (
                        <ApiLogLine icon="🔗" color="text-notion-blue"
                          text="Stripe · checkout session · $1.00 USD" />
                      )}
                      {pipeline.stripe_paid && (
                        <ApiLogLine icon="✓" color="text-notion-green"
                          text="Stripe · payment_intent.succeeded · $1.00" />
                      )}
                      {pipeline.stripe_paid && (
                        <ApiLogLine icon="✉" color="text-notion-green"
                          text={`AgentMail · booking confirmation → ${lead.email}`} />
                      )}
                      {pipeline.memory_saved && (
                        <ApiLogLine icon="🧠" color="text-notion-purple"
                          text={`Supermemory · transcript stored · ${lead.phone}`} />
                      )}
                      {memoryRecall && (
                        <ApiLogLine icon="↩" color="text-notion-purple"
                          text="Supermemory · context recalled for follow-up call" />
                      )}
                      {feedbackSent && (
                        <ApiLogLine icon="📝" color="text-notion-purple"
                          text={`AgentMail · instructor feedback → ${lead.email}`} />
                      )}
                    </>
                  )}
                </div>
              </Card>
            </div>
          </div>
        )}

        {activeTab === "schedule" && <ScheduleTab />}
        {activeTab === "leads"    && <LeadsTab />}
      </div>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <span className="text-[11px] text-notion-faint">Apex · AI Receptionist Agent</span>
        <span className="text-[11px] text-notion-faint">Built for Call My Agent Hackathon @ YC · May 17, 2026</span>
      </footer>
    </div>
  )
}
