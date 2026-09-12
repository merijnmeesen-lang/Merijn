// Wraps the optional `window.claude` artifact runtime (see the `sample`
// capability). Only present when this app is running inside a published
// Claude artifact preview — resolves to null everywhere else (a normal
// deployed site), so callers must treat null as "feature unavailable".
export interface SampleResult {
  text: string
  truncated: boolean
}

export interface SampleFn {
  (input: string, options?: SampleOptions): Promise<SampleResult>
  json<T = unknown>(input: string, options?: SampleOptions): Promise<T>
  limits(): Promise<{ maxPromptBytes: number; images?: { maxCount: number; maxInputBytes: number; mediaTypes: string[] } }>
}

interface SampleOptions {
  images?: Blob | Blob[] | FileList
  modelTier?: 'default' | 'complex' | 'quick'
  cache?: boolean
}

interface ClaudeWindow {
  claude?: {
    use(name: 'sample'): Promise<SampleFn | null>
  }
}

export async function getClaudeSample(): Promise<SampleFn | null> {
  try {
    const claude = (window as unknown as ClaudeWindow).claude
    if (!claude) return null
    return await claude.use('sample')
  } catch {
    return null
  }
}
