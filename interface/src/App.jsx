import { useEffect, useMemo, useRef, useState } from 'react'
import TimelineCalendar from 'react-calendar-timeline'
import 'react-calendar-timeline/style.css'
import moment from 'moment'
import { TimelineCanvas, useTimeline } from '@gravity-ui/timeline/react'
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
  const [activePage, setActivePage] = useState('home')
  const [n0Data, setN0Data] = useState(null)
  const [n0Status, setN0Status] = useState('idle')
  const [n0Error, setN0Error] = useState('')
  const [n0UpdatedAt, setN0UpdatedAt] = useState('')
  const [n0PasteText, setN0PasteText] = useState('')
  const [n0PasteError, setN0PasteError] = useState('')
  const [n0OrchestratorStatus, setN0OrchestratorStatus] = useState('idle')
  const [n0OrchestratorError, setN0OrchestratorError] = useState('')
  const [n0OrchestratorLog, setN0OrchestratorLog] = useState('')
  const [editorOpen, setEditorOpen] = useState(false)
  const [editorValue, setEditorValue] = useState('')
  const [editorOriginal, setEditorOriginal] = useState('')
  const [editorLabel, setEditorLabel] = useState('')
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
  const [isN0EsthetiqueOpen, setIsN0EsthetiqueOpen] = useState(true)
  const [mediaModalOpen, setMediaModalOpen] = useState(false)
  const [mediaModalKind, setMediaModalKind] = useState('')
  const [mediaModalUrl, setMediaModalUrl] = useState('')
  const [mediaModalFiles, setMediaModalFiles] = useState([])
  const [isMediaOpen, setIsMediaOpen] = useState(true)
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
    bible: 'bible',
    architecture: 'architecture',
    sequences: 'sequences',
    timeline: 'timeline',
    media: 'media',
    console: 'console'
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
        primary_output_format: data.production_summary?.primary_output_format || '',
        target_duration: data.production_summary?.target_duration || '',
        aspect_ratio: data.production_summary?.aspect_ratio || '',
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

  const sanitizeN1 = (payload) => {
    const root = payload && typeof payload === 'object' ? payload : {}
    const data =
      root.data && typeof root.data === 'object'
        ? root.data
        : root
    const sanitizeMotif = (entry) => {
      const motif = entry && typeof entry === 'object' ? entry : {}
      if (typeof entry === 'string') {
        return { description: entry, images: [], audio: [] }
      }
      return {
        description: motif.description || '',
        images: Array.isArray(motif.images) ? motif.images : [],
        audio: Array.isArray(motif.audio) ? motif.audio : []
      }
    }
    const sanitizeCostume = (entry) => {
      const costume = entry && typeof entry === 'object' ? entry : {}
      return {
        description: costume.description || '',
        images: Array.isArray(costume.images) ? costume.images : []
      }
    }
    const sanitizeCharacter = (entry) => {
      const character = entry && typeof entry === 'object' ? entry : {}
      const costumes = Array.isArray(character.costumes)
        ? character.costumes.map(sanitizeCostume)
        : []
      return {
        name: character.name || '',
        role: character.role || '',
        function: character.function || '',
        description: character.description || '',
        appearance: character.appearance || '',
        signature: character.signature || '',
        images: Array.isArray(character.images) ? character.images : [],
        costumes
      }
    }
    let personnages = []
    if (Array.isArray(data.personnages)) {
      personnages = data.personnages.map(sanitizeCharacter)
    } else if (typeof data.personnages === 'string' && data.personnages.trim()) {
      personnages = [sanitizeCharacter({ description: data.personnages })]
    }
    return {
      meta: {
        status: data.meta?.status || 'draft',
        version: data.meta?.version || '0.1',
        temperature_creative: Number.isFinite(data.meta?.temperature_creative)
          ? data.meta.temperature_creative
          : 2
      },
      pitch: data.pitch || '',
      intention: data.intention || '',
      axes_artistiques: data.axes_artistiques || '',
      dynamique_globale: data.dynamique_globale || '',
      personnages,
      monde_epoque: data.monde_epoque || '',
      esthetique: data.esthetique || '',
      son: {
        ambiances: data.son?.ambiances || '',
        musique: data.son?.musique || '',
        sfx: data.son?.sfx || '',
        dialogues: data.son?.dialogues || ''
      },
      motifs: Array.isArray(data.motifs)
        ? data.motifs.map(sanitizeMotif)
        : [],
      ancres_canon_continuite: Array.isArray(data.ancres_canon_continuite)
        ? data.ancres_canon_continuite
        : [],
      sources: data.sources || '',
      hypotheses: data.hypotheses || '',
      questions: data.questions || ''
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
      const resp = await fetch(getProjectStrataUrl(projectId, 'n0'))
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      setN0Data(sanitizeN0(data?.data || null))
      setN0UpdatedAt(data?.updated_at || '')
      setN0Status('done')
    } catch (err) {
      setN0Status('error')
      setN0Error(err.message)
      setN0Data(null)
      setN0UpdatedAt('')
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

  useEffect(() => {
    if (selectedProject) {
      fetchN0(selectedProject)
      fetchN1(selectedProject)
      fetchN2(selectedProject)
      fetchN3(selectedProject)
      fetchN4(selectedProject)
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
      openEditor(labelText || 'Edition', target.value || '')
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

  const applyN0FromJson = async () => {
    if (!n0PasteText.trim()) {
      setN0PasteError('Colle un JSON avant de remplacer.')
      return
    }
    try {
      const cleaned = normalizeJsonInput(n0PasteText)
      const parsed = JSON.parse(cleaned)
      const payload = parsed && typeof parsed === 'object' && 'data' in parsed
        ? parsed.data
        : parsed
      if (!payload || typeof payload !== 'object') {
        throw new Error('JSON invalide')
      }
      const normalized = sanitizeN0(payload)
      setN0Data(normalized)
      setN0PasteError('')
      if (selectedProject) {
        await handleN0Save(normalized)
      }
    } catch (err) {
      setN0PasteError('JSON invalide ou incomplet.')
    }
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

  const handleN0Save = async (overrideData = null) => {
    let payload = overrideData || n0Data
    if (!selectedProject || !payload) {
      return false
    }
    payload = sanitizeN0(payload)
    setN0Status('saving')
    setN0Error('')
    try {
      const body = JSON.stringify(payload)
      const resp = await fetch(getProjectStrataUrl(selectedProject, 'n0'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      })
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

  const handleN0Orchestrate = async (overrideData = null) => {
    const payloadData = overrideData || n0Data
    if (!selectedProject || !payloadData) {
      return
    }
    setN0OrchestratorStatus('loading')
    setN0OrchestratorError('')
    try {
      const resp = await fetch(
        `${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/n0/orchestrate`)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ n0: payloadData })
        }
      )
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const payload = data?.data || {}
      setN0OrchestratorLog(payload.narrative || '')
      setN0Data((prev) => {
        if (!prev) {
          return prev
        }
        return {
          ...prev,
          production_summary: {
            ...(prev.production_summary || {}),
            summary: payload.summary ?? prev.production_summary?.summary,
            visual_style: payload.esthetique ?? prev.production_summary?.visual_style
          },
          art_direction: {
            ...(prev.art_direction || {}),
            description:
              payload.art_direction_description ?? prev.art_direction?.description
          },
          sound_direction: {
            ...(prev.sound_direction || {}),
            description:
              payload.sound_direction_description ?? prev.sound_direction?.description
          }
        }
      })
      setN0OrchestratorStatus('done')
    } catch (err) {
      setN0OrchestratorStatus('error')
      setN0OrchestratorError(err.message)
    }
  }

  const openEditor = (label, value) => {
    setEditorLabel(label)
    setEditorValue(value || '')
    setEditorOriginal(value || '')
    setEditorOpen(true)
  }

  const closeEditor = () => {
    setEditorOpen(false)
    setEditorValue('')
    setEditorOriginal('')
    setEditorLabel('')
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
    const isSummary = target.dataset?.orchestrate === 'n0-summary'
    if (isSummary && n0Data) {
      const next = updateNestedValue(n0Data, ['production_summary', 'summary'], editorValue)
      setN0Data(next)
      await handleN0Orchestrate(next)
    }
    target.value = editorValue
    target.dispatchEvent(new Event('input', { bubbles: true }))
    closeEditor()
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

  const createProject = async () => {
    const projectId = newProjectId.trim()
    if (!projectId) {
      setProjectsError('Nom du projet requis.')
      return
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
      setNewProjectId('')
      await fetchProjects()
      setSelectedProject(projectId)
      setActivePage('project')
    } catch (err) {
      setProjectsStatus('error')
      setProjectsError(err.message)
    }
  }

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
  const gravitySections = useMemo(() => {
    const vTrack = timelineTracks.find((t) => t.id === 'V1') || timelineTracks[0]
    if (!vTrack || !Array.isArray(vTrack.segments)) return []
    const palette = ['rgba(120,180,255,0.35)', 'rgba(255,200,120,0.35)', 'rgba(200,255,180,0.35)', 'rgba(255,160,200,0.35)']
    return vTrack.segments.map((seg, idx) => {
      const start = parseTcToMs(seg.start_tc) ?? 0
      const end = parseTcToMs(seg.end_tc) ?? (Number.isFinite(seg.duration_ms) ? start + seg.duration_ms : start)
      return {
        id: seg.id || `seg-${idx}`,
        from: start,
        to: end,
        color: palette[idx % palette.length],
        hoverColor: palette[idx % palette.length],
      }
    })
  }, [timelineTracks])
  const gravityMarkers = useMemo(() => {
    const markers = []
    const vTrack = timelineTracks.find((t) => t.id === 'V1') || timelineTracks[0]
    if (vTrack && Array.isArray(vTrack.segments)) {
      vTrack.segments.forEach((seg, idx) => {
        const start = parseTcToMs(seg.start_tc)
        const end = parseTcToMs(seg.end_tc)
        if (Number.isFinite(start)) {
          markers.push({
            time: start,
            color: '#5fb7ff',
            activeColor: '#5fb7ff',
            hoverColor: '#8ed1ff',
            label: seg.label || seg.id || `Seg ${idx + 1}`
          })
        }
        if (Number.isFinite(end)) {
          markers.push({
            time: end,
            color: '#ff9f7f',
            activeColor: '#ff9f7f',
            hoverColor: '#ffc2a3',
            label: (seg.label || seg.id || `Seg ${idx + 1}`) + ' fin'
          })
        }
      })
    }
    return markers
  }, [timelineTracks, parseTcToMs])
  const { timeline: gravityTimeline } = useTimeline({
    settings: {
      start: 0,
      end: timelineTotalMs || 60000,
      axes: [],
      events: [],
      markers: gravityMarkers,
      sections: gravitySections
    },
    viewConfiguration: {}
  })
  const calendarGroups = useMemo(() => {
    return timelineTracks.map((track) => ({
      id: track.id || track.label,
      title: track.label || track.id || 'Track'
    }))
  }, [timelineTracks])
  const calendarItems = useMemo(() => {
    return timelineTracks.flatMap((track, trackIdx) => {
      if (!Array.isArray(track.segments)) return []
      return track.segments.map((seg, idx) => {
        const startMs = parseTcToMs(seg.start_tc) ?? 0
        const endMs =
          parseTcToMs(seg.end_tc) ??
          (Number.isFinite(seg.duration_ms) ? startMs + seg.duration_ms : startMs + 1000)
        return {
          id: seg.id || `${track.id || trackIdx}-seg-${idx}`,
          group: track.id || track.label,
          title: seg.label || seg.id || `Segment ${idx + 1}`,
          start_time: moment(startMs),
          end_time: moment(endMs),
          itemProps: {
            className: `calendar-item-${track.id || trackIdx}`
          }
        }
      })
    })
  }, [timelineTracks])
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
                  onClick={() => setActivePage('bible')}
                >
                  Bible (N1)
                </button>
                <button
                  type="button"
                  className={activePage === 'architecture' ? 'active' : ''}
                  onClick={() => setActivePage('architecture')}
                >
                  Architecture (N2)
                </button>
                <button
                  type="button"
                  className={activePage === 'sequences' ? 'active' : ''}
                  onClick={() => setActivePage('sequences')}
                >
                  Sequences (N3)
                </button>
                <button
                  type="button"
                  className={activePage === 'timeline' ? 'active' : ''}
                  onClick={() => setActivePage('timeline')}
                >
                  Timeline (N4)
                </button>
                <button
                  type="button"
                  className={activePage === 'script' ? 'active' : ''}
                  onClick={() => setActivePage('script')}
                >
                  Script
                </button>
                <button
                  type="button"
                  className={activePage === 'media' ? 'active' : ''}
                  onClick={() => setActivePage('media')}
                >
                  Media (N5)
                </button>
              </>
            ) : null}
            <button
              type="button"
              className={activePage === 'console' ? 'active' : ''}
              onClick={() => setActivePage('console')}
            >
              Console
            </button>
          </nav>
        </div>
        <div className="top-nav-right">
          <span className="status-pill small">
            {pageLabel[activePage] || activePage}
          </span>
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
                  <input
                    type="text"
                    className="project-input"
                    placeholder="Nouveau projet"
                    value={newProjectId}
                    onChange={(event) => setNewProjectId(event.target.value)}
                  />
                  <button type="button" onClick={createProject}>
                    Creer
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
        <section className="project-page">
          <div className="panel">
            <div className="panel-head">
              <h2 className="project-title">{selectedProject || 'Projet'}</h2>
              <div className="panel-actions">
                <button
                  type="button"
                  onClick={closeProject}
                  disabled={!selectedProject}
                >
                  Fermer le projet
                </button>
                <button
                  type="button"
                  onClick={() => selectedProject && fetchN0(selectedProject)}
                  disabled={!selectedProject}
                >
                  Rafraichir
                </button>
                <button
                  type="button"
                  onClick={handleN0Orchestrate}
                  disabled={!selectedProject || !n0Data || n0OrchestratorStatus === 'loading'}
                >
                  Orchestrer N0
                </button>
                <button
                  type="button"
                  className="primary"
                  onClick={handleN0Save}
                  disabled={!selectedProject || !n0Data}
                >
                  Enregistrer
                </button>
              </div>
            </div>
            {!selectedProject ? (
              <p className="hint">Selectionne un projet dans l’accueil.</p>
            ) : (
              <div className="project-detail">
                {n0Status === 'error' ? (
                  <p className="hint error">Erreur: {n0Error}</p>
                ) : null}
                {n0OrchestratorStatus === 'error' ? (
                  <p className="hint error">Erreur orchestration: {n0OrchestratorError}</p>
                ) : null}
                {n0Data ? (
                  <div className="project-form">
                  <section>
                    <h3>Coller N0.json</h3>
                    <div className="n0-import n0-import-inline">
                      <input
                        type="text"
                        placeholder="Colle ici le JSON N0 fourni par ChatGPT"
                        value={n0PasteText}
                        onChange={(event) => setN0PasteText(event.target.value)}
                      />
                      <button type="button" onClick={applyN0FromJson}>
                        Remplacer
                      </button>
                    </div>
                    {n0PasteError ? <span className="hint error">{n0PasteError}</span> : null}
                  </section>
                  <section>
                    <h3>Log orchestration N0</h3>
                    {n0OrchestratorLog ? (
                      <textarea readOnly value={n0OrchestratorLog} />
                    ) : (
                      <p className="hint">Aucun log pour l’instant.</p>
                    )}
                  </section>
                  <section>
                    <h3>Resume</h3>
                    <div className="resume-summary">
                      <label>
                        Resume (paragraphe)
                        <textarea
                          value={n0Data.production_summary?.summary || ''}
                          data-orchestrate="n0-summary"
                          onChange={(event) =>
                            handleN0FieldChange(
                              ['production_summary', 'summary'],
                              event.target.value
                            )
                          }
                        />
                      </label>
                    </div>
                    <div className="resume-grid">
                      <div className="resume-col main">
                        <label>
                          Type de production
                          <span className="field-note">(ex: court-metrage, docu, pub, clip)</span>
                          <input
                            type="text"
                            value={n0Data.production_summary?.production_type || ''}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['production_summary', 'production_type'],
                                event.target.value
                              )
                            }
                          />
                        </label>
                        <label>
                          Format
                          <span className="field-note">(ex: film, serie, capsule, reel)</span>
                          <input
                            type="text"
                            value={n0Data.production_summary?.primary_output_format || ''}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['production_summary', 'primary_output_format'],
                                event.target.value
                              )
                            }
                          />
                        </label>
                      </div>
                      <div className="resume-col side">
                        <label>
                          Duree cible
                          <input
                            type="text"
                            value={n0Data.production_summary?.target_duration || ''}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['production_summary', 'target_duration'],
                                event.target.value
                              )
                            }
                          />
                        </label>
                        <label>
                          Ratio
                          <input
                            type="text"
                            value={n0Data.production_summary?.aspect_ratio || ''}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['production_summary', 'aspect_ratio'],
                                event.target.value
                              )
                            }
                          />
                        </label>
                      </div>
                    </div>
                  </section>

                  <section>
                    <div className="section-head">
                      <h3>Esthetique</h3>
                      <button
                        type="button"
                        className="section-toggle"
                        onClick={() => setIsN0EsthetiqueOpen((prev) => !prev)}
                      >
                        {isN0EsthetiqueOpen ? 'Replier' : 'Deplier'}
                      </button>
                    </div>
                    {isN0EsthetiqueOpen ? (
                      <div className="form-grid form-stack">
                        <label>
                          Style visuel
                          <input
                            type="text"
                            value={n0Data.production_summary?.visual_style || ''}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['production_summary', 'visual_style'],
                                event.target.value
                              )
                            }
                          />
                        </label>
                        <label>
                          Ton
                          <input
                            type="text"
                            value={n0Data.production_summary?.tone || ''}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['production_summary', 'tone'],
                                event.target.value
                              )
                            }
                          />
                        </label>
                        <label>
                          Epoque
                          <input
                            type="text"
                            value={n0Data.production_summary?.era || ''}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['production_summary', 'era'],
                                event.target.value
                              )
                            }
                          />
                        </label>
                      </div>
                    ) : null}
                  </section>

                  <section>
                    <div className="section-head">
                      <h3>Medias</h3>
                      <button
                        type="button"
                        className="section-toggle"
                        onClick={() => setIsMediaOpen((prev) => !prev)}
                      >
                        {isMediaOpen ? 'Replier' : 'Deplier'}
                      </button>
                    </div>
                    {isMediaOpen ? (
                      <div className="form-grid media-grid">
                        <label className="checkbox">
                          <input
                            type="checkbox"
                            checked={n0Data.deliverables?.visuals?.images_enabled ?? true}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['deliverables', 'visuals', 'images_enabled'],
                                event.target.checked
                              )
                            }
                          />
                          Images
                        </label>
                        <label className="checkbox">
                          <input
                            type="checkbox"
                            checked={n0Data.deliverables?.visuals?.videos_enabled ?? true}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['deliverables', 'visuals', 'videos_enabled'],
                                event.target.checked
                              )
                            }
                          />
                          Video
                        </label>
                        <label className="checkbox">
                          <input
                            type="checkbox"
                            checked={n0Data.deliverables?.audio_stems?.dialogue ?? true}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['deliverables', 'audio_stems', 'dialogue'],
                                event.target.checked
                              )
                            }
                          />
                          Dialogue
                        </label>
                        <label className="checkbox">
                          <input
                            type="checkbox"
                            checked={n0Data.deliverables?.audio_stems?.sfx ?? true}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['deliverables', 'audio_stems', 'sfx'],
                                event.target.checked
                              )
                            }
                          />
                          SoundFX
                        </label>
                        <label className="checkbox">
                          <input
                            type="checkbox"
                            checked={n0Data.deliverables?.audio_stems?.music ?? true}
                            onChange={(event) =>
                              handleN0FieldChange(
                                ['deliverables', 'audio_stems', 'music'],
                                event.target.checked
                              )
                            }
                          />
                          Music
                        </label>
                      </div>
                    ) : null}
                  </section>


                  <section>
                    <h3>Direction Artistique Image</h3>
                    <div className="form-grid form-stack">
                      <label>
                        Description (paragraphe)
                        <textarea
                          value={n0Data.art_direction?.description || ''}
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
                          value={n0Data.sound_direction?.description || ''}
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
                      <h3>Importer N1</h3>
                      <div className="n0-import">
                        <textarea
                          placeholder="Colle ici le JSON N1 fourni par ChatGPT"
                          value={n1PasteText}
                          onChange={(event) => setN1PasteText(event.target.value)}
                        />
                        <div className="n0-import-actions">
                          <button type="button" onClick={applyN1FromJson}>
                            Remplacer le N1
                          </button>
                          {n1PasteError ? (
                            <span className="hint error">{n1PasteError}</span>
                          ) : null}
                        </div>
                      </div>
                    </section>

                    <section>
                      <h3>Statut</h3>
                      <div className="form-grid">
                        <label>
                          Version
                          <input
                            type="text"
                            value={n1Data.meta?.version || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['meta', 'version'], event.target.value)
                            }
                          />
                        </label>
                        <label>
                          Statut
                          <input
                            type="text"
                            value={n1Data.meta?.status || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['meta', 'status'], event.target.value)
                            }
                          />
                        </label>
                        <label>
                          Temperature creative
                          <input
                            type="text"
                            value={n1Data.meta?.temperature_creative ?? 2}
                            onChange={(event) => {
                              const parsed = Number(event.target.value)
                              handleN1FieldChange(
                                ['meta', 'temperature_creative'],
                                Number.isFinite(parsed) ? parsed : event.target.value
                              )
                            }}
                          />
                        </label>
                      </div>
                    </section>

                    <section>
                      <h3>Pitch & intention</h3>
                      <div className="form-grid form-stack">
                        <label>
                          Pitch
                          <textarea
                            value={n1Data.pitch || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['pitch'], event.target.value)
                            }
                          />
                        </label>
                        <label>
                          Intention
                          <textarea
                            value={n1Data.intention || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['intention'], event.target.value)
                            }
                          />
                        </label>
                      </div>
                    </section>

                    <section>
                      <h3>Axes artistiques & dynamique</h3>
                      <div className="form-grid form-stack">
                        <label>
                          Axes artistiques
                          <textarea
                            value={n1Data.axes_artistiques || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['axes_artistiques'], event.target.value)
                            }
                          />
                        </label>
                        <label>
                          Dynamique globale
                          <textarea
                            value={n1Data.dynamique_globale || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['dynamique_globale'], event.target.value)
                            }
                          />
                        </label>
                      </div>
                    </section>

                    <section>
                      <h3>Personnages</h3>
                      <div className="character-actions">
                        <button type="button" onClick={addCharacter}>
                          Ajouter un personnage
                        </button>
                      </div>
                      {n1Data.personnages && n1Data.personnages.length ? (
                        <div className="character-grid">
                          {n1Data.personnages.map((character, index) => (
                            <div key={`character-${index}`} className="character-card">
                              <div className="character-card-head">
                                <strong>{character.name || `Personnage ${index + 1}`}</strong>
                                <button
                                  type="button"
                                  className="danger"
                                  onClick={() => removeCharacter(index)}
                                >
                                  Supprimer
                                </button>
                              </div>
                              <div className="form-grid form-stack">
                                <label>
                                  Nom
                                  <input
                                    type="text"
                                    value={character.name || ''}
                                    onChange={(event) =>
                                      updateCharacterField(index, 'name', event.target.value)
                                    }
                                  />
                                </label>
                                <label>
                                  Role
                                  <input
                                    type="text"
                                    value={character.role || ''}
                                    onChange={(event) =>
                                      updateCharacterField(index, 'role', event.target.value)
                                    }
                                  />
                                </label>
                                <label>
                                  Fonction narrative
                                  <input
                                    type="text"
                                    value={character.function || ''}
                                    onChange={(event) =>
                                      updateCharacterField(index, 'function', event.target.value)
                                    }
                                  />
                                </label>
                                <label>
                                  Description
                                  <textarea
                                    value={character.description || ''}
                                    onChange={(event) =>
                                      updateCharacterField(
                                        index,
                                        'description',
                                        event.target.value
                                      )
                                    }
                                  />
                                </label>
                                <label>
                                  Apparence
                                  <textarea
                                    value={character.appearance || ''}
                                    onChange={(event) =>
                                      updateCharacterField(
                                        index,
                                        'appearance',
                                        event.target.value
                                      )
                                    }
                                  />
                                </label>
                                <label>
                                  Motivations et comportements
                                  <textarea
                                    value={character.signature || ''}
                                    onChange={(event) =>
                                      updateCharacterField(
                                        index,
                                        'signature',
                                        event.target.value
                                      )
                                    }
                                  />
                                </label>
                              </div>
                              <div className="character-media">
                                <label className="upload-label">
                                  Images du personnage
                                  <input
                                    type="file"
                                    accept="image/*"
                                    multiple
                                    onChange={(event) => {
                                      const files = Array.from(event.target.files || [])
                                      files.forEach((file) =>
                                        uploadN1CharacterImage(file, index + 1)
                                      )
                                    }}
                                  />
                                </label>
                                {character.images && character.images.length ? (
                                  <div className="character-media-grid">
                                    {character.images.map((image, imageIndex) => (
                                      <figure
                                        key={`${image}-${imageIndex}`}
                                        className="character-media-thumb"
                                      >
                                        <img
                                          src={`${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/mediapix/${image}`)}`}
                                          alt={image}
                                        />
                                        <figcaption>
                                          {image}
                                          <button
                                            type="button"
                                            className="thumb-remove"
                                            onClick={() =>
                                              removeN1CharacterImage(
                                                index + 1,
                                                imageIndex,
                                                image
                                              )
                                            }
                                          >
                                            Supprimer
                                          </button>
                                        </figcaption>
                                      </figure>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="hint">Aucune image associee.</p>
                                )}
                              </div>
                              <div className="costume-block">
                                <div className="costume-head">
                                  <h4>Costumes</h4>
                                  <button
                                    type="button"
                                    onClick={() => addCostume(index)}
                                  >
                                    Ajouter un costume
                                  </button>
                                </div>
                                {character.costumes && character.costumes.length ? (
                                  <div className="costume-grid">
                                    {character.costumes.map((costume, costumeIndex) => (
                                      <div
                                        key={`costume-${costume.id ?? costumeIndex}`}
                                        className="costume-card"
                                      >
                                        <div className="costume-card-head">
                                          <strong>
                                            {`Costume ${costumeIndex + 1}`}
                                          </strong>
                                          <button
                                            type="button"
                                            className="danger"
                                            onClick={() => removeCostume(index, costumeIndex)}
                                          >
                                            Supprimer
                                          </button>
                                        </div>
                                        <div className="form-grid form-stack">
                                          <label>
                                            Description
                                            <textarea
                                              value={costume.description || ''}
                                              onChange={(event) =>
                                                updateCostumeField(
                                                  index,
                                                  costumeIndex,
                                                  'description',
                                                  event.target.value
                                                )
                                              }
                                            />
                                          </label>
                                        </div>
                                        <div className="character-media">
                                          <label className="upload-label">
                                            Images du costume
                                            <input
                                              type="file"
                                              accept="image/*"
                                              multiple
                                              onChange={(event) => {
                                                const files = Array.from(event.target.files || [])
                                                files.forEach((file) =>
                                                  uploadN1CostumeImage(file, {
                                                    characterIndex: index + 1,
                                                    costumeIndex: costumeIndex + 1
                                                  })
                                                )
                                              }}
                                            />
                                          </label>
                                          {costume.images && costume.images.length ? (
                                            <div className="character-media-grid">
                                              {costume.images.map((image, imageIndex) => (
                                                <figure
                                                  key={`${image}-${imageIndex}`}
                                                  className="character-media-thumb"
                                                >
                                                  <img
                                                    src={`${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/mediapix/${image}`)}`}
                                                    alt={image}
                                                  />
                                                  <figcaption>
                                                    {image}
                                                    <button
                                                      type="button"
                                                      className="thumb-remove"
                                                      onClick={() =>
                                                        removeN1CostumeImage(
                                                          {
                                                            characterIndex: index + 1,
                                                            costumeIndex: costumeIndex + 1
                                                          },
                                                          imageIndex,
                                                          image
                                                        )
                                                      }
                                                    >
                                                      Supprimer
                                                    </button>
                                                  </figcaption>
                                                </figure>
                                              ))}
                                            </div>
                                          ) : (
                                            <p className="hint">Aucune image associee.</p>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="hint">Aucun costume pour l’instant.</p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="hint">Aucun personnage pour l’instant.</p>
                      )}
                    </section>

                    <section>
                      <h3>Monde & epoque</h3>
                      <div className="form-grid form-stack">
                        <label>
                          Monde & epoque
                          <textarea
                            value={n1Data.monde_epoque || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['monde_epoque'], event.target.value)
                            }
                          />
                        </label>
                      </div>
                    </section>

                    <section>
                      <h3>Esthetique</h3>
                      <div className="form-grid form-stack">
                        <label>
                          Direction artistique macro
                          <textarea
                            value={n1Data.esthetique || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['esthetique'], event.target.value)
                            }
                          />
                        </label>
                      </div>
                    </section>

                    <section>
                      <h3>Son</h3>
                      <div className="form-grid form-stack">
                        <label>
                          Ambiances
                          <textarea
                            value={n1Data.son?.ambiances || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['son', 'ambiances'], event.target.value)
                            }
                          />
                        </label>
                        <label>
                          Musique
                          <textarea
                            value={n1Data.son?.musique || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['son', 'musique'], event.target.value)
                            }
                          />
                        </label>
                        <label>
                          SFX signatures
                          <textarea
                            value={n1Data.son?.sfx || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['son', 'sfx'], event.target.value)
                            }
                          />
                        </label>
                        <label>
                          Dialogues
                          <textarea
                            value={n1Data.son?.dialogues || ''}
                            onChange={(event) =>
                              handleN1FieldChange(['son', 'dialogues'], event.target.value)
                            }
                          />
                        </label>
                      </div>
                    </section>

                    <section>
                      <h3>Motifs</h3>
                      <div className="motif-head">
                        <button type="button" onClick={addMotif}>
                          Ajouter un motif
                        </button>
                      </div>
                      {n1Data.motifs && n1Data.motifs.length ? (
                        <div className="motif-grid">
                          {n1Data.motifs.map((motif, motifIndex) => (
                            <div key={`motif-${motifIndex}`} className="motif-card">
                              <div className="motif-card-head">
                                <strong>{`Motif ${motifIndex + 1}`}</strong>
                                <button
                                  type="button"
                                  className="danger"
                                  onClick={() => removeMotif(motifIndex)}
                                >
                                  Supprimer
                                </button>
                              </div>
                              <div className="form-grid form-stack">
                                <label>
                                  Description
                                  <textarea
                                    value={motif.description || ''}
                                    onChange={(event) =>
                                      updateMotifField(
                                        motifIndex,
                                        'description',
                                        event.target.value
                                      )
                                    }
                                  />
                                </label>
                              </div>
                              <div className="character-media">
                                <label className="upload-label">
                                  Images du motif
                                  <input
                                    type="file"
                                    accept="image/*"
                                    multiple
                                    onChange={(event) => {
                                      const files = Array.from(event.target.files || [])
                                      files.forEach((file) =>
                                        uploadN1MotifImage(file, motifIndex + 1)
                                      )
                                    }}
                                  />
                                </label>
                                {motif.images && motif.images.length ? (
                                  <div className="character-media-grid">
                                    {motif.images.map((image, imageIndex) => (
                                      <figure
                                        key={`${image}-${imageIndex}`}
                                        className="character-media-thumb"
                                      >
                                        <img
                                          src={`${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/mediapix/${image}`)}`}
                                          alt={image}
                                        />
                                        <figcaption>
                                          {image}
                                          <button
                                            type="button"
                                            className="thumb-remove"
                                            onClick={() =>
                                              removeN1MotifImage(
                                                motifIndex + 1,
                                                imageIndex,
                                                image
                                              )
                                            }
                                          >
                                            Supprimer
                                          </button>
                                        </figcaption>
                                      </figure>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="hint">Aucune image associee.</p>
                                )}
                              </div>
                              <div className="character-media">
                                <label className="upload-label">
                                  Sons du motif
                                  <input
                                    type="file"
                                    accept="audio/*"
                                    multiple
                                    onChange={(event) => {
                                      const files = Array.from(event.target.files || [])
                                      files.forEach((file) =>
                                        uploadN1MotifAudio(file, motifIndex + 1)
                                      )
                                    }}
                                  />
                                </label>
                                {motif.audio && motif.audio.length ? (
                                  <div className="audio-list">
                                    {motif.audio.map((audio, audioIndex) => (
                                      <div key={`${audio}-${audioIndex}`} className="audio-item">
                                        <audio
                                          controls
                                          src={`${apiOrigin}${joinPath(apiBasePath, `/projects/${selectedProject}/mediapix/${audio}`)}`}
                                        />
                                        <span>{audio}</span>
                                        <button
                                          type="button"
                                          className="danger"
                                          onClick={() =>
                                            removeN1MotifAudio(
                                              motifIndex + 1,
                                              audioIndex,
                                              audio
                                            )
                                          }
                                        >
                                          Supprimer
                                        </button>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="hint">Aucun son associe.</p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="hint">Aucun motif pour l’instant.</p>
                      )}
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
                  <h3>Moniteur (Gravity Timeline)</h3>
                  <div className="gravity-wrapper">
                    <TimelineCanvas timeline={gravityTimeline} />
                  </div>
                  <p className="hint">
                    Vue compacte (canvas) basée sur V1 : segments colorés, marqueurs aux bornes. Zoom/pan natif Gravity UI.
                  </p>
                </section>

                <section>
                  <h3>Timeline (react-calendar-timeline)</h3>
                  <div className="calendar-wrapper">
                    <TimelineCalendar
                      groups={calendarGroups}
                      items={calendarItems}
                      defaultTimeStart={moment(0)}
                      defaultTimeEnd={moment(timelineTotalMs || 60000)}
                      visibleTimeStart={moment(0)}
                      visibleTimeEnd={moment(timelineTotalMs || 60000)}
                      minZoom={timelineTotalMs || 60000}
                      maxZoom={timelineTotalMs || 60000}
                      canMove={false}
                      canResize={false}
                      canChangeGroup={false}
                      stackItems
                      itemHeightRatio={0.75}
                    />
                  </div>
                  <p className="hint">
                    Vue multi-pistes (V1/A1/A2/A3) en lecture seule. Les items reflètent les segments définis dans le JSON N4.
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
                      <strong>Pitch</strong>
                      <p>{n1Data.pitch || '—'}</p>
                      <strong>Intention</strong>
                      <p>{n1Data.intention || '—'}</p>
                      <strong>Dynamique</strong>
                      <p>{n1Data.dynamique_globale || '—'}</p>
                      <strong>Axes artistiques</strong>
                      <p>{n1Data.axes_artistiques || '—'}</p>
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
      {editorOpen ? (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-head">
              <h3>{editorLabel || 'Editeur'}</h3>
            </div>
            <textarea
              value={editorValue}
              onChange={(event) => setEditorValue(event.target.value)}
            />
            <div className="modal-actions">
              <button type="button" onClick={closeEditor}>
                Annuler
              </button>
              <button
                type="button"
                className="primary"
                onClick={saveEditor}
                disabled={n0OrchestratorStatus === 'loading'}
              >
                {n0OrchestratorStatus === 'loading' ? (
                  <>
                    <span className="spinner" />
                    Calcul en cours
                  </>
                ) : (
                  'Valider'
                )}
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
