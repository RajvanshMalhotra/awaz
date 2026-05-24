import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const relationships = [
  "friend",
  "best_friend",
  "parent",
  "sibling",
  "romantic",
  "colleague",
  "boss",
  "stranger",
];

const moods = [
  "auto",
  "happy",
  "sad",
  "shocked",
  "sarcastic",
  "angry",
  "scared",
  "laughing",
  "whispering",
  "neutral",
  "excited",
];

const voiceOptions = ["female", "female_alt", "male", "male_deep"];

const defaultPersonality = {
  energy: "chaotic",
  filter: "unfiltered",
  style: "dramatic",
  tone: "sarcastic",
  lang_lean: "hindi",
};

function titleize(value = "") {
  return value.replaceAll("_", " ");
}

function audioUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_BASE}/${path.replace(/^\/+/, "")}`;
}

async function readJson(response) {
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!response.ok) {
    const detail = data?.detail || response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function ChipGroup({ label, value, options, onChange }) {
  return (
    <section className="chipGroup" aria-label={label}>
      <div className="sectionLabel">{label}</div>
      <div className="chips" role="radiogroup" aria-label={label}>
        {options.map((option) => (
          <button
            key={option}
            className={option === value ? "chip active" : "chip"}
            onClick={() => onChange(option)}
            type="button"
            aria-pressed={option === value}
          >
            {titleize(option)}
          </button>
        ))}
      </div>
    </section>
  );
}

function App() {
  const [relationship, setRelationship] = useState("friend");
  const [mood, setMood] = useState("auto");
  const [manualInput, setManualInput] = useState("");
  const [voiceGender, setVoiceGender] = useState("male");
  const [audioFile, setAudioFile] = useState(null);
  const [recording, setRecording] = useState(false);
  const [recordedUrl, setRecordedUrl] = useState("");
  const [processResult, setProcessResult] = useState(null);
  const [ttsResult, setTtsResult] = useState(null);
  const [saveName, setSaveName] = useState("");
  const [saveRelationship, setSaveRelationship] = useState("friend");
  const [status, setStatus] = useState("Ready");
  const [busy, setBusy] = useState(false);
  const [onboarding, setOnboarding] = useState(null);
  const [profileName, setProfileName] = useState("Raj");
  const [customVibe, setCustomVibe] = useState("");

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const fileInputRef = useRef(null);

  const canSubmit = useMemo(() => Boolean(audioFile) && !busy, [audioFile, busy]);
  const stage = ttsResult ? "Voice ready" : processResult ? "Review reply" : audioFile ? "Ready to generate" : "Capture";
  const outputAudio = audioUrl(ttsResult?.tts_audio_url);

  useEffect(() => {
    refreshOnboarding();
  }, []);

  useEffect(() => {
    return () => {
      if (recordedUrl) URL.revokeObjectURL(recordedUrl);
    };
  }, [recordedUrl]);

  async function refreshOnboarding() {
    try {
      const data = await readJson(await fetch(`${API_BASE}/onboarding/status`));
      setOnboarding(data);
      if (data.profile?.voice_gender) setVoiceGender(data.profile.voice_gender);
      if (data.profile?.name) setProfileName(data.profile.name);
      if (data.profile?.custom_vibe) setCustomVibe(data.profile.custom_vibe);
    } catch (error) {
      setStatus(`Backend unavailable: ${error.message}`);
    }
  }

  async function saveOnboarding() {
    setBusy(true);
    setStatus("Saving profile...");
    try {
      const profile = await readJson(
        await fetch(`${API_BASE}/onboarding`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: profileName,
            voice_gender: voiceGender,
            personality: defaultPersonality,
            custom_vibe: customVibe,
          }),
        })
      );
      setOnboarding({ completed: true, profile });
      setStatus("Profile saved");
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function startRecording() {
    try {
      setStatus("Opening microphone...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const file = new File([blob], "awaaz-recording.webm", { type: blob.type });
        setAudioFile(file);
        if (recordedUrl) URL.revokeObjectURL(recordedUrl);
        setRecordedUrl(URL.createObjectURL(blob));
        setStatus("Recording captured");
      };
      recorder.start();
      setRecording(true);
      setStatus("Recording...");
    } catch (error) {
      setStatus(`Mic error: ${error.message}`);
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  function chooseFile(file) {
    setAudioFile(file);
    if (recordedUrl) URL.revokeObjectURL(recordedUrl);
    setRecordedUrl(file ? URL.createObjectURL(file) : "");
    if (file) setStatus("Audio selected");
  }

  function clearAudio() {
    if (recordedUrl) URL.revokeObjectURL(recordedUrl);
    setRecordedUrl("");
    setAudioFile(null);
    setProcessResult(null);
    setTtsResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setStatus("Ready");
  }

  async function submitAudio() {
    if (!audioFile) return;
    setBusy(true);
    setTtsResult(null);
    setProcessResult(null);
    setStatus("Processing voice...");
    try {
      const form = new FormData();
      form.append("audio", audioFile);
      form.append("relationship", relationship);
      form.append("mood_override", mood);
      form.append("extra_text", manualInput);
      form.append("voice_gender", voiceGender);

      const data = await readJson(
        await fetch(`${API_BASE}/pipeline/process`, {
          method: "POST",
          body: form,
        })
      );
      setProcessResult(data);
      setSaveRelationship(data.effective_relationship || relationship);
      setStatus("Reply generated");
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!processResult?.session_id) return;
    setBusy(true);
    setStatus("Synthesizing voice...");
    try {
      const data = await readJson(
        await fetch(`${API_BASE}/pipeline/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: processResult.session_id }),
        })
      );
      setTtsResult(data);
      setStatus("Voice ready");
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function regenerate() {
    if (!processResult?.session_id) return;
    setBusy(true);
    setTtsResult(null);
    setStatus("Regenerating...");
    try {
      const data = await readJson(
        await fetch(`${API_BASE}/pipeline/deny`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: processResult.session_id,
            mood_override: mood,
            relationship_override: relationship,
            extra_text: manualInput,
          }),
        })
      );
      setProcessResult((current) => ({
        ...current,
        llm: data.llm,
        session_id: data.session_id,
      }));
      setStatus("Regenerated");
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveSpeaker() {
    if (!processResult?.session_id || !saveName.trim()) return;
    setBusy(true);
    setStatus("Saving speaker...");
    try {
      const form = new FormData();
      form.append("session_id", processResult.session_id);
      form.append("name", saveName.trim());
      form.append("relationship", saveRelationship);
      const data = await readJson(
        await fetch(`${API_BASE}/pipeline/save-speaker`, {
          method: "POST",
          body: form,
        })
      );
      setProcessResult((current) => ({
        ...current,
        save_voice_prompt: false,
        speaker: {
          ...current.speaker,
          speaker_id: data.speaker_id,
          name: data.name,
          relationship: data.relationship,
          is_new_speaker: false,
        },
      }));
      setSaveName("");
      setStatus(data.message);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <div className="brandLockup">
          <div className="mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div>
            <p className="eyebrow">Awaaz studio</p>
            <h1>Voice in. Perfect reply out.</h1>
          </div>
        </div>
        <div className="statusCluster">
          <div className="stagePill">{stage}</div>
          <div className={busy ? "status busy" : "status"}>{status}</div>
        </div>
      </header>

      <section className="profileBar" aria-label="Profile settings">
        <div className="profileBadge">
          <span className={onboarding?.completed ? "dot live" : "dot"} />
          <div>
            <span className="microLabel">Profile</span>
            <strong>{onboarding?.completed ? onboarding.profile.name : "Not set"}</strong>
          </div>
        </div>
        <label>
          <span>Name</span>
          <input value={profileName} onChange={(event) => setProfileName(event.target.value)} />
        </label>
        <label>
          <span>Voice</span>
          <select value={voiceGender} onChange={(event) => setVoiceGender(event.target.value)}>
            {voiceOptions.map((voice) => (
              <option key={voice} value={voice}>
                {titleize(voice)}
              </option>
            ))}
          </select>
        </label>
        <label className="vibeField">
          <span>Vibe</span>
          <input
            value={customVibe}
            onChange={(event) => setCustomVibe(event.target.value)}
            placeholder="chaotic, warm, deadpan..."
          />
        </label>
        <button className="button ghost" type="button" onClick={saveOnboarding} disabled={busy}>
          Save
        </button>
      </section>

      <section className="contextDock">
        <ChipGroup
          label="Relationship"
          value={relationship}
          options={relationships}
          onChange={setRelationship}
        />
        <ChipGroup label="Mood" value={mood} options={moods} onChange={setMood} />
      </section>

      <section className="workspace">
        <section className="panel capturePanel" aria-label="Voice input">
          <div className="panelHeader">
            <div>
              <p className="eyebrow">Input</p>
              <h2>Capture the thought</h2>
            </div>
            {audioFile && (
              <button className="iconButton" type="button" onClick={clearAudio} title="Clear audio">
                x
              </button>
            )}
          </div>

          <div className={recording ? "recordWell recording" : "recordWell"}>
            <div className="meter" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <div>
              <strong>{recording ? "Listening..." : audioFile ? audioFile.name : "No audio yet"}</strong>
              <p>{audioFile ? "Review, add context, then generate." : "Record live or upload an audio file."}</p>
            </div>
          </div>

          {recordedUrl && <audio controls src={recordedUrl} className="audio" />}

          <div className="captureActions">
            <button
              className={recording ? "button danger" : "button primary"}
              type="button"
              onClick={recording ? stopRecording : startRecording}
              disabled={busy}
            >
              {recording ? "Stop" : "Record"}
            </button>
            <label className="button ghost fileButton">
              Upload
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                onChange={(event) => chooseFile(event.target.files?.[0] || null)}
              />
            </label>
          </div>

          <label className="textField">
            <span>Extra direction</span>
            <textarea
              value={manualInput}
              onChange={(event) => setManualInput(event.target.value)}
              placeholder="Add corrections, intent, or the exact flavor you want..."
            />
          </label>

          <button className="button primary full" type="button" onClick={submitAudio} disabled={!canSubmit}>
            Generate reply
          </button>
        </section>

        <section className="panel resultPanel" aria-label="Generated response">
          <div className="panelHeader">
            <div>
              <p className="eyebrow">Output</p>
              <h2>Review and ship</h2>
            </div>
            {processResult && <span className="miniPill">{titleize(processResult.effective_relationship)}</span>}
          </div>

          {!processResult ? (
            <div className="emptyState">
              <div className="emptyGlyph" aria-hidden="true">
                <span />
                <span />
              </div>
              <strong>Waiting for audio</strong>
              <p>Your transcript, mood read, and expressive reply will appear here.</p>
            </div>
          ) : (
            <div className="resultStack">
              <div className="insights">
                <div>
                  <span>Transcript</span>
                  <strong>{processResult.transcript || "None"}</strong>
                </div>
                <div>
                  <span>Speaker</span>
                  <strong>{processResult.speaker?.name || "Unknown"}</strong>
                </div>
                <div>
                  <span>Mood</span>
                  <strong>{titleize(processResult.llm?.detected_mood)}</strong>
                </div>
                <div>
                  <span>Source</span>
                  <strong>{titleize(processResult.relationship_source)}</strong>
                </div>
              </div>

              <article className="generatedText">{processResult.llm?.expressive_text}</article>
              {processResult.llm?.reasoning && <p className="reasoning">{processResult.llm.reasoning}</p>}

              {processResult.save_voice_prompt && (
                <div className="saveSpeaker">
                  <div>
                    <span className="microLabel">New speaker</span>
                    <strong>Save this voice</strong>
                  </div>
                  <input
                    value={saveName}
                    onChange={(event) => setSaveName(event.target.value)}
                    placeholder="Name"
                  />
                  <select
                    value={saveRelationship}
                    onChange={(event) => setSaveRelationship(event.target.value)}
                  >
                    {relationships.map((item) => (
                      <option key={item} value={item}>
                        {titleize(item)}
                      </option>
                    ))}
                  </select>
                  <button className="button ghost" type="button" onClick={saveSpeaker} disabled={busy}>
                    Save
                  </button>
                </div>
              )}

              <div className="reviewActions">
                <button className="button primary" type="button" onClick={approve} disabled={busy}>
                  Approve voice
                </button>
                <button className="button ghost" type="button" onClick={regenerate} disabled={busy}>
                  Regenerate
                </button>
              </div>
            </div>
          )}
        </section>
      </section>

      {ttsResult && (
        <section className="playerBar" aria-label="Generated audio player">
          <div>
            <span className="microLabel">TTS ready</span>
            <strong>{ttsResult.tts_payload?.speaker || titleize(voiceGender)}</strong>
          </div>
          <audio controls src={outputAudio} className="audioPlayer" autoPlay />
          <a className="button ghost download" href={outputAudio} download>
            Download
          </a>
        </section>
      )}
    </main>
  );
}

export default App;
