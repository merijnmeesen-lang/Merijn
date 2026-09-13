export type MotionType = 'zoom-in' | 'zoom-out' | 'pan-left' | 'pan-right'

export interface Slide {
  id: string
  img: HTMLImageElement
  caption: string
  durationMs: number
  motion: MotionType
}

export interface RenderOptions {
  slides: Slide[]
  width: number
  height: number
  fps: number
  audioFile: File | null
  onProgress: (fraction: number) => void
}

const MOTIONS: MotionType[] = ['zoom-in', 'pan-left', 'zoom-out', 'pan-right']

export function pickMotion(index: number): MotionType {
  return MOTIONS[index % MOTIONS.length]
}

function easeInOut(t: number) {
  return t * t * (3 - 2 * t)
}

function drawSlideFrame(
  ctx: CanvasRenderingContext2D,
  slide: Slide,
  t: number,
  width: number,
  height: number,
) {
  const eased = easeInOut(Math.min(1, Math.max(0, t)))
  const img = slide.img
  const canvasRatio = width / height
  const imgRatio = img.naturalWidth / img.naturalHeight

  let baseW: number
  let baseH: number
  if (imgRatio > canvasRatio) {
    baseH = height
    baseW = height * imgRatio
  } else {
    baseW = width
    baseH = width / imgRatio
  }

  const zoomRange = 0.18
  let scale = 1
  let dx = 0

  switch (slide.motion) {
    case 'zoom-in':
      scale = 1 + zoomRange * eased
      break
    case 'zoom-out':
      scale = 1 + zoomRange * (1 - eased)
      break
    case 'pan-left':
      scale = 1 + zoomRange
      dx = 1 - 2 * eased
      break
    case 'pan-right':
      scale = 1 + zoomRange
      dx = -1 + 2 * eased
      break
  }

  const drawW = baseW * scale
  const drawH = baseH * scale
  const maxOffsetX = (drawW - width) / 2
  const x = (width - drawW) / 2 - maxOffsetX * dx
  const y = (height - drawH) / 2

  ctx.drawImage(img, x, y, drawW, drawH)
}

function roundRectPath(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  if (typeof ctx.roundRect === 'function') {
    ctx.beginPath()
    ctx.roundRect(x, y, w, h, r)
    return
  }
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function drawCaption(ctx: CanvasRenderingContext2D, caption: string, width: number, height: number) {
  const text = caption.trim()
  if (!text) return

  const fontSize = Math.round(width * 0.06)
  ctx.font = `700 ${fontSize}px system-ui, -apple-system, "Segoe UI", sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  const maxWidth = width * 0.84
  const words = text.split(/\s+/)
  const lines: string[] = []
  let line = ''
  for (const word of words) {
    const test = line ? `${line} ${word}` : word
    if (line && ctx.measureText(test).width > maxWidth) {
      lines.push(line)
      line = word
    } else {
      line = test
    }
  }
  if (line) lines.push(line)

  const lineHeight = fontSize * 1.3
  const paddingY = fontSize * 0.55
  const paddingX = width * 0.05
  const boxHeight = lines.length * lineHeight + paddingY * 2
  const boxBottom = height * 0.8
  const boxTop = boxBottom - boxHeight
  const boxWidth = width - paddingX * 2

  ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
  roundRectPath(ctx, paddingX, boxTop, boxWidth, boxHeight, fontSize * 0.4)
  ctx.fill()

  ctx.fillStyle = '#ffffff'
  lines.forEach((l, i) => {
    const ly = boxTop + paddingY + lineHeight * i + lineHeight / 2
    ctx.fillText(l, width / 2, ly)
  })
}

function pickMimeType(): string {
  const candidates = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm']
  return candidates.find((c) => MediaRecorder.isTypeSupported(c)) ?? 'video/webm'
}

export function isVideoRenderSupported(): boolean {
  return (
    typeof MediaRecorder !== 'undefined' &&
    typeof HTMLCanvasElement !== 'undefined' &&
    typeof HTMLCanvasElement.prototype.captureStream === 'function'
  )
}

export async function renderVideo(
  { slides, width, height, fps, audioFile, onProgress }: RenderOptions,
  canvas: HTMLCanvasElement,
): Promise<Blob> {
  if (slides.length === 0) throw new Error('Geen foto\'s om te renderen.')

  const context2d = canvas.getContext('2d')
  if (!context2d) throw new Error('Canvas wordt niet ondersteund.')
  const ctx: CanvasRenderingContext2D = context2d

  canvas.width = width
  canvas.height = height

  const totalMs = slides.reduce((sum, s) => sum + s.durationMs, 0)
  const videoStream = canvas.captureStream(fps)
  const tracks: MediaStreamTrack[] = [...videoStream.getVideoTracks()]

  let audioCtx: AudioContext | undefined
  let audioEl: HTMLAudioElement | undefined
  if (audioFile) {
    audioEl = new Audio(URL.createObjectURL(audioFile))
    audioEl.loop = true
    audioCtx = new AudioContext()
    const source = audioCtx.createMediaElementSource(audioEl)
    const dest = audioCtx.createMediaStreamDestination()
    source.connect(dest)
    tracks.push(...dest.stream.getAudioTracks())
    try {
      await audioEl.play()
    } catch {
      // autoplay geblokkeerd — video wordt dan zonder geluid opgenomen
    }
  }

  const stream = new MediaStream(tracks)
  const mimeType = pickMimeType()
  const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 8_000_000 })
  const chunks: Blob[] = []
  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data)
  }

  const stopped = new Promise<Blob>((resolve) => {
    recorder.onstop = () => resolve(new Blob(chunks, { type: mimeType }))
  })

  recorder.start()
  const start = performance.now()

  await new Promise<void>((resolve) => {
    function tick(now: number) {
      const elapsed = now - start
      onProgress(Math.min(1, elapsed / totalMs))
      if (elapsed >= totalMs) {
        resolve()
        return
      }

      let acc = 0
      let active = slides[0]
      let localT = 0
      for (const s of slides) {
        if (elapsed < acc + s.durationMs) {
          active = s
          localT = (elapsed - acc) / s.durationMs
          break
        }
        acc += s.durationMs
      }

      ctx.fillStyle = '#000'
      ctx.fillRect(0, 0, width, height)
      drawSlideFrame(ctx, active, localT, width, height)
      drawCaption(ctx, active.caption, width, height)

      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  })

  recorder.stop()
  const blob = await stopped

  audioEl?.pause()
  audioCtx?.close()
  tracks.forEach((t) => t.stop())

  return blob
}
