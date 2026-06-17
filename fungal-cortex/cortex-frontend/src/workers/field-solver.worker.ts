/** Web Worker: PDE Stigmergy field solver using spectral method. */

interface FieldParams {
  width: number;
  height: number;
  dx: number;
  dt: number;
  diffusion_signal: number;
  diffusion_nutrient: number;
  diffusion_damage: number;
  decay_signal: number;
  decay_nutrient: number;
  decay_damage: number;
  convection_x: number;
  convection_y: number;
}

interface AgentDeposit {
  x: number;
  y: number;
  signal: number;
  nutrient: number;
}

interface SolverMessage {
  type: "step";
  params: FieldParams;
  signal: Float64Array;
  nutrient: Float64Array;
  damage: Float64Array;
  agents: AgentDeposit[];
}

interface SolverResult {
  type: "field_result";
  signal: Float64Array;
  nutrient: Float64Array;
  damage: Float64Array;
  temperature: Float64Array;
}

function laplacian(field: Float64Array, width: number, height: number, dx: number): Float64Array {
  const result = new Float64Array(width * height);
  const dx2 = dx * dx;
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = y * width + x;
      result[idx] =
        (field[idx - 1] + field[idx + 1] + field[idx - width] + field[idx + width] -
          4 * field[idx]) / dx2;
    }
  }
  return result;
}

function gradientX(field: Float64Array, width: number, _height: number, dx: number): Float64Array {
  const result = new Float64Array(field.length);
  for (let i = 0; i < field.length; i++) {
    const x = i % width;
    if (x < width - 1) result[i] = (field[i + 1] - field[i]) / dx;
  }
  return result;
}

function gradientY(field: Float64Array, width: number, _height: number, dy: number): Float64Array {
  const result = new Float64Array(field.length);
  for (let i = 0; i < field.length - width; i++) {
    result[i] = (field[i + width] - field[i]) / dy;
  }
  return result;
}

function applyDeposits(
  signal: Float64Array,
  nutrient: Float64Array,
  agents: AgentDeposit[],
  width: number,
  rate: number
): void {
  for (const agent of agents) {
    const ix = Math.round(agent.x);
    const iy = Math.round(agent.y);
    if (ix >= 0 && ix < width && iy >= 0) {
      const idx = iy * width + ix;
      if (idx < signal.length) {
        signal[idx] += agent.signal * rate;
        nutrient[idx] += agent.nutrient * rate;
      }
    }
  }
}

self.onmessage = (e: MessageEvent<SolverMessage>) => {
  if (e.data.type !== "step") return;

  const { params, signal, nutrient, damage, agents } = e.data;
  const { width, height, dx, dt } = params;

  // Reaction-diffusion-convection step
  const lapS = laplacian(signal, width, height, dx);
  const lapN = laplacian(nutrient, width, height, dx);
  const lapD = laplacian(damage, width, height, dx);
  const gradSx = gradientX(signal, width, height, dx);
  const gradSy = gradientY(signal, width, height, dx);

  const newSignal = new Float64Array(width * height);
  const newNutrient = new Float64Array(width * height);
  const newDamage = new Float64Array(width * height);
  const temperature = new Float64Array(width * height);

  for (let i = 0; i < width * height; i++) {
    // dS/dt = D_s ∇²S - γ_s S + convection
    newSignal[i] = signal[i] + dt * (
      params.diffusion_signal * lapS[i] -
      params.decay_signal * signal[i] -
      params.convection_x * gradSx[i] -
      params.convection_y * gradSy[i]
    );

    // dN/dt = D_n ∇²N - γ_n N (nutrient consumed by agents)
    newNutrient[i] = nutrient[i] + dt * (
      params.diffusion_nutrient * lapN[i] -
      params.decay_nutrient * nutrient[i]
    );

    // dD/dt = D_d ∇²D - γ_d D (damage slowly decays)
    newDamage[i] = damage[i] + dt * (
      params.diffusion_damage * lapD[i] -
      params.decay_damage * damage[i]
    );

    // Temperature = local kinetic energy proxy
    temperature[i] = Math.abs(newSignal[i] - signal[i]) / dt;
  }

  // Apply agent deposits
  applyDeposits(newSignal, newNutrient, agents, width, params.diffusion_signal);

  // Clamp to valid range
  for (let i = 0; i < width * height; i++) {
    newSignal[i] = Math.max(0, Math.min(1, newSignal[i]));
    newNutrient[i] = Math.max(0, Math.min(1, newNutrient[i]));
    newDamage[i] = Math.max(0, Math.min(1, newDamage[i]));
    temperature[i] = Math.min(1, temperature[i] * 10);
  }

  const result: SolverResult = {
    type: "field_result",
    signal: newSignal,
    nutrient: newNutrient,
    damage: newDamage,
    temperature,
  };
  self.postMessage(result, { transfer: [newSignal.buffer, newNutrient.buffer, newDamage.buffer, temperature.buffer] });
};

export {};
