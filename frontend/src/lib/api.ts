export interface ProfilePayload {
  profile_id?: string
  name: string
  personality: Record<string, string>
  custom_vibe?: string
}

export interface ProfilesResponse {
  profiles: Profile[]
  active_id: string | null
}

export interface Profile {
  profile_id: string
  name: string
  personality: Record<string, string>
  custom_vibe?: string
}

// Single-shot response — returned by both /pipeline/voice and /pipeline/speak
export interface VoiceResponse {
  transcript: string
  expressive_text: string
  detected_mood: string
  reasoning: string
  tts_audio_url: string
}

export interface Speaker {
  speaker_id: string
  name: string
  relationship: string
}

export const api = {
  async getSpeakers(): Promise<{ speakers: Speaker[] }> {
    const r = await fetch('/pipeline/speakers')
    if (!r.ok) throw new Error('Failed to fetch speakers')
    return r.json()
  },

  async getProfiles(): Promise<ProfilesResponse> {
    const r = await fetch('/onboarding/profiles')
    if (!r.ok) throw new Error('Failed to fetch profiles')
    return r.json()
  },

  async saveProfile(payload: ProfilePayload): Promise<Profile> {
    const r = await fetch('/onboarding', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async activateProfile(profileId: string): Promise<void> {
    const r = await fetch(`/onboarding/profiles/${profileId}/activate`, { method: 'PUT' })
    if (!r.ok) throw new Error('Failed to switch profile')
  },

  async speak(text: string, moodOverride: string): Promise<VoiceResponse> {
    const fd = new FormData()
    fd.append('text', text)
    fd.append('mood_override', moodOverride)
    const r = await fetch('/pipeline/speak', { method: 'POST', body: fd })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async voice(blob: Blob, moodOverride: string): Promise<VoiceResponse> {
    const fd = new FormData()
    fd.append('audio', blob, 'recording.webm')
    fd.append('mood_override', moodOverride)
    const r = await fetch('/pipeline/voice', { method: 'POST', body: fd })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async deleteProfile(profileId: string): Promise<ProfilesResponse> {
    const r = await fetch(`/onboarding/profiles/${profileId}`, { method: 'DELETE' })
    if (!r.ok) throw new Error('Failed to delete profile')
    return r.json()
  },
}
