import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const templates = {
  ping: {
    action: 'ping',
    payload: {}
  },
  list_tools: {
    action: 'list_tools',
    payload: {}
  },
  elevenlabs_voice: {
    action: 'elevenlabs_voice',
    payload: {
      text: 'Hello, this is a test',
      voice_id: '21m00Tcm4TlvDq8ikWAM',
      model_id: 'eleven_multilingual_v2'
    }
  },
  higgsfield_image: {
    action: 'higgsfield_image',
    payload: {
      prompt: 'A cinematic portrait with warm studio lighting',
      width: 1024,
      height: 1024,
      wait_for_completion: false
    }
  },
  pipeline_audio_stack: {
    action: 'pipeline_audio_stack',
    payload: {
      voice: {
        text: 'Welcome to the Narrations pipeline',
        voice_id: '21m00Tcm4TlvDq8ikWAM'
      },
      music: {
        prompt: 'Ambient cinematic bed',
        duration: 20
      },
      soundfx: {
        prompt: 'Soft wind swell',
        duration: 4
      },
      wait_for_completion: true
    }
  }
}

const N0_PROGRESS_DEFAULT_MS = 90000
const N0_PROGRESS_MIN_MS = 60000
const N0_PROGRESS_PADDING = 1.35

const defaultTemplate = JSON.stringify(templates.pipeline_audio_stack, null, 2)

const getBasePath = (pathname) => {
  const path = pathname || ''
  const trimmed = path.replace(/\/+$/, '')
  if (!trimmed || trimmed === '/') {
    return ''
  }
  return trimmed
}

const joinPath = (base, suffix) => {
  if (!base) {
    return suffix
  }
  if (base.endsWith('/')) {
    return `${base.replace(/\/+$/, '')}${suffix}`
  }
  return `${base}${suffix}`
}

const getApiOrigin = () => {
  const { protocol, hostname, port } = window.location
  if (port === '5173') {
    return `${protocol}//${hostname}:3333`
  }
  if (port) {
    return `${protocol}//${hostname}:${port}`
  }
  return `${protocol}//${hostname}`
}

