export interface Level {
  id: string;
  number: number;
  title: string;
  blurb: string;
  description?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

/** Backend traces are free-form per level; Inspector normalizes common fields. */
export type TraceData = Record<string, any>;

export interface ChatResponse {
  answer: string;
  citations?: string[];
  level?: string;
  trace?: TraceData;
}

export interface CorpusDocument {
  id: string;
  name: string;
  path?: string;
  bytes: number;
  chars: number;
  chunk_count: number;
  preview: string;
  uploaded: boolean;
}

export interface CorpusDocumentDetail extends Omit<CorpusDocument, 'preview' | 'path'> {
  content: string;
  chunks: Array<{
    id?: string;
    heading?: string;
    text: string;
    method?: string;
    size?: number;
  }>;
}

export interface SecurityTier {
  id: string;
  name: string;
  description: string;
}

export interface EvalResult {
  id: string;
  level: string;
  question: string;
  expectedAnswer: string;
  actualAnswer: string;
  score: number;
  metrics: {
    accuracy: number;
    relevance: number;
    completeness: number;
  };
  timestamp: number;
}
