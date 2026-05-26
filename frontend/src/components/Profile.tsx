import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'
import type { Profile as ProfileData } from '@/lib/api'

const DIMS = [
  { dim: 'energy',    label: 'Energy',   desc: 'How you recharge',    a: 'Chill',      b: 'Chaotic',      av: 'chill',    bv: 'chaotic' },
  { dim: 'filter',    label: 'Filter',   desc: 'How direct you are',  a: 'Clean',      b: 'Unfiltered',   av: 'clean',    bv: 'unfiltered' },
  { dim: 'style',     label: 'Style',    desc: 'How you communicate', a: 'Punchy',     b: 'Dramatic',     av: 'punchy',   bv: 'dramatic' },
  { dim: 'tone',      label: 'Tone',     desc: 'Your emotional lean', a: 'Sincere',    b: 'Sarcastic',    av: 'sincere',  bv: 'sarcastic' },
  { dim: 'lang_lean', label: 'Language', desc: 'Your Hinglish mix',   a: 'Hindi-lean', b: 'English-lean', av: 'hindi',    bv: 'english' },
]

interface ProfileProps {
  onSave?: (profile: ProfileData) => void
  onClose: () => void
}

export function Profile({ onSave, onClose }: ProfileProps) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [profileId, setProfileId] = useState<string | undefined>()
  const [name, setName] = useState('')
  const [personality, setPersonality] = useState<Record<string, string>>({})
  const [vibe, setVibe] = useState('')

  useEffect(() => {
    api.getProfiles().then(res => {
      const active = res.profiles.find(p => p.profile_id === res.active_id) ?? res.profiles[0]
      if (active) {
        setProfileId(active.profile_id)
        setName(active.name)
        setPersonality(active.personality ?? {})
        setVibe(active.custom_vibe ?? '')
      }
    }).finally(() => setLoading(false))
  }, [])

  const setDim = (dim: string, val: string) => setPersonality(p => ({ ...p, [dim]: val }))

  const handleSave = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      const saved = await api.saveProfile({ profile_id: profileId, name: name.trim(), personality, custom_vibe: vibe })
      onSave?.(saved)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteSpeakers = async () => {
    await api.deleteAllSpeakers()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 rounded-full border-2 border-white/10 border-t-indigo-400 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-widest text-white/30 mb-2">Name</label>
        <input value={name} onChange={e => setName(e.target.value)} maxLength={64}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white/80 placeholder-white/25 outline-none focus:border-indigo-500/40 transition-colors" />
      </div>

      <div className="space-y-2">
        {DIMS.map(d => (
          <div key={d.dim} className="flex items-center justify-between rounded-xl bg-white/3 border border-white/8 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-white/70">{d.label}</p>
              <p className="text-xs text-white/30">{d.desc}</p>
            </div>
            <div className="flex gap-1.5">
              {[{ label: d.a, val: d.av }, { label: d.b, val: d.bv }].map(opt => (
                <button key={opt.val} onClick={() => setDim(d.dim, opt.val)}
                  className={cn('px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
                    personality[d.dim] === opt.val
                      ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300'
                      : 'bg-white/3 border-white/10 text-white/40 hover:border-white/20 hover:text-white/60',
                  )}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div>
        <label className="block text-xs font-semibold uppercase tracking-widest text-white/30 mb-2">
          Custom Vibe <span className="normal-case font-normal">(optional)</span>
        </label>
        <textarea value={vibe} onChange={e => setVibe(e.target.value)} maxLength={400} rows={2}
          placeholder="e.g. like a chaotic Delhi college kid who's always running late…"
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white/80 placeholder-white/25 outline-none resize-none focus:border-indigo-500/40 transition-colors" />
      </div>

      <div className="flex gap-2 pt-1">
        <button onClick={onClose}
          className="flex-1 py-2.5 rounded-xl text-sm font-medium bg-white/5 hover:bg-white/8 text-white/50 border border-white/10 transition-colors">
          Cancel
        </button>
        <button onClick={handleSave} disabled={saving || !name.trim()}
          className="flex-[2] py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white transition-all disabled:opacity-50">
          {saving ? 'Saving…' : 'Save Changes ✓'}
        </button>
      </div>

      <div className="pt-2 border-t border-white/8">
        <p className="text-xs font-semibold uppercase tracking-widest text-red-500/50 mb-2">Danger Zone</p>
        <button onClick={handleDeleteSpeakers}
          className="px-4 py-2 rounded-xl text-xs font-medium bg-red-500/8 hover:bg-red-500/14 text-red-400 border border-red-500/20 transition-colors">
          Delete All Enrolled Voices
        </button>
      </div>
    </div>
  )
}
