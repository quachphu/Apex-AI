import { useState, useRef } from "react"

const BUSINESS_TYPES = [
  { id: "fitness",     icon: "🧘", label: "Fitness & Wellness",    description: "Pilates, yoga, gyms, personal training" },
  { id: "realestate",  icon: "🏠", label: "Real Estate",           description: "Agents, brokers, property managers" },
  { id: "restaurant",  icon: "🍽️", label: "Restaurant & Events",   description: "Reservations, catering, events" },
  { id: "beauty",      icon: "💆", label: "Beauty & Spa",          description: "Salons, spas, med spas" },
  { id: "other",       icon: "📦", label: "Other Business",        description: "Any outbound sales workflow" },
]

export default function Onboarding({ onComplete }) {
  const [step, setStep]                   = useState(1)
  const [selectedBusiness, setSelectedBusiness] = useState("fitness")
  const [uploadStatus, setUploadStatus]   = useState("idle") // idle | uploading | done
  const [leadsPreview, setLeadsPreview]   = useState([])
  const [businessName, setBusinessName]   = useState("CoreFlow Pilates")
  const fileRef                           = useRef(null)

  // Normalise a phone number to E.164 (+1XXXXXXXXXX for US)
  const normalisePhone = (raw) => {
    const digits = raw.replace(/\D/g, "")
    if (digits.length === 10) return `+1${digits}`
    if (digits.length === 11 && digits.startsWith("1")) return `+${digits}`
    return raw.trim() // return as-is if already international format
  }

  const parseCSV = (text) => {
    const lines = text.trim().split(/\r?\n/)
    if (lines.length < 2) return []
    const headers = lines[0].split(",").map(h => h.trim().toLowerCase())
    const nameIdx  = headers.findIndex(h => h === "name")
    const phoneIdx = headers.findIndex(h => h === "phone")
    const emailIdx = headers.findIndex(h => h === "email")
    if (nameIdx < 0 || phoneIdx < 0) return []
    return lines.slice(1)
      .filter(l => l.trim())
      .map(line => {
        const cols = line.split(",").map(c => c.trim().replace(/^"|"$/g, ""))
        return {
          name:  cols[nameIdx]  || "",
          phone: normalisePhone(cols[phoneIdx] || ""),
          email: emailIdx >= 0 ? (cols[emailIdx] || "") : "",
        }
      })
      .filter(l => l.name && l.phone)
  }

  const handleFileUpload = (file) => {
    if (!file) return
    setUploadStatus("uploading")
    const reader = new FileReader()
    reader.onload = (e) => {
      const parsed = parseCSV(e.target.result)
      if (parsed.length > 0) {
        setLeadsPreview(parsed)
        setUploadStatus("done")
      } else {
        setUploadStatus("idle")
        alert("Could not read leads. Make sure columns are: name, phone, email")
      }
    }
    reader.readAsText(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  }

  const handleUseDemoData = () => {
    setUploadStatus("uploading")
    setTimeout(() => {
      setLeadsPreview([
        { name: "Sarah K.", phone: "+17143101206", email: "quachphuwork@gmail.com" }
      ])
      setUploadStatus("done")
    }, 600)
  }

  const selectedType = BUSINESS_TYPES.find(b => b.id === selectedBusiness)

  return (
    <div className="min-h-screen bg-[#f7f6f3] flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-[#0f9b58] rounded-lg flex items-center justify-center text-white font-bold text-sm select-none">A</div>
            <span className="text-2xl font-semibold text-[#37352f]">Apex</span>
          </div>
          <p className="text-[#787774] text-sm">AI Receptionist Agent — Setup</p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3].map(s => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-300 ${
                s < step  ? "bg-[#0f9b58] text-white" :
                s === step ? "bg-[#37352f] text-white" :
                             "bg-[#e9e8e4] text-[#9b9a97]"
              }`}>
                {s < step ? "✓" : s}
              </div>
              {s < 3 && (
                <div className={`w-12 h-0.5 transition-all duration-300 ${s < step ? "bg-[#0f9b58]" : "bg-[#e9e8e4]"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-[#e9e8e4] shadow-sm p-8">

          {/* ── STEP 1: Business type ────────────────────────────────── */}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-semibold text-[#37352f] mb-1">What kind of business are you?</h2>
              <p className="text-[#787774] text-sm mb-6">Apex customizes the AI agent and sales script for your industry.</p>

              <div className="space-y-2 mb-6">
                {BUSINESS_TYPES.map(bt => (
                  <button
                    key={bt.id}
                    onClick={() => setSelectedBusiness(bt.id)}
                    className={`w-full flex items-center gap-4 p-4 rounded-xl border text-left transition-all ${
                      selectedBusiness === bt.id
                        ? "border-[#0f9b58] bg-[#f0fdf4]"
                        : "border-[#e9e8e4] hover:border-[#c9c8c4] hover:bg-[#fafaf8]"
                    }`}
                  >
                    <span className="text-2xl">{bt.icon}</span>
                    <div className="flex-1">
                      <div className="font-medium text-[#37352f] text-sm">{bt.label}</div>
                      <div className="text-[#9b9a97] text-xs">{bt.description}</div>
                    </div>
                    {selectedBusiness === bt.id && (
                      <div className="w-5 h-5 rounded-full bg-[#0f9b58] flex items-center justify-center flex-shrink-0">
                        <span className="text-white text-xs">✓</span>
                      </div>
                    )}
                  </button>
                ))}
              </div>

              <div className="mb-6">
                <label className="block text-xs font-semibold text-[#787774] uppercase tracking-widest mb-2">
                  Business Name
                </label>
                <input
                  type="text"
                  value={businessName}
                  onChange={e => setBusinessName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-[#e9e8e4] text-[#37352f] text-sm focus:outline-none focus:border-[#0f9b58] transition-colors bg-white"
                  placeholder="Your business name"
                />
              </div>

              <button
                onClick={() => setStep(2)}
                className="w-full py-3 bg-[#37352f] hover:bg-[#2f2d28] text-white rounded-xl font-medium text-sm transition-colors"
              >
                Continue →
              </button>
            </div>
          )}

          {/* ── STEP 2: Upload leads ─────────────────────────────────── */}
          {step === 2 && (
            <div>
              <h2 className="text-xl font-semibold text-[#37352f] mb-1">Upload your customer list</h2>
              <p className="text-[#787774] text-sm mb-6">
                CSV with columns: <code className="bg-[#f7f6f3] px-1.5 py-0.5 rounded text-xs font-mono">name, phone, email</code>
              </p>

              {uploadStatus !== "done" ? (
                <>
                  <div
                    onDrop={handleDrop}
                    onDragOver={e => e.preventDefault()}
                    onClick={() => fileRef.current?.click()}
                    className="border-2 border-dashed border-[#e9e8e4] rounded-xl p-10 text-center cursor-pointer hover:border-[#0f9b58] hover:bg-[#f0fdf4] transition-all mb-4"
                  >
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".csv"
                      className="hidden"
                      onChange={e => handleFileUpload(e.target.files[0])}
                    />
                    {uploadStatus === "uploading" ? (
                      <div className="text-[#0f9b58] text-sm font-medium">Uploading…</div>
                    ) : (
                      <>
                        <div className="text-3xl mb-2">📎</div>
                        <div className="text-[#37352f] text-sm font-medium">Drop CSV file here</div>
                        <div className="text-[#9b9a97] text-xs mt-1">or click to browse</div>
                      </>
                    )}
                  </div>

                  <div className="relative flex items-center mb-4">
                    <div className="flex-1 h-px bg-[#e9e8e4]" />
                    <span className="px-3 text-[#9b9a97] text-xs">or</span>
                    <div className="flex-1 h-px bg-[#e9e8e4]" />
                  </div>

                  <button
                    onClick={handleUseDemoData}
                    className="w-full py-3 border border-[#e9e8e4] hover:border-[#0f9b58] text-[#37352f] rounded-xl font-medium text-sm transition-colors"
                  >
                    Use demo data (Sarah K.)
                  </button>
                </>
              ) : (
                <div>
                  <div className="bg-[#f0fdf4] border border-[#0f9b58]/30 rounded-xl p-4 mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-[#0f9b58] text-sm font-semibold">✓ {leadsPreview.length} lead loaded</span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-[#9b9a97] uppercase tracking-widest">
                            <th className="text-left pb-2 pr-4 font-semibold">Name</th>
                            <th className="text-left pb-2 pr-4 font-semibold">Phone</th>
                            <th className="text-left pb-2 font-semibold">Email</th>
                          </tr>
                        </thead>
                        <tbody>
                          {leadsPreview.map((lead, i) => (
                            <tr key={i} className="text-[#37352f]">
                              <td className="pr-4 py-1 font-medium">{lead.name}</td>
                              <td className="pr-4 py-1 font-mono">{lead.phone}</td>
                              <td className="py-1">{lead.email}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => { setUploadStatus("idle"); setLeadsPreview([]) }}
                      className="flex-1 py-3 border border-[#e9e8e4] text-[#787774] rounded-xl text-sm hover:bg-[#fafaf8] transition-colors"
                    >
                      Re-upload
                    </button>
                    <button
                      onClick={() => setStep(3)}
                      className="flex-1 py-3 bg-[#37352f] hover:bg-[#2f2d28] text-white rounded-xl font-medium text-sm transition-colors"
                    >
                      Continue →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── STEP 3: Confirm and launch ───────────────────────────── */}
          {step === 3 && (
            <div>
              <h2 className="text-xl font-semibold text-[#37352f] mb-1">Ready to launch</h2>
              <p className="text-[#787774] text-sm mb-6">Review your setup, then start your campaign.</p>

              <div className="space-y-3 mb-8">
                <div className="flex items-center justify-between p-4 bg-[#fafaf8] rounded-xl border border-[#e9e8e4]">
                  <div>
                    <div className="text-xs text-[#9b9a97] uppercase tracking-widest mb-0.5 font-semibold">Business</div>
                    <div className="text-[#37352f] font-medium text-sm">{businessName}</div>
                    <div className="text-[#9b9a97] text-xs">{selectedType?.label}</div>
                  </div>
                  <span className="text-2xl">{selectedType?.icon}</span>
                </div>

                <div className="flex items-center justify-between p-4 bg-[#fafaf8] rounded-xl border border-[#e9e8e4]">
                  <div>
                    <div className="text-xs text-[#9b9a97] uppercase tracking-widest mb-0.5 font-semibold">Leads</div>
                    <div className="text-[#37352f] font-medium text-sm">{leadsPreview.length} contact{leadsPreview.length !== 1 ? "s" : ""} loaded</div>
                    <div className="text-[#9b9a97] text-xs">{leadsPreview[0]?.name} · {leadsPreview[0]?.phone}</div>
                  </div>
                  <span className="text-[#0f9b58] text-lg">✓</span>
                </div>

                <div className="flex items-center justify-between p-4 bg-[#fafaf8] rounded-xl border border-[#e9e8e4]">
                  <div>
                    <div className="text-xs text-[#9b9a97] uppercase tracking-widest mb-0.5 font-semibold">AI Agent</div>
                    <div className="text-[#37352f] font-medium text-sm">Maya — Fitness &amp; Wellness SDR</div>
                    <div className="text-[#9b9a97] text-xs">AgentPhone + Gemini 2.5 Flash + Moss</div>
                  </div>
                  <span className="text-[#0f9b58] text-lg">✓</span>
                </div>

                <div className="flex items-center justify-between p-4 bg-[#fafaf8] rounded-xl border border-[#e9e8e4]">
                  <div>
                    <div className="text-xs text-[#9b9a97] uppercase tracking-widest mb-0.5 font-semibold">Follow-up</div>
                    <div className="text-[#37352f] font-medium text-sm">AgentMail + Stripe</div>
                    <div className="text-[#9b9a97] text-xs">Email + $1 payment link on close</div>
                  </div>
                  <span className="text-[#0f9b58] text-lg">✓</span>
                </div>
              </div>

              <button
                onClick={() => onComplete({ leads: leadsPreview, businessName, businessType: selectedBusiness })}
                className="w-full py-4 bg-[#0f9b58] hover:bg-[#0d8a4f] text-white rounded-xl font-semibold text-base transition-colors"
              >
                Launch Apex →
              </button>
            </div>
          )}
        </div>

        {/* Back button */}
        {step > 1 && (
          <button
            onClick={() => setStep(s => s - 1)}
            className="mt-4 mx-auto block text-[#9b9a97] text-sm hover:text-[#37352f] transition-colors"
          >
            ← Back
          </button>
        )}
      </div>
    </div>
  )
}
