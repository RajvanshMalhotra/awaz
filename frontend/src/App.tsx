import { useState, useEffect } from 'react'
import { Onboarding } from '@/pages/Onboarding'
import { Main } from '@/pages/Main'
import { ToastProvider } from '@/components/Toast'
import { api, type Profile } from '@/lib/api'

type AppState = 'loading' | 'onboarding' | 'main'

export default function App() {
  const [appState, setAppState] = useState<AppState>('loading')
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [activeProfile, setActiveProfile] = useState<Profile | null>(null)

  useEffect(() => {
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
  }, [])

  const handleOnboardingComplete = (profile: Profile) => {
    setProfiles([profile])
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

  return (
    <>
      <ToastProvider />
      {appState === 'loading' && (
        <div className="min-h-screen bg-black flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-indigo-400 animate-spin" />
        </div>
      )}
      {appState === 'onboarding' && <Onboarding onComplete={handleOnboardingComplete} />}
      {appState === 'main' && activeProfile && (
        <Main profiles={profiles} activeProfile={activeProfile} onProfileUpdate={handleProfileUpdate} />
      )}
    </>
  )
}
