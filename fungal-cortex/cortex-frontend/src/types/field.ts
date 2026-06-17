/** Stigmergy Field types. */

export interface FieldPoint {
  x: number;
  y: number;
  signal: number;
  nutrient: number;
  damage: number;
  temperature: number;
}

export interface FieldGradient {
  x: number;
  y: number;
  dx: number;
  dy: number;
  magnitude: number;
}

export interface FieldTexture {
  width: number;
  height: number;
  rgba: Uint8Array;
}

export interface FieldAgentPosition {
  agent_id: string;
  x: number;
  y: number;
  specialty: string;
  trail: [number, number][];
}

export interface FieldSettings {
  diffusion_signal: number;
  diffusion_nutrient: number;
  diffusion_damage: number;
  decay_signal: number;
  decay_nutrient: number;
  decay_damage: number;
  convection_x: number;
  convection_y: number;
  agent_deposit_rate: number;
}

export type FieldLayer = "signal" | "nutrient" | "damage" | "temperature";
