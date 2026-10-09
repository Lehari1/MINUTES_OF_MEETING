"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownUp,
  AudioLines,
  CalendarDays,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  FileAudio2,
  FileText,
  Filter,
  Headphones,
  ListChecks,
  LoaderCircle,
  MapPin,
  MessageSquareText,
  Plus,
  Search,
  Sparkles,
  UsersRound,
  X,
} from "lucide-react";

type ActionItem = {
  task: string;
  owner: string | null;
  due_date: string | null;
  status: "pending" | "in_progress" | "done";
};

type Minutes = {
  summary: string;
  attendees: string[];
  meeting_date: string | null;
  location: string | null;
  discussion_points: string[];
  key_takeaways: string[];
  decisions: string[];
  action_items: ActionItem[];
};

type Meeting = {
  id: string;
  title: string;
  source_type: "audio" | "transcript";
  created_at: string;
  transcript: string;
  minutes: Minutes;
};

type MeetingJob = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: "queued" | "transcribing" | "summarizing" | "completed" | "failed";
  message: string;
  error: string | null;
  meeting: Meeting | null;
};

type ProcessingStage = "uploading" | MeetingJob["stage"];

type ModelReadiness = {
  status: "queued" | "loading" | "ready" | "failed" | "disabled";
  stage: "queued" | "loading_whisper" | "loading_qwen" | "ready" | "failed" | "disabled";
  message: string;
};

type Analytics = {
  total_meetings: number;
  audio_meetings: number;
  transcript_meetings: number;
  action_items: number;
  decisions: number;
  recent_meetings: number;
};

