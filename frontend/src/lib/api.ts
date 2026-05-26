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

export interface ProcessResponse {
  session_id: string
  transcript: string
  detected_language: string | null
  speaker: {
    name: string | null
    similarity: number
    relationship: string | null
  }
  llm: {
    expressive_text: string
    reasoning: string
    detected_mood: string
  }
  save_voice_prompt: boolean
  effective_relationship: string
  relationship_source: string
}

export interface ApproveResponse {
  tts_audio_url: string | null
  tts_payload: { model: string; text: string; description: string; f0_up_key: number }
  expressive_text: string
}

export interface DenyResponse {
  session_id: string
  llm: {
    expressive_text: string
    reasoning: string
    detected_mood: string
  }
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

  async processText(
    text: string,
    relationship: string,
    moodOverride: string,
    extraText?: string,
  ): Promise<ProcessResponse> {
    const fd = new FormData()
    fd.append('text', text)
    fd.append('relationship', relationship)
    fd.append('mood_override', moodOverride)
    if (extraText) fd.append('extra_text', extraText)
    const r = await fetch('/pipeline/process-text', { method: 'POST', body: fd })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async processAudio(
    blob: Blob,
    relationship: string,
    moodOverride: string,
    extraText: string,
  ): Promise<ProcessResponse> {
    const fd = new FormData()
    fd.append('audio', blob, 'recording.webm')
    fd.append('relationship', relationship)
    fd.append('mood_override', moodOverride)
    if (extraText) fd.append('extra_text', extraText)
    const r = await fetch('/pipeline/process', { method: 'POST', body: fd })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async approve(sessionId: string): Promise<ApproveResponse> {
    const r = await fetch('/pipeline/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async deny(
    sessionId: string,
    overrides: { mood_override?: string; relationship_override?: string; extra_text?: string },
  ): Promise<DenyResponse> {
    const r = await fetch('/pipeline/deny', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, ...overrides }),
    })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async saveSpeaker(sessionId: string, name: string, relationship: string): Promise<void> {
    const fd = new FormData()
    fd.append('session_id', sessionId)
    fd.append('name', name)
    fd.append('relationship', relationship)
    const r = await fetch('/pipeline/save-speaker', { method: 'POST', body: fd })
    if (!r.ok) throw new Error(await r.text())
  },

  async deleteAllSpeakers(): Promise<{ deleted: number }> {
    const r = await fetch('/pipeline/speakers', { method: 'DELETE' })
    if (!r.ok) throw new Error('Failed to delete speakers')
    return r.json()
  },

  async deleteProfile(profileId: string): Promise<ProfilesResponse> {
    const r = await fetch(`/onboarding/profiles/${profileId}`, { method: 'DELETE' })
    if (!r.ok) throw new Error('Failed to delete profile')
    return r.json()
  },
}