function App() {
  const isCrossOrigin = getApiOrigin() !== window.location.origin
  const basePath = isCrossOrigin ? '' : getBasePath(window.location.pathname)
  const apiBasePath = basePath === '/console' ? '' : basePath
  const apiOrigin = getApiOrigin()
  const [endpoint, setEndpoint] = useState(
    `${apiOrigin}${joinPath(apiBasePath, '/mcp')}`
  )
  const projectsEndpoint = `${apiOrigin}${joinPath(apiBasePath, '/projects')}`
  const [requestText, setRequestText] = useState(defaultTemplate)
  const [responseText, setResponseText] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [lastDuration, setLastDuration] = useState(null)
  const [projects, setProjects] = useState([])
  const [projectsStatus, setProjectsStatus] = useState('idle')
  const [projectsError, setProjectsError] = useState('')
  const [selectedProject, setSelectedProject] = useState('')
  const [newProjectId, setNewProjectId] = useState('')
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [canCloseCreateModal, setCanCloseCreateModal] = useState(false)
  const [createProjectName, setCreateProjectName] = useState('')
  const [createProjectStatus, setCreateProjectStatus] = useState('idle')
  const [createProjectError, setCreateProjectError] = useState('')
  const [createdProjectId, setCreatedProjectId] = useState('')
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatStatus, setChatStatus] = useState('idle')
  const [chatError, setChatError] = useState('')
  const [chatSessionId, setChatSessionId] = useState('')
  const [hasPendingQuestions, setHasPendingQuestions] = useState(false)
  const [progressActive, setProgressActive] = useState(false)
  const [progressValue, setProgressValue] = useState(0)
  const [progressEstimateMs, setProgressEstimateMs] = useState(() => {
    const stored = window.localStorage.getItem('n0ProgressEstimateMs')
    const parsed = stored ? Number(stored) : NaN
    if (Number.isFinite(parsed) && parsed > 0) {
      return Math.max(parsed, N0_PROGRESS_MIN_MS)
    }
    return N0_PROGRESS_DEFAULT_MS
  })
  const progressStartRef = useRef(null)
  const [logOverlayOpen, setLogOverlayOpen] = useState(false)
  const [logApiText, setLogApiText] = useState('')
  const [logUiText, setLogUiText] = useState('')
  const [logAgentText, setLogAgentText] = useState('')
  const [logStatus, setLogStatus] = useState('idle')
  const [logError, setLogError] = useState('')
  const [ragStopStatus, setRagStopStatus] = useState('idle')
  const [ragStopError, setRagStopError] = useState('')
  const [activePage, setActivePage] = useState('home')
  const [n0Data, setN0Data] = useState(null)
  const [n0FromUi, setN0FromUi] = useState(false)
  const [n0Status, setN0Status] = useState('idle')
  const [n0Error, setN0Error] = useState('')
  const [n0UpdatedAt, setN0UpdatedAt] = useState('')
  const [editorOpen, setEditorOpen] = useState(false)
  const [editorValue, setEditorValue] = useState('')
  const [editorOriginal, setEditorOriginal] = useState('')
  const [editorLabel, setEditorLabel] = useState('')
  const [editorTargetPath, setEditorTargetPath] = useState('')
  const [editorChatMessages, setEditorChatMessages] = useState([])
  const [editorChatInput, setEditorChatInput] = useState('')
  const [editorChatStatus, setEditorChatStatus] = useState('idle')
  const [editorChatError, setEditorChatError] = useState('')
  const [editorChatSessionId, setEditorChatSessionId] = useState('')
  const [editorChatSummary, setEditorChatSummary] = useState('')
  const editorTargetRef = useRef(null)
  const [n1Data, setN1Data] = useState(null)
  const [n1Status, setN1Status] = useState('idle')
  const [n1Error, setN1Error] = useState('')
  const [n1UpdatedAt, setN1UpdatedAt] = useState('')
  const [n1PasteText, setN1PasteText] = useState('')
  const [n1PasteError, setN1PasteError] = useState('')
  const [n2Data, setN2Data] = useState(null)
  const [n2Status, setN2Status] = useState('idle')
  const [n2Error, setN2Error] = useState('')
  const [n2UpdatedAt, setN2UpdatedAt] = useState('')
  const [n2PasteText, setN2PasteText] = useState('')
  const [n2PasteError, setN2PasteError] = useState('')
  const [n3Data, setN3Data] = useState(null)
  const [n3Status, setN3Status] = useState('idle')
  const [n3Error, setN3Error] = useState('')
  const [n3UpdatedAt, setN3UpdatedAt] = useState('')
  const [n3PasteText, setN3PasteText] = useState('')
  const [n3PasteError, setN3PasteError] = useState('')
  const [selectedN3UnitId, setSelectedN3UnitId] = useState('')
  const [n4Data, setN4Data] = useState(null)
  const [n4Status, setN4Status] = useState('idle')
  const [n4Error, setN4Error] = useState('')
  const [n4UpdatedAt, setN4UpdatedAt] = useState('')
  const [n4PasteText, setN4PasteText] = useState('')
  const [n4PasteError, setN4PasteError] = useState('')
  const [n5Data, setN5Data] = useState(null)
  const [n5Status, setN5Status] = useState('idle')
  const [n5Error, setN5Error] = useState('')
  const [n5UpdatedAt, setN5UpdatedAt] = useState('')
  const [n5PasteText, setN5PasteText] = useState('')
  const [n5PasteError, setN5PasteError] = useState('')
  const [mediaModalOpen, setMediaModalOpen] = useState(false)
  const [mediaModalKind, setMediaModalKind] = useState('')
  const [mediaModalUrl, setMediaModalUrl] = useState('')
  const [mediaModalFiles, setMediaModalFiles] = useState([])
  const [artImageFiles, setArtImageFiles] = useState([])
  const [artAudioFiles, setArtAudioFiles] = useState([])
  const [artImageUrl, setArtImageUrl] = useState('')
  const [higgsfieldStatus, setHiggsfieldStatus] = useState('idle')
  const [higgsfieldJobId, setHiggsfieldJobId] = useState('')
  const [higgsfieldUrl, setHiggsfieldUrl] = useState('')
  const [higgsfieldInfo, setHiggsfieldInfo] = useState('Aucune requete en cours.')
  const [higgsfieldStatusUrl, setHiggsfieldStatusUrl] = useState('')
  const [higgsfieldLastStatus, setHiggsfieldLastStatus] = useState('')
  const [higgsfieldAttempts, setHiggsfieldAttempts] = useState(0)
  const [higgsfieldRaw, setHiggsfieldRaw] = useState('')
  const pollRef = useRef(null)
  const pageLabel = {
    home: 'projets',
    project: selectedProject || 'projet',
    old: 'old',
    bible: 'bible',
    architecture: 'architecture',
    sequences: 'sequences',
    timeline: 'timeline',
    script: 'script',
    media: 'media',
    prompts: 'prompts',
    console: 'console'
  }
  const oldPages = [
    { id: 'bible', label: 'Bible (N1)' },
    { id: 'architecture', label: 'Architecture (N2)' },
    { id: 'sequences', label: 'Sequences (N3)' },
    { id: 'timeline', label: 'Timeline (N4)' },
    { id: 'script', label: 'Script' },
    { id: 'media', label: 'Media (N5)' },
    { id: 'prompts', label: 'Prompts (N5)' },
    { id: 'console', label: 'Console' }
  ]
  const isOldPage = oldPages.some((page) => page.id === activePage)
  const resolvedChatProjectId = createModalOpen
    ? createdProjectId
    : selectedProject
  const canSendChat = Boolean(chatInput.trim() && resolvedChatProjectId)
  const chatDisabled = createModalOpen && !createdProjectId
  const resizeTextarea = (element) => {
    if (!element) {
      return
    }
    element.style.height = 'auto'
    element.style.height = `${element.scrollHeight}px`
  }

  const handleStopRag = async () => {
    const confirmStop = window.confirm(
      'Arreter les services RAG locaux (R2R + Postgres) ?'
    )
    if (!confirmStop) {
      return
    }
    setRagStopStatus('loading')
    setRagStopError('')
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, '/system/rag/stop')}`,
        { method: 'POST' }
      )
      let payload = {}
      try {
        payload = await resp.json()
      } catch (err) {
        payload = {}
      }
      if (!resp.ok) {
        throw new Error(payload?.error || `HTTP ${resp.status}`)
      }
      setRagStopStatus('done')
    } catch (err) {
      setRagStopStatus('error')
      setRagStopError(err.message)
    }
  }
  const handleAutoResize = (event) => {
    resizeTextarea(event.target)
  }

  const normalizeJsonInput = (raw) => {
    let cleaned = raw.replace(/^\uFEFF/, '')
    const fenced = cleaned.match(/^\s*```(?:json)?\s*([\s\S]*?)\s*```\s*$/i)
    if (fenced) {
      cleaned = fenced[1]
    }
    return cleaned.trim()
  }

  const parsedRequest = useMemo(() => {
    const cleaned = normalizeJsonInput(requestText)
    try {
      return { value: JSON.parse(cleaned), error: '' }
    } catch (err) {
      const preview = cleaned
        .slice(0, 120)
        .replace(/\s+/g, ' ')
        .trim()
      const detail = preview ? ` | debut: "${preview}"` : ''
      return { value: null, error: `${err.message}${detail}` }
    }
  }, [requestText])

  const chatLogText = useMemo(() => {
    if (!chatMessages.length) {
      return ''
    }
    return chatMessages
      .map((entry) => `${entry.role === 'user' ? 'Vous' : 'Aoid'}: ${entry.content}`)
      .join('\n\n')
  }, [chatMessages])

  const hasAssistantReply = chatMessages.some((entry) => entry.role === 'assistant')
  const showChatHistory = Boolean(createdProjectId && hasAssistantReply)
  const showChatInput = Boolean(createdProjectId)

  const fetchLogText = async (name, setter) => {
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/logs/${name}?lines=200`)}`
      )
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setter(data?.content || '')
    } catch (err) {
      setLogError(err.message)
    }
  }

  useEffect(() => {
    if (!logOverlayOpen) {
      return undefined
    }
    let timer = null
    const loadLogs = async () => {
      setLogStatus('loading')
      setLogError('')
      await Promise.all([
        fetchLogText('api', setLogApiText),
        fetchLogText('ui', setLogUiText),
        fetchLogText('agent', setLogAgentText)
      ])
      setLogStatus('idle')
    }
    loadLogs()
    timer = setInterval(loadLogs, 2000)
    return () => {
      if (timer) {
        clearInterval(timer)
      }
    }
  }, [logOverlayOpen])


  const uploadImageFile = async (file) => {
    if (!selectedProject) {
      return
    }
    try {
      const form = new FormData()
      form.append('file', file)
      await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/media/pix/upload`)}`,
        {
          method: 'POST',
          body: form
        }
      )
    } catch (err) {
      console.warn('Upload image failed', err)
    }
  }

  const applyArtImageFiles = (files) => {
    setArtImageFiles((prev) => {
      prev.forEach((item) => {
        if (item.url && item.isObjectUrl) {
          URL.revokeObjectURL(item.url)
        }
      })
      return files.map((file) => ({
        file,
        url: URL.createObjectURL(file),
        isObjectUrl: true
      }))
    })
    files.forEach(uploadImageFile)
  }

  const handleImageFilesChange = (event) => {
    const files = Array.from(event.target.files || [])
    applyArtImageFiles(files)
  }

  const handleImageUrlLoad = (value) => {
    const raw = (value ?? artImageUrl).trim()
    if (!raw) {
      return
    }
    let name = raw
    try {
      const parsed = new URL(raw)
      name = parsed.pathname.split('/').filter(Boolean).pop() || parsed.hostname
    } catch (err) {
      name = raw
    }
    setArtImageFiles((prev) => [
      ...prev,
      {
        file: { name },
        url: raw,
        isObjectUrl: false
      }
    ])
    if (selectedProject) {
      fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/media/pix/url`)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: raw })
        }
      ).catch((err) => {
        console.warn('Upload image url failed', err)
      })
    }
    setArtImageUrl('')
  }

  const removeImageFile = (urlToRemove) => {
    setArtImageFiles((prev) => {
      const next = prev.filter((item) => item.url !== urlToRemove)
      const removed = prev.find((item) => item.url === urlToRemove)
      if (removed?.url && removed?.isObjectUrl) {
        URL.revokeObjectURL(removed.url)
      }
      return next
    })
  }

  const applyArtAudioFiles = (files) => {
    setArtAudioFiles((prev) => {
      prev.forEach((item) => {
        if (item.url && item.isObjectUrl) {
          URL.revokeObjectURL(item.url)
        }
      })
      return files.map((file) => ({
        file,
        url: URL.createObjectURL(file),
        isObjectUrl: true
      }))
    })
  }

  const handleAudioFilesChange = (event) => {
    const files = Array.from(event.target.files || [])
    applyArtAudioFiles(files)
  }

  const handleAudioUrlLoad = (value) => {
    const raw = (value ?? '').trim()
    if (!raw) {
      return
    }
    let name = raw
    try {
      const parsed = new URL(raw)
      name = parsed.pathname.split('/').filter(Boolean).pop() || parsed.hostname
    } catch (err) {
      name = raw
    }
    setArtAudioFiles((prev) => [
      ...prev,
      {
        file: { name },
        url: raw,
        isObjectUrl: false
      }
    ])
    if (selectedProject) {
      fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/media/audio/url`)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: raw })
        }
      ).catch((err) => {
        console.warn('Upload audio url failed', err)
      })
    }
  }

  const removeAudioFile = (urlToRemove) => {
    setArtAudioFiles((prev) => {
      const next = prev.filter((item) => item.url !== urlToRemove)
      const removed = prev.find((item) => item.url === urlToRemove)
      if (removed?.url && removed?.isObjectUrl) {
        URL.revokeObjectURL(removed.url)
      }
      return next
    })
  }

  useEffect(() => {
    return () => {
      artImageFiles.forEach((item) => {
        if (item.isObjectUrl) {
          URL.revokeObjectURL(item.url)
        }
      })
      artAudioFiles.forEach((item) => {
        if (item.isObjectUrl) {
          URL.revokeObjectURL(item.url)
        }
      })
    }
  }, [artImageFiles, artAudioFiles])

  const openMediaModal = (kind) => {
    setMediaModalKind(kind)
    setMediaModalUrl('')
    setMediaModalFiles([])
    setMediaModalOpen(true)
  }

  const closeMediaModal = () => {
    setMediaModalOpen(false)
    setMediaModalKind('')
    setMediaModalUrl('')
    setMediaModalFiles([])
  }

  const saveMediaModal = () => {
    if (mediaModalKind === 'image') {
      if (mediaModalFiles.length) {
        applyArtImageFiles(mediaModalFiles)
      }
      if (mediaModalUrl.trim()) {
        handleImageUrlLoad(mediaModalUrl)
      }
    }
    if (mediaModalKind === 'audio') {
      if (mediaModalFiles.length) {
        applyArtAudioFiles(mediaModalFiles)
      }
      if (mediaModalUrl.trim()) {
        handleAudioUrlLoad(mediaModalUrl)
      }
    }
    closeMediaModal()
  }

  const stopHiggsfieldPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  useEffect(() => stopHiggsfieldPolling, [])

  const getProjectStrataUrl = (projectId, strata) =>
    `${apiOrigin}${joinPath(apiBasePath, `/projects/${projectId}/${strata}`)}`

  const fetchProjects = async () => {
    setProjectsStatus('loading')
    setProjectsError('')
    try {
      const resp = await fetch(projectsEndpoint)
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setProjects(Array.isArray(data.projects) ? data.projects : [])
      setProjectsStatus('done')
    } catch (err) {
      setProjectsStatus('error')
      setProjectsError(err.message)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [projectsEndpoint])

  useEffect(() => {
    setChatMessages([])
    setChatSessionId('')
    setChatError('')
    setN0FromUi(false)
    setHasPendingQuestions(false)
  }, [selectedProject])

  useEffect(() => {
    if (!createModalOpen) {
      return
    }
    setChatMessages([])
    setChatSessionId('')
    setChatError('')
    setChatInput('')
    setCreateProjectError('')
    setCreatedProjectId('')
    setCreateProjectStatus('idle')
  }, [createModalOpen])

  useEffect(() => {
    if (activePage !== 'project' || !n0Data) {
      return
    }
    document.querySelectorAll('.auto-resize').forEach((element) => {
      resizeTextarea(element)
    })
  }, [activePage, n0Data])

  const sanitizeN0 = (payload) => {
    const root = payload && typeof payload === 'object' ? payload : {}
    const data =
      root.data && typeof root.data === 'object'
        ? root.data
        : root
    return {
      production_summary: {
        summary: data.production_summary?.summary || '',
        production_type: data.production_summary?.production_type || '',
        target_duration: data.production_summary?.target_duration || '',
        aspect_ratio: data.production_summary?.aspect_ratio || '16:9',
        visual_style: data.production_summary?.visual_style || '',
        tone: data.production_summary?.tone || '',
        era: data.production_summary?.era || ''
      },
      deliverables: {
        visuals: {
          images_enabled: data.deliverables?.visuals?.images_enabled ?? true,
          videos_enabled: data.deliverables?.visuals?.videos_enabled ?? true
        },
        audio_stems: {
          dialogue: data.deliverables?.audio_stems?.dialogue ?? true,
          sfx: data.deliverables?.audio_stems?.sfx ?? true,
          music: data.deliverables?.audio_stems?.music ?? true
        }
      },
      art_direction: {
        description: data.art_direction?.description || '',
        references: data.art_direction?.references || ''
      },
      sound_direction: {
        description: data.sound_direction?.description || '',
        references: data.sound_direction?.references || ''
      }
    }
  }

  const buildN0UiPayload = (payload) => {
    const data = payload && typeof payload === 'object' ? payload : {}
    return {
      production_summary: {
        summary: data.production_summary?.summary || '',
        production_type: data.production_summary?.production_type || '',
        target_duration: data.production_summary?.target_duration || '',
        aspect_ratio: data.production_summary?.aspect_ratio || ''
      },
      art_direction: {
        description: data.art_direction?.description || ''
      },
      sound_direction: {
        description: data.sound_direction?.description || ''
      }
    }
  }

  const hasText = (value) => typeof value === 'string' && value.trim().length > 0
  const isN0Complete = (payload) =>
    Boolean(
      payload &&
        hasText(payload.production_summary?.summary) &&
        hasText(payload.art_direction?.description) &&
        hasText(payload.sound_direction?.description)
    )

  const sanitizeN1 = (payload) => {
    const root = payload && typeof payload === 'object' ? payload : {}
    const data =
      root.data && typeof root.data === 'object'
        ? root.data
        : root
    const toNumber = (value) => {
      const parsed = Number(value)
      return Number.isFinite(parsed) ? parsed : 0
    }
    const characters =
      data.characters && typeof data.characters === 'object' ? data.characters : {}
    return {
      characters: {
        main_characters: {
          number: toNumber(characters.main_characters?.number)
        },
        secondary_characters: {
          number: toNumber(characters.secondary_characters?.number)
        },
        background_characters: {
          number: toNumber(characters.background_characters?.number)
        }
      }
    }
  }

  const sanitizeN2 = (payload) => {
    const root = payload && typeof payload === 'object' ? payload : {}
    const data =
      root.data && typeof root.data === 'object'
        ? root.data
        : root
    const isStructuredN2 =
      Array.isArray(data.structure?.acts) ||
      data.document_level === 'N2' ||
      data.document_name === 'N2_ARCHITECTURE__global_structure'
    if (isStructuredN2) {
      const sanitizeNarrative = (entry) =>
        entry && typeof entry === 'object' ? entry : {}
      const sanitizeScene = (entry) => {
        const scene = entry && typeof entry === 'object' ? entry : {}
        return {
          id: scene.id || '',
          type: scene.type || '',
          index: Number.isFinite(scene.index) ? scene.index : 0,
          title: scene.title || '',
          budget_duration_s: Number.isFinite(scene.budget_duration_s)
            ? scene.budget_duration_s
            : 0,
          summary: scene.summary || '',
          focus: Array.isArray(scene.focus) ? scene.focus : [],
          entry_to_exit: scene.entry_to_exit || ''
        }
      }
      const sanitizeSequence = (entry) => {
        const sequence = entry && typeof entry === 'object' ? entry : {}
        return {
          id: sequence.id || '',
          type: sequence.type || 'sequence',
          index: Number.isFinite(sequence.index) ? sequence.index : 0,
          title: sequence.title || '',
          timecode_in: sequence.timecode_in || '',
          timecode_out: sequence.timecode_out || '',
          duration_s: Number.isFinite(sequence.duration_s) ? sequence.duration_s : 0,
          narrative: sanitizeNarrative(sequence.narrative),
          scenes: Array.isArray(sequence.scenes)
            ? sequence.scenes.map(sanitizeScene)
            : []
        }
      }
      const sanitizeAct = (entry) => {
        const act = entry && typeof entry === 'object' ? entry : {}
        return {
          id: act.id || '',
          type: act.type || 'act',
          index: Number.isFinite(act.index) ? act.index : 0,
          title: act.title || '',
          timecode_in: act.timecode_in || '',
          timecode_out: act.timecode_out || '',
          duration_s: Number.isFinite(act.duration_s) ? act.duration_s : 0,
          narrative: sanitizeNarrative(act.narrative),
          sequences: Array.isArray(act.sequences)
            ? act.sequences.map(sanitizeSequence)
            : []
        }
      }
      const normalized = { ...data }
      normalized.project_id = data.project_id || root.project_id || ''
      normalized.document_level = data.document_level || 'N2'
      normalized.document_name = data.document_name || ''
      normalized.version = data.version || ''
      normalized.meta = {
        ...(data.meta || {}),
        format: {
          target_duration_tc: data.meta?.format?.target_duration_tc || '',
          target_duration_s: Number.isFinite(data.meta?.format?.target_duration_s)
            ? data.meta.format.target_duration_s
            : 0,
          aspect_ratio: data.meta?.format?.aspect_ratio || '',
          timebase: data.meta?.format?.timebase || '',
          language: data.meta?.format?.language || ''
        },
        granularity: {
          n2: data.meta?.granularity?.n2 || '',
          n3_target: data.meta?.granularity?.n3_target || ''
        },
        canon: {
          tone: Array.isArray(data.meta?.canon?.tone) ? data.meta.canon.tone : [],
          visual_style: data.meta?.canon?.visual_style || '',
          sound_style: data.meta?.canon?.sound_style || '',
          characters: Array.isArray(data.meta?.canon?.characters)
            ? data.meta.canon.characters
            : [],
          narrative_arc: Array.isArray(data.meta?.canon?.narrative_arc)
            ? data.meta.canon.narrative_arc
            : []
        }
      }
      normalized.timeline = {
        ...(data.timeline || {}),
        acts_count: Number.isFinite(data.timeline?.acts_count)
          ? data.timeline.acts_count
          : 0,
        sequences_count: Number.isFinite(data.timeline?.sequences_count)
          ? data.timeline.sequences_count
          : 0,
        scenes_count: Number.isFinite(data.timeline?.scenes_count)
          ? data.timeline.scenes_count
          : 0,
        duration_s_total: Number.isFinite(data.timeline?.duration_s_total)
          ? data.timeline.duration_s_total
          : 0,
        timecode_in: data.timeline?.timecode_in || '',
        timecode_out: data.timeline?.timecode_out || ''
      }
      normalized.cast = {
        ...(data.cast || {}),
        primary: Array.isArray(data.cast?.primary) ? data.cast.primary : [],
        rule: data.cast?.rule || ''
      }
      normalized.structure = {
        ...(data.structure || {}),
        acts: Array.isArray(data.structure?.acts)
          ? data.structure.acts.map(sanitizeAct)
          : []
      }
      normalized.constraints_check =
        data.constraints_check && typeof data.constraints_check === 'object'
          ? data.constraints_check
          : {}
      normalized.handoff_to_n3 = {
        ...(data.handoff_to_n3 || {}),
        n3_units_to_expand: Array.isArray(data.handoff_to_n3?.n3_units_to_expand)
          ? data.handoff_to_n3.n3_units_to_expand
          : [],
        n3_expectations: Array.isArray(data.handoff_to_n3?.n3_expectations)
          ? data.handoff_to_n3.n3_expectations
          : []
      }
      return normalized
    }
    const sanitizeUnit = (entry) => {
      const unit = entry && typeof entry === 'object' ? entry : {}
      const rawStakes = unit.stakes
      const stakes =
        rawStakes && typeof rawStakes === 'object'
          ? rawStakes
          : { primary: rawStakes || '', secondary: '' }
      return {
        id: unit.id || '',
        type: unit.type || '',
        title: unit.title || '',
        function: unit.function || '',
        stakes: {
          primary: stakes.primary || '',
          secondary: stakes.secondary || ''
        },
        evolution: unit.evolution || '',
        setting_time: unit.setting_time || '',
        exit_change: unit.exit_change || '',
        continuity_notes: unit.continuity_notes || ''
      }
    }
    const sanitizeReference = (entry) => {
      const reference = entry && typeof entry === 'object' ? entry : {}
      return {
        concept: reference.concept || '',
        source: reference.source || '',
        usage: reference.usage || ''
      }
    }
    const sanitizeOutlineEntry = (entry) => {
      const node = entry && typeof entry === 'object' ? entry : {}
      const kind = node.kind || ''
      return {
        id: node.id || '',
        kind,
        title: node.title || '',
        summary: node.summary || '',
        children: Array.isArray(node.children)
          ? node.children.map(sanitizeOutlineEntry)
          : []
      }
    }
    return {
      meta: {
        status: data.meta?.status || 'draft',
        version: data.meta?.version || '0.1',
        dependencies: {
          n0: data.meta?.dependencies?.n0 || '',
          n1: data.meta?.dependencies?.n1 || ''
        }
      },
      rappel_entrees: data.rappel_entrees || '',
      structure: {
        format: data.structure?.format || '',
        justification: data.structure?.justification || ''
      },
      granularite: {
        niveau: data.granularite?.niveau || '',
        justification: data.granularite?.justification || ''
      },
      outline: Array.isArray(data.outline)
        ? data.outline.map(sanitizeOutlineEntry)
        : [],
      units: Array.isArray(data.units) ? data.units.map(sanitizeUnit) : [],
      contraintes_verifications: data.contraintes_verifications || '',
      hypotheses: data.hypotheses || '',
      questions: data.questions || '',
      references: Array.isArray(data.references)
        ? data.references.map(sanitizeReference)
        : [],
      cartographie_macro: {
        arc_principal: data.cartographie_macro?.arc_principal || '',
        arcs_secondaires: Array.isArray(data.cartographie_macro?.arcs_secondaires)
          ? data.cartographie_macro.arcs_secondaires
          : [],
        motifs_variation: data.cartographie_macro?.motifs_variation || ''
      }
    }
  }

  const sanitizeN3 = (payload) => {
    const root = payload && typeof payload === 'object' ? payload : {}
    const data =
      root.data && typeof root.data === 'object'
        ? root.data
        : root
    const normalizeN3Unit = (unit) => {
      const identity = unit?.identity || {}
      return {
        ...unit,
        id: unit?.id || identity.id || '',
        title: unit?.title || identity.title_short || unit?.title_short || '',
        duration_s: unit?.duration_s ?? identity.duration_s,
        treatment:
          unit?.treatment ||
          unit?.deroule_detaille ||
          unit?.deroule_detaille ||
          []
      }
    }
    return {
      project_id: data.project_id || root.project_id || '',
      document_level: data.document_level || 'N3',
      document_name: data.document_name || '',
      version: data.version || '',
      meta: {
        status: data.meta?.status || 'draft',
        language: data.meta?.language || data.meta?.format?.language || '',
        target_duration_s: Number.isFinite(data.meta?.target_duration_s)
          ? data.meta.target_duration_s
          : Number.isFinite(data.meta?.format?.target_duration_s)
            ? data.meta.format.target_duration_s
            : 0,
        aspect_ratio: data.meta?.aspect_ratio || data.meta?.format?.aspect_ratio || '',
        granularity: data.meta?.granularity || '',
        dependencies: {
          n0_updated_at:
            data.meta?.dependencies?.N0?.updated_at ||
            data.meta?.dependencies?.n0_updated_at ||
            '',
          n1_version:
            data.meta?.dependencies?.N1?.version ||
            data.meta?.dependencies?.n1_version ||
            '',
          n1_updated_at:
            data.meta?.dependencies?.N1?.updated_at ||
            data.meta?.dependencies?.n1_updated_at ||
            '',
          n2_version:
            data.meta?.dependencies?.N2?.version ||
            data.meta?.dependencies?.n2_version ||
            '',
          n2_updated_at:
            data.meta?.dependencies?.N2?.updated_at ||
            data.meta?.dependencies?.n2_updated_at ||
            ''
        },
        canon: data.meta?.canon || data.meta?.canon_reminders || {},
        constraints: data.meta?.constraints || {}
      },
      units_index: Array.isArray(data.index_des_unites_traitees)
        ? data.index_des_unites_traitees
        : Array.isArray(data.units_index)
          ? data.units_index
          : [],
      units: Array.isArray(data.unites)
        ? data.unites.map(normalizeN3Unit)
        : Array.isArray(data.units)
          ? data.units.map(normalizeN3Unit)
          : [],
      sequence_estimates: Array.isArray(data.sequence_estimates)
        ? data.sequence_estimates
        : [],
      global_continuity:
        data.table_continuite_globale && typeof data.table_continuite_globale === 'object'
          ? data.table_continuite_globale
          : data.global_continuity && typeof data.global_continuity === 'object'
            ? data.global_continuity
            : {},
      design_notes_internal: Array.isArray(data.notes_de_conception_narratologie)
        ? data.notes_de_conception_narratologie
        : Array.isArray(data.design_notes_internal)
          ? data.design_notes_internal
          : [],
      alertes_incoherences: Array.isArray(data.alertes_incoherences)
        ? data.alertes_incoherences
        : [],
      hypotheses: Array.isArray(data.hypotheses) ? data.hypotheses : [],
      questions: Array.isArray(data.questions) ? data.questions : []
    }
  }

  const buildOutlineFromUnits = (units) =>
    units.map((unit, index) => ({
      id: unit.id || `U${String(index + 1).padStart(3, '0')}`,
      kind: 'PART',
      title: unit.title || `Unite ${index + 1}`,
      summary: unit.summary || unit.function || unit.stakes?.primary || '',
      children: []
    }))

  const sanitizeN4Timeline = (payload) => {
    const root = payload && typeof payload === 'object' ? payload : {}
    const data =
      root.data && typeof root.data === 'object'
        ? root.data
        : root
    const sanitizeSegment = (segment) => {
      const entry = segment && typeof segment === 'object' ? segment : {}
      return {
        id: entry.id || '',
        label: entry.label || '',
        start_tc: entry.start_tc || '',
        end_tc: entry.end_tc || '',
        duration_ms: Number.isFinite(entry.duration_ms) ? entry.duration_ms : null,
        source_ref: entry.source_ref || '',
        notes: entry.notes || ''
      }
    }
    const sanitizeTrack = (track) => {
      const t = track && typeof track === 'object' ? track : {}
      return {
        id: t.id || '',
        type: t.type || '',
        label: t.label || t.id || '',
        segments: Array.isArray(t.segments) ? t.segments.map(sanitizeSegment) : []
      }
    }
    return {
      meta: {
        status: data.meta?.status || 'draft',
        version: data.meta?.version || '0.1',
        dependencies: {
          n2: data.meta?.dependencies?.n2 || '',
          n3: data.meta?.dependencies?.n3 || ''
        }
      },
      tracks: Array.isArray(data.tracks) ? data.tracks.map(sanitizeTrack) : [],
      notes: data.notes || ''
    }
  }

  const sanitizeN5 = (payload) => {
    const root = payload && typeof payload === 'object' ? payload : {}
    const data =
      root.data && typeof root.data === 'object'
        ? root.data
        : root
    const sanitizeList = (entries) => (Array.isArray(entries) ? entries : [])
    return {
      project_id: data.project_id || root.project_id || '',
      document_level: data.document_level || 'N5',
      document_name: data.document_name || '',
      version: data.version || '',
      meta: {
        status: data.meta?.status || 'draft',
        language: data.meta?.language || '',
        aspect_ratio: data.meta?.aspect_ratio || '',
        timebase: data.meta?.timebase || '',
        dependencies: data.dependencies || data.meta?.dependencies || {}
      },
      scope: data.meta?.scope || {},
      stack: data.stack || {},
      render_specs: data.render_specs || {},
      safety_and_branding: data.safety_and_branding || {},
      global_prompt_tokens: data.global_prompt_tokens || {},
      assets: data.assets || {},
      prompts: data.prompts || {},
      notes: data.notes || ''
    }
  }

  const getN2Outline = (data) => {
    if (!data) return []
    const summaryFromNarrative = (narrative) =>
      narrative?.function ||
      narrative?.local_objective ||
      narrative?.sequence_exit_change ||
      narrative?.act_exit_change ||
      ''
    if (Array.isArray(data.structure?.acts) && data.structure.acts.length) {
      return data.structure.acts.map((act, actIndex) => {
        const actSummary =
          summaryFromNarrative(act.narrative) ||
          (Array.isArray(act.sequences) ? act.sequences[0]?.title : '')
        return {
          id: act.id || `U${String(actIndex + 1).padStart(3, '0')}`,
          kind: 'ACT',
          title: act.title || `Acte ${actIndex + 1}`,
          summary: actSummary,
          duration_s: act.duration_s,
          timecode_in: act.timecode_in,
          timecode_out: act.timecode_out,
          children: Array.isArray(act.sequences)
            ? act.sequences.map((sequence, seqIndex) => {
                const sequenceSummary =
                  summaryFromNarrative(sequence.narrative) ||
                  (Array.isArray(sequence.scenes) ? sequence.scenes[0]?.summary : '')
                return {
                  id: sequence.id || `S${String(seqIndex + 1).padStart(3, '0')}`,
                  kind: 'SEQ',
                  title: sequence.title || `Sequence ${seqIndex + 1}`,
                  summary: sequenceSummary,
                  duration_s: sequence.duration_s,
                  timecode_in: sequence.timecode_in,
                  timecode_out: sequence.timecode_out,
                  children: Array.isArray(sequence.scenes)
                    ? sequence.scenes.map((scene, sceneIndex) => ({
                        id: scene.id || `SC${String(sceneIndex + 1).padStart(3, '0')}`,
                        kind: 'SCENE',
                        title: scene.title || `Scene ${sceneIndex + 1}`,
                        summary:
                          scene.summary ||
                          scene.narrative?.function ||
                          scene.narrative?.sequence_exit_change ||
                          '',
                        duration_s: scene.budget_duration_s,
                        timecode_in: scene.timecode_in,
                        timecode_out: scene.timecode_out,
                        children: []
                      }))
                    : []
                }
              })
            : []
        }
      })
    }
    if (Array.isArray(data.outline) && data.outline.length) {
      return data.outline
    }
    if (Array.isArray(data.units) && data.units.length) {
      return buildOutlineFromUnits(data.units)
    }
    return []
  }

  const renderN2Outline = (nodes, path = 'root') => (
    <ol className="outline-tree">
      {nodes.map((node, index) => {
        const key = node.id ? `${path}-${node.id}` : `${path}-${index}`
        const title = node.title || 'Sans titre'
        const summary = node.summary || ''
        const isSequence =
          node.kind === 'SEQ' || (node.id && node.id.startsWith('S'))
        const isAct = node.kind === 'ACT' || (node.id && node.id.startsWith('U'))
        const duration =
          Number.isFinite(node.duration_s) && node.duration_s > 0
            ? `${node.duration_s}s`
            : ''
        const timecode =
          node.timecode_in || node.timecode_out
            ? `${node.timecode_in || '--:--'} - ${node.timecode_out || '--:--'}`
            : ''
        const meta = timecode && duration ? `${timecode} | ${duration}` : timecode || duration
        const badge = isSequence ? 'SEQ' : isAct ? 'ACT' : 'PART'
        const label = node.id
          ? node.id
          : isSequence
          ? `S${String(index + 1).padStart(3, '0')}`
          : `U${String(index + 1).padStart(3, '0')}`
        return (
          <li key={key} className="outline-node">
            <div className="outline-card">
              <div className="outline-title">
                <span className={`outline-id ${isSequence ? 'is-seq' : ''}`}>
                  {label}
                </span>
                <span className={`outline-kind ${isSequence ? 'is-seq' : ''}`}>
                  {badge}
                </span>
                <strong>{title}</strong>
              </div>
              {meta ? <p className="outline-meta">{meta}</p> : null}
              {summary ? (
                <p className="outline-summary">{summary}</p>
              ) : (
                <p className="hint">Resume manquant.</p>
              )}
            </div>
            {node.children && node.children.length
              ? renderN2Outline(node.children, key)
              : null}
          </li>
        )
      })}
    </ol>
  )

  const fetchN0 = async (projectId) => {
    setN0Status('loading')
    setN0Error('')
    try {
      let data = null
      let fromUi = false
      const uiResp = await fetch(`${getProjectStrataUrl(projectId, 'n0')}/ui`)
      if (uiResp.ok) {
        data = await uiResp.json()
        fromUi = true
      } else if (uiResp.status !== 404) {
        throw new Error(`HTTP ${uiResp.status}`)
      }
      if (!data) {
        const resp = await fetch(getProjectStrataUrl(projectId, 'n0'))
        data = await resp.json()
        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}`)
        }
        fromUi = false
      }
      const sanitized = sanitizeN0(data?.data || null)
      setN0Data(sanitized)
      setN0FromUi(fromUi)
      setN0UpdatedAt(data?.updated_at || '')
      setN0Status('done')
      return sanitized
    } catch (err) {
      setN0Status('error')
      setN0Error(err.message)
      setN0Data(null)
      setN0UpdatedAt('')
      return null
    }
  }

  const fetchN1 = async (projectId) => {
    setN1Status('loading')
    setN1Error('')
    try {
      const resp = await fetch(getProjectStrataUrl(projectId, 'n1'))
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN1Data(sanitizeN1(data?.data || null))
      setN1UpdatedAt(data?.updated_at || '')
      setN1Status('done')
    } catch (err) {
      setN1Status('error')
      setN1Error(err.message)
      setN1Data(null)
      setN1UpdatedAt('')
    }
  }

  const fetchN2 = async (projectId) => {
    setN2Status('loading')
    setN2Error('')
    try {
      const resp = await fetch(getProjectStrataUrl(projectId, 'n2'))
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN2Data(sanitizeN2(data?.data || null))
      setN2UpdatedAt(data?.updated_at || '')
      setN2Status('done')
    } catch (err) {
      setN2Status('error')
      setN2Error(err.message)
      setN2Data(null)
      setN2UpdatedAt('')
    }
  }

  const fetchN3 = async (projectId) => {
    setN3Status('loading')
    setN3Error('')
    try {
      const resp = await fetch(getProjectStrataUrl(projectId, 'n3'))
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN3Data(sanitizeN3(data?.data || null))
      setN3UpdatedAt(data?.updated_at || '')
      setN3Status('done')
    } catch (err) {
      setN3Status('error')
      setN3Error(err.message)
      setN3Data(null)
      setN3UpdatedAt('')
    }
  }

  const fetchN4 = async (projectId) => {
    setN4Status('loading')
    setN4Error('')
    try {
      const resp = await fetch(getProjectStrataUrl(projectId, 'n4'))
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN4Data(sanitizeN4Timeline(data?.data || null))
      setN4UpdatedAt(data?.updated_at || '')
      setN4Status('done')
    } catch (err) {
      setN4Status('error')
      setN4Error(err.message)
      setN4Data(null)
      setN4UpdatedAt('')
    }
  }

  const fetchN5 = async (projectId) => {
    setN5Status('loading')
    setN5Error('')
    try {
      const resp = await fetch(getProjectStrataUrl(projectId, 'n5'))
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN5Data(sanitizeN5(data?.data || null))
      setN5UpdatedAt(data?.updated_at || '')
      setN5Status('done')
    } catch (err) {
      setN5Status('error')
      setN5Error(err.message)
      setN5Data(null)
      setN5UpdatedAt('')
    }
  }

  useEffect(() => {
    if (selectedProject) {
      fetchN0(selectedProject)
      fetchN1(selectedProject)
      fetchN2(selectedProject)
      fetchN3(selectedProject)
      fetchN4(selectedProject)
      fetchN5(selectedProject)
    } else {
      setN0Data(null)
      setN0UpdatedAt('')
      setN0Status('idle')
      setN0Error('')
      setN1Data(null)
      setN1UpdatedAt('')
      setN1Status('idle')
      setN1Error('')
      setN2Data(null)
      setN2UpdatedAt('')
      setN2Status('idle')
      setN2Error('')
      setN3Data(null)
      setN3UpdatedAt('')
      setN3Status('idle')
      setN3Error('')
      setN4Data(null)
      setN4UpdatedAt('')
      setN4Status('idle')
      setN4Error('')
      setN5Data(null)
      setN5UpdatedAt('')
      setN5Status('idle')
      setN5Error('')
    }
  }, [selectedProject])

  useEffect(() => {
    const handleDoubleClick = (event) => {
      if (editorOpen) {
        return
      }
      const target = event.target
      if (!target || !(target instanceof HTMLElement)) {
        return
      }
      if (target.closest('.modal')) {
        return
      }
      const tag = target.tagName
      const isTextInput =
        tag === 'TEXTAREA' ||
        (tag === 'INPUT' && (!target.type || target.type === 'text'))
      if (!isTextInput || target.readOnly || target.disabled) {
        return
      }
      const label = target.closest('label')
      let labelText = ''
      if (label) {
        const textNodes = Array.from(label.childNodes).filter(
          (node) => node.nodeType === Node.TEXT_NODE
        )
        labelText = textNodes.map((node) => node.textContent || '').join(' ').trim()
        if (!labelText) {
          labelText = label.textContent?.trim() || ''
        }
      }
      editorTargetRef.current = target
      const targetPath = target.dataset?.editPath || ''
      openEditor(labelText || 'Edition', target.value || '')
      setEditorTargetPath(targetPath)
    }
    document.addEventListener('dblclick', handleDoubleClick)
    return () => document.removeEventListener('dblclick', handleDoubleClick)
  }, [editorOpen])

  useEffect(() => {
    if (!n3Data) {
      setSelectedN3UnitId('')
      return
    }
    if (selectedN3UnitId) {
      return
    }
    const firstId =
      n3Data.units_index?.[0]?.id || n3Data.units?.[0]?.id || ''
    if (firstId) {
      setSelectedN3UnitId(firstId)
    }
  }, [n3Data, selectedN3UnitId])

  const updateNestedValue = (data, path, value) => {
    const next = { ...data }
    let cursor = next
    for (let i = 0; i < path.length - 1; i += 1) {
      const key = path[i]
      cursor[key] = { ...(cursor[key] || {}) }
      cursor = cursor[key]
    }
    cursor[path[path.length - 1]] = value
    return next
  }

  const toArray = (value) =>
    value
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean)

  const fromArray = (value) =>
    Array.isArray(value) ? value.join(', ') : ''

  const handleN0FieldChange = (path, value) => {
    setN0Data((prev) => (prev ? updateNestedValue(prev, path, value) : prev))
  }

  const handleN0ArrayChange = (path, value) => {
    handleN0FieldChange(path, toArray(value))
  }

  const handleN1FieldChange = (path, value) => {
    setN1Data((prev) => (prev ? updateNestedValue(prev, path, value) : prev))
  }

  const handleN1ArrayChange = (path, value) => {
    handleN1FieldChange(path, toArray(value))
  }

  const handleN2FieldChange = (path, value) => {
    setN2Data((prev) => (prev ? updateNestedValue(prev, path, value) : prev))
  }

  const handleN2ArrayChange = (path, value) => {
    handleN2FieldChange(path, toArray(value))
  }

  const formatN3Value = (value) => {
    if (value === null || value === undefined) {
      return ''
    }
    if (typeof value === 'string' || typeof value === 'number') {
      return String(value)
    }
    return JSON.stringify(value, null, 2)
  }

  const updateCharacterField = (index, field, value) => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const next = { ...prev }
      const current = Array.isArray(next.personnages) ? next.personnages : []
      next.personnages = current.map((item, idx) =>
        idx === index ? { ...item, [field]: value } : item
      )
      return next
    })
  }

  const addCharacter = () => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.personnages) ? prev.personnages : []
      return {
        ...prev,
        personnages: [
          ...current,
          {
            name: '',
            role: '',
            function: '',
            description: '',
            appearance: '',
            signature: '',
            images: [],
            costumes: []
          }
        ]
      }
    })
  }

  const addCostume = (characterIndex) => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.personnages) ? prev.personnages : []
      const updated = current.map((character, idx) => {
        if (idx !== characterIndex) {
          return character
        }
        const costumes = Array.isArray(character.costumes) ? character.costumes : []
        return {
          ...character,
          costumes: [
            ...costumes,
            {
              description: '',
              images: []
            }
          ]
        }
      })
      return { ...prev, personnages: updated }
    })
  }

  const removeCostume = (characterIndex, costumeIndex) => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.personnages) ? prev.personnages : []
      const updated = current.map((character, idx) => {
        if (idx !== characterIndex) {
          return character
        }
        const costumes = Array.isArray(character.costumes) ? character.costumes : []
        return {
          ...character,
          costumes: costumes.filter((_, i) => i !== costumeIndex)
        }
      })
      return { ...prev, personnages: updated }
    })
  }

  const updateCostumeField = (characterIndex, costumeIndex, field, value) => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.personnages) ? prev.personnages : []
      const updated = current.map((character, idx) => {
        if (idx !== characterIndex) {
          return character
        }
        const costumes = Array.isArray(character.costumes) ? character.costumes : []
        return {
          ...character,
          costumes: costumes.map((item, i) =>
            i === costumeIndex ? { ...item, [field]: value } : item
          )
        }
      })
      return { ...prev, personnages: updated }
    })
  }

  const addMotif = () => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const motifs = Array.isArray(prev.motifs) ? prev.motifs : []
      return {
        ...prev,
        motifs: [...motifs, { description: '', images: [], audio: [] }]
      }
    })
  }

  const removeMotif = (index) => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const motifs = Array.isArray(prev.motifs) ? prev.motifs : []
      return { ...prev, motifs: motifs.filter((_, i) => i !== index) }
    })
  }

  const updateMotifField = (index, field, value) => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const motifs = Array.isArray(prev.motifs) ? prev.motifs : []
      return {
        ...prev,
        motifs: motifs.map((motif, i) =>
          i === index ? { ...motif, [field]: value } : motif
        )
      }
    })
  }

  const uploadN1CharacterImage = async (file, characterIndex) => {
    if (!selectedProject || !file) {
      return
    }
    try {
      const form = new FormData()
      form.append('file', file)
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n1/characters/${characterIndex}/images`)}`,
        {
          method: 'POST',
          body: form
        }
      )
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const filename = data?.filename
      if (filename) {
        setN1Data((prev) => {
          if (!prev) {
            return prev
          }
          const current = Array.isArray(prev.personnages) ? prev.personnages : []
          const nextCharacters = current.map((item, idx) => {
            if (idx !== characterIndex - 1) {
              return item
            }
            const images = Array.isArray(item.images) ? item.images : []
            return { ...item, images: [...images, filename] }
          })
          return { ...prev, personnages: nextCharacters }
        })
      }
    } catch (err) {
      console.warn('Upload N1 character image failed', err)
    }
  }

  const uploadN1CostumeImage = async (file, costumeId) => {
    if (!selectedProject || !file) {
      return
    }
    try {
      const form = new FormData()
      form.append('file', file)
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n1/characters/${costumeId.characterIndex}/costumes/${costumeId.costumeIndex}/images`)}`,
        {
          method: 'POST',
          body: form
        }
      )
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const filename = data?.filename
      if (filename) {
        setN1Data((prev) => {
          if (!prev) {
            return prev
          }
          const current = Array.isArray(prev.personnages) ? prev.personnages : []
          const updated = current.map((character, idx) => {
            if (idx !== costumeId.characterIndex - 1) {
              return character
            }
            const costumes = Array.isArray(character.costumes) ? character.costumes : []
            return {
              ...character,
              costumes: costumes.map((costume, cIdx) => {
                if (cIdx !== costumeId.costumeIndex - 1) {
                  return costume
                }
                const images = Array.isArray(costume.images) ? costume.images : []
                return { ...costume, images: [...images, filename] }
              })
            }
          })
          return { ...prev, personnages: updated }
        })
      }
    } catch (err) {
      console.warn('Upload N1 costume image failed', err)
    }
  }

  const uploadN1MotifImage = async (file, motifIndex) => {
    if (!selectedProject || !file) {
      return
    }
    try {
      const form = new FormData()
      form.append('file', file)
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n1/motifs/${motifIndex}/images`)}`,
        {
          method: 'POST',
          body: form
        }
      )
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const filename = data?.filename
      if (filename) {
        setN1Data((prev) => {
          if (!prev) {
            return prev
          }
          const motifs = Array.isArray(prev.motifs) ? prev.motifs : []
          const updated = motifs.map((motif, i) => {
            if (i !== motifIndex - 1) {
              return motif
            }
            const images = Array.isArray(motif.images) ? motif.images : []
            return { ...motif, images: [...images, filename] }
          })
          return { ...prev, motifs: updated }
        })
      }
    } catch (err) {
      console.warn('Upload N1 motif image failed', err)
    }
  }

  const uploadN1MotifAudio = async (file, motifIndex) => {
    if (!selectedProject || !file) {
      return
    }
    try {
      const form = new FormData()
      form.append('file', file)
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n1/motifs/${motifIndex}/audio`)}`,
        {
          method: 'POST',
          body: form
        }
      )
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const filename = data?.filename
      if (filename) {
        setN1Data((prev) => {
          if (!prev) {
            return prev
          }
          const motifs = Array.isArray(prev.motifs) ? prev.motifs : []
          const updated = motifs.map((motif, i) => {
            if (i !== motifIndex - 1) {
              return motif
            }
            const audio = Array.isArray(motif.audio) ? motif.audio : []
            return { ...motif, audio: [...audio, filename] }
          })
          return { ...prev, motifs: updated }
        })
      }
    } catch (err) {
      console.warn('Upload N1 motif audio failed', err)
    }
  }

  const removeN1CharacterImage = async (characterIndex, imageIndex, filename) => {
    if (!selectedProject || !filename) {
      return
    }
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n1/characters/${characterIndex}/images/${encodeURIComponent(filename)}`)}`,
        { method: 'DELETE' }
      )
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN1Data((prev) => {
        if (!prev) {
          return prev
        }
        const current = Array.isArray(prev.personnages) ? prev.personnages : []
        const nextCharacters = current.map((item, idx) => {
          if (idx !== characterIndex - 1) {
            return item
          }
          const images = Array.isArray(item.images) ? item.images : []
          return { ...item, images: images.filter((_, i) => i !== imageIndex) }
        })
        return { ...prev, personnages: nextCharacters }
      })
    } catch (err) {
      console.warn('Remove N1 character image failed', err)
    }
  }

  const removeN1MotifImage = async (motifIndex, imageIndex, filename) => {
    if (!selectedProject || !filename) {
      return
    }
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n1/motifs/${motifIndex}/images/${encodeURIComponent(filename)}`)}`,
        { method: 'DELETE' }
      )
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN1Data((prev) => {
        if (!prev) {
          return prev
        }
        const motifs = Array.isArray(prev.motifs) ? prev.motifs : []
        const updated = motifs.map((motif, i) => {
          if (i !== motifIndex - 1) {
            return motif
          }
          const images = Array.isArray(motif.images) ? motif.images : []
          return { ...motif, images: images.filter((_, idx) => idx !== imageIndex) }
        })
        return { ...prev, motifs: updated }
      })
    } catch (err) {
      console.warn('Remove N1 motif image failed', err)
    }
  }

  const removeN1MotifAudio = async (motifIndex, audioIndex, filename) => {
    if (!selectedProject || !filename) {
      return
    }
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n1/motifs/${motifIndex}/audio/${encodeURIComponent(filename)}`)}`,
        { method: 'DELETE' }
      )
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN1Data((prev) => {
        if (!prev) {
          return prev
        }
        const motifs = Array.isArray(prev.motifs) ? prev.motifs : []
        const updated = motifs.map((motif, i) => {
          if (i !== motifIndex - 1) {
            return motif
          }
          const audio = Array.isArray(motif.audio) ? motif.audio : []
          return { ...motif, audio: audio.filter((_, idx) => idx !== audioIndex) }
        })
        return { ...prev, motifs: updated }
      })
    } catch (err) {
      console.warn('Remove N1 motif audio failed', err)
    }
  }
  const removeN1CostumeImage = async (costumeId, imageIndex, filename) => {
    if (!selectedProject || !filename) {
      return
    }
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n1/characters/${costumeId.characterIndex}/costumes/${costumeId.costumeIndex}/images/${encodeURIComponent(filename)}`)}`,
        { method: 'DELETE' }
      )
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN1Data((prev) => {
        if (!prev) {
          return prev
        }
        const current = Array.isArray(prev.personnages) ? prev.personnages : []
        const updated = current.map((character, idx) => {
          if (idx !== costumeId.characterIndex - 1) {
            return character
          }
          const costumes = Array.isArray(character.costumes) ? character.costumes : []
          return {
            ...character,
            costumes: costumes.map((costume, cIdx) => {
              if (cIdx !== costumeId.costumeIndex - 1) {
                return costume
              }
              const images = Array.isArray(costume.images) ? costume.images : []
              return { ...costume, images: images.filter((_, i) => i !== imageIndex) }
            })
          }
        })
        return { ...prev, personnages: updated }
      })
    } catch (err) {
      console.warn('Remove N1 costume image failed', err)
    }
  }

  const removeCharacter = (index) => {
    setN1Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.personnages) ? prev.personnages : []
      return {
        ...prev,
        personnages: current.filter((_, idx) => idx !== index)
      }
    })
  }

  const addUnit = () => {
    setN2Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.units) ? prev.units : []
      const nextIndex = current.length + 1
      const nextId = `U${String(nextIndex).padStart(3, '0')}`
      return {
        ...prev,
        units: [
          ...current,
          {
            id: nextId,
            type: '',
            title: '',
            function: '',
            stakes: {
              primary: '',
              secondary: ''
            },
            evolution: '',
            setting_time: '',
            exit_change: '',
            continuity_notes: ''
          }
        ]
      }
    })
  }

  const removeUnit = (index) => {
    setN2Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.units) ? prev.units : []
      return { ...prev, units: current.filter((_, i) => i !== index) }
    })
  }

  const updateUnitField = (index, field, value) => {
    setN2Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.units) ? prev.units : []
      return {
        ...prev,
        units: current.map((unit, i) =>
          i === index ? { ...unit, [field]: value } : unit
        )
      }
    })
  }

  const updateUnitStake = (index, field, value) => {
    setN2Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.units) ? prev.units : []
      return {
        ...prev,
        units: current.map((unit, i) =>
          i === index
            ? {
                ...unit,
                stakes: {
                  ...(unit.stakes || {}),
                  [field]: value
                }
              }
            : unit
        )
      }
    })
  }

  const addReference = () => {
    setN2Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.references) ? prev.references : []
      return {
        ...prev,
        references: [...current, { concept: '', source: '', usage: '' }]
      }
    })
  }

  const removeReference = (index) => {
    setN2Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.references) ? prev.references : []
      return { ...prev, references: current.filter((_, i) => i !== index) }
    })
  }

  const updateReferenceField = (index, field, value) => {
    setN2Data((prev) => {
      if (!prev) {
        return prev
      }
      const current = Array.isArray(prev.references) ? prev.references : []
      return {
        ...prev,
        references: current.map((reference, i) =>
          i === index ? { ...reference, [field]: value } : reference
        )
      }
    })
  }


  const applyN1FromJson = async () => {
    if (!n1PasteText.trim()) {
      setN1PasteError('Colle un JSON avant de remplacer.')
      return
    }
    try {
      const cleaned = normalizeJsonInput(n1PasteText)
      const parsed = JSON.parse(cleaned)
      const payload = parsed && typeof parsed === 'object' && 'data' in parsed
        ? parsed.data
        : parsed
      if (!payload || typeof payload !== 'object') {
        throw new Error('JSON invalide')
      }
      const normalized = sanitizeN1(payload)
      setN1Data(normalized)
      setN1PasteError('')
      if (selectedProject) {
        await handleN1Save(normalized)
      }
    } catch (err) {
      setN1PasteError('JSON invalide ou incomplet.')
    }
  }

  const applyN2FromJson = async () => {
    if (!n2PasteText.trim()) {
      setN2PasteError('Colle un JSON avant de remplacer.')
      return
    }
    try {
      const cleaned = normalizeJsonInput(n2PasteText)
      const parsed = JSON.parse(cleaned)
      const payload = parsed && typeof parsed === 'object' && 'data' in parsed
        ? parsed.data
        : parsed
      if (!payload || typeof payload !== 'object') {
        throw new Error('JSON invalide')
      }
      const normalized = sanitizeN2(payload)
      setN2Data(normalized)
      setN2PasteError('')
      if (selectedProject) {
        await handleN2Save(normalized)
      }
    } catch (err) {
      setN2PasteError('JSON invalide ou incomplet.')
    }
  }

  const applyN3FromJson = async () => {
    if (!n3PasteText.trim()) {
      setN3PasteError('Colle un JSON avant de remplacer.')
      return
    }
    try {
      const cleaned = normalizeJsonInput(n3PasteText)
      const parsed = JSON.parse(cleaned)
      const payload = parsed && typeof parsed === 'object' && 'data' in parsed
        ? parsed.data
        : parsed
      if (!payload || typeof payload !== 'object') {
        throw new Error('JSON invalide')
      }
      const normalized = sanitizeN3(payload)
      setN3Data(normalized)
      setN3PasteError('')
      if (selectedProject) {
        await handleN3Save(normalized)
      }
    } catch (err) {
      setN3PasteError('JSON invalide ou incomplet.')
    }
  }

  const applyN4FromJson = async () => {
    if (!n4PasteText.trim()) {
      setN4PasteError('Colle un JSON avant de remplacer.')
      return
    }
    try {
      const cleaned = normalizeJsonInput(n4PasteText)
      const parsed = JSON.parse(cleaned)
      const payload = parsed && typeof parsed === 'object' && 'data' in parsed
        ? parsed.data
        : parsed
      if (!payload || typeof payload !== 'object') {
        throw new Error('JSON invalide')
      }
      const normalized = sanitizeN4Timeline(payload)
      setN4Data(normalized)
      setN4PasteError('')
      if (selectedProject) {
        await handleN4Save(normalized)
      }
    } catch (err) {
      setN4PasteError('JSON invalide ou incomplet.')
    }
  }

  const applyN5FromJson = async () => {
    if (!n5PasteText.trim()) {
      setN5PasteError('Colle un JSON avant de remplacer.')
      return
    }
    try {
      const cleaned = normalizeJsonInput(n5PasteText)
      const parsed = JSON.parse(cleaned)
      const payload = parsed && typeof parsed === 'object' && 'data' in parsed
        ? parsed.data
        : parsed
      if (!payload || typeof payload !== 'object') {
        throw new Error('JSON invalide')
      }
      const normalized = sanitizeN5(payload)
      setN5Data(normalized)
      setN5PasteError('')
      if (selectedProject) {
        await handleN5Save(normalized)
      }
    } catch (err) {
      setN5PasteError('JSON invalide ou incomplet.')
    }
  }

  const handleN0Save = async (overrideData = null) => {
    let payload = overrideData || n0Data
    if (!selectedProject || !payload) {
      return false
    }
    setN0Status('saving')
    setN0Error('')
    try {
      let resp = null
      if (n0FromUi) {
        const uiPayload = buildN0UiPayload(payload)
        const body = JSON.stringify(uiPayload)
        resp = await fetch(`${getProjectStrataUrl(selectedProject, 'n0')}/ui`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body
        })
      } else {
        payload = sanitizeN0(payload)
        const body = JSON.stringify(payload)
        resp = await fetch(getProjectStrataUrl(selectedProject, 'n0'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body
        })
      }
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN0UpdatedAt(data?.updated_at || n0UpdatedAt)
      setN0Status('done')
      return true
    } catch (err) {
      setN0Status('error')
      setN0Error(err.message)
      return false
    }
  }

  const openEditor = (label, value) => {
    setEditorLabel(label)
    setEditorValue(value || '')
    setEditorOriginal(value || '')
    setEditorTargetPath('')
    setEditorChatMessages([])
    setEditorChatInput('')
    setEditorChatStatus('idle')
    setEditorChatError('')
    setEditorChatSessionId('')
    setEditorChatSummary('')
    setEditorOpen(true)
  }

  const closeEditor = () => {
    setEditorOpen(false)
    setEditorValue('')
    setEditorOriginal('')
    setEditorLabel('')
    setEditorTargetPath('')
    setEditorChatMessages([])
    setEditorChatInput('')
    setEditorChatStatus('idle')
    setEditorChatError('')
    setEditorChatSessionId('')
    setEditorChatSummary('')
    editorTargetRef.current = null
  }

  const saveEditor = async () => {
    const target = editorTargetRef.current
    if (!target) {
      closeEditor()
      return
    }
    if (editorValue === editorOriginal) {
      closeEditor()
      return
    }
    const targetPath = target.dataset?.editPath || ''
    if (n0Data && targetPath.startsWith('n0.')) {
      const parts = targetPath.split('.').slice(1)
      const next = updateNestedValue(n0Data, parts, editorValue)
      setN0Data(next)
    }
    target.value = editorValue
    target.dispatchEvent(new Event('input', { bubbles: true }))
    closeEditor()
  }

  const handleEditorChatSend = async () => {
    const projectId = selectedProject
    const message = editorChatInput.trim()
    if (!projectId) {
      setEditorChatError('Selectionne un projet pour activer le chat.')
      return
    }
    if (!editorTargetPath) {
      setEditorChatError('Champ cible introuvable pour le mode edit.')
      return
    }
    if (!message) {
      setEditorChatError('Message requis.')
      return
    }
    setEditorChatStatus('sending')
    setEditorChatError('')
    setEditorChatMessages((prev) => [...prev, { role: 'user', content: message }])
    setEditorChatInput('')
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${encodeURIComponent(projectId)}/narration/message`)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message,
            session_id: editorChatSessionId || null,
            auto_create: false,
            mode: 'edit',
            target_path: editorTargetPath,
            actual_text: editorOriginal,
            edited_text: editorValue.trim() ? editorValue : editorOriginal,
            edit_session_id: editorChatSessionId || null
          })
        }
      )
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const nextEditSessionId = data?.edit_session_id || editorChatSessionId || ''
      if (nextEditSessionId) {
        setEditorChatSessionId(nextEditSessionId)
      }
      const assistantMessage = data?.assistant_message
        ? data.assistant_message
        : null
      const replyText = assistantMessage
        ? assistantMessage
            .split('\n')
            .filter((line) => !line.trim().startsWith('JSON'))
            .join('\n')
            .trim()
        : 'Reponse vide.'
      setEditorChatMessages((prev) => [...prev, { role: 'assistant', content: replyText }])
      const summary = data?.edit_summary
        ? String(data.edit_summary).trim()
        : replyText
      setEditorChatSummary(summary)
    } catch (err) {
      setEditorChatError(err.message)
      setEditorChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Erreur: ${err.message}` }
      ])
    } finally {
      setEditorChatStatus('idle')
    }
  }

  const handleN1Save = async (overrideData = null) => {
    let payload = overrideData || n1Data
    if (!selectedProject || !payload) {
      return false
    }
    payload = sanitizeN1(payload)
    setN1Status('saving')
    setN1Error('')
    try {
      const body = JSON.stringify(payload)
      const resp = await fetch(getProjectStrataUrl(selectedProject, 'n1'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      })
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN1UpdatedAt(data?.updated_at || n1UpdatedAt)
      setN1Status('done')
      return true
    } catch (err) {
      setN1Status('error')
      setN1Error(err.message)
      return false
    }
  }

  const handleN2Save = async (overrideData = null) => {
    let payload = overrideData || n2Data
    if (!selectedProject || !payload) {
      return false
    }
    payload = sanitizeN2(payload)
    setN2Status('saving')
    setN2Error('')
    try {
      const body = JSON.stringify(payload)
      const resp = await fetch(getProjectStrataUrl(selectedProject, 'n2'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      })
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN2UpdatedAt(data?.updated_at || n2UpdatedAt)
      setN2Status('done')
      return true
    } catch (err) {
      setN2Status('error')
      setN2Error(err.message)
      return false
    }
  }

  const handleN3Save = async (overrideData = null) => {
    let payload = overrideData || n3Data
    if (!selectedProject || !payload) {
      return false
    }
    payload = sanitizeN3(payload)
    setN3Status('saving')
    setN3Error('')
    try {
      const body = JSON.stringify(payload)
      const resp = await fetch(getProjectStrataUrl(selectedProject, 'n3'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      })
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN3UpdatedAt(data?.updated_at || n3UpdatedAt)
      setN3Status('done')
      return true
    } catch (err) {
      setN3Status('error')
      setN3Error(err.message)
      return false
    }
  }

  const handleN4Save = async (overrideData = null) => {
    let payload = overrideData || n4Data
    if (!selectedProject || !payload) {
      return false
    }
    payload = sanitizeN4Timeline(payload)
    setN4Status('saving')
    setN4Error('')
    try {
      const body = JSON.stringify(payload)
      const resp = await fetch(getProjectStrataUrl(selectedProject, 'n4'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      })
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN4UpdatedAt(data?.updated_at || n4UpdatedAt)
      setN4Status('done')
      return true
    } catch (err) {
      setN4Status('error')
      setN4Error(err.message)
      return false
    }
  }

  const handleN5Save = async (overrideData = null) => {
    let payload = overrideData || n5Data
    if (!selectedProject || !payload) {
      return false
    }
    payload = sanitizeN5(payload)
    setN5Status('saving')
    setN5Error('')
    try {
      const body = JSON.stringify(payload)
      const resp = await fetch(getProjectStrataUrl(selectedProject, 'n5'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      })
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN5UpdatedAt(data?.updated_at || n5UpdatedAt)
      setN5Status('done')
      return true
    } catch (err) {
      setN5Status('error')
      setN5Error(err.message)
      return false
    }
  }

  const closeProject = async () => {
    if (!selectedProject) {
      return
    }
    if (n0Data) {
      const saved = await handleN0Save()
      if (!saved) {
        setActivePage('project')
        return
      }
    }
    if (n1Data) {
      const saved = await handleN1Save()
      if (!saved) {
        setActivePage('bible')
        return
      }
    }
    if (n2Data) {
      const saved = await handleN2Save()
      if (!saved) {
        setActivePage('architecture')
        return
      }
    }
    if (n3Data) {
      const saved = await handleN3Save()
      if (!saved) {
        setActivePage('sequences')
        return
      }
    }
    if (n4Data) {
      const saved = await handleN4Save()
      if (!saved) {
        setActivePage('timeline')
        return
      }
    }
    if (n5Data) {
      const saved = await handleN5Save()
      if (!saved) {
        setActivePage('prompts')
        return
      }
    }
    setSelectedProject('')
    setActivePage('home')
  }

  const deleteProject = async (projectId) => {
    const ok = window.confirm(`Supprimer le projet "${projectId}" ?`)
    if (!ok) {
      return
    }
    setProjectsStatus('loading')
    setProjectsError('')
    try {
      const resp = await fetch(`${projectsEndpoint}/${projectId}`, {
        method: 'DELETE'
      })
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setSelectedProject((prev) => (prev === projectId ? '' : prev))
      if (selectedProject === projectId) {
        setActivePage('home')
      }
      await fetchProjects()
    } catch (err) {
      setProjectsStatus('error')
      setProjectsError(err.message)
    }
  }

  const createProject = async (projectId, options = {}) => {
    const { navigate = false } = options
    if (!projectId) {
      setProjectsError('Nom du projet requis.')
      return false
    }
    setProjectsStatus('loading')
    setProjectsError('')
    try {
      const resp = await fetch(projectsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId })
      })
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      await fetchProjects()
      setSelectedProject(projectId)
      if (navigate) {
        setActivePage('project')
      }
      return true
    } catch (err) {
      setProjectsStatus('error')
      setProjectsError(err.message)
      return false
    }
  }

  const openCreateModal = () => {
    setCreateProjectName('')
    setCanCloseCreateModal(false)
    setProgressActive(false)
    setProgressValue(0)
    progressStartRef.current = null
    setCreateModalOpen(true)
  }

  const closeCreateModal = () => {
    setCreateModalOpen(false)
    setCanCloseCreateModal(false)
    setProgressActive(false)
    setProgressValue(0)
    progressStartRef.current = null
  }

  const handleCreateProject = async () => {
    const projectId = createProjectName.trim()
    if (!projectId) {
      setCreateProjectError('Nom du projet requis.')
      return
    }
    setCreateProjectStatus('loading')
    setCreateProjectError('')
    const ok = await createProject(projectId, { navigate: false })
    if (ok) {
      setCreatedProjectId(projectId)
      setCreateProjectStatus('done')
    } else {
      setCreateProjectStatus('error')
      setCreateProjectError('Impossible de creer le projet.')
    }
  }

  const handleNarrationChatSend = async () => {
    const projectId = resolvedChatProjectId
    const message = chatInput.trim()
    if (!projectId) {
      setChatError('Cree le projet pour activer le chat.')
      return
    }
    if (!message) {
      setChatError('Message requis.')
      return
    }
    setChatStatus('sending')
    setChatError('')
    setChatMessages((prev) => [...prev, { role: 'user', content: message }])
    setChatInput('')
    if (createModalOpen && !progressActive) {
      setProgressActive(true)
      setProgressValue(0)
      progressStartRef.current = Date.now()
    }
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${encodeURIComponent(projectId)}/narration/message`)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message,
            session_id: chatSessionId || null,
            auto_create: !selectedProject
          })
        }
      )
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const nextSessionId = data?.session_id || chatSessionId || ''
      if (nextSessionId) {
        setChatSessionId(nextSessionId)
      }
      const assistantMessage = data?.assistant_message
        ? data.assistant_message
        : null
      const replyText = assistantMessage
        ? assistantMessage
            .split('\n')
            .filter((line) => !line.trim().startsWith('JSON'))
            .join('\n')
            .trim()
        : 'Reponse vide.'
      setChatMessages((prev) => [...prev, { role: 'assistant', content: replyText }])
      setHasPendingQuestions(Boolean(data?.has_pending_questions))
      const narrationResults = Array.isArray(data?.narration_run_result?.results)
        ? data.narration_run_result.results
        : []
      const n0Written = narrationResults.some((result) => {
        const outputRef = result?.output_ref || ''
        const outputStatus = result?.output?.status || ''
        return (
          typeof outputRef === 'string' &&
          outputRef.startsWith('n0.') &&
          outputStatus === 'done'
        )
      })
      if (!selectedProject) {
        setSelectedProject(projectId)
        await fetchProjects()
      }
      if (data?.has_pending_questions && !n0Written) {
        setProgressActive(false)
        setProgressValue(0)
        progressStartRef.current = null
      }
      if (n0Written) {
        const latestN0 = await fetchN0(projectId)
        const n0Complete = isN0Complete(latestN0)
        if (progressStartRef.current) {
          const elapsedMs = Date.now() - progressStartRef.current
          if (elapsedMs > 0) {
            const padded = Math.round(elapsedMs * N0_PROGRESS_PADDING)
            const nextEstimate = Math.max(padded, N0_PROGRESS_MIN_MS)
            setProgressEstimateMs(nextEstimate)
            window.localStorage.setItem('n0ProgressEstimateMs', String(nextEstimate))
          }
        }
        setProgressActive(false)
        setProgressValue(100)
        progressStartRef.current = null
        if (n0Complete) {
          setActivePage('project')
          closeCreateModal()
        }
      }
    } catch (err) {
      setChatError(err.message)
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Erreur: ${err.message}` }
      ])
      setProgressActive(false)
      setProgressValue(0)
      progressStartRef.current = null
    } finally {
      setChatStatus('idle')
    }
  }

  useEffect(() => {
    if (!progressActive) {
      return undefined
    }
    if (!progressStartRef.current) {
      progressStartRef.current = Date.now()
    }
    const tick = () => {
      const elapsedMs = Date.now() - progressStartRef.current
      const ratio = progressEstimateMs > 0 ? elapsedMs / progressEstimateMs : 0
      const next = Math.min(100, Math.max(0, ratio * 100))
      setProgressValue(next)
    }
    tick()
    const timer = window.setInterval(tick, 200)
    return () => window.clearInterval(timer)
  }, [progressActive, progressEstimateMs])

  const openProject = (projectId) => {
    setSelectedProject(projectId)
    setActivePage('project')
  }

  const handleHiggsfieldResponse = (data) => {
    if (!data || data.provider !== 'higgsfield') {
      return
    }
    const jobId = data.job_id || data.request_id || ''
    const statusUrl = data.status_url || ''
    const statusValue = (data.status || '').toLowerCase()
    const linkUrl =
      data.links?.find((link) => link.url && link.url !== 'pending')?.url || ''
    if (statusValue === 'completed' && linkUrl) {
      stopHiggsfieldPolling()
      setHiggsfieldStatus('done')
      setHiggsfieldJobId(jobId)
      setHiggsfieldUrl(linkUrl)
      setHiggsfieldStatusUrl(statusUrl)
      setHiggsfieldInfo('Termine.')
      setHiggsfieldLastStatus(statusValue || 'completed')
      return
    }
    if (jobId || statusUrl) {
      setHiggsfieldStatus('pending')
      setHiggsfieldJobId(jobId)
      setHiggsfieldUrl('')
      setHiggsfieldStatusUrl(statusUrl)
      setHiggsfieldInfo('Requete en cours...')
      setHiggsfieldLastStatus(statusValue)
      setHiggsfieldAttempts(0)
      stopHiggsfieldPolling()
      pollRef.current = setInterval(async () => {
        try {
          const query = statusUrl ? `?status_url=${encodeURIComponent(statusUrl)}` : ''
          const resp = await fetch(
            `${apiOrigin}${joinPath(apiBasePath, `/higgsfield/status/${encodeURIComponent(jobId || 'unknown')}`)}${query}`
          )
          if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`)
          }
          const statusData = await resp.json()
          if (statusData?.raw) {
            setHiggsfieldRaw(JSON.stringify(statusData.raw, null, 2))
          }
          const normalizedStatus = (statusData.status || '').toLowerCase()
          const resultUrl = statusData.result_url || statusData.url || ''
          setHiggsfieldLastStatus(normalizedStatus || 'pending')
          setHiggsfieldAttempts((prev) => prev + 1)
          if (statusData.error?.message) {
            stopHiggsfieldPolling()
            setHiggsfieldStatus('error')
            setHiggsfieldInfo(statusData.error.message)
            return
          }
          if (normalizedStatus === 'completed' && resultUrl) {
            stopHiggsfieldPolling()
            setHiggsfieldStatus('done')
            setHiggsfieldUrl(resultUrl)
            setHiggsfieldInfo('Termine.')
          } else if (normalizedStatus === 'completed' && !resultUrl) {
            stopHiggsfieldPolling()
            setHiggsfieldStatus('done')
            setHiggsfieldInfo('Termine, URL non disponible.')
          } else if (['failed', 'error', 'canceled', 'nsfw'].includes(normalizedStatus)) {
            stopHiggsfieldPolling()
            setHiggsfieldStatus('error')
            setHiggsfieldInfo(`Echec: ${normalizedStatus}`)
          } else if (higgsfieldAttempts >= 120) {
            stopHiggsfieldPolling()
            setHiggsfieldStatus('error')
            setHiggsfieldInfo('Timeout: pas de reponse finale.')
          } else {
            setHiggsfieldStatus('pending')
            setHiggsfieldInfo('Requete en cours...')
          }
        } catch (err) {
          stopHiggsfieldPolling()
          setHiggsfieldStatus('error')
          setHiggsfieldInfo(err.message)
        }
      }, 2000)
    }
  }

  const formatJson = () => {
    if (!parsedRequest.value) {
      return
    }
    setRequestText(JSON.stringify(parsedRequest.value, null, 2))
  }

  const normalizeRequest = async () => {
    if (!parsedRequest.value) {
      setError('JSON invalide. Corrige avant normalisation.')
      return
    }
    setStatus('sending')
    setError('')
    setResponseText('')
    const start = performance.now()
    const normalizeEndpoint = /\/mcp\/?$/.test(endpoint)
      ? endpoint.replace(/\/mcp\/?$/, '/normalize')
      : `${apiOrigin}${joinPath(apiBasePath, '/normalize')}`
    try {
      const resp = await fetch(`${normalizeEndpoint}?dispatch=false`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsedRequest.value)
      })
      const text = await resp.text()
      let data = null
      let parseError = null
      if (text) {
        try {
          data = JSON.parse(text)
        } catch (err) {
          parseError = err
        }
      }
      if (!resp.ok) {
        setResponseText(text || '(reponse vide)')
        throw new Error(`HTTP ${resp.status}`)
      }
      if (parseError || !data) {
        setResponseText(text || '(reponse vide)')
        throw new Error('Reponse /normalize non-JSON')
      }
      if (data?.normalized) {
        setRequestText(JSON.stringify(data.normalized, null, 2))
      }
      setStatus('normalized')
    } catch (err) {
      setStatus('error')
      setError(err.message)
    } finally {
      const end = performance.now()
      setLastDuration(Math.round(end - start))
    }
  }

  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText()
      if (text) {
        setRequestText(text)
      }
    } catch (err) {
      setError("Impossible d'acceder au presse-papier.")
    }
  }

  const loadTemplate = (key) => {
    const template = templates[key]
    if (!template) {
      return
    }
    setRequestText(JSON.stringify(template, null, 2))
  }

  const sendRequest = async () => {
    if (!parsedRequest.value) {
      setError('JSON invalide. Corrige avant envoi.')
      return
    }
    setStatus('sending')
    setError('')
    setResponseText('')
    stopHiggsfieldPolling()
    setHiggsfieldStatus('idle')
    setHiggsfieldJobId('')
    setHiggsfieldUrl('')
    setHiggsfieldInfo('Aucune requete en cours.')
    setHiggsfieldStatusUrl('')
    setHiggsfieldLastStatus('')
    setHiggsfieldAttempts(0)
    setHiggsfieldRaw('')
    const start = performance.now()
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsedRequest.value)
      })
      const text = await resp.text()
      let pretty = text
      let responseJson = null
      try {
        responseJson = JSON.parse(text)
        pretty = JSON.stringify(responseJson, null, 2)
      } catch {
        // Response is not JSON, keep raw text.
      }
      setResponseText(pretty)
      setStatus(resp.ok ? 'done' : 'error')
      if (!resp.ok) {
        setError(`HTTP ${resp.status}`)
      } else if (responseJson?.data) {
        handleHiggsfieldResponse(responseJson.data)
      }
    } catch (err) {
      setStatus('error')
      setError(err.message)
    } finally {
      const end = performance.now()
      setLastDuration(Math.round(end - start))
    }
  }

  const n2Outline = getN2Outline(n2Data)
  const n3UnitsIndex = n3Data?.units_index || []
  const n3Units = n3Data?.units || []
  const n2SourceLookup = useMemo(() => {
    const map = {}
    const walk = (nodes) => {
      if (!Array.isArray(nodes)) return
      nodes.forEach((node) => {
        if (node?.id) {
          map[node.id] = { title: node.title || '', summary: node.summary || '' }
        }
        if (Array.isArray(node?.children)) {
          walk(node.children)
        }
      })
    }
    walk(n2Outline)
    return map
  }, [n2Outline])
  const n3SourceLookup = useMemo(() => {
    const map = {}
    n3Units.forEach((unit) => {
      const id = unit?.identity?.id || unit?.id
      if (!id) return
      const title =
        unit?.identity?.title_short || unit?.title || unit?.identity?.title || ''
      const summary =
        unit?.n2_recall?.function_narrative ||
        (Array.isArray(unit?.treatment) && unit.treatment[0]) ||
        (Array.isArray(unit?.deroule_detaille) && unit.deroule_detaille[0]) ||
        ''
      map[id] = { title, summary }
    })
    return map
  }, [n3Units])
  const timelineTracks = useMemo(() => {
    if (Array.isArray(n4Data?.tracks) && n4Data.tracks.length) {
      return n4Data.tracks
    }
    return [
      { id: 'V1', type: 'video', label: 'Video 1', segments: [] },
      { id: 'A1', type: 'audio', label: 'Audio 1', segments: [] },
      { id: 'A2', type: 'audio', label: 'Audio 2', segments: [] },
      { id: 'A3', type: 'audio', label: 'Audio 3', segments: [] }
    ]
  }, [n4Data])
  const getSourceSummary = (ref) => {
    if (!ref) return null
    return n3SourceLookup[ref] || n2SourceLookup[ref] || null
  }
  const formatDurationMs = (ms) => {
    if (!Number.isFinite(ms)) return ''
    const seconds = ms / 1000
    if (seconds >= 60) {
      const m = Math.floor(seconds / 60)
      const s = Math.round(seconds % 60)
      return `${m}m${String(s).padStart(2, '0')}s`
    }
    return `${seconds.toFixed(1)}s`
  }
  const parseTcToMs = (tc) => {
    if (!tc) return null
    const match = tc.match(/^(\d\d):(\d\d):(\d\d)(?:\.(\d{1,3}))?$/)
    if (!match) return null
    const [, hh, mm, ss, msPart] = match
    const ms = Number(msPart || 0)
    return Number(hh) * 3600000 + Number(mm) * 60000 + Number(ss) * 1000 + ms
  }
  const timelineTotalMs = useMemo(() => {
    const vTrack = timelineTracks.find((t) => t.id === 'V1') || timelineTracks[0]
    if (vTrack && Array.isArray(vTrack.segments) && vTrack.segments.length) {
      const maxEnd = vTrack.segments.reduce((acc, seg) => {
        const end = seg.end_tc ? parseTcToMs(seg.end_tc) : null
        const start = seg.start_tc ? parseTcToMs(seg.start_tc) : 0
        const dur = Number.isFinite(seg.duration_ms) ? seg.duration_ms : null
        const computedEnd = end ?? (dur != null ? start + dur : start)
        return Math.max(acc, computedEnd || 0)
      }, 0)
      return maxEnd || 60000
    }
    return 60000
  }, [timelineTracks])
  // Custom simple timeline: ticks and empty tracks; acts/sequences info reused for ruler length
  const n3SequenceList =
    n3Data?.sequence_estimates && n3Data.sequence_estimates.length
      ? n3Data.sequence_estimates
      : n3UnitsIndex.length
        ? n3UnitsIndex.map((unit, index) => {
            const match = n3Units.find((entry) => entry?.id === unit.id)
            return {
              id: unit.id || `SEQ_${index + 1}`,
              title: unit.title || match?.title || '',
              units: unit.id ? [unit.id] : [],
              duration_s: match?.duration_s,
              video_shots: null,
              audio_clips_total: null
            }
          })
        : n3Units.map((unit, index) => ({
            id: unit.id || `SEQ_${index + 1}`,
            title: unit.title || '',
            units: unit.id ? [unit.id] : [],
            duration_s: unit.duration_s,
            video_shots: null,
            audio_clips_total: null
          }))
  const selectedN3Unit =
    n3Units.find((unit) => unit?.id === selectedN3UnitId) ||
    n3Units.find((unit) => unit?.id === n3UnitsIndex[0]?.id) ||
    null

  return (
    <div className="app">
      <header className="top-nav">
        <div className="top-nav-left">
          <div className="brand">Narrations</div>
          <nav>
            <button
              type="button"
              className={activePage === 'home' ? 'active' : ''}
              onClick={() => setActivePage('home')}
            >
              Projets
            </button>
            {selectedProject ? (
              <>
                <button
                  type="button"
                  className={activePage === 'project' ? 'active' : ''}
                  onClick={() => setActivePage('project')}
                >
                  {selectedProject}
                </button>
                <button
                  type="button"
                  className={activePage === 'bible' ? 'active' : ''}
                  onClick={() => {
                    setActivePage('bible')
                    if (selectedProject) {
                      fetchN1(selectedProject)
                    }
                  }}
                >
                  N1
                </button>
                <button
                  type="button"
                  className={activePage === 'old' || isOldPage ? 'active' : ''}
                  onClick={() => setActivePage('old')}
                >
                  Old
                </button>
              </>
            ) : null}
          </nav>
        </div>
        <div className="top-nav-right">
          <span className="status-pill small">
            {pageLabel[activePage] || activePage}
          </span>
          <button
            type="button"
            className="danger"
            onClick={handleStopRag}
            disabled={ragStopStatus === 'loading'}
            title={
              ragStopError ||
              'Arrete les services RAG locaux (R2R + Postgres).'
            }
          >
            {ragStopStatus === 'loading'
              ? 'Arret...'
              : ragStopStatus === 'done'
                ? 'Arrete'
                : 'Quitter'}
          </button>
          <button
            type="button"
            className={logOverlayOpen ? 'active' : ''}
            onClick={() => setLogOverlayOpen((prev) => !prev)}
          >
            Logs
          </button>
        </div>
      </header>

      {activePage === 'home' ? (
        <>
          <header className="hero">
            <div>
              <p className="kicker">Narrations</p>
              <h1>Projets Narrations</h1>
              <p className="subtitle">
                Gere tes projets, ouvre une session de travail, puis explore les strates.
              </p>
            </div>
            <div className="hero-panel">
              <div className="hero-label">Projets</div>
              <div className="hero-metrics">
                <div>
                  <span>Total</span>
                  <strong>{projects.length}</strong>
                </div>
                <div>
                  <span>Actif</span>
                  <strong>{selectedProject || '--'}</strong>
                </div>
              </div>
            </div>
          </header>

          <section className="projects">
            <div className="panel">
              <div className="panel-head">
                <h2>Projets</h2>
                <div className="panel-actions">
                  <button type="button" onClick={openCreateModal}>
                    Creer un projet
                  </button>
                  <button type="button" onClick={fetchProjects}>
                    Rafraichir
                  </button>
                </div>
              </div>
              <p className="hint">
                Total: {projects.length}{' '}
                {projectsStatus === 'loading' ? '(chargement...)' : ''}
              </p>
              {projectsStatus === 'error' ? (
                <p className="hint error">Erreur: {projectsError}</p>
              ) : null}
              <ul className="project-list">
                {projects.length === 0 ? (
                  <li className="project-empty">Aucun projet trouve.</li>
                ) : (
                  projects.map((project) => (
                    <li key={project.project_id} className="project-item">
                      <div>
                        <strong>{project.project_id}</strong>
                        <div className="project-meta">
                          {project.has_metadata ? 'metadata' : 'no-metadata'}
                          {project.has_media ? 'media' : 'no-media'}
                        </div>
                      </div>
                      <div className="project-actions">
                        <button
                          type="button"
                          onClick={() => openProject(project.project_id)}
                        >
                          Ouvrir
                        </button>
                        {project.project_id === selectedProject ? (
                          <button type="button" onClick={closeProject}>
                            Fermer
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="danger"
                          onClick={() => deleteProject(project.project_id)}
                        >
                          Supprimer
                        </button>
                      </div>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </section>

        </>
      ) : null}

      {activePage === 'project' ? (
        <>
          <section className="project-page">
            <div className="panel">
              <div className="panel-head">
                <h2 className="project-title">{selectedProject || 'Projet'}</h2>
                <div className="project-head-fields">
                <input
                  type="text"
                  className="project-input"
                  placeholder="type de production"
                  aria-label="Type de production"
                  value={n0Data?.production_summary?.production_type || ''}
                  disabled={!selectedProject || !n0Data}
                  onChange={(event) =>
                    handleN0FieldChange(
                      ['production_summary', 'production_type'],
                      event.target.value
                    )
                  }
                />
                <input
                  type="text"
                  className="project-input"
                  placeholder="00h00m00s"
                  aria-label="Duree cible"
                  value={n0Data?.production_summary?.target_duration || ''}
                  disabled={!selectedProject || !n0Data}
                  onChange={(event) =>
                    handleN0FieldChange(
                      ['production_summary', 'target_duration'],
                      event.target.value
                    )
                  }
                />
                <input
                  type="text"
                  className="project-input"
                  aria-label="Ratio"
                  value={n0Data?.production_summary?.aspect_ratio || '16:9'}
                  disabled={!selectedProject || !n0Data}
                  onChange={(event) =>
                    handleN0FieldChange(
                      ['production_summary', 'aspect_ratio'],
                      event.target.value
                    )
                  }
                />
              </div>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : (
              <div className="project-detail">
                {n0Status === 'error' ? (
                  <p className="hint error">Erreur: {n0Error}</p>
                ) : null}
                {n0Data ? (
                  <div className="project-form">
                  <section>
                    <h3>Resume</h3>
                    <div className="resume-summary">
                      <label>
                        Resume (paragraphe)
                        <textarea
                          className="auto-resize"
                          value={n0Data.production_summary?.summary || ''}
                          data-orchestrate="n0-summary"
                          data-edit-path="n0.production_summary.summary"
                          onInput={handleAutoResize}
                          onChange={(event) =>
                            handleN0FieldChange(
                              ['production_summary', 'summary'],
                              event.target.value
                            )
                          }
                        />
                      </label>
                    </div>
                  </section>

                  
                  <section>
                    <h3>Direction Artistique Image</h3>
                    <div className="form-grid form-stack">
                      <label>
                        Description (paragraphe)
                        <textarea
                          className="auto-resize"
                          value={n0Data.art_direction?.description || ''}
                          data-edit-path="n0.art_direction.description"
                          onInput={handleAutoResize}
                          onChange={(event) =>
                            handleN0FieldChange(
                              ['art_direction', 'description'],
                              event.target.value
                            )
                          }
                        />
                      </label>
                    </div>
                    <div className="uploader">
                      <div className="upload-controls">
                        <button
                          type="button"
                          className="icon-plus"
                          onClick={() => openMediaModal('image')}
                        >
                          + Ajouter
                        </button>
                      </div>
                      {artImageFiles.length ? (
                        <div className="upload-grid">
                          {artImageFiles.map((item) => (
                            <figure key={item.url} className="upload-thumb">
                              <img src={item.url} alt={item.file.name} />
                              <figcaption>
                                {item.file.name}
                                <button
                                  type="button"
                                  className="thumb-remove"
                                  onClick={() => removeImageFile(item.url)}
                                >
                                  Supprimer
                                </button>
                              </figcaption>
                            </figure>
                          ))}
                        </div>
                      ) : (
                        <p className="hint">Aucune image chargee.</p>
                      )}
                    </div>
                  </section>

                  <section>
                    <h3>Direction artistique musique</h3>
                    <div className="form-grid form-stack">
                      <label>
                        Description
                        <textarea
                          className="auto-resize"
                          value={n0Data.sound_direction?.description || ''}
                          data-edit-path="n0.sound_direction.description"
                          onInput={handleAutoResize}
                          onChange={(event) =>
                            handleN0FieldChange(
                              ['sound_direction', 'description'],
                              event.target.value
                            )
                          }
                        />
                      </label>
                    </div>
                    <div className="uploader">
                      <button
                        type="button"
                        className="icon-plus"
                        onClick={() => openMediaModal('audio')}
                      >
                        + Ajouter
                      </button>
                      {artAudioFiles.length ? (
                        <div className="upload-list">
                          {artAudioFiles.map((item) => (
                            <div key={item.url} className="upload-audio">
                              <audio controls src={item.url} />
                              <span>{item.file.name}</span>
                              <button
                                type="button"
                                className="audio-remove"
                                onClick={() => removeAudioFile(item.url)}
                              >
                                Supprimer
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="hint">Aucun son charge.</p>
                      )}
                    </div>
                  </section>


                </div>
              ) : (
                <p className="hint">Chargement des intentions...</p>
              )}
            </div>
          )}
        </div>
      </section>
      {isN0Complete(n0Data) ? (
        <div className="n0-next-actions">
          <button
            type="button"
            className="primary"
            onClick={() => {
              setActivePage('bible')
              if (selectedProject) {
                fetchN1(selectedProject)
              }
            }}
          >
            Ouvrir N1
          </button>
          <button
            type="button"
            className="n0-next-arrow"
            aria-label="Passer a la suite"
            title="Ouvrir N1"
            onClick={() => {
              setActivePage('bible')
              if (selectedProject) {
                fetchN1(selectedProject)
              }
            }}
          >
            →
          </button>
        </div>
      ) : null}
        </>
      ) : null}

      {activePage === 'old' ? (
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2>Old</h2>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : (
              <div className="project-detail">
                <p className="hint">
                  Anciennes pages de travail (temporaires).
                </p>
                <div className="project-actions">
                  {oldPages.map((page) => (
                    <button
                      key={page.id}
                      type="button"
                      onClick={() => setActivePage(page.id)}
                    >
                      {page.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      ) : null}

      {activePage === 'bible' ? (
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2>Bible (N1)</h2>
              <div className="panel-actions">
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN1(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir
                </button>
                <button
                  type="button"
                  className="primary"
                  onClick={handleN1Save}
                  disabled={!selectedProject || !n1Data}
                >
                  Enregistrer
                </button>
              </div>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : (
              <div className="project-detail">
                {n1Status === 'error' ? (
                  <p className="hint error">Erreur: {n1Error}</p>
                ) : null}
                {n1Data ? (
                  <div className="project-form">
                    <section>
                      <h3>Personnages</h3>
                      <div className="form-grid">
                        <label>
                          Personnages principaux (nombre)
                          <input
                            type="number"
                            value={n1Data.characters?.main_characters?.number ?? 0}
                            onChange={(event) =>
                              handleN1FieldChange(
                                ['characters', 'main_characters', 'number'],
                                Number(event.target.value || 0)
                              )
                            }
                          />
                        </label>
                        <label>
                          Personnages secondaires (nombre)
                          <input
                            type="number"
                            value={n1Data.characters?.secondary_characters?.number ?? 0}
                            onChange={(event) =>
                              handleN1FieldChange(
                                ['characters', 'secondary_characters', 'number'],
                                Number(event.target.value || 0)
                              )
                            }
                          />
                        </label>
                        <label>
                          Personnages de fond (nombre)
                          <input
                            type="number"
                            value={n1Data.characters?.background_characters?.number ?? 0}
                            onChange={(event) =>
                              handleN1FieldChange(
                                ['characters', 'background_characters', 'number'],
                                Number(event.target.value || 0)
                              )
                            }
                          />
                        </label>
                      </div>
                    </section>
                  </div>
                ) : (
                  <p className="hint">Chargement de la bible...</p>
                )}
              </div>
            )}
          </div>
        </section>
      ) : null}

      {activePage === 'architecture' ? (
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2>Architecture (N2)</h2>
              <div className="panel-actions">
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN2(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir
                </button>
              </div>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : (
              <div className="project-detail">
                {n2Status === 'error' ? (
                  <p className="hint error">Erreur: {n2Error}</p>
                ) : null}
                {n2Data ? (
                  <div className="project-form">
                    <section>
                      <h3>Importer N2</h3>
                      <div className="n0-import">
                        <textarea
                          placeholder="Colle ici le JSON N2 fourni par ChatGPT"
                          value={n2PasteText}
                          onChange={(event) => setN2PasteText(event.target.value)}
                        />
                        <div className="n0-import-actions">
                          <button type="button" onClick={applyN2FromJson}>
                            Remplacer le N2
                          </button>
                          {n2PasteError ? (
                            <span className="hint error">{n2PasteError}</span>
                          ) : null}
                        </div>
                      </div>
                    </section>

                    <section>
                      <h3>Arborescence</h3>
                      {n2Outline.length ? (
                        renderN2Outline(n2Outline)
                      ) : (
                        <p className="hint">Aucune partie chargee pour l'instant.</p>
                      )}
                    </section>
                  </div>
                ) : (
                  <p className="hint">Chargement de l’architecture...</p>
                )}
              </div>
            )}
          </div>
        </section>
      ) : null}

      {activePage === 'sequences' ? (
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2>Sequences (N3)</h2>
              <div className="panel-actions">
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN3(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir
                </button>
                <button
                  type="button"
                  className="primary"
                  onClick={handleN3Save}
                  disabled={!selectedProject || !n3Data}
                >
                  Enregistrer
                </button>
              </div>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : (
              <div className="project-detail">
                {n3Status === 'error' ? (
                  <p className="hint error">Erreur: {n3Error}</p>
                ) : null}
                {n3Data ? (
                  <div className="project-form">
                    <section>
                      <h3>Importer N3</h3>
                      <div className="n0-import">
                        <textarea
                          placeholder="Colle ici le JSON N3 fourni par ChatGPT"
                          value={n3PasteText}
                          onChange={(event) => setN3PasteText(event.target.value)}
                        />
                        <div className="n0-import-actions">
                          <button type="button" onClick={applyN3FromJson}>
                            Remplacer le N3
                          </button>
                          {n3PasteError ? (
                            <span className="hint error">{n3PasteError}</span>
                          ) : null}
                        </div>
                      </div>
                    </section>

                    <section>
                      <h3>Sequences</h3>
                      {n3SequenceList.length ? (
                        <div className="n3-sequence-grid">
                          {n3SequenceList.map((sequence, sequenceIndex) => {
                            const unitEntries = Array.isArray(sequence.units)
                              ? sequence.units
                                  .map((unitId) =>
                                    n3Units.find((unit) => unit?.id === unitId)
                                  )
                                  .filter(Boolean)
                              : []
                            const unitTitles = unitEntries
                              .map((unit) => `${unit.id} — ${unit.title || 'Sans titre'}`)
                              .join(' / ')
                            return (
                              <div key={sequence.id} className="n3-sequence-card">
                                <div className="n3-sequence-head">
                                  <div>
                                    <strong>{`Sequence ${sequenceIndex + 1}`}</strong>
                                    <span>{sequence.title || unitTitles || sequence.id}</span>
                                  </div>
                                  <em>
                                    {sequence.duration_s ?? '--'}s ·{' '}
                                    {sequence.video_shots ?? '--'} plans ·{' '}
                                    {sequence.audio_clips_total ?? '--'} audio
                                  </em>
                                </div>
                                <div className="n3-sequence-details">
                                  {unitEntries.length ? (
                                    unitEntries.map((unit) => (
                                      <div key={unit.id} className="n3-unit-block">
                                        <div className="n3-unit-head">
                                          <strong>{unit.id}</strong>
                                          <span>{unit.title || 'Scene'}</span>
                                        </div>
                                        {Array.isArray(unit.treatment) ? (
                                          <ul>
                                            {unit.treatment.map((line, index) => (
                                              <li key={`${unit.id}-t-${index}`}>{line}</li>
                                            ))}
                                          </ul>
                                        ) : (
                                          <p className="hint">Aucun traitement.</p>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <p className="hint">Aucune scene pour cette sequence.</p>
                                  )}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <p className="hint">Aucune sequence chargee.</p>
                      )}
                    </section>
                  </div>
                ) : (
                  <p className="hint">Chargement des scenes...</p>
                )}
              </div>
            )}
          </div>
        </section>
      ) : null}

      {activePage === 'timeline' ? (
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2>Timeline (N4)</h2>
              <div className="panel-actions">
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN4(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir
                </button>
                <button
                  type="button"
                  className="primary"
                  onClick={handleN4Save}
                  disabled={!selectedProject || !n4Data || n4Status === 'saving'}
                >
                  Enregistrer
                </button>
              </div>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : n4Status === 'error' ? (
              <p className="hint error">Erreur: {n4Error}</p>
            ) : null}
            {selectedProject ? (
              <div className="project-detail timeline-layout">
                <section>
                  <h3>Coller N4 Timeline</h3>
                  <div className="timeline-import">
                    <textarea
                      placeholder="Colle ici le JSON N4 Timeline (pistes V1/A1/A2/A3)"
                      value={n4PasteText}
                      onChange={(event) => setN4PasteText(event.target.value)}
                    />
                    <div className="n0-import-actions">
                      <button type="button" onClick={applyN4FromJson}>
                        Remplacer
                      </button>
                      {n4PasteError ? <span className="hint error">{n4PasteError}</span> : null}
                    </div>
                  </div>
                  {n4UpdatedAt ? (
                    <p className="hint">Derniere mise a jour: {n4UpdatedAt}</p>
                  ) : null}
                </section>

                <section>
                  <h3>Pistes</h3>
                  <div className="timeline-grid">
                    {timelineTracks.map((track, trackIndex) => (
                      <div key={track.id || trackIndex} className="timeline-track">
                        <div className="timeline-track-head">
                          <div>
                            <div className="script-id">{track.id || `Track ${trackIndex + 1}`}</div>
                            <div className="timeline-track-title">{track.label || 'Sans titre'}</div>
                          </div>
                          <span className="timeline-track-type">{track.type || 'track'}</span>
                        </div>
                        {Array.isArray(track.segments) && track.segments.length ? (
                          <div className="timeline-segments">
                            {track.segments.map((segment, segIndex) => {
                              const label = segment.label || segment.id || `Segment ${segIndex + 1}`
                              const timeRange =
                                (segment.start_tc || segment.end_tc) &&
                                `${segment.start_tc || '--:--'} - ${segment.end_tc || '--:--'}`
                              const durationText = formatDurationMs(segment.duration_ms)
                              const sourceInfo = getSourceSummary(segment.source_ref)
                              return (
                                <div key={segment.id || segIndex} className="timeline-segment">
                                  <div className="timeline-segment-head">
                                    <strong>{label}</strong>
                                    <span className="script-meta">
                                      {timeRange}
                                      {timeRange && durationText ? ' · ' : ''}
                                      {durationText}
                                    </span>
                                  </div>
                                  {segment.source_ref ? (
                                    <div className="timeline-segment-meta">
                                      <span className="script-id">{segment.source_ref}</span>
                                      <span className="timeline-source">
                                        {sourceInfo
                                          ? `${sourceInfo.title} — ${sourceInfo.summary || ''}`
                                          : 'Reference inconnue'}
                                      </span>
                                    </div>
                                  ) : null}
                                  {segment.notes ? (
                                    <p className="timeline-notes">{segment.notes}</p>
                                  ) : null}
                                  {!segment.notes && sourceInfo ? (
                                    <p className="timeline-notes hint">
                                      {sourceInfo.summary || sourceInfo.title}
                                    </p>
                                  ) : null}
                                </div>
                              )
                            })}
                          </div>
                        ) : (
                          <p className="hint">Aucun segment.</p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>

                <section>
                  <h3>Timeline (personnalisée)</h3>
                  <div className="timeline-custom">
                    <div className="time-ruler">
                      {Array.from({ length: Math.max(1, Math.ceil((timelineTotalMs || 60000) / 10000)) }).map((_, idx) => {
                        const ms = idx * 10000
                        const seconds = Math.floor(ms / 1000)
                        const label = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
                        return (
                          <div key={idx} className="time-tick">
                            <span>{label}</span>
                          </div>
                        )
                      })}
                    </div>
                    <div className="track-row">
                      <div className="track-label">N0</div>
                      <div className="track-body">—</div>
                    </div>
                    <div className="track-row">
                      <div className="track-label">N1</div>
                      <div className="track-body">—</div>
                    </div>
                    <div className="track-row">
                      <div className="track-label">Video 1</div>
                      <div className="track-body">—</div>
                    </div>
                    <div className="track-row">
                      <div className="track-label">Audio 1</div>
                      <div className="track-body">—</div>
                    </div>
                    <div className="track-row">
                      <div className="track-label">Audio 2</div>
                      <div className="track-body">—</div>
                    </div>
                    <div className="track-row">
                      <div className="track-label">Audio 3</div>
                      <div className="track-body">—</div>
                    </div>
                  </div>
                  <p className="hint">
                    Timeline vide prête à accueillir des objets (drag & drop à implémenter). La règle de temps s’adapte à la durée estimée (N4/N2).
                  </p>
                </section>

                {n4Data?.notes ? (
                  <section>
                    <h3>Notes</h3>
                    <p>{n4Data.notes}</p>
                  </section>
                ) : null}
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {activePage === 'script' ? (
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2>Script</h2>
              <div className="panel-actions">
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN1(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir N1
                </button>
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN2(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir N2
                </button>
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN3(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir N3
                </button>
              </div>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : (
              <div className="project-detail script-layout-vertical">
                <section className="script-bible">
                  <h3>N1 — Bible</h3>
                  {n1Data ? (
                    <div className="script-card">
                      <strong>Personnages principaux</strong>
                      <p>{n1Data.characters?.main_characters?.number ?? 0}</p>
                      <strong>Personnages secondaires</strong>
                      <p>{n1Data.characters?.secondary_characters?.number ?? 0}</p>
                      <strong>Personnages de fond</strong>
                      <p>{n1Data.characters?.background_characters?.number ?? 0}</p>
                    </div>
                  ) : (
                    <p className="hint">Charge ou colle un N1 pour afficher le résumé.</p>
                  )}
                </section>

                <section className="script-tree">
                  <h3>N2 + N3 — Arborescence et scènes</h3>
                  {n2Outline && n2Outline.length ? (
                    <div className="script-tree-list">
                      {n2Outline.map((act, actIndex) => (
                        <div key={act.id || actIndex} className="script-card">
                          <div className="script-id">{act.id || `ACT${actIndex + 1}`}</div>
                          <div className="script-title">{act.title || 'Acte'}</div>
                          <div className="script-meta">
                            {(act.timecode_in || act.timecode_out) &&
                              `${act.timecode_in || '--:--'} - ${act.timecode_out || '--:--'}`}
                            {act.duration_s ? ` · ${act.duration_s}s` : ''}
                          </div>
                          <p>{act.summary || '—'}</p>

                          {Array.isArray(act.children) && act.children.length ? (
                            <div className="script-sublist">
                              {act.children.map((seq, seqIndex) => (
                                <div key={seq.id || seqIndex} className="script-subcard">
                                  <div className="script-id">{seq.id || `SEQ${seqIndex + 1}`}</div>
                                  <div className="script-title">{seq.title || 'Sequence'}</div>
                                  <div className="script-meta">
                                    {(seq.timecode_in || seq.timecode_out) &&
                                      `${seq.timecode_in || '--:--'} - ${seq.timecode_out || '--:--'}`}
                                    {seq.duration_s ? ` · ${seq.duration_s}s` : ''}
                                  </div>
                                  <p>{seq.summary || '—'}</p>

                                  {Array.isArray(seq.children) && seq.children.length ? (
                                    <div className="script-scenes">
                                      {seq.children.map((scene, sceneIndex) => {
                                        const n3Scene =
                                          n3Units &&
                                          n3Units.find(
                                            (entry) =>
                                              entry?.identity?.id === scene.id || entry?.id === scene.id
                                          )
                                        const sceneDuration =
                                          n3Scene?.identity?.duration_s ||
                                          n3Scene?.duration_s ||
                                          scene.duration_s ||
                                          scene.budget_duration_s
                                        const sceneTimecodeIn =
                                          n3Scene?.identity?.timecode_in || scene.timecode_in
                                        const sceneTimecodeOut =
                                          n3Scene?.identity?.timecode_out || scene.timecode_out
                                        const sceneTitle =
                                          n3Scene?.identity?.title_short ||
                                          n3Scene?.title ||
                                          n3Scene?.identity?.title ||
                                          scene.title ||
                                          'Scene'
                                        const sceneSummary =
                                          n3Scene?.n2_recall?.function_narrative ||
                                          (Array.isArray(n3Scene?.treatment) && n3Scene.treatment[0]) ||
                                          (Array.isArray(n3Scene?.deroule_detaille) &&
                                            n3Scene.deroule_detaille[0]) ||
                                          scene.summary ||
                                          ''
                                        return (
                                          <div key={scene.id || sceneIndex} className="script-scene">
                                            <div className="script-id">{scene.id || `SC${sceneIndex + 1}`}</div>
                                            <div className="script-title">{sceneTitle}</div>
                                            <div className="script-meta">
                                              {(sceneTimecodeIn || sceneTimecodeOut) &&
                                                `${sceneTimecodeIn || '--:--'} - ${
                                                  sceneTimecodeOut || '--:--'
                                                }`}
                                              {sceneDuration ? ` · ${sceneDuration}s` : ''}
                                            </div>
                                            <p>{sceneSummary || '—'}</p>
                                          </div>
                                        )
                                      })}
                                    </div>
                                  ) : null}
                                </div>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="hint">Charge ou colle un N2 pour afficher l’arborescence.</p>
                  )}
                </section>
              </div>
            )}
          </div>
        </section>
      ) : null}

      {activePage === 'media' ? (
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2>Media (N5)</h2>
            </div>
            <p className="hint">
              Page N5 (prompts/generation) en preparation. Le projet selectionne est{' '}
              <strong>{selectedProject || 'aucun'}</strong>.
            </p>
          </div>
        </section>
      ) : null}

      {activePage === 'prompts' ? (
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2>Prompts (N5)</h2>
              <div className="panel-actions">
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN5(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir
                </button>
                <button
                  type="button"
                  className="primary"
                  onClick={handleN5Save}
                  disabled={!selectedProject || !n5Data || n5Status === 'saving'}
                >
                  Enregistrer
                </button>
              </div>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : n5Status === 'error' ? (
              <p className="hint error">Erreur: {n5Error}</p>
            ) : null}
            {selectedProject ? (
              <div className="project-detail script-layout-vertical">
                <section>
                  <h3>Coller N5.json</h3>
                  <div className="timeline-import">
                    <textarea
                      placeholder="Colle ici le JSON N5 (prompts/plans)"
                      value={n5PasteText}
                      onChange={(event) => setN5PasteText(event.target.value)}
                    />
                    <div className="n0-import-actions">
                      <button type="button" onClick={applyN5FromJson}>
                        Remplacer
                      </button>
                      {n5PasteError ? <span className="hint error">{n5PasteError}</span> : null}
                    </div>
                  </div>
                  {n5UpdatedAt ? (
                    <p className="hint">Derniere mise a jour: {n5UpdatedAt}</p>
                  ) : null}
                </section>

                {n5Data ? (
                  <>
                    <section>
                      <h3>Meta</h3>
                      <div className="script-card">
                        <div>Status: {n5Data.meta?.status || '—'}</div>
                        <div>Version: {n5Data.version || n5Data.meta?.version || '—'}</div>
                        <div>Langue: {n5Data.meta?.language || '—'}</div>
                        <div>Ratio: {n5Data.meta?.aspect_ratio || '—'}</div>
                        <div>Timebase: {n5Data.meta?.timebase || '—'}</div>
                      </div>
                    </section>

                    <section>
                      <h3>Scope (N2/N3)</h3>
                      <div className="script-card">
                        <strong>Actes</strong>
                        <ul>
                          {(n5Data.meta?.scope?.acts || []).map((act) => (
                            <li key={act.id || act.title}>
                              {act.id || ''} {act.title || ''} ({act.timecode_in || '--'} -{' '}
                              {act.timecode_out || '--'})
                            </li>
                          ))}
                        </ul>
                        <strong>Sequences</strong>
                        <ul>
                          {(n5Data.meta?.scope?.sequences || []).map((seq) => (
                            <li key={seq.id || seq.title}>
                              {seq.id || ''} {seq.title || ''} ({seq.timecode_in || '--'} -{' '}
                              {seq.timecode_out || '--'})
                            </li>
                          ))}
                        </ul>
                        <strong>Scenes</strong>
                        <ul>
                          {(n5Data.meta?.scope?.scenes || []).map((scene) => (
                            <li key={scene.id || scene.title}>
                              {scene.id || ''} {scene.title || ''} ({scene.timecode_in || '--'} -{' '}
                              {scene.timecode_out || '--'})
                            </li>
                          ))}
                        </ul>
                      </div>
                    </section>

                    <section>
                      <h3>Tokens globaux</h3>
                      <div className="script-card">
                        {Object.entries(n5Data.global_prompt_tokens || {}).map(([key, value]) => (
                          <div key={key}>
                            <strong>{key}</strong>: {String(value)}
                          </div>
                        ))}
                      </div>
                    </section>

                    <section>
                      <h3>Assets</h3>
                      <div className="script-card">
                        <div>Props: {(n5Data.assets?.visual_props || []).length}</div>
                        <div>Audio assets: {(n5Data.assets?.audio_assets || []).length}</div>
                        <div>Music assets: {(n5Data.assets?.music_assets || []).length}</div>
                      </div>
                    </section>

                    <section>
                      <h3>Stack / Render</h3>
                      <div className="script-card">
                        <div>Image: {n5Data.stack?.image_generation_primary || '—'}</div>
                        <div>Video: {n5Data.stack?.video_generation || '—'}</div>
                        <div>SFX: {n5Data.stack?.sound_sfx || '—'}</div>
                        <div>Music: {n5Data.stack?.music || '—'}</div>
                        <div>Resolution: {n5Data.render_specs?.resolution_px?.join('x') || '—'}</div>
                        <div>FPS: {n5Data.render_specs?.fps || '—'}</div>
                      </div>
                    </section>
                  </>
                ) : (
                  <p className="hint">Aucun N5 charge pour l’instant.</p>
                )}
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {activePage === 'console' ? (
        <>
          <header className="hero">
            <div>
              <p className="kicker">Narrations Console</p>
              <h1>Envoyer des commandes JSON au serveur MCP</h1>
              <p className="subtitle">
                Colle le JSON depuis ChatGPT, valide, puis envoie vers <code>/mcp</code>.
                Les champs inutiles seront ignores par le serveur.
              </p>
            </div>
            <div className="hero-panel">
              <div className="hero-label">Etat</div>
              <div className={`status-pill ${status}`}>{status}</div>
              <div className="hero-metrics">
                <div>
                  <span>Latence</span>
                  <strong>{lastDuration ? `${lastDuration} ms` : '--'}</strong>
                </div>
                <div>
                  <span>JSON</span>
                  <strong>{parsedRequest.error ? 'Invalide' : 'Valide'}</strong>
                </div>
              </div>
            </div>
          </header>

          <section className="controls">
            <label className="field">
              <span>Endpoint</span>
              <input
                type="text"
                value={endpoint}
                onChange={(event) => setEndpoint(event.target.value)}
                placeholder="http://localhost:3333/mcp"
              />
            </label>
            <div className="field">
              <span>Templates rapides</span>
              <div className="template-row">
                {Object.keys(templates).map((key) => (
                  <button key={key} type="button" onClick={() => loadTemplate(key)}>
                    {key}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section className="console">
            <div className="panel">
              <div className="panel-head">
                <h2>Commande</h2>
                <div className="panel-actions">
                  <button type="button" onClick={pasteFromClipboard}>
                    Coller
                  </button>
                  <button type="button" onClick={formatJson}>
                    Formatter JSON
                  </button>
                  <button type="button" onClick={normalizeRequest}>
                    Normaliser
                  </button>
                  <button type="button" className="primary" onClick={sendRequest}>
                    Envoyer
                  </button>
                </div>
              </div>
              <textarea
                value={requestText}
                onChange={(event) => setRequestText(event.target.value)}
                spellCheck="false"
              />
              {parsedRequest.error ? (
                <p className="hint error">JSON invalide: {parsedRequest.error}</p>
              ) : (
                <p className="hint">
                  Coller un fichier <code>NARR_CMD_*.json</code> fonctionne aussi.
                </p>
              )}
            </div>

            <div className="panel">
              <div className="panel-head">
                <h2>Reponse</h2>
                <div className="panel-actions">
                  <button
                    type="button"
                    onClick={() => navigator.clipboard.writeText(responseText)}
                    disabled={!responseText}
                  >
                    Copier
                  </button>
                </div>
              </div>
              <pre className="response">
                {responseText || 'La reponse du serveur apparaitra ici.'}
              </pre>
              {error ? <p className="hint error">{error}</p> : null}
              <div className="higgsfield-panel">
                <div className="higgsfield-head">
                  <span className={`signal ${higgsfieldStatus}`} />
                  <h3>Higgsfield</h3>
                  <span className="higgsfield-status">
                    {higgsfieldLastStatus || 'idle'}
                  </span>
                </div>
                <p className="hint">
                  {higgsfieldInfo}
                  {higgsfieldLastStatus ? ` (status: ${higgsfieldLastStatus})` : ''}
                </p>
                <input
                  type="text"
                  readOnly
                  value={higgsfieldUrl}
                  placeholder="URL image / video"
                />
                <textarea
                  className="higgsfield-raw"
                  readOnly
                  value={higgsfieldRaw}
                  placeholder="Raw status Higgsfield"
                />
              </div>
            </div>
          </section>
        </>
      ) : null}
      {logOverlayOpen ? (
        <div className="log-overlay">
          <div className="log-panel">
            <div className="panel-head">
              <h2>Logs runtime</h2>
              <div className="panel-actions">
                <span className={`status-pill small ${logStatus === 'loading' ? 'sending' : ''}`}>
                  {logStatus === 'loading' ? 'chargement' : 'actif'}
                </span>
                <button type="button" onClick={() => setLogOverlayOpen(false)}>
                  Fermer
                </button>
              </div>
            </div>
            {logError ? <p className="hint error">Erreur: {logError}</p> : null}
            <div className="log-grid">
              <div className="log-column">
                <h3>API</h3>
                <textarea readOnly value={logApiText} placeholder="api.log" />
              </div>
              <div className="log-column">
                <h3>UI</h3>
                <textarea readOnly value={logUiText} placeholder="ui.log" />
              </div>
              <div className="log-column">
                <h3>Agent</h3>
                <textarea readOnly value={logAgentText} placeholder="agent.log" />
              </div>
            </div>
          </div>
        </div>
      ) : null}
      {createModalOpen ? (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-head">
              <h3>Creer un projet</h3>
            </div>
            <div className="modal-body">
              <label className="modal-label">
                Nom du projet (obligatoire)
                <input
                  type="text"
                  value={createProjectName}
                  onChange={(event) => setCreateProjectName(event.target.value)}
                  placeholder="ex: projet001"
                />
              </label>
              {createProjectError ? (
                <p className="hint error">Erreur: {createProjectError}</p>
              ) : null}
              <button
                type="button"
                className="primary"
                onClick={handleCreateProject}
                disabled={!createProjectName.trim() || createProjectStatus === 'loading'}
              >
                {createProjectStatus === 'loading' ? 'Creation...' : 'Creer'}
              </button>
              <div className="hint-row">
                <p className="hint">Decrivez votre projet</p>
                {hasPendingQuestions ? (
                  <span className="status-pill warning">En attente de reponses</span>
                ) : null}
              </div>
              {progressActive ? (
                <div className="progress-wrap">
                  <div className="progress-label">
                    <span>Generation N0</span>
                    <span>{Math.round(progressValue)}%</span>
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${progressValue}%` }}
                    />
                  </div>
                </div>
              ) : null}
              {showChatInput ? (
                <div className={`chat-box ${chatDisabled ? 'disabled' : ''}`}>
                  {showChatHistory ? (
                    <textarea
                      className="chat-log"
                      readOnly
                      value={chatLogText}
                      placeholder="Historique du chat."
                    />
                  ) : null}
                  {chatError ? <p className="hint error">Erreur: {chatError}</p> : null}
                  <div className="chat-input">
                    <textarea
                      value={chatInput}
                      onChange={(event) => setChatInput(event.target.value)}
                      placeholder="Ecris un message pour cadrer le projet."
                      disabled={chatDisabled}
                    />
                    <button
                      type="button"
                      className="primary"
                      onClick={handleNarrationChatSend}
                      disabled={chatDisabled || !canSendChat || chatStatus === 'sending'}
                      aria-label="Envoyer le message"
                      title="Envoyer"
                    >
                      {chatStatus === 'sending' ? '...' : '→'}
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
      {editorOpen ? (
        <div className="modal-backdrop">
          <div className="modal editor-modal">
            <div className="modal-head">
              <h3>{editorLabel || 'Editeur'}</h3>
            </div>
            <textarea
              value={editorValue}
              onChange={(event) => setEditorValue(event.target.value)}
            />
            <div className="editor-chat">
              <div className="editor-chat-head">
                <h4>Chat de modification</h4>
                {editorTargetPath ? (
                  <span className="hint">Cible: {editorTargetPath}</span>
                ) : (
                  <span className="hint warning">Aucune cible detectee</span>
                )}
              </div>
              {editorChatSummary ? (
                <div className="editor-chat-summary">
                  <span className="label">Resume:</span>
                  <p>{editorChatSummary}</p>
                </div>
              ) : null}
              {editorChatError ? (
                <p className="hint error">Erreur: {editorChatError}</p>
              ) : null}
              <div className="editor-chat-messages">
                {editorChatMessages.length ? (
                  editorChatMessages.map((entry, idx) => (
                    <div
                      key={`${entry.role}-${idx}`}
                      className={`chat-bubble ${entry.role}`}
                    >
                      {entry.content}
                    </div>
                  ))
                ) : (
                  <p className="hint">Aucune conversation pour ce champ.</p>
                )}
              </div>
              <div className="editor-chat-input">
                <textarea
                  value={editorChatInput}
                  onChange={(event) => setEditorChatInput(event.target.value)}
                  placeholder="Explique la modification souhaitee."
                />
                <button
                  type="button"
                  className="primary"
                  onClick={handleEditorChatSend}
                  disabled={
                    editorChatStatus === 'sending' ||
                    !editorChatInput.trim() ||
                    !selectedProject
                  }
                >
                  {editorChatStatus === 'sending' ? '...' : 'Envoyer'}
                </button>
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" onClick={closeEditor}>
                Annuler
              </button>
              <button
                type="button"
                className="primary"
                onClick={saveEditor}
              >
                Valider
              </button>
            </div>
          </div>
        </div>
      ) : null}
      {mediaModalOpen ? (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-head">
              <h3>
                {mediaModalKind === 'image' ? 'Ajouter des images' : 'Ajouter un son'}
              </h3>
            </div>
            <div className="modal-grid">
              <label className="upload-label">
                Fichier{mediaModalKind === 'image' ? 's' : ''}
                <input
                  type="file"
                  multiple
                  accept={mediaModalKind === 'image' ? 'image/*' : 'audio/*'}
                  onChange={(event) =>
                    setMediaModalFiles(Array.from(event.target.files || []))
                  }
                />
              </label>
              <label className="upload-label">
                URL
                <div className="upload-url">
                  <input
                    type="text"
                    value={mediaModalUrl}
                    onChange={(event) => setMediaModalUrl(event.target.value)}
                    placeholder="https://example.com/media"
                  />
                  <button type="button" onClick={() => setMediaModalUrl('')}>
                    Effacer
                  </button>
                </div>
              </label>
            </div>
            <div className="modal-actions">
              <button type="button" onClick={closeMediaModal}>
                Annuler
              </button>
              <button
                type="button"
                className="primary"
                onClick={saveMediaModal}
                disabled={!mediaModalFiles.length && !mediaModalUrl.trim()}
              >
                Valider
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default App