type UploadMode = "audio" | "file" | "paste";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const emptyAnalytics: Analytics = {
  total_meetings: 0,
  audio_meetings: 0,
  transcript_meetings: 0,
  action_items: 0,
  decisions: 0,
  recent_meetings: 0,
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function readableStatus(status: ActionItem["status"]) {
  return status.replace("_", " ");
}

export default function Home() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [selected, setSelected] = useState<Meeting | null>(null);
  const [analytics, setAnalytics] = useState(emptyAnalytics);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadMode, setUploadMode] = useState<UploadMode>("audio");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [transcriptFile, setTranscriptFile] = useState<File | null>(null);
  const [transcriptText, setTranscriptText] = useState("");
  const [meetingTitle, setMeetingTitle] = useState("");
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState<ProcessingStage | null>(null);
  const [modelReadiness, setModelReadiness] = useState<ModelReadiness>({ status: "queued", stage: "queued", message: "Models will load before the first job." });
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/api/analytics`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not connect to the meeting service.");
        return response.json() as Promise<Analytics>;
      })
      .then((data) => active && setAnalytics(data))
      .catch(() => active && setError("Meeting service is offline. Start the FastAPI server to load your workspace."));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const updateReadiness = () => {
      fetch(`${API_BASE}/api/models/status`)
        .then((response) => {
          if (!response.ok) throw new Error("Model status unavailable");
          return response.json() as Promise<ModelReadiness>;
        })
        .then((status) => {
          if (!active) return;
          setModelReadiness(status);
          setError((current) => current === "Meeting service is offline. Start the FastAPI server to load your workspace." ? "" : current);
        })
        .catch(() => undefined);
    };
    updateReadiness();
    const interval = modelReadiness.status === "loading" || modelReadiness.status === "queued"
      ? window.setInterval(updateReadiness, 2000)
      : undefined;
    return () => {
      active = false;
      if (interval) window.clearInterval(interval);
    };
  }, [modelReadiness.status]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setBusy(true);
      const params = new URLSearchParams();
      if (search.trim()) params.set("q", search.trim());
      if (sourceFilter) params.set("source_type", sourceFilter);
      fetch(`${API_BASE}/api/meetings?${params.toString()}`, { signal: controller.signal })
        .then((response) => {
          if (!response.ok) throw new Error("Could not load meetings.");
          return response.json() as Promise<{ meetings: Meeting[]; total: number }>;
        })
        .then((data) => {
          if (!active) return;
          setMeetings(data.meetings);
          setSelected((current) => data.meetings.find((item) => item.id === current?.id) ?? data.meetings[0] ?? null);
          setError("");
        })
        .catch((reason: unknown) => {
          if (active && !(reason instanceof DOMException && reason.name === "AbortError")) {
            setError("Meeting service is offline. Start the FastAPI server to load your workspace.");
          }
        })
        .finally(() => active && setBusy(false));
    }, 180);
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [search, sourceFilter]);

  function updateFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (!file) return;
    if (uploadMode === "audio") setAudioFile(file);
    else setTranscriptFile(file);
  }

  async function submitMeeting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProcessing(true);
    setProcessingStage("uploading");
    setError("");
    const body = new FormData();
    if (meetingTitle.trim()) body.append("title", meetingTitle.trim());
    if (uploadMode === "audio" && audioFile) body.append("audio_file", audioFile);
    if (uploadMode === "file" && transcriptFile) body.append("transcript_file", transcriptFile);
    if (uploadMode === "paste") body.append("transcript_text", transcriptText);

    try {
      const response = await fetch(`${API_BASE}/api/meetings/jobs`, { method: "POST", body });
      const result = (await response.json()) as MeetingJob | { detail?: string };
      if (!response.ok) throw new Error("detail" in result ? result.detail : "Could not queue this meeting.");

      let job = result as MeetingJob;
      setProcessingStage(job.stage);
      while (job.status === "queued" || job.status === "running") {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        const statusResponse = await fetch(`${API_BASE}/api/meetings/jobs/${job.job_id}`);
        const statusResult = (await statusResponse.json()) as MeetingJob | { detail?: string };
        if (!statusResponse.ok) throw new Error("detail" in statusResult ? statusResult.detail : "Could not check meeting progress.");
        job = statusResult as MeetingJob;
        setProcessingStage(job.stage);
      }
      if (job.status === "failed") throw new Error(job.error || job.message || "Meeting processing failed.");
      if (!job.meeting) throw new Error("Processing finished without returning meeting minutes.");

      const record = job.meeting;
      setProcessingStage("completed");
      setSelected(record);
      setMeetings((current) => [record, ...current.filter((item) => item.id !== record.id)]);
      setAnalytics(await (await fetch(`${API_BASE}/api/analytics`)).json() as Analytics);
      await new Promise((resolve) => window.setTimeout(resolve, 800));
      setUploadOpen(false);
      setAudioFile(null);
      setTranscriptFile(null);
      setTranscriptText("");
      setMeetingTitle("");
      setSearch("");
      setSourceFilter("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Meeting processing failed. Please try again.");
    } finally {
      setProcessing(false);
      setProcessingStage(null);
    }
  }

  const processingMessage = processingStage === "uploading"
    ? "Uploading your meeting…"
    : processingStage === "queued"
      ? "Upload complete; waiting for the processor."
    : processingStage === "transcribing"
      ? "Transcribing audio with Whisper. Longer recordings take more time."
      : processingStage === "summarizing"
        ? "Transcription complete; generating your summary."
        : processingStage === "completed" ? "Completed. Your meeting minutes are ready." : "Preparing your meeting…";
  const processingPercent = processingStage === "uploading" ? 12 : processingStage === "queued" ? 20 : processingStage === "transcribing" ? 48 : processingStage === "summarizing" ? 78 : processingStage === "completed" ? 100 : 5;
  const progressSteps = ["uploading", "transcribing", "summarizing", "completed"] as const;
  const activeStep = processingStage === "queued" ? 0 : progressSteps.indexOf(processingStage as (typeof progressSteps)[number]);

  const chosenFile = uploadMode === "audio" ? audioFile : transcriptFile;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="Minutes home">
          <span className="brand-mark"><AudioLines size={20} strokeWidth={2.3} /></span>
          <span>minute<span className="brand-dot">.</span></span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <a className="nav-link active" href="#overview"><Activity size={17} /> Overview</a>
          <a className="nav-link" href="#meetings"><MessageSquareText size={17} /> Meetings <span className="nav-count">{analytics.total_meetings}</span></a>
        </nav>
        <div className="sidebar-bottom">
          <div className="service-state" title={modelReadiness.message}><span className={`status-dot ${error || modelReadiness.status === "failed" ? "offline" : modelReadiness.status !== "ready" ? "warming" : ""}`} />{error ? "Service offline" : modelReadiness.stage === "loading_whisper" ? "Loading Whisper…" : modelReadiness.stage === "loading_qwen" ? "Loading Qwen…" : modelReadiness.status === "ready" ? "Models ready" : modelReadiness.status === "failed" ? "Model warm-up failed" : modelReadiness.status === "disabled" ? "Models load on demand" : "Warming models…"}</div>
          <a className="help-link" href="mailto:support@example.com"><CircleHelp size={16} /> Help & feedback</a>
          <div className="profile-row"><span className="profile-avatar">M</span><span><strong>My workspace</strong><small>Personal</small></span><ChevronDown size={15} /></div>
        </div>
      </aside>

      <div className="main-area" id="overview">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="crumb-divider">/</span><strong>Overview</strong></div>
          <div className="top-actions">
            <span className="today-label"><CalendarDays size={15} /> {formatDate(new Date().toISOString())}</span>
            <button className="primary-button" onClick={() => { setUploadOpen(true); setError(""); }}><Plus size={17} /> New meeting</button>
          </div>
        </header>

        <div className="page-content">
          <section className="page-heading">
            <div>
              <div className="eyebrow"><span className="eyebrow-rule" /> MEETING INTELLIGENCE</div>
              <h1>Your meetings,<br className="mobile-break" /> in clear focus.</h1>
              <p className="heading-copy">A considered record of what was said, decided, and what happens next.</p>
            </div>
            <div className="heading-stamp"><span className="stamp-icon"><Sparkles size={18} /></span><span><strong>Minutes that move work forward</strong><small>Transcripts into thoughtful next steps</small></span></div>
          </section>

          {error && <div className="notice" role="status"><span className="status-dot offline" />{error}</div>}

          <section className="metric-grid" aria-label="Meeting analytics">
            <article className="metric-card metric-featured"><div className="metric-top"><span>MEETINGS HELD</span><CalendarDays size={17} /></div><div className="metric-value">{analytics.total_meetings}</div><div className="metric-foot"><span className="metric-highlight">{analytics.recent_meetings} this week</span><span>across your workspace</span></div></article>
            <article className="metric-card"><div className="metric-top"><span>ACTION ITEMS</span><ListChecks size={17} /></div><div className="metric-value">{analytics.action_items}</div><div className="metric-foot">captured from discussions</div></article>
            <article className="metric-card"><div className="metric-top"><span>DECISIONS</span><Check size={17} /></div><div className="metric-value">{analytics.decisions}</div><div className="metric-foot">documented and searchable</div></article>
            <article className="metric-card metric-sources"><div className="metric-top"><span>CAPTURED FROM</span><AudioLines size={17} /></div><div className="source-mix"><span><i className="mix-audio" />{analytics.audio_meetings} audio</span><span><i className="mix-text" />{analytics.transcript_meetings} transcript</span></div><div className="mix-track"><span style={{ width: `${analytics.total_meetings ? (analytics.audio_meetings / analytics.total_meetings) * 100 : 0}%` }} /></div><div className="metric-foot">ways your meetings are captured</div></article>
          </section>

          <section className="workspace-grid" id="meetings">
            <div className="meeting-column">
              <div className="section-heading">
                <div><div className="section-kicker">YOUR RECORD</div><h2>Meeting history <span className="heading-count">{meetings.length}</span></h2></div>
                <button className="text-button" onClick={() => { setSearch(""); setSourceFilter(""); }}><ArrowDownUp size={15} /> Reset</button>
              </div>
              <div className="toolbar">
                <label className="search-box"><Search size={16} /><input aria-label="Search meetings" placeholder="Search meetings or notes" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
                <label className="filter-box"><Filter size={15} /><select aria-label="Filter meetings by source" value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}><option value="">All sources</option><option value="audio">Audio</option><option value="transcript">Transcript</option></select></label>
              </div>

              <div className="meeting-list" aria-live="polite">
                {busy && meetings.length === 0 ? <div className="empty-state"><LoaderCircle className="spin" size={22} /><span>Loading meeting history</span></div> : meetings.length === 0 ? (
                  <div className="empty-state empty-first"><span className="empty-icon"><Headphones size={22} /></span><strong>{search || sourceFilter ? "No matching meetings" : "A clear record starts here"}</strong><span>{search || sourceFilter ? "Try another search or source." : "Add an audio recording or transcript to create your first set of minutes."}</span>{!search && !sourceFilter && <button className="subtle-button" onClick={() => setUploadOpen(true)}><Plus size={15} /> Add a meeting</button>}</div>
                ) : meetings.map((meeting) => (
                  <button className={`meeting-row ${selected?.id === meeting.id ? "selected" : ""}`} key={meeting.id} onClick={() => setSelected(meeting)}>
                    <span className={`meeting-type-icon ${meeting.source_type}`} aria-hidden="true">{meeting.source_type === "audio" ? <AudioLines size={18} /> : <FileText size={18} />}</span>
                    <span className="meeting-row-copy"><strong>{meeting.title}</strong><span>{formatDate(meeting.created_at)} <i /> {meeting.minutes.attendees.length ? `${meeting.minutes.attendees.length} attendees` : "No attendees listed"}</span></span>
                    <span className="row-side"><span className={`source-tag ${meeting.source_type}`}>{meeting.source_type}</span><ChevronDown className="row-chevron" size={15} /></span>
                  </button>
                ))}
              </div>
              <div className="list-footer"><span>{busy ? "Updating" : `${meetings.length} ${meetings.length === 1 ? "meeting" : "meetings"}`}</span><span><span className="status-dot" /> Synced with your workspace</span></div>
            </div>

            <aside className="detail-column" aria-label="Selected meeting minutes">
              {selected ? <MeetingDetail meeting={selected} /> : meetings.length > 0 ? <div className="detail-placeholder"><div className="placeholder-line" /><div className="placeholder-line short" /><div className="placeholder-block" /><div className="placeholder-line" /><div className="placeholder-line short" /></div> : <div className="detail-empty"><span className="empty-icon"><MessageSquareText size={21} /></span><strong>Your meeting notes will live here</strong><span>Choose a meeting from your history to review the full record.</span></div>}
            </aside>
          </section>
          <footer className="page-footer"><span>MINUTE<span className="brand-dot">.</span></span><span>Good meetings deserve a good record.</span></footer>
        </div>
      </div>

      {uploadOpen && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !processing) setUploadOpen(false); }}>
        <section className="upload-modal" role="dialog" aria-modal="true" aria-labelledby="upload-title">
          <div className="modal-header"><div><div className="section-kicker">NEW RECORD</div><h2 id="upload-title">Bring a meeting in</h2></div><button className="icon-button" aria-label="Close dialog" onClick={() => !processing && setUploadOpen(false)}><X size={19} /></button></div>
          <div className="mode-tabs" role="tablist" aria-label="Meeting source">
            <button className={uploadMode === "audio" ? "active" : ""} role="tab" aria-selected={uploadMode === "audio"} onClick={() => setUploadMode("audio")}><FileAudio2 size={16} /> Audio</button>
            <button className={uploadMode === "file" ? "active" : ""} role="tab" aria-selected={uploadMode === "file"} onClick={() => setUploadMode("file")}><FileText size={16} /> Text file</button>
            <button className={uploadMode === "paste" ? "active" : ""} role="tab" aria-selected={uploadMode === "paste"} onClick={() => setUploadMode("paste")}><MessageSquareText size={16} /> Paste text</button>
          </div>
          <form onSubmit={submitMeeting}>
            <label className="field-label" htmlFor="meeting-title">Meeting name <span>OPTIONAL</span></label>
            <input id="meeting-title" className="title-input" placeholder="e.g. Product planning, Q3" value={meetingTitle} onChange={(event) => setMeetingTitle(event.target.value)} />
            {uploadMode === "paste" ? <label className="field-label transcript-label" htmlFor="transcript-text">Transcript</label> : <label className="field-label transcript-label">{uploadMode === "audio" ? "Audio recording" : "Transcript file"}</label>}
            {uploadMode === "paste" ? <textarea id="transcript-text" className="transcript-input" placeholder="Paste your meeting transcript here..." value={transcriptText} onChange={(event) => setTranscriptText(event.target.value)} required minLength={10} /> : <label className="drop-zone">
              <input type="file" accept={uploadMode === "audio" ? ".mp3,.wav,.m4a,.flac,.ogg,.webm,.mp4,.mpeg,.mpga,audio/*" : ".txt,.md,text/plain"} onChange={updateFile} required={!chosenFile} />
              <span className="drop-icon">{uploadMode === "audio" ? <AudioLines size={22} /> : <FileText size={22} />}</span>
              <strong>{chosenFile?.name || (uploadMode === "audio" ? "Drop an audio file or browse" : "Drop a transcript or browse")}</strong>
              <span>{chosenFile ? `${(chosenFile.size / 1024 / 1024).toFixed(1)} MB` : uploadMode === "audio" ? "MP3, WAV, M4A, FLAC, OGG · up to 100 MB" : "TXT or MD · up to 100 MB"}</span>
            </label>}
            <div className="modal-note"><Sparkles size={15} /><span>{uploadMode === "audio" ? "Audio is transcribed first, then shaped into structured minutes." : "Your text is transformed into clear, structured meeting minutes."}</span></div>
            {processing && <div className="job-progress" role="status" aria-live="polite">
              <div className="job-progress-copy"><LoaderCircle className="spin" size={15} /><span>{processingMessage}</span></div>
              <div className="job-progress-track"><span style={{ width: `${processingPercent}%` }} /></div>
              <div className="job-steps">{["Uploading", "Transcribing", "Generating summary", "Completed"].map((label, index) => <span className={index < activeStep ? "complete" : index === activeStep ? "current" : ""} key={label}>{label}</span>)}</div>
            </div>}
            {error && <div className="modal-error" role="alert">{error}</div>}
            <button className="primary-button modal-submit" type="submit" disabled={processing || (uploadMode === "audio" ? !audioFile : uploadMode === "file" ? !transcriptFile : transcriptText.trim().length < 10)}>{processing ? <><LoaderCircle className="spin" size={17} /> Processing meeting...</> : <><Sparkles size={16} /> Generate minutes</>}</button>
          </form>
        </section>
      </div>}
    </main>
  );
}

function MeetingDetail({ meeting }: { meeting: Meeting }) {
  const minutes = meeting.minutes;
  return <article className="detail-card">
    <div className="detail-topline"><span className="detail-label">MEETING MINUTES</span><span className={`source-tag ${meeting.source_type}`}>{meeting.source_type === "audio" ? <AudioLines size={12} /> : <FileText size={12} />}{meeting.source_type}</span></div>
    <h2 className="detail-title">{meeting.title}</h2>
    <div className="detail-meta"><span><CalendarDays size={14} />{minutes.meeting_date || formatDate(meeting.created_at)}</span><span><Clock3 size={14} />{formatTime(meeting.created_at)}</span>{minutes.location && <span><MapPin size={14} />{minutes.location}</span>}</div>
    <div className="detail-summary"><span className="summary-mark">“</span><p>{minutes.summary}</p></div>
    {minutes.attendees.length > 0 && <DetailSection icon={<UsersRound size={15} />} title={`Attendees · ${minutes.attendees.length}`}><div className="attendee-list">{minutes.attendees.map((person) => <span className="attendee-chip" key={person}>{person}</span>)}</div></DetailSection>}
    {minutes.discussion_points.length > 0 && <DetailSection icon={<MessageSquareText size={15} />} title="Discussion points"><ul className="detail-list">{minutes.discussion_points.map((point, index) => <li key={`${point}-${index}`}>{point}</li>)}</ul></DetailSection>}
    {minutes.key_takeaways.length > 0 && <DetailSection icon={<Sparkles size={15} />} title="Key takeaways"><ul className="detail-list takeaway-list">{minutes.key_takeaways.map((point, index) => <li key={`${point}-${index}`}>{point}</li>)}</ul></DetailSection>}
    {minutes.decisions.length > 0 && <DetailSection icon={<Check size={15} />} title={`Decisions · ${minutes.decisions.length}`}><ul className="detail-list decision-list">{minutes.decisions.map((decision, index) => <li key={`${decision}-${index}`}>{decision}</li>)}</ul></DetailSection>}
    {minutes.action_items.length > 0 && <DetailSection icon={<ListChecks size={15} />} title={`Action items · ${minutes.action_items.length}`}><div className="action-list">{minutes.action_items.map((item, index) => <div className="action-item" key={`${item.task}-${index}`}><span className={`action-check ${item.status === "done" ? "done" : ""}`}>{item.status === "done" && <Check size={12} />}</span><span className="action-copy"><strong>{item.task}</strong><small>{item.owner || "Unassigned"}{item.due_date ? ` · Due ${item.due_date}` : ""}</small></span><span className={`action-status ${item.status}`}>{readableStatus(item.status)}</span></div>)}</div></DetailSection>}
    <details className="transcript-details"><summary>View original transcript <ChevronDown size={14} /></summary><p>{meeting.transcript}</p></details>
  </article>;
}

function DetailSection({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return <section className="detail-section"><h3>{icon}{title}</h3>{children}</section>;
}
