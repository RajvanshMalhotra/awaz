import { useState, useEffect } from 'react'
import { Landing } from '@/pages/Landing'
import { Onboarding } from '@/pages/Onboarding'
import { Main } from '@/pages/Main'
import { ToastProvider } from '@/components/Toast'
import { api, type Profile } from '@/lib/api'
import { toast } from '@/components/Toast'

type AppState = 'landing' | 'loading' | 'onboarding' | 'main'

export default function App() {
  const [appState, setAppState] = useState<AppState>('landing')
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [activeProfile, setActiveProfile] = useState<Profile | null>(null)

  useEffect(() => {
    document.documentElement.classList.add('dark')
  }, [])

  const handleEnter = () => {
    setAppState('loading')
    api.getProfiles()
      .then(({ profiles: ps, active_id }) => {
        if (ps.length === 0) {
          setAppState('onboarding')
        } else {
          setProfiles(ps)
          setActiveProfile(ps.find(p => p.profile_id === active_id) ?? ps[0])
          setAppState('main')
        }
      })
      .catch(() => setAppState('onboarding'))
  }

  // Upserts profile into list — works for both first-time and "add new"
  const handleOnboardingComplete = (profile: Profile) => {
    setProfiles(prev => {
      const idx = prev.findIndex(p => p.profile_id === profile.profile_id)
      if (idx >= 0) { const next = [...prev]; next[idx] = profile; return next }
      return [...prev, profile]
    })
    setActiveProfile(profile)
    setAppState('main')
  }

  const handleProfileUpdate = (profile: Profile) => {
    setProfiles(prev => {
      const idx = prev.findIndex(p => p.profile_id === profile.profile_id)
      if (idx >= 0) { const next = [...prev]; next[idx] = profile; return next }
      return [...prev, profile]
    })
    setActiveProfile(profile)
  }

  const handleAddProfile = () => {
    setAppState('onboarding')
  }

  const handleDeleteProfile = async (profileId: string) => {
    try {
      const { profiles: remaining, active_id } = await api.deleteProfile(profileId)
      if (remaining.length === 0) {
        setProfiles([])
        setActiveProfile(null)
        setAppState('onboarding')
      } else {
        setProfiles(remaining)
        const next = remaining.find(p => p.profile_id === active_id) ?? remaining[0]
        setActiveProfile(next)
      }
    } catch {
      toast('Failed to delete profile', 'error')
    }
  }

  return (
    <>
      <ToastProvider />

      {appState === 'landing' && <Landing onEnter={handleEnter} />}

      {appState === 'loading' && (
        <div className="min-h-screen bg-[#050508] flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-indigo-400 animate-spin" />
            <p className="text-white/20 text-sm">Loading…</p>
          </div>
        </div>
      )}

      {appState === 'onboarding' && <Onboarding onComplete={handleOnboardingComplete} />}

      {appState === 'main' && activeProfile && (
        <Main
          profiles={profiles}
          activeProfile={activeProfile}
          onProfileUpdate={handleProfileUpdate}
          onAddProfile={handleAddProfile}
          onDeleteProfile={handleDeleteProfile}
        />
      )}
    </>
  )
}
