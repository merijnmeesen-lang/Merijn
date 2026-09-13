import { useEffect, useRef, useState } from 'react'
import {
  estimateSpeechDurationMs,
  isVideoRenderSupported,
  pickMotion,
  renderVideo,
  type MotionType,
  type Slide,
} from '../lib/videoRender'

interface PhotoItem {
  id: string
  file: File | null
  url: string | null
  img: HTMLImageElement | null
  caption: string
  durationSec: number
  motion: 'auto' | MotionType
}

function splitScript(script: string): string[] {
  const paragraphs = script
    .split(/\n\s*\n/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (paragraphs.length > 1) return paragraphs

  return script
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

const MOTION_LABELS: Record<'auto' | MotionType, string> = {
  auto: 'Automatisch',
  'zoom-in': 'Inzoomen',
  'zoom-out': 'Uitzoomen',
  'pan-left': 'Pan naar links',
  'pan-right': 'Pan naar rechts',
}

const WIDTH = 1080
const HEIGHT = 1920
const FPS = 30

export function ShortsVideoMaker() {
  const [photos, setPhotos] = useState<PhotoItem[]>([])
  const [defaultDuration, setDefaultDuration] = useState(3)
  const [musicFile, setMusicFile] = useState<File | null>(null)
  const [script, setScript] = useState('')
  const [narrate, setNarrate] = useState(false)
  const [captureNarrationAudio, setCaptureNarrationAudio] = useState(false)
  const [isRendering, setIsRendering] = useState(false)
  const [progress, setProgress] = useState(0)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const supported = isVideoRenderSupported()

  useEffect(() => {
    return () => {
      photos.forEach((p) => {
        if (p.url) URL.revokeObjectURL(p.url)
      })
      if (resultUrl) URL.revokeObjectURL(resultUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function loadImage(id: string, url: string) {
    const img = new Image()
    img.onload = () => {
      setPhotos((prev) => prev.map((p) => (p.id === id ? { ...p, img } : p)))
    }
    img.src = url
  }

  function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return
    const items: PhotoItem[] = Array.from(fileList).map((file) => ({
      id: crypto.randomUUID(),
      file,
      url: URL.createObjectURL(file),
      img: null,
      caption: '',
      durationSec: defaultDuration,
      motion: 'auto',
    }))
    setPhotos((prev) => [...prev, ...items])
    setResultUrl(null)
    items.forEach((item) => loadImage(item.id, item.url!))
  }

  function attachPhoto(id: string, file: File) {
    const url = URL.createObjectURL(file)
    setPhotos((prev) => prev.map((p) => (p.id === id ? { ...p, file, url, img: null } : p)))
    loadImage(id, url)
  }

  function generateScenes() {
    const scenes = splitScript(script)
    if (scenes.length === 0) return
    setResultUrl(null)
    setPhotos((prev) => {
      const next = [...prev]
      scenes.forEach((text, i) => {
        const durationSec = Math.max(1, Math.round((estimateSpeechDurationMs(text) / 1000) * 2) / 2)
        if (next[i]) {
          next[i] = { ...next[i], caption: text, durationSec }
        } else {
          next.push({
            id: crypto.randomUUID(),
            file: null,
            url: null,
            img: null,
            caption: text,
            durationSec,
            motion: 'auto',
          })
        }
      })
      return next
    })
    setNarrate(true)
  }

  function updatePhoto(id: string, patch: Partial<PhotoItem>) {
    setPhotos((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)))
  }

  function removePhoto(id: string) {
    setPhotos((prev) => {
      const target = prev.find((p) => p.id === id)
      if (target?.url) URL.revokeObjectURL(target.url)
      return prev.filter((p) => p.id !== id)
    })
  }

  function move(id: string, dir: -1 | 1) {
    setPhotos((prev) => {
      const index = prev.findIndex((p) => p.id === id)
      const target = index + dir
      if (index === -1 || target < 0 || target >= prev.length) return prev
      const next = [...prev]
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  }

  function applyDurationToAll() {
    setPhotos((prev) => prev.map((p) => ({ ...p, durationSec: defaultDuration })))
  }

  async function handleGenerate() {
    if (photos.length === 0) return
    if (photos.some((p) => !p.file)) {
      setError('Voeg bij elke scène nog een foto toe voordat je genereert.')
      return
    }
    if (photos.some((p) => !p.img)) {
      setError('Wacht tot alle foto\'s geladen zijn en probeer opnieuw.')
      return
    }
    const canvas = canvasRef.current
    if (!canvas) return

    setError(null)
    setResultUrl(null)
    setIsRendering(true)
    setProgress(0)

    try {
      const slides: Slide[] = photos.map((p, i) => ({
        id: p.id,
        img: p.img!,
        caption: p.caption,
        durationMs: Math.max(500, p.durationSec * 1000),
        motion: p.motion === 'auto' ? pickMotion(i) : p.motion,
      }))

      const blob = await renderVideo(
        {
          slides,
          width: WIDTH,
          height: HEIGHT,
          fps: FPS,
          audioFile: musicFile,
          narrate,
          captureNarrationAudio: narrate && captureNarrationAudio,
          onProgress: setProgress,
        },
        canvas,
      )
      setResultUrl(URL.createObjectURL(blob))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Genereren van de video is mislukt.')
    } finally {
      setIsRendering(false)
    }
  }

  const totalSeconds = photos.reduce((sum, p) => sum + p.durationSec, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-neutral-900">Shorts videomaker</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Upload foto's en krijg een verticale video met beweging (zoom/pan) en ondertitels — geen
          montagekennis nodig. Alles gebeurt in je browser, er wordt niets geüpload.
        </p>
      </div>

      {!supported && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Je browser ondersteunt het opnemen van video niet volledig. Probeer dit in de nieuwste
          Chrome voor het beste resultaat.
        </p>
      )}

      <div className="space-y-2 rounded-xl border border-neutral-200 bg-white p-4">
        <label className="block text-xs font-medium text-neutral-500">
          Script (optioneel) — plak je tekst, elke alinea of zin wordt een scène
        </label>
        <textarea
          value={script}
          onChange={(e) => setScript(e.target.value)}
          rows={4}
          placeholder={'Vandaag laat ik je zien hoe...\n\nHet eerste wat je moet weten is...'}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={generateScenes}
          disabled={!script.trim()}
          className="rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Scènes genereren uit script
        </button>
        <p className="text-xs text-neutral-400">
          Dit vult de ondertitels hieronder en zet automatisch een passende duur — jij voegt per
          scène nog een foto toe.
        </p>
      </div>

      <div className="rounded-xl border border-neutral-200 bg-white p-4">
        <label className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-neutral-300 py-8 text-center hover:border-neutral-400">
          <span className="text-sm font-medium text-neutral-700">Foto's kiezen</span>
          <span className="text-xs text-neutral-400">Meerdere tegelijk mag, volgorde pas je hieronder aan</span>
          <input
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
      </div>

      {photos.length > 0 && (
        <>
          <div className="flex flex-wrap items-end gap-2 rounded-xl border border-neutral-200 bg-white p-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-500">
                Standaardduur per foto (sec)
              </label>
              <input
                type="number"
                min={1}
                step={0.5}
                value={defaultDuration}
                onChange={(e) => setDefaultDuration(Math.max(0.5, Number(e.target.value) || 1))}
                className="w-28 rounded-lg border border-neutral-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="button"
              onClick={applyDurationToAll}
              className="rounded-lg bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-200"
            >
              Toepassen op alle foto's
            </button>
            <p className="ml-auto text-sm text-neutral-500">
              Totale lengte: {totalSeconds.toFixed(1)}s
            </p>
          </div>

          <div className="space-y-2">
            {photos.map((p, i) => (
              <div key={p.id} className="flex gap-3 rounded-xl border border-neutral-200 bg-white p-3">
                {p.url ? (
                  <img src={p.url} alt="" className="h-20 w-14 flex-shrink-0 rounded-lg object-cover" />
                ) : (
                  <label className="flex h-20 w-14 flex-shrink-0 cursor-pointer flex-col items-center justify-center gap-0.5 rounded-lg border-2 border-dashed border-neutral-300 text-center hover:border-neutral-400">
                    <span className="text-[10px] font-medium leading-tight text-neutral-500">
                      Foto
                      <br />
                      toevoegen
                    </span>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) attachPhoto(p.id, file)
                      }}
                    />
                  </label>
                )}
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <input
                    type="text"
                    placeholder="Ondertitel (optioneel)"
                    value={p.caption}
                    onChange={(e) => updatePhoto(p.id, { caption: e.target.value })}
                    className="w-full rounded-lg border border-neutral-300 px-3 py-1.5 text-sm"
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      type="number"
                      min={0.5}
                      step={0.5}
                      value={p.durationSec}
                      onChange={(e) =>
                        updatePhoto(p.id, { durationSec: Math.max(0.5, Number(e.target.value) || 1) })
                      }
                      className="w-20 rounded-lg border border-neutral-300 px-2 py-1 text-sm"
                    />
                    <span className="text-xs text-neutral-400">sec</span>
                    <select
                      value={p.motion}
                      onChange={(e) => updatePhoto(p.id, { motion: e.target.value as PhotoItem['motion'] })}
                      className="rounded-lg border border-neutral-300 px-2 py-1 text-sm"
                    >
                      {Object.entries(MOTION_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                    {!p.img && <span className="text-xs text-neutral-400">laden…</span>}
                  </div>
                </div>
                <div className="flex flex-shrink-0 flex-col items-center gap-1">
                  <button
                    type="button"
                    onClick={() => move(p.id, -1)}
                    disabled={i === 0}
                    className="text-neutral-400 hover:text-neutral-900 disabled:opacity-30"
                    aria-label="Naar boven"
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    onClick={() => move(p.id, 1)}
                    disabled={i === photos.length - 1}
                    className="text-neutral-400 hover:text-neutral-900 disabled:opacity-30"
                    aria-label="Naar beneden"
                  >
                    ▼
                  </button>
                  <button
                    type="button"
                    onClick={() => removePhoto(p.id)}
                    className="mt-1 text-xs text-neutral-400 hover:text-red-600"
                  >
                    Wis
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-3 rounded-xl border border-neutral-200 bg-white p-4">
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={narrate}
                onChange={(e) => setNarrate(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                <span className="font-medium text-neutral-700">Ondertitels voorlezen als voice-over</span>
                <br />
                <span className="text-xs text-neutral-400">
                  Gratis tekst-naar-spraak van je browser (klinkt robotachtig). De duur per scène
                  wordt automatisch aangepast aan hoe lang de zin duurt om uit te spreken.
                </span>
              </span>
            </label>

            {narrate && (
              <label className="flex items-start gap-2 pl-6 text-sm">
                <input
                  type="checkbox"
                  checked={captureNarrationAudio}
                  onChange={(e) => setCaptureNarrationAudio(e.target.checked)}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-medium text-neutral-700">
                    Stem meenemen in de gedownloade video (experimenteel)
                  </span>
                  <br />
                  <span className="text-xs text-neutral-400">
                    Werkt alleen in Chrome. Er verschijnt een schermdeel-venster — kies "Dit
                    tabblad" en vink "Tabbladgeluid delen" aan, anders is de video stil.
                  </span>
                </span>
              </label>
            )}

            {!(narrate && captureNarrationAudio) && (
              <div className="space-y-2 border-t border-neutral-100 pt-3">
                <label className="block text-xs font-medium text-neutral-500">
                  Achtergrondmuziek (optioneel)
                </label>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => setMusicFile(e.target.files?.[0] ?? null)}
                  className="text-sm"
                />
                <p className="text-xs text-neutral-400">
                  Gebruik alleen muziek waar je rechten op hebt (bv. de YouTube Audio Library),
                  anders kan je Short gedempt worden of een claim krijgen.
                </p>
              </div>
            )}
          </div>

          <div className="flex flex-col items-center gap-3 rounded-xl border border-neutral-200 bg-white p-4">
            <canvas
              ref={canvasRef}
              className="w-full max-w-[220px] rounded-lg bg-black"
              style={{ aspectRatio: '9 / 16' }}
            />

            <button
              type="button"
              onClick={handleGenerate}
              disabled={isRendering || !supported}
              className="w-full max-w-xs rounded-lg bg-neutral-900 py-2.5 text-sm font-medium text-white disabled:opacity-40"
            >
              {isRendering ? `Bezig… ${Math.round(progress * 100)}%` : 'Video genereren'}
            </button>

            {isRendering && (
              <div className="h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-neutral-100">
                <div
                  className="h-1.5 rounded-full bg-neutral-900 transition-[width]"
                  style={{ width: `${Math.round(progress * 100)}%` }}
                />
              </div>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}

            {resultUrl && (
              <div className="w-full max-w-xs space-y-2">
                <video src={resultUrl} controls className="w-full rounded-lg" />
                <a
                  href={resultUrl}
                  download="short.webm"
                  className="block rounded-lg bg-neutral-100 py-2 text-center text-sm font-medium text-neutral-700 hover:bg-neutral-200"
                >
                  Video downloaden
                </a>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
