export interface ReactionCreate {
  name: string;
  reactants: string[];
  products: string[];
  temperature?: number;
  temperature_unit?: string;
  pressure?: number;
  pressure_unit?: string;
  solvent?: string;
  description?: string;
}

export interface ReactionResponse {
  id: string;
  name: string;
  reactants: string[];
  products: string[];
  temperature: number;
  temperature_unit: string;
  pressure: number;
  pressure_unit: string;
  solvent: string;
  description?: string | null;
  created_at: string;
}

export interface CatalystResponse {
  id: string;
  reaction_id: string;
  name: string;
  composition: string;
  structure_data?: Record<string, any> | null;
  source: string;
  confidence: number;
  description?: string | null;
  created_at: string;
}

export interface CatalystListResponse {
  known: CatalystResponse[];
  generated: CatalystResponse[];
  total_count: number;
}

export interface GeneratedCatalystSchema {
  name: string;
  composition: string;
  modification: string;
  confidence: number;
  predicted_improvement: number;
}

export interface PredictionRankingResponse {
  catalyst_id: string;
  catalyst_name: string;
  composition: string;
  source: string;
  activity: number;
  selectivity: number;
  stability: number;
  combined_score: number;
  rank: number;
  uncertainty: number;
}
